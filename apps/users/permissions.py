"""
Custom permissions for NARADHA application.
"""
from rest_framework import permissions


class IsCitizen(permissions.BasePermission):
    """Allows access only to citizens."""

    message = 'Only citizens can perform this action.'

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == 'CITIZEN'
        )


class IsReviewer(permissions.BasePermission):
    """Allows access only to reviewers."""

    message = 'Only reviewers can perform this action.'

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == 'REVIEWER'
        )


class IsOfficial(permissions.BasePermission):
    """Allows access only to officials (including ministers)."""

    message = 'Only officials can perform this action.'

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in ('OFFICIAL', 'MINISTER')
        )


class IsMinister(permissions.BasePermission):
    """Allows access only to ministers."""

    message = 'Only ministers can perform this action.'

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == 'MINISTER'
        )


class IsFieldWorker(permissions.BasePermission):
    """Allows access only to field workers."""

    message = 'Only field workers can perform this action.'

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == 'FIELD_WORKER'
        )


class IsAdmin(permissions.BasePermission):
    """Allows access only to administrators."""

    message = 'Only administrators can perform this action.'

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.role == 'ADMIN' or request.user.is_staff)
        )


class IsOwnerOrReadOnly(permissions.BasePermission):
    """Object-level permission to only allow owners of an object to edit it."""

    message = 'You do not have permission to modify this object.'

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        # Check common owner attribute names
        owner_attributes = ['citizen', 'user', 'sender', 'official', 'worker', 'owner']
        for attr in owner_attributes:
            owner = getattr(obj, attr, None)
            if owner is not None:
                return owner == request.user

        return False


class IsComplaintParticipant(permissions.BasePermission):
    """Allows access to citizens, assigned officials, and field workers on a complaint."""

    message = 'You are not a participant of this complaint.'

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not (user and user.is_authenticated):
            return False

        # Admins can see everything
        if user.role == 'ADMIN' or user.is_staff:
            return True

        complaint = getattr(obj, 'complaint', obj)
        return (
            complaint.citizen == user
            or complaint.assigned_official == user
            or complaint.assigned_field_worker == user
        )
