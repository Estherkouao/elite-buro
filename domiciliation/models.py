from __future__ import annotations

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
import uuid


class DomiciliationPlan(models.Model):
    class Meta:
        verbose_name = "Formule de domiciliation"
        verbose_name_plural = "Formules de domiciliation"
        ordering = ["ordre"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["actif"]),
        ]

    nom = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    description = models.TextField()
    prix = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    durée = models.PositiveIntegerField(help_text="Durée en mois")
    avantages = models.TextField(help_text="Liste des avantages, séparés par des retours à la ligne")
    actif = models.BooleanField(default=True)
    ordre = models.PositiveIntegerField(default=0, db_index=True, help_text="Ordre d’affichage")

    @property
    def avantages_list(self):
        """Retourne la liste des avantages, séparés par des retours à la ligne."""
        if not self.avantages:
            return []
        return [a.strip() for a in self.avantages.split('\n') if a.strip()]

    def save(self, *args, **kwargs):
        if not self.slug and self.nom:
            self.slug = slugify(self.nom)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.nom


class DomiciliationRequest(models.Model):
    class Status(models.TextChoices):
        BROUILLON = "Brouillon", "Brouillon"
        EN_ATTENTE = "En attente", "En attente"
        DOCUMENTS_REÇUS = "Documents reçus", "Documents reçus"
        EN_VÉRIFICATION = "En vérification", "En vérification"
        CONTRAT_GÉNÉRÉ = "Contrat généré", "Contrat généré"
        SIGNATURE_EN_ATTENTE = "Signature en attente", "Signature en attente"
        PAIEMENT_EN_ATTENTE = "Paiement en attente", "Paiement en attente"
        ACTIVE = "Active", "Active"
        REFUSÉE = "Refusée", "Refusée"
        EXPIRÉE = "Expirée", "Expirée"
        RÉSILIÉE = "Résiliée", "Résiliée"

    class Meta:
        verbose_name = "Demande de domiciliation"
        verbose_name_plural = "Demandes de domiciliation"
        indexes = [
            models.Index(fields=["statut"]),
            models.Index(fields=["date_fin"]),
            models.Index(fields=["entreprise"]),
            models.Index(fields=["utilisateur"]),
        ]
        ordering = ["-date_creation"]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Relations
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="domiciliation_requests",
    )
    entreprise = models.ForeignKey(
        "accounts.Company",
        on_delete=models.CASCADE,
        related_name="domiciliation_requests",
        help_text="Entreprise concernée par la domiciliation",
    )
    formule = models.ForeignKey(
        DomiciliationPlan,
        on_delete=models.PROTECT,
        related_name="domiciliation_requests",
    )

    # Identifiants
    numero_demande = models.CharField(max_length=60, unique=True, db_index=True)

    # Statut & dates
    statut = models.CharField(max_length=64, choices=Status.choices, default=Status.BROUILLON)
    date_debut = models.DateField(null=True, blank=True)
    date_fin = models.DateField(null=True, blank=True)

    # Adresse & notes
    adresse_domiciliation = models.TextField()
    observations = models.TextField(blank=True)

    # Fichiers/étapes
    date_creation = models.DateTimeField(auto_now_add=True, db_index=True)
    derniere_modification = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.numero_demande} - {self.entreprise}"

    @property
    def is_active(self) -> bool:
        return self.statut == self.Status.ACTIVE

    @property
    def est_expiree(self) -> bool:
        if not self.date_fin:
            return False
        return self.date_fin < timezone.localdate()


class DomiciliationDocument(models.Model):
    class Type(models.TextChoices):
        PIECE_IDENTITE = "Pièce d'identité", "Pièce d'identité"
        RCCM = "RCCM", "RCCM"
        STATUTS = "Statuts", "Statuts"
        ATTESTATION = "Attestation", "Attestation"
        JUSTIFICATIF = "Justificatif", "Justificatif"
        AUTRE = "Autre", "Autre"

    class Meta:
        verbose_name = "Document de domiciliation"
        verbose_name_plural = "Documents de domiciliation"
        indexes = [
            models.Index(fields=["demande"]),
            models.Index(fields=["type"]),
            models.Index(fields=["validé"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["demande", "type"], name="uniq_document_type_per_request"),
        ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    demande = models.ForeignKey(
        DomiciliationRequest,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    type = models.CharField(max_length=64, choices=Type.choices)
    fichier = models.FileField(upload_to="domiciliation/documents/%Y/%m/%d/", max_length=500)
    validé = models.BooleanField(default=False, db_index=True)
    commentaire = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.type} ({self.demande.numero_demande})"


class DomiciliationContract(models.Model):
    class Meta:
        verbose_name = "Contrat de domiciliation"
        verbose_name_plural = "Contrats de domiciliation"
        indexes = [
            models.Index(fields=["demande"]),
        ]

    demande = models.OneToOneField(
        DomiciliationRequest,
        on_delete=models.CASCADE,
        related_name="contrat",
    )

    numero = models.CharField(max_length=80, unique=True, db_index=True)
    fichier_pdf = models.FileField(upload_to="domiciliation/contracts/%Y/%m/%d/", max_length=500)

    signature_docuseal = models.CharField(max_length=120, blank=True, default="", help_text="ID Docuseal envelope")
    signé = models.BooleanField(default=False)
    date_signature = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Contrat {self.numero} ({self.demande.numero_demande})"


class DomiciliationInvoice(models.Model):
    class Status(models.TextChoices):
        EN_ATTENTE = "En attente", "En attente"
        PAYÉE = "Payée", "Payée"
        ANNULÉE = "Annulée", "Annulée"

    class Meta:
        verbose_name = "Facture de domiciliation"
        verbose_name_plural = "Factures de domiciliation"
        indexes = [
            models.Index(fields=["demande"]),
            models.Index(fields=["statut"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["demande"], name="uniq_invoice_per_request"),
        ]

    demande = models.OneToOneField(
        DomiciliationRequest,
        on_delete=models.CASCADE,
        related_name="facture",
    )

    numero = models.CharField(max_length=80, unique=True, db_index=True)
    montant = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    fichier_pdf = models.FileField(upload_to="domiciliation/invoices/%Y/%m/%d/", max_length=500)
    statut = models.CharField(max_length=40, choices=Status.choices, default=Status.EN_ATTENTE, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Facture {self.numero} ({self.demande.numero_demande})"


class DomiciliationRenewal(models.Model):
    class Meta:
        verbose_name = "Renouvellement de domiciliation"
        verbose_name_plural = "Renouvellements de domiciliation"
        indexes = [
            models.Index(fields=["demande"]),
            models.Index(fields=["statut"]),
        ]
        ordering = ["-created_at"]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    demande = models.ForeignKey(
        DomiciliationRequest,
        on_delete=models.CASCADE,
        related_name="renouvellements",
    )
    nouvelle_periode = models.PositiveIntegerField(help_text="Durée en mois")
    montant = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    statut = models.CharField(max_length=40, default="En attente", db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Renouvellement ({self.demande.numero_demande})"


class DomiciliationLog(models.Model):
    class Meta:
        verbose_name = "Journal de domiciliation"
        verbose_name_plural = "Journaux de domiciliation"
        indexes = [
            models.Index(fields=["demande"]),
            models.Index(fields=["created_at"]),
        ]
        ordering = ["-created_at"]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    demande = models.ForeignKey(
        DomiciliationRequest,
        on_delete=models.CASCADE,
        related_name="logs",
    )
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="domiciliation_logs",
    )
    action = models.CharField(max_length=80)
    details = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.action} - {self.demande.numero_demande}"  

