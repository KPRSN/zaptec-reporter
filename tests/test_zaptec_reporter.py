import unittest
import responses
from datetime import datetime

import zaptec_reporter as zap


class TestParseDateArg(unittest.TestCase):
    def test_year(self):
        self.assertEqual(datetime.fromisoformat("2024-01-01"), zap.parse_date_arg("2024"))

    def test_month(self):
        self.assertEqual(datetime.fromisoformat("2024-05-01"), zap.parse_date_arg("2024-5"))

    def test_day(self):
        self.assertEqual(datetime.fromisoformat("2024-05-30"), zap.parse_date_arg("2024-5-30"))

    def test_year_relative(self):
        self.assertEqual(datetime(datetime.now().year - 1, 1, 1), zap.parse_date_arg("last year"))

    def test_value_error(self):
        with self.assertRaises(ValueError):
            zap.parse_date_arg("zap")


class TestReporter(unittest.TestCase):
    @responses.activate
    def test_generate_usage_report(self):
        ACCESS_TOKEN = "blablaiamatokenblablabla"
        INSTALLATION_IDS = ["aaaa-aaa-aaaa", "bbbb-bbb-bbbb"]

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
                        "toDate": "2025-01-01T00:00:00",
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

        # Trigger request.
        api = zap.api.ZaptecAPI(ACCESS_TOKEN)
        buffer = zap.generate_usage_report(
            api,
            INSTALLATION_IDS,
            datetime.fromisoformat("2024-12-01"),
            datetime.fromisoformat("2025-01-01"),
        )
