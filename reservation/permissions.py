from __future__ import annotations

from typing import Any


from django.contrib.auth import get_user_model

User = get_user_model()


def can_view_reservation(user, reservation):

    if not user.is_authenticated:
        return False


    role = user.role


    if role == User.Role.ADMIN:
        return True


    # Some deployments may not define STAFF on Role.
    if hasattr(User.Role, "STAFF") and role == User.Role.STAFF:
        return True


    # Reservation model uses `utilisateur` (not `user`).
    if getattr(reservation, "utilisateur_id", None) == getattr(user, "id", None):
        return True


    return False


def can_change_reservation(user, reservation) -> bool:
    if not can_view_reservation(user, reservation):
        return False

    role = getattr(user, "role", None)

    # Role checks should not crash if the enum/attribute doesn't exist.
    # Also handle Django's SimpleLazyObject (user proxy) where `.Role` may not exist.
    user_model = getattr(type(user), "__mro__", [type(user)])[0]
    if hasattr(User, "Role") and hasattr(User.Role, "ADMIN"):
        if role == getattr(User.Role, "ADMIN", None):
            return True
        if role == getattr(User.Role, "MANAGER", None):
            return True

    # Reservation model ownership
    return getattr(reservation, "utilisateur_id", None) == getattr(user, "id", None)


def can_cancel_reservation(user, reservation) -> bool:
    return can_change_reservation(user, reservation)


def can_export_invoice(user, reservation) -> bool:
    return can_view_reservation(user, reservation)

