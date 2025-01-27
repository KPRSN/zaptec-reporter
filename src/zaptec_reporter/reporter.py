import argparse
import dateparser
import io
import logging
import pandas as pd
import pathlib
import sys
import yaml
import jinja2 as jinja
import smtplib
from datetime import datetime
from email_validator import validate_email
from email.message import EmailMessage
from email.utils import formataddr
from enum import StrEnum

from zaptec_reporter import api as zapi


class EmailEncryption(StrEnum):
    DISABLED = "disabled"
    EXPLICIT = "explicit"
    IMPLICIT = "implicit"


class Email:
    def __init__(
        self,
        server_address,
        server_port,
        encryption,
        username,
        password,
        subject,
        from_email,
        to_emails,
        text,
        html,
        filename,
    ):
        self.server_address = server_address
        self.server_port = server_port
        self.encryption = encryption
        self.username = username
        self.password = password
        self.from_email = from_email
        self.to_emails = to_emails
        self.subject = subject
        self.text = text
        self.html = html
        self.filename = filename

    def send(self, values, buffer):
        msg = EmailMessage()
        msg["Subject"] = jinja.Template(self.subject).render(values)
        msg["From"] = formataddr(self.from_email)
        msg["To"] = ", ".join(self.to_emails)

        # Add body.
        if self.text is not None:
            msg.set_content(jinja.Template(self.text).render(values))

        if self.html is not None:
            msg.add_alternative(jinja.Template(self.html).render(values), subtype="html")

        # Add charge report attachment.
        msg.add_attachment(
            buffer.getbuffer().tobytes(),
            maintype="application",
            subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=jinja.Template(self.filename).render(values),
        )

        # Send using the perfect level of encryption.
        logging.info(f"Sending email to {len(self.to_emails)} recipients.")
        if self.encryption == EmailEncryption.IMPLICIT:
            with smtplib.SMTP_SSL(host=self.server_address, port=self.server_port) as server:
                server.login(self.username, self.password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(host=self.server_address, port=self.server_port) as server:
                if self.encryption == EmailEncryption.EXPLICIT:
                    server.starttls()

                server.login(self.username, self.password)
                server.send_message(msg)


def parse_date_arg(date):
    ddp = dateparser.DateDataParser(settings={"PREFER_DAY_OF_MONTH": "first", "RETURN_TIME_AS_PERIOD": True})
    date_data = ddp.get_date_data(date)
    date_obj = date_data.date_obj

    if date_obj is None:
        raise ValueError(f"{date} is not a valid date.")

    # Truncate specified date down to beginning of period.
    if date_data.period == "year":
        date_obj = date_obj.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    elif date_data.period == "month":
        date_obj = date_obj.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        date_obj = date_obj.replace(hour=0, minute=0, second=0, microsecond=0)

    return date_obj


def create_excel_usage_report(data):
    sheet_name = "Report"
    df_usage = pd.DataFrame(data["Usage"])
    df_meta = pd.DataFrame([(key, value) for key, value in data["Metadata"].items()])

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter", datetime_format="yyyy-mm-dd hh:mm:ss") as writer:
        df_meta.to_excel(writer, sheet_name=sheet_name, index=False, header=False)
        df_usage.to_excel(
            writer,
            sheet_name=sheet_name,
            startrow=len(df_meta) + 1,
            index=False,
            float_format="%.2f",
        )

        # Autofit columns.
        worksheet = writer.sheets[sheet_name]
        worksheet.autofit()

    return buffer


def fetch_usage_data(api, installation_ids, date_from, date_to, group_by=zapi.InstallationGroupBy.CHARGER):
    # Fetch reports from all installations.
    installation_reports = [
        api.fetch_installation_report(installation_id, date_from.isoformat(), date_to.isoformat())
        for installation_id in installation_ids
    ]

    # Aggregate usage data in human readable format.
    usage = []
    for report in installation_reports:
        for entry in report["totalUserChargerReportModel"]:
            usage.append(
                {
                    report["GroupedBy"]: entry["GroupAsString"],
                    "Energy": entry["TotalChargeSessionEnergy"],
                    "Duration": str(pd.Timedelta(hours=entry["TotalChargeSessionDuration"]).round("s")),
                    "Sessions": entry["TotalChargeSessionCount"],
                    "Installation": report["InstallationName"],
                }
            )

    # Assemble metadata.
    report = installation_reports[0]
    metadata = {
        "Generated": datetime.now(),
        "From": datetime.fromisoformat(report["Fromdate"]),
        "To": datetime.fromisoformat(report["Enddate"]),
        "Timezone": report["InstallationTimeZone"],
    }

    return {"Usage": usage, "Metadata": metadata}


def report(api, installations, from_date, to_date, excel_path, email):
    usage_data = fetch_usage_data(api, installations, from_date, to_date)
    buffer = create_excel_usage_report(usage_data)

    if excel_path is not None:
        # Write usage report to file.
        path = jinja.Template(excel_path).render(usage_data)
        logging.info(f"Writing usage report to file {path}.")
        pathlib.Path(path).write_bytes(buffer.getbuffer().tobytes())

    if email is not None:
        email.send(usage_data, buffer)


def parse_email_config(email_path):
    # Read email config yaml file.
    with open(email_path, "r") as f:
        config = yaml.load(f, Loader=yaml.Loader)

    # Validate that server configuration is set.
    server_config = config["server"]
    server_address = server_config["address"]
    server_port = server_config["port"]
    username = server_config["username"]
    password = server_config["password"]

    # Validate and parse encryption.
    encryption = EmailEncryption(server_config["encryption"])

    # Validate source email.
    from_name = config["from"]["name"]
    from_email = config["from"]["address"]
    validate_email(from_email, check_deliverability=False)

    # Validate destination email(s).
    to_emails = config["to"] if isinstance(config["to"], list) else [config["to"]]
    for email in to_emails:
        validate_email(email, check_deliverability=False)

    # Validate that subject and filename is set.
    subject = config["subject"]
    filename = config["filename"]

    # A brief body check.
    text = config.get("text", None)
    html = config.get("html", None)
    if text is None and html is None:
        logging.warning("Email template does not contain a body.")

    return Email(
        server_address,
        server_port,
        encryption,
        username,
        password,
        subject,
        (from_name, from_email),
        to_emails,
        text,
        html,
        filename,
    )


def main(argv=sys.argv[1:]) -> None:
    # Setup argument parser.
    parser = argparse.ArgumentParser(description="Generate usage reports from Zaptec chargers.")
    subparsers = parser.add_subparsers(dest="action", help="Action to take.")

    # Global arguments.
    parser.add_argument(
        "-v",
        "--verbose",
        help="Enable verbose logging.",
        action="store_const",
        const=logging.DEBUG,
        default=logging.INFO,
    )
    parser.add_argument("-d", "--dry-run", help="Print command arguments to log.", action="store_true")
    parser.add_argument("-u", "--username", help="Username to access Zaptec Cloud.")
    parser.add_argument(
        "-p",
        "--password",
        help="Password to access Zaptec Cloud."
        " If no username is provided then the password will be treated as an API access token.",
        required=True,
    )

    # List installations.
    subparsers.add_parser("installations", help="List Zaptec installations.")

    # Generate usage report.
    parser_report = subparsers.add_parser("report", help="Generate usage report.")
    parser_report.add_argument(
        "--from-date",
        help='Start date to cover in the report. Example: "2024-10" or "last month".'
        "Defaults to beginning of last month.",
        type=parse_date_arg,
        default=parse_date_arg("last month"),
    )
    parser_report.add_argument(
        "--to-date",
        help='End date to cover in the report. Example: "2025" or "next year".' "Defaults to beginning of this month.",
        type=parse_date_arg,
        default=parse_date_arg("this month"),
    )
    parser_report.add_argument("-x", "--excelout", help="Excel output file.")
    parser_report.add_argument("-e", "--email", help="Email YAML configuration file.")
    parser_report.add_argument(
        "installations",
        help="IDs for the installations to collect usage from.",
        nargs="+",
    )

    # Parse arguments.
    args = parser.parse_args(argv)

    # Configure logging.
    logging.basicConfig(
        stream=sys.stdout,
        level=args.verbose,
        format="[%(asctime)s %(levelname)s] %(message)s",
    )

    # Parse email configuration.
    if args.email is not None:
        email = parse_email_config(args.email)

    # Dry run.
    if args.dry_run:
        logging.info(sys.argv)
        logging.debug(args)
        sys.exit(0)

    # Initialize API (and authorize if needed).
    api = zapi.ZaptecAPI(args.password)
    if args.username is not None:
        api.authorize(args.username, args.password)

    # Run command.
    if "installations" == args.action:
        logging.info(api.fetch_installations())
    elif "report" == args.action:
        report(api, args.installations, args.from_date, args.to_date, args.excelout, email)
