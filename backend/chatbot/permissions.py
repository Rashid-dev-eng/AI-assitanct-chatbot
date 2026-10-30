from rest_framework.permissions import BasePermission, IsAdminUser


class IsStaffOrAdmin(IsAdminUser):
    """Django staff accounts only; browser-supplied role names are ignored."""


class IsAuthenticatedDemoOrInstitutional(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)
