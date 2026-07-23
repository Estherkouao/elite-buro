from __future__ import annotations

from dataclasses import dataclass

from django.contrib.auth import get_user_model

from .models import Trainer


User = get_user_model()


def user_is_admin(user: User | None) -> bool:
    return bool(user and getattr(user, "role", None) == user.Role.ADMIN)


def user_is_manager(user: User | None) -> bool:
    return bool(user and getattr(user, "role", None) == user.Role.MANAGER)


def user_is_trainer(user: User | None) -> bool:
    return bool(user and getattr(user, "role", None) == user.Role.TRAINER)


def user_is_member(user: User | None) -> bool:
    return bool(user and getattr(user, "role", None) == user.Role.MEMBER)


def get_trainer_for_user(user: User) -> Trainer | None:
    if not user_is_trainer(user):
        return None
    try:
        return user.trainer_profile
    except Trainer.DoesNotExist:
        return None


@dataclass(frozen=True)
class FormationAccess:
    """Vérifications centralisées des accès formation."""

    user: User

    def is_admin_or_manager(self) -> bool:
        return user_is_admin(self.user) or user_is_manager(self.user)

    def can_manage_trainer_object(self, trainer: Trainer) -> bool:
        if self.is_admin_or_manager():
            return True
        if not user_is_trainer(self.user):
            return False
        trainer_profile = get_trainer_for_user(self.user)
        return bool(trainer_profile and trainer_profile.id == trainer.id)

    def can_manage_session(self, session: object) -> bool:
        if self.is_admin_or_manager():
            return True
        if not user_is_trainer(self.user):
            return False
        trainer_profile = get_trainer_for_user(self.user)
        if not trainer_profile:
            return False
        # session.formateur est un FK vers Trainer
        return getattr(session, "formateur_id", None) == trainer_profile.id

    def can_view_registration(self, registration: object) -> bool:
        if self.is_admin_or_manager():
            return True
        if user_is_member(self.user):
            return getattr(registration, "membre_id", None) == self.user.id
        if user_is_trainer(self.user):
            trainer_profile = get_trainer_for_user(self.user)
            if not trainer_profile:
                return False
            # registration.session.formateur
            session = getattr(registration, "session", None)
            if not session:
                return False
            return getattr(session, "formateur_id", None) == trainer_profile.id
        return False

    def can_submit_review(self, review: object) -> bool:
        if self.is_admin_or_manager():
            return True
        return getattr(review, "membre_id", None) == self.user.id

