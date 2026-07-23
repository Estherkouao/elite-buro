import uuid

from django.conf import settings
from django.db import models


class Reclamation(models.Model):
    class Status(models.TextChoices):
        OUVERTE = "ouverte", "Ouverte"
        CLOTUREE = "cloturee", "Clôturée"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Pour l’admin (back-office) uniquement pour cette V1 :
    # on garde quand même le champ pour historiser / afficher.
    auteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reclamations",
    )

    objet = models.CharField(max_length=255)
    description = models.TextField()

    statut = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OUVERTE,
        db_index=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    closed_at = models.DateTimeField(null=True, blank=True)
    # optionnel: réponse/ commentaire admin
    reponse_admin = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Réclamation"
        verbose_name_plural = "Réclamations"

    def __str__(self) -> str:
        return f"{self.objet} ({self.statut})"

