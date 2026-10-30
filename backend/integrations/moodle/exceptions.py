class MoodleIntegrationError(Exception):
    """Base exception with messages safe to return to API clients."""


class MoodleNotConfigured(MoodleIntegrationError):
    pass


class MoodleUnavailable(MoodleIntegrationError):
    pass


class MoodleAuthenticationError(MoodleIntegrationError):
    pass


class MoodlePermissionError(MoodleIntegrationError):
    pass
