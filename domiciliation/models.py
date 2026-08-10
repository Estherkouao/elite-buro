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
        CONTRAT_ENVOYÉ = "Contrat envoyé", "Contrat envoyé"
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

    class TypeDemande(models.TextChoices):

        DOMICILIATION = "DOMICILIATION", "Domiciliation simple"
        ENTREPRISE_INDIVIDUELLE = "EI", "Entreprise Individuelle"
        SARL = "SARL", "SARL"
        SARLU = "SARLU", "SARLU"
        SAS = "SAS", "SAS"
        SASU = "SASU", "SASU"
        ONG = "ONG", "ONG"
        STARTUP = "STARTUP", "Startup"
        SCI = "SCI", "SCI"
        ASSOCIATION = "ASSOCIATION", "Association"
        FONDATION = "FONDATION", "Fondation"
        SCOOP = "SCOOP", "SCOOP"



    type_demande = models.CharField(
        max_length=50,
        choices=TypeDemande.choices,
        default=TypeDemande.DOMICILIATION
    )

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


from django.conf import settings
from django.db import models
from django.utils import timezone


class ChangementGerant(models.Model):

    class Statut(models.TextChoices):
        BROUILLON = "BROUILLON", "Brouillon"
        EN_ATTENTE = "EN_ATTENTE", "En attente"
        EN_VERIFICATION = "EN_VERIFICATION", "En vérification"
        DOCUMENTS_MANQUANTS = "DOCUMENTS_MANQUANTS", "Documents manquants"
        EN_TRAITEMENT = "EN_TRAITEMENT", "En traitement"
        VALIDE = "VALIDE", "Validé"
        REJETE = "REJETE", "Rejeté"
        TERMINE = "TERMINE", "Terminé"

    # ==========================================================
    # CLIENT / DEMANDEUR
    # ==========================================================

    demandeur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="demandes_changement_gerant",
        verbose_name="Demandeur"
    )

    # ==========================================================
    # ENTREPRISE
    # ==========================================================

    entreprise = models.ForeignKey(
        "accounts.Company",
        on_delete=models.CASCADE,
        related_name="changements_gerant",
        verbose_name="Entreprise"
    )

    # ==========================================================
    # ANCIEN GERANT
    # ==========================================================

    ancien_nom = models.CharField(
        max_length=100,
        verbose_name="Nom de l'ancien gérant"
    )

    ancien_prenoms = models.CharField(
        max_length=150,
        verbose_name="Prénoms de l'ancien gérant"
    )

    ancien_email = models.EmailField(
        blank=True,
        null=True,
        verbose_name="Email de l'ancien gérant"
    )

    ancien_telephone = models.CharField(
        max_length=30,
        blank=True,
        verbose_name="Téléphone de l'ancien gérant"
    )

    # ==========================================================
    # NOUVEAU GERANT
    # ==========================================================

    nouveau_nom = models.CharField(
        max_length=100,
        verbose_name="Nom du nouveau gérant"
    )

    nouveau_prenoms = models.CharField(
        max_length=150,
        verbose_name="Prénoms du nouveau gérant"
    )

    nouveau_email = models.EmailField(
        verbose_name="Email du nouveau gérant"
    )

    nouveau_telephone = models.CharField(
        max_length=30,
        verbose_name="Téléphone du nouveau gérant"
    )

    nouveau_date_naissance = models.DateField(
        blank=True,
        null=True,
        verbose_name="Date de naissance"
    )

    nouveau_lieu_naissance = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Lieu de naissance"
    )

    nouveau_nationalite = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Nationalité"
    )

    nouveau_adresse = models.TextField(
        blank=True,
        verbose_name="Adresse du nouveau gérant"
    )

    # ==========================================================
    # INFORMATIONS SUR LE CHANGEMENT
    # ==========================================================

    date_prise_fonction = models.DateField(
        blank=True,
        null=True,
        verbose_name="Date de prise de fonction"
    )

    motif = models.TextField(
        verbose_name="Motif du changement"
    )

    # ==========================================================
    # DOCUMENTS
    # ==========================================================

    piece_identite_ancien = models.FileField(
        upload_to="gestion_entreprise/changement_gerant/",
        blank=True,
        null=True,
        verbose_name="Pièce d'identité ancien gérant"
    )

    piece_identite_nouveau = models.FileField(
        upload_to="gestion_entreprise/changement_gerant/",
        blank=True,
        null=True,
        verbose_name="Pièce d'identité nouveau gérant"
    )

    proces_verbal = models.FileField(
        upload_to="gestion_entreprise/changement_gerant/",
        blank=True,
        null=True,
        verbose_name="Procès-verbal"
    )

    statuts = models.FileField(
        upload_to="gestion_entreprise/changement_gerant/",
        blank=True,
        null=True,
        verbose_name="Statuts"
    )

    rccm = models.FileField(
        upload_to="gestion_entreprise/changement_gerant/",
        blank=True,
        null=True,
        verbose_name="RCCM"
    )

    autres_documents = models.FileField(
        upload_to="gestion_entreprise/changement_gerant/",
        blank=True,
        null=True,
        verbose_name="Autres documents"
    )

    # ==========================================================
    # TRAITEMENT
    # ==========================================================

    statut = models.CharField(
        max_length=30,
        choices=Statut.choices,
        default=Statut.EN_ATTENTE,
        verbose_name="Statut"
    )

    commentaire_admin = models.TextField(
        blank=True,
        verbose_name="Commentaire administrateur"
    )

    # ==========================================================
    # PAIEMENT
    # ==========================================================

    montant = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Montant"
    )

    paiement_effectue = models.BooleanField(
        default=False,
        verbose_name="Paiement effectué"
    )

    reference_paiement = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Référence paiement"
    )

    # ==========================================================
    # DATES
    # ==========================================================

    date_creation = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date de création"
    )

    date_modification = models.DateTimeField(
        auto_now=True,
        verbose_name="Dernière modification"
    )

    date_validation = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Date de validation"
    )

    date_terminaison = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Date de terminaison"
    )

    # ==========================================================
    # METHODES
    # ==========================================================

    def __str__(self):
        return (
            f"Changement de gérant - "
            f"{self.entreprise} - "
            f"#{self.pk}"
        )

    def marquer_valide(self):
        """
        Valide la demande.
        """

        self.statut = self.Statut.VALIDE
        self.date_validation = timezone.now()
        self.save(
            update_fields=[
                "statut",
                "date_validation",
                "date_modification"
            ]
        )

    def marquer_termine(self):
        """
        Termine le traitement de la demande.
        """

        self.statut = self.Statut.TERMINE
        self.date_terminaison = timezone.now()

        self.save(
            update_fields=[
                "statut",
                "date_terminaison",
                "date_modification"
            ]
        )

    @property
    def ancien_gerant_complet(self):
        return f"{self.ancien_nom} {self.ancien_prenoms}"

    @property
    def nouveau_gerant_complet(self):
        return f"{self.nouveau_nom} {self.nouveau_prenoms}"

    class Meta:
        verbose_name = "Changement de gérant"
        verbose_name_plural = "Changements de gérant"
        ordering = ["-date_creation"]


class CessionPartsSociales(models.Model):

    class Statut(models.TextChoices):
        EN_ATTENTE = "EN_ATTENTE", "En attente"
        EN_VERIFICATION = "EN_VERIFICATION", "En vérification"
        DOCUMENTS_MANQUANTS = "DOCUMENTS_MANQUANTS", "Documents manquants"
        EN_TRAITEMENT = "EN_TRAITEMENT", "En traitement"
        VALIDE = "VALIDE", "Validé"
        REJETE = "REJETE", "Rejeté"
        TERMINE = "TERMINE", "Terminé"

    # ==========================================================
    # DEMANDEUR
    # ==========================================================

    demandeur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="demandes_cession_parts",
        verbose_name="Demandeur"
    )

    # ==========================================================
    # ENTREPRISE
    # ==========================================================

    entreprise = models.ForeignKey(
        "accounts.Company",
        on_delete=models.CASCADE,
        related_name="cessions_parts",
        verbose_name="Entreprise"
    )

    # ==========================================================
    # CEDANT
    # ==========================================================

    cedant_nom = models.CharField(
        max_length=100,
        verbose_name="Nom du cédant"
    )

    cedant_prenoms = models.CharField(
        max_length=150,
        verbose_name="Prénoms du cédant"
    )

    cedant_email = models.EmailField(
        blank=True,
        verbose_name="Email du cédant"
    )

    cedant_telephone = models.CharField(
        max_length=30,
        blank=True,
        verbose_name="Téléphone du cédant"
    )

    # ==========================================================
    # CESSIONNAIRE
    # ==========================================================

    cessionnaire_nom = models.CharField(
        max_length=100,
        verbose_name="Nom du cessionnaire"
    )

    cessionnaire_prenoms = models.CharField(
        max_length=150,
        verbose_name="Prénoms du cessionnaire"
    )

    cessionnaire_email = models.EmailField(
        blank=True,
        verbose_name="Email du cessionnaire"
    )

    cessionnaire_telephone = models.CharField(
        max_length=30,
        blank=True,
        verbose_name="Téléphone du cessionnaire"
    )

    cessionnaire_nationalite = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Nationalité"
    )

    cessionnaire_adresse = models.TextField(
        blank=True,
        verbose_name="Adresse du cessionnaire"
    )

    # ==========================================================
    # PARTS SOCIALES
    # ==========================================================

    nombre_parts = models.PositiveIntegerField(
        verbose_name="Nombre de parts cédées"
    )

    valeur_nominale = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name="Valeur nominale d'une part"
    )

    prix_cession = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name="Prix total de la cession"
    )

    date_cession = models.DateField(
        blank=True,
        null=True,
        verbose_name="Date prévue de la cession"
    )

    # ==========================================================
    # INFORMATIONS
    # ==========================================================

    motif = models.TextField(
        blank=True,
        verbose_name="Motif de la cession"
    )

    observations = models.TextField(
        blank=True,
        verbose_name="Observations"
    )

    # ==========================================================
    # DOCUMENTS
    # ==========================================================

    piece_identite_cedant = models.FileField(
        upload_to="gestion_entreprise/cession_parts/",
        blank=True,
        null=True,
        verbose_name="Pièce d'identité du cédant"
    )

    piece_identite_cessionnaire = models.FileField(
        upload_to="gestion_entreprise/cession_parts/",
        blank=True,
        null=True,
        verbose_name="Pièce d'identité du cessionnaire"
    )

    acte_cession = models.FileField(
        upload_to="gestion_entreprise/cession_parts/",
        blank=True,
        null=True,
        verbose_name="Acte de cession"
    )

    proces_verbal = models.FileField(
        upload_to="gestion_entreprise/cession_parts/",
        blank=True,
        null=True,
        verbose_name="Procès-verbal"
    )

    statuts = models.FileField(
        upload_to="gestion_entreprise/cession_parts/",
        blank=True,
        null=True,
        verbose_name="Statuts"
    )

    autres_documents = models.FileField(
        upload_to="gestion_entreprise/cession_parts/",
        blank=True,
        null=True,
        verbose_name="Autres documents"
    )

    # ==========================================================
    # TRAITEMENT
    # ==========================================================

    statut = models.CharField(
        max_length=30,
        choices=Statut.choices,
        default=Statut.EN_ATTENTE,
        verbose_name="Statut"
    )

    commentaire_admin = models.TextField(
        blank=True,
        verbose_name="Commentaire administrateur"
    )

    # ==========================================================
    # PAIEMENT
    # ==========================================================

    montant = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Montant de la prestation"
    )

    paiement_effectue = models.BooleanField(
        default=False,
        verbose_name="Paiement effectué"
    )

    reference_paiement = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Référence paiement"
    )

    # ==========================================================
    # DATES
    # ==========================================================

    date_creation = models.DateTimeField(
        auto_now_add=True
    )

    date_modification = models.DateTimeField(
        auto_now=True
    )

    date_validation = models.DateTimeField(
        blank=True,
        null=True
    )

    date_terminaison = models.DateTimeField(
        blank=True,
        null=True
    )

    # ==========================================================
    # METHODES
    # ==========================================================

    def __str__(self):
        return (
            f"Cession de {self.nombre_parts} parts - "
            f"{self.entreprise.company_name}"
        )

    @property
    def cedant_complet(self):
        return f"{self.cedant_nom} {self.cedant_prenoms}"

    @property
    def cessionnaire_complet(self):
        return f"{self.cessionnaire_nom} {self.cessionnaire_prenoms}"

    class Meta:
        verbose_name = "Cession de parts sociales"
        verbose_name_plural = "Cessions de parts sociales"
        ordering = ["-date_creation"]


class ModificationActivite(models.Model):

    class Statut(models.TextChoices):
        EN_ATTENTE = "EN_ATTENTE", "En attente"
        EN_VERIFICATION = "EN_VERIFICATION", "En vérification"
        DOCUMENTS_MANQUANTS = "DOCUMENTS_MANQUANTS", "Documents manquants"
        EN_TRAITEMENT = "EN_TRAITEMENT", "En traitement"
        VALIDE = "VALIDE", "Validé"
        REJETE = "REJETE", "Rejeté"
        TERMINE = "TERMINE", "Terminé"

    # Demandeur
    demandeur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="demandes_modification_activite",
        verbose_name="Demandeur"
    )

    # Entreprise
    # IMPORTANT : mets ici la vraie application qui contient Company.
    # Si Company est dans core, utilise "core.Company".
    entreprise = models.ForeignKey(
        "accounts.Company",
        on_delete=models.CASCADE,
        related_name="modifications_activite",
        verbose_name="Entreprise"
    )

    # Activité actuelle
    activite_actuelle = models.TextField(
        verbose_name="Activité actuelle"
    )

    # Nouvelle activité
    nouvelle_activite = models.TextField(
        verbose_name="Nouvelle activité"
    )

    # Motif
    motif = models.TextField(
        blank=True,
        verbose_name="Motif de la modification"
    )

    observations = models.TextField(
        blank=True,
        verbose_name="Observations"
    )

    # Documents
    statuts = models.FileField(
        upload_to="gestion_entreprise/modification_activite/",
        blank=True,
        null=True,
        verbose_name="Statuts"
    )

    proces_verbal = models.FileField(
        upload_to="gestion_entreprise/modification_activite/",
        blank=True,
        null=True,
        verbose_name="Procès-verbal"
    )

    justificatif = models.FileField(
        upload_to="gestion_entreprise/modification_activite/",
        blank=True,
        null=True,
        verbose_name="Justificatif"
    )

    autres_documents = models.FileField(
        upload_to="gestion_entreprise/modification_activite/",
        blank=True,
        null=True,
        verbose_name="Autres documents"
    )

    # Traitement
    statut = models.CharField(
        max_length=30,
        choices=Statut.choices,
        default=Statut.EN_ATTENTE,
        verbose_name="Statut"
    )

    commentaire_admin = models.TextField(
        blank=True,
        verbose_name="Commentaire administrateur"
    )

    # Paiement
    montant = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    paiement_effectue = models.BooleanField(
        default=False
    )

    reference_paiement = models.CharField(
        max_length=150,
        blank=True
    )

    # Dates
    date_creation = models.DateTimeField(
        auto_now_add=True
    )

    date_modification = models.DateTimeField(
        auto_now=True
    )

    date_validation = models.DateTimeField(
        blank=True,
        null=True
    )

    date_terminaison = models.DateTimeField(
        blank=True,
        null=True
    )

    def __str__(self):
        return (
            f"Modification activité - "
            f"{self.entreprise.company_name}"
        )

    class Meta:
        verbose_name = "Modification d'activité"
        verbose_name_plural = "Modifications d'activité"
        ordering = ["-date_creation"]


class ChangementNomEntreprise(models.Model):

    class Statut(models.TextChoices):
        EN_ATTENTE = "EN_ATTENTE", "En attente"
        EN_VERIFICATION = "EN_VERIFICATION", "En vérification"
        DOCUMENTS_MANQUANTS = "DOCUMENTS_MANQUANTS", "Documents manquants"
        EN_TRAITEMENT = "EN_TRAITEMENT", "En traitement"
        VALIDE = "VALIDE", "Validé"
        REJETE = "REJETE", "Rejeté"
        TERMINE = "TERMINE", "Terminé"

    demandeur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="demandes_changement_nom",
        verbose_name="Demandeur"
    )

    entreprise = models.ForeignKey(
        "accounts.Company",
        on_delete=models.CASCADE,
        related_name="changements_nom",
        verbose_name="Entreprise"
    )

    ancien_nom = models.CharField(
        max_length=255,
        verbose_name="Ancienne dénomination"
    )

    nouveau_nom = models.CharField(
        max_length=255,
        verbose_name="Nouvelle dénomination"
    )

    motif = models.TextField(
        blank=True,
        verbose_name="Motif du changement"
    )

    observations = models.TextField(
        blank=True,
        verbose_name="Observations"
    )

    statuts = models.FileField(
        upload_to="gestion_entreprise/changement_nom/",
        blank=True,
        null=True,
        verbose_name="Statuts"
    )

    proces_verbal = models.FileField(
        upload_to="gestion_entreprise/changement_nom/",
        blank=True,
        null=True,
        verbose_name="Procès-verbal"
    )

    justificatif = models.FileField(
        upload_to="gestion_entreprise/changement_nom/",
        blank=True,
        null=True,
        verbose_name="Justificatif"
    )

    autres_documents = models.FileField(
        upload_to="gestion_entreprise/changement_nom/",
        blank=True,
        null=True,
        verbose_name="Autres documents"
    )

    statut = models.CharField(
        max_length=30,
        choices=Statut.choices,
        default=Statut.EN_ATTENTE,
        verbose_name="Statut"
    )

    commentaire_admin = models.TextField(
        blank=True,
        verbose_name="Commentaire administrateur"
    )

    montant = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    paiement_effectue = models.BooleanField(
        default=False
    )

    reference_paiement = models.CharField(
        max_length=150,
        blank=True
    )

    date_creation = models.DateTimeField(
        auto_now_add=True
    )

    date_modification = models.DateTimeField(
        auto_now=True
    )

    date_validation = models.DateTimeField(
        blank=True,
        null=True
    )

    date_terminaison = models.DateTimeField(
        blank=True,
        null=True
    )

    def __str__(self):
        return (
            f"Changement de nom - "
            f"{self.ancien_nom} → {self.nouveau_nom}"
        )

    class Meta:
        verbose_name = "Changement de dénomination"
        verbose_name_plural = "Changements de dénomination"
        ordering = ["-date_creation"]