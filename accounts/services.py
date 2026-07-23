from django.utils import timezone
from django.conf import settings

from .models import User, Profile, UserPreference, EmailVerification


# =========================
# SERVICE UTILISATEUR
# =========================

class UserService:

    @staticmethod
    def create_user(validated_data):
        """
        Création propre d'un utilisateur (SaaS ready)
        """

        password = validated_data.pop("password1")

        user = User.objects.create(**validated_data)

        user.set_password(password)
        user.save()

        return user


    @staticmethod
    def update_last_activity(user):
        """
        Met à jour la dernière activité utilisateur
        """

        user.last_activity = timezone.now()
        user.save(update_fields=["last_activity"])


# =========================
# SERVICE PROFIL
# =========================

class ProfileService:

    @staticmethod
    def create_default_profile(user):
        """
        Création automatique du profil utilisateur
        """

        profile, created = Profile.objects.get_or_create(
            user=user
        )

        return profile

    @staticmethod
    def update_profile(user, data):
        """
        Mise à jour profil
        """

        for field, value in data.items():
            setattr(user, field, value)

        user.save()

        return user


# =========================
# SERVICE PRÉFÉRENCES
# =========================

class PreferenceService:

    @staticmethod
    def create_default_preferences(user):

        prefs, created = UserPreference.objects.get_or_create(
            user=user
        )

        return prefs


# =========================
# SERVICE EMAIL VERIFICATION
# =========================

class EmailVerificationService:

    @staticmethod
    def create_verification(user):
        """
        Crée un token de vérification email
        """

        verification = EmailVerification.objects.create(
            user=user,
            expires_at=timezone.now() + timezone.timedelta(days=1)
        )

        return verification


    @staticmethod
    def verify_email(token):
        """
        Vérifie l'email utilisateur
        """

        try:
            verification = EmailVerification.objects.get(token=token)

            if verification.is_expired():
                return False

            user = verification.user
            user.is_email_verified = True
            user.save()

            verification.verified = True
            verification.save()

            return True

        except EmailVerification.DoesNotExist:
            return False