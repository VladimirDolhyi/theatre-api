from rest_framework import permissions


class IsAdminUserOrCreateOnly(permissions.BasePermission):
    """
    Allows access only to anonymous users for reading,
    authenticated users for creating, and administrators for all operations.
    """

    def has_permission(self, request, view):
        # Allows all users to perform GET requests
        if request.method in permissions.SAFE_METHODS:
            return True

        # Allows authenticated users to make POST requests
        if request.method == 'POST':
            return request.user.is_authenticated

        # Allows administrators to perform any requests (PUT, PATCH, DELETE)
        return request.user.is_authenticated and request.user.is_staff
