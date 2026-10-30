import json
import logging
import re
from dataclasses import dataclass
from urllib.parse import urlparse

import requests
from django.conf import settings

from integrations.moodle.exceptions import (
    MoodleAuthenticationError,
    MoodleNotConfigured,
    MoodlePermissionError,
    MoodleUnavailable,
)

logger = logging.getLogger("chatbot.moodle")
FUNCTION_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{2,120}$")
# Read-only core candidates only. DMI ICT must verify each name, parameters and
# capabilities in the target site's API docs before adding an operation mapping.
APPROVED_READ_FUNCTIONS = {
    "core_webservice_get_site_info",
    "core_enrol_get_users_courses",
    "core_course_get_contents",
    "mod_assign_get_assignments",
    "mod_assign_get_submission_status",
    "mod_quiz_get_quizzes_by_courses",
    "gradereport_overview_get_course_grades",
}


@dataclass(frozen=True)
class MoodleConfig:
    enabled: bool
    rest_url: str
    service_token: str
    allowed_functions: dict[str, str]
    connect_timeout: float = 3.0
    read_timeout: float = 8.0
    max_retries: int = 1


class MoodleAdapter:
    """Allowlisted, read-only client for Moodle's REST web-service endpoint."""

    def __init__(self, config: MoodleConfig | None = None, session=None):
        if config is None:
            try:
                functions = json.loads(settings.MOODLE_FUNCTIONS_JSON or "{}")
            except (TypeError, json.JSONDecodeError):
                functions = {}
            if not isinstance(functions, dict):
                functions = {}
            config = MoodleConfig(
                enabled=settings.MOODLE_ENABLED,
                rest_url=settings.MOODLE_REST_URL,
                service_token=settings.MOODLE_SERVICE_TOKEN,
                allowed_functions=functions,
                connect_timeout=settings.MOODLE_CONNECT_TIMEOUT,
                read_timeout=settings.MOODLE_READ_TIMEOUT,
                max_retries=settings.MOODLE_MAX_RETRIES,
            )
        self.config = config
        self.session = session or requests.Session()

    def status(self) -> dict:
        valid_url = self._valid_https_url(self.config.rest_url)
        configured = bool(self.config.enabled and valid_url and self.config.service_token and self.config.allowed_functions)
        if not self.config.enabled:
            status = "disabled"
        elif configured:
            status = "configured_unverified"
        else:
            status = "incomplete_configuration"
        return {
            "enabled": self.config.enabled,
            "configured": configured,
            "status": status,
            "allowedOperations": sorted(self.config.allowed_functions.keys()) if self.config.enabled else [],
        }

    @staticmethod
    def _valid_https_url(value: str) -> bool:
        parsed = urlparse(value)
        return parsed.scheme == "https" and bool(parsed.hostname) and not parsed.username and not parsed.password

    def call_read_only(self, operation: str, params: dict | None = None) -> dict | list:
        config = self.config
        if not config.enabled or not config.service_token or not self._valid_https_url(config.rest_url):
            raise MoodleNotConfigured("Moodle integration is disabled or not securely configured.")
        function_name = config.allowed_functions.get(operation)
        if not function_name or not FUNCTION_NAME_RE.fullmatch(function_name):
            raise MoodleNotConfigured("This read-only Moodle operation has not been authorized and configured.")
        if function_name not in APPROVED_READ_FUNCTIONS:
            raise MoodleNotConfigured("Only reviewed, allowlisted read-only Moodle functions can be called.")

        form_data = {
            "wstoken": config.service_token,
            "wsfunction": function_name,
            "moodlewsrestformat": "json",
        }
        for key, value in (params or {}).items():
            if key in {"wstoken", "wsfunction", "moodlewsrestformat"}:
                raise ValueError("Moodle protocol fields cannot be overridden")
            if isinstance(value, (str, int, float, bool)):
                form_data[key] = str(value)
            elif value is not None:
                raise ValueError("Only scalar parameters are currently supported by this adapter")

        attempts = config.max_retries + 1
        for attempt in range(attempts):
            try:
                response = self.session.post(
                    config.rest_url,
                    data=form_data,
                    timeout=(config.connect_timeout, config.read_timeout),
                    verify=True,
                    allow_redirects=False,
                )
                if response.status_code in {401, 403}:
                    raise MoodleAuthenticationError("Moodle rejected the configured service credentials or permissions.")
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, (dict, list)):
                    raise MoodleUnavailable("Moodle returned an unexpected response format.")
                if isinstance(payload, dict) and (payload.get("errorcode") or payload.get("exception")):
                    code = str(payload.get("errorcode", "")).casefold()
                    if "token" in code or "invalidrecord" in code:
                        raise MoodleAuthenticationError("Moodle rejected the configured service credentials.")
                    if "permission" in code or "capability" in code:
                        raise MoodlePermissionError("The configured Moodle service lacks an approved capability.")
                    raise MoodleUnavailable("Moodle could not complete the configured read-only operation.")
                return payload
            except (MoodleAuthenticationError, MoodlePermissionError, MoodleNotConfigured):
                raise
            except requests.Timeout as exc:
                if attempt + 1 >= attempts:
                    logger.warning("Moodle read-only request timed out; secrets and payload omitted")
                    raise MoodleUnavailable("Moodle did not respond before the configured timeout.") from exc
            except requests.RequestException as exc:
                logger.warning("Moodle read-only request failed (%s); secrets and payload omitted", type(exc).__name__)
                raise MoodleUnavailable("Moodle is currently unavailable.") from exc
            except (ValueError, json.JSONDecodeError) as exc:
                logger.warning("Moodle returned invalid JSON; response body omitted")
                raise MoodleUnavailable("Moodle returned an invalid response.") from exc
        raise MoodleUnavailable("Moodle is currently unavailable.")
