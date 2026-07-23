from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied


User = get_user_model()


class DomiciliationPermissionError(PermissionDenied):
    pass


def can_consulter_request(*, user: User, demande) -> bool:
    if not user.is_authenticated:
        return False
    if getattr(user, "role", None) == getattr(User.Role, "ADMIN", "ADMIN"):
        return True
    if getattr(user, "role", None) == getattr(User.Role, "MANAGER", "MANAGER"):
        return True
    if getattr(user, "role", None) == getattr(User.Role, "MEMBER", "MEMBER"):
        return demande.utilisateur_id == user.id
    return False


def can_traiter_request(*, user: User, demande) -> bool:
    if not user.is_authenticated:
        return False
    if getattr(user, "role", None) in {getattr(User.Role, "ADMIN", "ADMIN"), getattr(User.Role, "MANAGER", "MANAGER")}:
        return True
    return False


def require_can_consulter_request(*, user: User, demande) -> None:
    if not can_consulter_request(user=user, demande=demande):
        raise DomiciliationPermissionError("Accès refusé.")


def require_can_traiter_request(*, user: User, demande) -> None:
    if not can_traiter_request(user=user, demande=demande):
        raise DomiciliationPermissionError("Vous n’avez pas les droits pour traiter cette demande.")

