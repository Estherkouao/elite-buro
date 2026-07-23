from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import user_passes_test


def admin_required(view_func):
    """
    Autorise uniquement les administrateurs.
    """
    return user_passes_test(
        lambda user: user.is_authenticated and user.role == user.Role.ADMIN
    )(view_func)


def manager_required(view_func):
    """
    Autorise les gestionnaires et administrateurs.
    """
    return user_passes_test(
        lambda user: user.is_authenticated and (
            user.role == user.Role.ADMIN or
            user.role == user.Role.MANAGER
        )
    )(view_func)


def trainer_required(view_func):
    """
    Autorise uniquement les formateurs.
    """
    return user_passes_test(
        lambda user: user.is_authenticated and user.role == user.Role.TRAINER
    )(view_func)


def member_required(view_func):
    """
    Autorise uniquement les membres.
    """
    return user_passes_test(
        lambda user: user.is_authenticated and user.role == user.Role.MEMBER
    )(view_func)