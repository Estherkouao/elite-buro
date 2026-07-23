from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import (
    User,
    Profile,
    Address,
    UserPreference,
)


@receiver(post_save, sender=User)
def create_user_related_models(sender, instance, created, **kwargs):
    """
    Création automatique des modèles liés
    lors de la création d'un utilisateur.
    """

    if created:

        Profile.objects.create(
            user=instance
        )

        Address.objects.create(
            user=instance,
            city="Abidjan",
            address=""
        )

        UserPreference.objects.create(
            user=instance
        )


@receiver(post_save, sender=User)
def save_user_related_models(sender, instance, **kwargs):

    if hasattr(instance, "profile"):
        instance.profile.save()

    if hasattr(instance, "address"):
        instance.address.save()

    if hasattr(instance, "preferences"):
        instance.preferences.save()