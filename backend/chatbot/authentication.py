from dataclasses import dataclass

from django.conf import settings
from rest_framework.authentication import BaseAuthentication


@dataclass(frozen=True)
class DemoPrincipal:
    pk: str
    username: str = "demo-student"
    role: str = "preview"
    is_authenticated: bool = True
    is_anonymous: bool = False
    is_staff: bool = False
    is_superuser: bool = False

    def __str__(self) -> str:
        return self.username


class DevelopmentDemoAuthentication(BaseAuthentication):
    """Fixed synthetic identity in local demo mode; accepts no identity headers."""

    def authenticate(self, request):
        if settings.DEMO_AUTH_MODE and settings.DEBUG:
            return DemoPrincipal(pk=settings.DEMO_AUTH_USER_ID), None
        return None

    def authenticate_header(self, request):
        return "Session"
