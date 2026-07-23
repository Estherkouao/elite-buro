from __future__ import annotations

from accounts.models import User


def is_member(user) -> bool:
    return getattr(user, "is_authenticated", False) and getattr(user, "role", None) == User.Role.MEMBER


def is_admin_or_manager(user) -> bool:
    return getattr(user, "is_authenticated", False) and getattr(user, "role", None) in {User.Role.ADMIN, User.Role.MANAGER}


def is_trainer(user) -> bool:
    return getattr(user, "is_authenticated", False) and getattr(user, "role", None) == User.Role.TRAINER

