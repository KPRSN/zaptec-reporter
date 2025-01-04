import argparse
import dateparser
import io
import logging
import pandas as pd
import pathlib
import sys
from datetime import datetime

from zaptec_reporter import api as zapi


def parse_date_arg(date):
    ddp = dateparser.DateDataParser(settings={"PREFER_DAY_OF_MONTH": "first", "RETURN_TIME_AS_PERIOD": True})
    date_data = ddp.get_date_data(date)
    date_obj = date_data.date_obj

    if date_obj is None:
        raise ValueError("{date} is not a valid date.")

    # Truncate specified date down to beginning of period.
    if date_data.period == "year":
        date_obj = date_obj.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    elif date_data.period == "month":
        date_obj = date_obj.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        date_obj = date_obj.replace(hour=0, minute=0, second=0, microsecond=0)

    return date_obj


def generate_usage_report(api, installation_ids, date_from, date_to, group_by=zapi.InstallationGroupBy.CHARGER):
    installation_reports = [
        api.fetch_installation_report(installation_id, date_from.isoformat(), date_to.isoformat())
        for installation_id in installation_ids
    ]

    # Aggregate usage data in human readable format.
    data = []
    for report in installation_reports:
        for entry in report["totalUserChargerReportModel"]:
            data.append(
                {
                    report["GroupedBy"]: entry["GroupAsString"],
                    "Energy": entry["TotalChargeSessionEnergy"],
                    "Duration": str(pd.Timedelta(hours=entry["TotalChargeSessionDuration"]).round("s")),
                    "Sessions": entry["TotalChargeSessionCount"],
                    "Installation": report["InstallationName"],
                }
            )

    # Convert usage data to a data frame.
    df = pd.DataFrame(data)

    # Create a data frame with metadata.
    report = installation_reports[0]
    df_meta = pd.DataFrame(
        [
            ("Generated", datetime.now()),
            ("From", datetime.fromisoformat(report["Fromdate"])),
            ("To", datetime.fromisoformat(report["Enddate"])),
            ("Timezone", report["InstallationTimeZone"]),
        ]
    )

    # Write usage report as Excel data to an in-memory buffer.
    sheet_name = "Report"
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter", datetime_format="yyyy-mm-dd hh:mm:ss") as writer:
        df_meta.to_excel(writer, sheet_name=sheet_name, index=False, header=False)
        df.to_excel(
            writer,
            sheet_name=sheet_name,
            startrow=len(df_meta) + 1,
            index=False,
            float_format="%0.1f",
        )

        # Autofit columns.
        worksheet = writer.sheets[sheet_name]
        worksheet.autofit()

    return buffer


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
    parser_report.add_argument("-x", "--excelout", help="Excel output file.", required=True)
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

    # Initialize API (and authorize if needed).
    api = zapi.ZaptecAPI(args.password)
    if args.username is not None:
        api.authorize(args.username, args.password)

    # Run command.
    if "installations" == args.action:
        logging.info(api.fetch_installations())
    elif "report" == args.action:
        buffer = generate_usage_report(api, args.installations, args.from_date, args.to_date)
        pathlib.Path(args.excelout).write_bytes(buffer.getbuffer().tobytes())
