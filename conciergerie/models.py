from django.db import models

# Create your models here.
from django.db import models


from django.db import models


class DemandeConciergerie(models.Model):

    STATUT_CHOICES = (

        ("nouvelle", "Nouvelle"),

        ("etude", "En étude"),

        ("acceptee", "Acceptée"),

        ("refusee", "Refusée"),

        ("terminee", "Terminée"),

    )


    reference = models.CharField(
        max_length=30,
        unique=True
    )


    civilite = models.CharField(
        max_length=10
    )

    nom = models.CharField(
        max_length=150
    )

    fonction = models.CharField(
        max_length=150
    )

    entreprise = models.CharField(
        max_length=150
    )


    email = models.EmailField()

    telephone = models.CharField(
        max_length=30
    )


    secteur = models.CharField(
        max_length=100
    )


    service = models.CharField(
        max_length=100
    )


    participants = models.PositiveIntegerField(
        default=1
    )


    date_debut = models.DateField()


    duree = models.CharField(
        max_length=50
    )


    budget = models.CharField(
        max_length=100,
        blank=True
    )


    horaires = models.CharField(
        max_length=100
    )


    commentaire = models.TextField(
        blank=True
    )


    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default="nouvelle"
    )


    created_at = models.DateTimeField(
        auto_now_add=True
    )


    updated_at = models.DateTimeField(
        auto_now=True
    )


    class Meta:
        ordering = [
            "-created_at"
        ]


    def __str__(self):

        return f"{self.reference} - {self.nom}"