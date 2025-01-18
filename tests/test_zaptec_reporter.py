import openpyxl
import os
import pytest
import responses
import yaml
from datetime import datetime
from unittest.mock import patch


import zaptec_reporter as zap


class TestParseDateArg:
    def test_year(self):
        assert datetime.fromisoformat("2024-01-01"), zap.parse_date_arg("2024")

    def test_month(self):
        assert datetime.fromisoformat("2024-05-01"), zap.parse_date_arg("2024-5")

    def test_day(self):
        assert datetime.fromisoformat("2024-05-30"), zap.parse_date_arg("2024-5-30")

    def test_year_relative(self):
        assert datetime(datetime.now().year - 1, 1, 1) == zap.parse_date_arg("last year")

    def test_value_error(self):
        with pytest.raises(ValueError):
            zap.parse_date_arg("zap")


class TestReporter:
    @pytest.fixture
    def fake_filesystem(fs):  # pylint:disable=invalid-name
        """Variable name 'fs' causes a pylint warning. Provide a longer name
        acceptable to pylint for use in tests.
        """
        yield fs

    @responses.activate
    @patch("zaptec_reporter.reporter.smtplib.SMTP")
    def test_generate_usage_report(self, mock_smtp, fs):
        ACCESS_TOKEN = "blablaiamatokenblablabla"
        INSTALLATION_IDS = ["aaaa-aaa-aaaa", "bbbb-bbb-bbbb"]
        FILEPATH = "/tmp/report.xlsx"
        EMAIL_FILEPATH = "/tmp/email_config.yml"

        # First request/response.
        response_json = {
            "InstallationName": "Installation A (north)",
            "InstallationAddress": "Gatan",
            "InstallationZipCode": "44100",
            "InstallationCity": "Alingsås",
            "InstallationTimeZone": "Central European Standard Time",
            "GroupedBy": "Charger",
            "Fromdate": "2024-12-01T00:00:00",
            "Enddate": "2025-01-01T00:00:00",
            "totalUserChargerReportModel": [
                {
                    "GroupAsString": "NP1",
                    "TotalChargeSessionCount": 11,
                    "TotalChargeSessionEnergy": 272.797,
                    "TotalChargeSessionDuration": 279.0285275,
                }
            ],
        }

        # Verify authorization request and mock response.
        responses.post(
            "https://api.zaptec.com/api/chargehistory/installationreport",
            json=response_json,
            match=[
                responses.matchers.json_params_matcher(
                    {
                        "fromDate": "2024-12-01T00:00:00",
                        "endDate": "2025-01-01T00:00:00",
                        "installationId": INSTALLATION_IDS[0],
                        "groupBy": 1,
                    }
                )
            ],
        )

        # Second request/response.
        response_json = {
            "InstallationName": "Installation B (west)",
            "InstallationAddress": "Gatan",
            "InstallationZipCode": "44100",
            "InstallationCity": "Alingsås",
            "InstallationTimeZone": "Central European Standard Time",
            "GroupedBy": "Charger",
            "Fromdate": "2024-12-01T00:00:00",
            "Enddate": "2025-01-01T00:00:00",
            "totalUserChargerReportModel": [
                {
                    "GroupAsString": "VP1",
                    "TotalChargeSessionCount": 2,
                    "TotalChargeSessionEnergy": 43.114,
                    "TotalChargeSessionDuration": 10.500001,
                }
            ],
        }

        # Verify authorization request and mock response.
        responses.post(
            "https://api.zaptec.com/api/chargehistory/installationreport",
            json=response_json,
            match=[
                responses.matchers.json_params_matcher(
                    {
                        "fromDate": "2024-12-01T00:00:00",
                        "endDate": "2025-01-01T00:00:00",
                        "installationId": INSTALLATION_IDS[1],
                        "groupBy": 1,
                    }
                )
            ],
        )

        # Prepare email configuration file.
        with open(EMAIL_FILEPATH, "w") as f:
            html = (
                '<html lang="en">'
                "  <head>"
                "    <title>Charge report</title>"
                "    <style>"
                "      table {"
                "        border-collapse: collapse;"
                "      }"
                "      th, td {"
                "        text-align: left;"
                "        padding: 8px;"
                "        border-bottom: 1px solid #ddd;"
                "      }"
                "      th {"
                "        background-color: #04AA6D;"
                "        color: white;"
                "      }"
                "    </style>"
                "  </head>"
                "  <body>"
                "    <p>"
                '      See the attached Zaptec charge report for {{ Metadata.From.strftime("%Y-%m-%d") }}.'
                "    </p>"
                "    <table>"
                "      <tbody><tr>"
                '      <th scope="col">Charger</th>'
                '      <th scope="col">Energy (kWh)</th>'
                "      </tr></tbody>"
                "      <tbody>"
                "      {% for item in Usage %}"
                "      <tr>"
                "        <td><b>{{ item.Charger }}</b></td>"
                "        <td>{{ item.Energy|round(2) }}</td>"
                "      </tr>"
                "      {% endfor %}"
                "      </tbody>"
                "    </table>"
                "  </body>"
                "</html>"
            )
            yaml.dump(
                {
                    "server": {
                        "address": "localhost",
                        "username": "nikola",
                        "password": "Zaptec!23",
                        "port": 2525,
                        "encryption": "disabled",
                    },
                    "subject": "Zaptec charge report for {{ Metadata.From.strftime('%Y-%m')}}",
                    "filename": "charger_report_{{ Metadata.From.strftime('%Y_%m')}}",
                    "from": {
                        "name": "Zaptec Reporter",
                        "address": "nikola.tesla@mail.com",
                    },
                    "to": ["thomas.edison@mail.com", "joseph.swan@mail.com"],
                    "text": "See the attached Zaptec charge report covering {{ Metadata.From.strftime('%Y-%m-%d') }} "
                    "to {{ Metadata.To.strftime('%Y-%m-%d')}}.",
                    "html": html,
                },
                f,
            )

        # Trigger request.
        zap.main(
            (
                f"-v -p {ACCESS_TOKEN} report -x {FILEPATH} -e {EMAIL_FILEPATH} "
                f"--from-date 2024-12-01 --to-date 2025-01-01 "
                f"{INSTALLATION_IDS[0]} {INSTALLATION_IDS[1]}"
            ).split()
        )

        # Verify that a file was written.
        assert os.path.exists(FILEPATH)

        # Verify some of the file contents.
        workbook = openpyxl.load_workbook(FILEPATH)
        worksheet = workbook.worksheets[0]

        assert worksheet["B2"].value == datetime.fromisoformat("2024-12-01")  # From
        assert worksheet["B3"].value == datetime.fromisoformat("2025-01-01")  # To

        assert worksheet["A7"].value == "NP1"
        assert worksheet["B7"].value == 272.8
        assert worksheet["C7"].value == "11 days 15:01:43"
        assert worksheet["D7"].value == 11
        assert worksheet["E7"].value == "Installation A (north)"

        assert worksheet["A8"].value == "VP1"
        assert worksheet["B8"].value == 43.11
        assert worksheet["C8"].value == "0 days 10:30:00"
        assert worksheet["D8"].value == 2
        assert worksheet["E8"].value == "Installation B (west)"

        # Verify that an email was sent.
        # Note that printing mock calls may help debugging: print(mock_smtp.mock_calls)
        assert mock_smtp.return_value.__enter__.return_value.send_message.call_count == 1

        # Verify some of the email contents.
        sent_msg = mock_smtp.return_value.__enter__.return_value.send_message.call_args.args[0]
        assert sent_msg["Subject"] == "Zaptec charge report for 2024-12"
        assert sent_msg["From"] == "Zaptec Reporter <nikola.tesla@mail.com>"
        assert sent_msg["To"] == "thomas.edison@mail.com, joseph.swan@mail.com"
