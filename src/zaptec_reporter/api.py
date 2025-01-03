import logging
import requests
from enum import Flag, auto


class UserRole(Flag):
    NONE = 0
    USER = auto()
    OWNER = auto()
    MAINTAINER = auto()
    ADMINISTRATOR = auto()
    ONBOARDING = auto()
    DEVICE_ADMINISTRATOR = auto()
    PARTNER_ADMINISTRATOR = auto()
    TECHNICAL = auto()
    INTERNAL_DATA = auto()


class InstallationType(Flag):
    PRO = 0
    SMART = auto()
    OCPP_NATIVE = auto()


class InstallationGroupBy(Flag):
    USER = 0
    CHARGER = auto()
    CHARGE_CARD_NAME = auto()


class ZaptecAPI:
    def __init__(self, access_token=None):
        self.access_token = access_token

    def auth_header(self):
        if self.access_token is None:
            return None

        return f"Bearer {self.access_token}"

    def authorize(self, username, password):
        AUTH_URL = "https://api.zaptec.com/oauth/token"

        # Authorize.
        response = requests.post(
            AUTH_URL,
            data={"grant_type": "password", "username": username, "password": password},
        )
        response.raise_for_status()

        # Read token.
        response_json = response.json()
        self.access_token = response_json["access_token"]

    def fetch_installations(
        self,
        user_role=UserRole.OWNER,
        installation_type=InstallationType.PRO,
        include_disabled=False,
    ):
        INSTALLATIONS_URL = "https://api.zaptec.com/api/installation"
        params = {
            "Roles": user_role.value,
            "InstallationType": installation_type.value,
            "ReturnIdNameOnly": str(True).lower(),
            "SortDescending": str(False).lower(),
            "IncludeDisabled": str(include_disabled).lower(),
        }

        response = requests.get(
            INSTALLATIONS_URL,
            headers={"Authorization": self.auth_header()},
            params=params,
        )
        response.raise_for_status()

        response_json = response.json()
        logging.debug(response_json)

        pages = response_json["Pages"]
        if pages > 1:
            logging.warning(f"Some installations may not be shown (showing page 1 of {pages})")

        return {installation["Name"]: installation["Id"] for installation in response_json["Data"]}

    def fetch_installation_report(self, installation_id, date_from, date_to, group_by=InstallationGroupBy.CHARGER):
        INSTALLATION_REPORT_URL = "https://api.zaptec.com/api/chargehistory/installationreport"
        json = {
            "fromDate": date_from,
            "endDate": date_to,
            "installationId": installation_id,
            "groupBy": group_by.value,
        }

        logging.debug(json)

        response = requests.post(
            INSTALLATION_REPORT_URL,
            headers={"Authorization": self.auth_header()},
            json=json,
        )
        response.raise_for_status()

        response_json = response.json()
        logging.debug(response_json)

        return response_json
