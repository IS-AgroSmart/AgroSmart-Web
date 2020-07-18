from rest_framework import permissions

from core.models import UserType


class OnlySelfUnlessAdminPermission(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user.type == UserType.ADMIN.name or obj == request.user
