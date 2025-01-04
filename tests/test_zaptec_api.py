import responses

from zaptec_reporter import api as zapi


class TestAPI:
    @responses.activate
    def test_authorization(self):
        ACCESS_TOKEN = "blablaiamatokenblablabla"
        USERNAME = "username"
        PASSWORD = "password"

        # Verify authorization request and mock response.
        responses.post(
            "https://api.zaptec.com/oauth/token",
            json={
                "access_token": ACCESS_TOKEN,
                "token_type": "Bearer",
                "expires_in": 86400,
            },
            match=[
                responses.matchers.urlencoded_params_matcher(
                    {
                        "grant_type": "password",
                        "username": USERNAME,
                        "password": PASSWORD,
                    }
                )
            ],
        )

        api = zapi.ZaptecAPI()

        # Make sure there is no access token before initializing.
        assert api.access_token is None
        assert api.auth_header() is None

        # Trigger authorization request.
        api.authorize(USERNAME, PASSWORD)

        # Verify that access token is correctly set.
        assert ACCESS_TOKEN == api.access_token
        assert f"Bearer {ACCESS_TOKEN}" == api.auth_header()

    @responses.activate
    def test_installations(self):
        ACCESS_TOKEN = "blablaiamatokenblablabla"

        params = {
            "Roles": zapi.UserRole.OWNER.value,
            "InstallationType": zapi.InstallationType.PRO.value,
            "ReturnIdNameOnly": "true",
            "SortDescending": "false",
            "IncludeDisabled": "false",
        }

        response_json = {
            "Pages": 1,
            "Data": [
                {
                    "Id": "aaaa-aaa-aaaa",
                    "Name": "Installation A (north)",
                    "UpdatedOn": "2024-09-27T08:13:51.167",
                    "CurrentUserRoles": 2,
                },
                {
                    "Id": "bbbb-bbb-bbbb",
                    "Name": "Installation B (west)",
                    "UpdatedOn": "2024-09-27T08:13:38.597",
                    "CurrentUserRoles": 2,
                },
            ],
        }

        # Verify request and mock response.
        responses.get(
            "https://api.zaptec.com/api/installation",
            json=response_json,
            match=[responses.matchers.query_param_matcher(params)],
        )

        # Trigger request.
        api = zapi.ZaptecAPI(ACCESS_TOKEN)
        installations = api.fetch_installations()

        # Verify that we got all expected installations.
        assert "aaaa-aaa-aaaa" == installations["Installation A (north)"]
        assert "bbbb-bbb-bbbb" == installations["Installation B (west)"]
        assert 2 == len(installations)

    @responses.activate
    def test_installation_report(self):
        ACCESS_TOKEN = "blablaiamatokenblablabla"
        INSTALLATION_ID = "aaaa-aaa-aaaa"

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
                },
                {
                    "GroupAsString": "NP2",
                    "TotalChargeSessionCount": 1,
                    "TotalChargeSessionEnergy": 43.114,
                    "TotalChargeSessionDuration": 31.057044444444443,
                },
                {
                    "GroupAsString": "NP3",
                    "TotalChargeSessionCount": 8,
                    "TotalChargeSessionEnergy": 289.603,
                    "TotalChargeSessionDuration": 99.43554916666665,
                },
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
                        "installationId": INSTALLATION_ID,
                        "groupBy": 1,
                    }
                )
            ],
        )

        # Trigger request.
        api = zapi.ZaptecAPI(ACCESS_TOKEN)
        report = api.fetch_installation_report(INSTALLATION_ID, "2024-12-01T00:00:00", "2025-01-01T00:00:00")

        # Sanity check that we got the JSON response back.
        assert "Installation A (north)" == report["InstallationName"]
