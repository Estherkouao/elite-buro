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


class DevisFormation(models.Model):
    """Demande de devis pour les formations professionnelles."""

    # === Section 1: Informations entreprise ===
    company_name = models.CharField(max_length=255, verbose_name="Nom de l'entreprise")
    rccm = models.CharField(max_length=100, blank=True, default="", verbose_name="Numéro RCCM / RC")
    secteur = models.CharField(max_length=100, verbose_name="Secteur d'activité")
    taille_entreprise = models.CharField(max_length=50, verbose_name="Taille de l'entreprise")
    adresse = models.CharField(max_length=500, blank=True, default="", verbose_name="Adresse de l'entreprise")

    # === Section 2: Contact ===
    civilite = models.CharField(max_length=10, blank=True, default="mr", verbose_name="Civilité")
    fonction = models.CharField(max_length=200, verbose_name="Fonction / Poste")
    nom_complet = models.CharField(max_length=255, verbose_name="Nom complet")
    email = models.EmailField(verbose_name="Email professionnel")
    telephone = models.CharField(max_length=50, verbose_name="Téléphone")
    telephone_secondaire = models.CharField(max_length=50, blank=True, default="", verbose_name="Téléphone secondaire")

    # === Section 3: Besoin de formation ===
    type_formation = models.CharField(max_length=255, blank=True, default="", verbose_name="Type de formation souhaitée")
    domaines = models.TextField(blank=True, default="", verbose_name="Domaine(s) de formation")
    nombre_participants = models.PositiveIntegerField(default=10, verbose_name="Nombre de participants")
    budget = models.DecimalField(max_digits=14, decimal_places=2, default=500000, verbose_name="Budget estimé (FCFA)")
    date_debut_souhaitee = models.DateField(null=True, blank=True, verbose_name="Date de début souhaitée")
    duree_souhaitee = models.CharField(max_length=50, blank=True, default="", verbose_name="Durée souhaitée")
    lieu_formation = models.CharField(max_length=100, blank=True, default="nos-locaux", verbose_name="Lieu de formation")

    # === Section 4: Description du besoin ===
    objectifs = models.TextField(verbose_name="Objectifs de la formation")
    public_cible = models.TextField(blank=True, default="", verbose_name="Public cible / Profil des participants")
    fichier_joint = models.FileField(upload_to="devis_formation/", blank=True, null=True, verbose_name="Document joint")

    # === Métadonnées ===
    lu = models.BooleanField(default=False, verbose_name="Lu")
    lu_le = models.DateTimeField(null=True, blank=True, verbose_name="Lu le")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")

    class Meta:
        verbose_name = "Demande de devis formation"
        verbose_name_plural = "Demandes de devis formation"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Devis {self.company_name} - {self.nom_complet} ({self.created_at.strftime('%d/%m/%Y')})"
