"""Custom DRF permissions for the Shop API."""

from typing import Any, cast

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request


def is_seller(user: Any) -> bool:
    """
    Treat a user as a 'seller' if they belong to the configured auth group.
    (No is_staff check here – group membership only.)
    """
    if not user or isinstance(user, AnonymousUser) or not getattr(user, "is_authenticated", False):
        return False
    group_name = getattr(settings, "SHOP_SELLER_GROUP", "seller")
    return cast(bool, user.groups.filter(name=group_name).exists())


class IsSellerOrReadOnly(BasePermission):
    """Read for everyone, write only for sellers (group-based)."""

    def has_permission(self, request: Request, view: Any) -> bool:
        if request.method in SAFE_METHODS:
            return True
        return is_seller(request.user)

    def has_object_permission(self, request: Request, view: Any, obj: Any) -> bool:
        if request.method in SAFE_METHODS:
            return True
        return is_seller(request.user)


class IsSeller(BasePermission):
    """Access limited to sellers (group-based)."""

    def has_permission(self, request: Request, view: Any) -> bool:
        return is_seller(request.user)
