from django.db import models
from django.conf import settings


class ContactMessage(models.Model):
    """Message envoyé depuis le formulaire de contact public."""

    nom = models.CharField(max_length=255)
    email = models.EmailField()
    telephone = models.CharField(max_length=50, blank=True, default="")
    sujet = models.CharField(max_length=255)
    message = models.TextField()
    lu = models.BooleanField(default=False, verbose_name="Lu")
    lu_le = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Message de contact"
        verbose_name_plural = "Messages de contact"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Message de {self.nom} - {self.sujet[:50]}"




from django.db import models


class Ressource(models.Model):

    class Categorie(models.TextChoices):
        CREATION = "CREATION", "Création d'entreprise"
        GESTION = "GESTION", "Gestion d'entreprise"
        DOMICILIATION = "DOMICILIATION", "Domiciliation"
        JURIDIQUE = "JURIDIQUE", "Juridique"
        FISCALITE = "FISCALITE", "Fiscalité"
        BUSINESS = "BUSINESS", "Business"
        AUTRE = "AUTRE", "Autres"

    categorie = models.CharField(
        max_length=30,
        choices=Categorie.choices
    )

    question = models.CharField(
        max_length=500
    )

    reponse = models.TextField()

    ordre = models.PositiveIntegerField(
        default=0
    )

    est_public = models.BooleanField(
        default=True
    )

    date_creation = models.DateTimeField(
        auto_now_add=True
    )

    date_modification = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["categorie", "ordre", "date_creation"]
        verbose_name = "Ressource"
        verbose_name_plural = "Ressources"

    def __str__(self):
        return self.question


