from __future__ import annotations

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import DomiciliationRequest


@receiver(post_save, sender=DomiciliationRequest)
def auto_generer_contrat(sender, instance, created, **kwargs):
    """Génère automatiquement le contrat de domiciliation à la création de la demande.

    La génération est idempotente : si un contrat existe déjà, `generer_contrat_pour_demande`
    le renvoie sans le recréer. On recrée uniquement s'il n'existe pas encore.
    """
    if not created:
        return

    # Ne pas générer pendant les migrations / fixtures
    try:
        from .services import generer_contrat_pour_demande

        generer_contrat_pour_demande(demande=instance)
    except Exception:
        # Échec silencieux : l'admin pourra régénérer le contrat manuellement.
        import logging

        logger = logging.getLogger("domiciliation")
        logger.exception("Impossible de générer automatiquement le contrat pour %s", instance.numero_demande)
