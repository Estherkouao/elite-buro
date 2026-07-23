import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.text import slugify


def _uuid4():
    return uuid.uuid4()


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class FormationCategory(TimeStampedModel):
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=220, unique=True, blank=True)

    class Meta:
        verbose_name = "Catégorie de formation"
        verbose_name_plural = "Catégories de formations"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug and self.name:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name

from decimal import Decimal
from django.db import models
from django.utils.text import slugify


class Formation(TimeStampedModel):

    class Niveau(models.TextChoices):
        BEGINNER = "BEGINNER", "Débutant"
        INTERMEDIATE = "INTERMEDIATE", "Intermédiaire"
        ADVANCED = "ADVANCED", "Avancé"

    class Statut(models.TextChoices):
        ACTIVE = "active", "Actif"
        INACTIVE = "inactive", "Inactif"

    category = models.ForeignKey(
        FormationCategory,
        on_delete=models.PROTECT,
        related_name="formations",
    )

    titre = models.CharField(max_length=250)
    slug = models.SlugField(max_length=260, unique=True, blank=True)

    description_courte = models.TextField(blank=True, default="")
    description_complete = models.TextField(blank=True, default="")

    objectifs = models.TextField(blank=True, default="")
    programme = models.TextField(blank=True, default="")
    prerequis = models.TextField(blank=True, default="")

    duree = models.PositiveIntegerField(
        help_text="Durée en heures"
    )

    niveau = models.CharField(
        max_length=30,
        choices=Niveau.choices,
        db_index=True
    )

    prix = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        db_index=True
    )

    # IMAGE
    image = models.ImageField(
        upload_to="formation/formations/images/",
        blank=True,
        null=True
    )

    # VIDEO MP4
    video = models.FileField(
        upload_to="formation/formations/videos/",
        blank=True,
        null=True
    )

    # DOCUMENT PDF
    pdf = models.FileField(
        upload_to="formation/formations/pdfs/",
        blank=True,
        null=True
    )

    # YouTube ou Vimeo
    video_url = models.URLField(
        blank=True,
        null=True,
        help_text="Lien YouTube ou Vimeo"
    )

    certificat = models.BooleanField(default=True)

    actif = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Formation"
        verbose_name_plural = "Formations"

        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["actif"]),
            models.Index(fields=["prix"]),
            models.Index(fields=["niveau"]),
        ]

    def save(self, *args, **kwargs):

        if not self.slug and self.titre:
            self.slug = slugify(self.titre)

        if self.slug:
            self.slug = slugify(self.slug)

        super().save(*args, **kwargs)

    def __str__(self):
        return self.titre


class Trainer(TimeStampedModel):
    class Disponibilite(models.TextChoices):
        AVAILABLE = "available", "Disponible"
        UNAVAILABLE = "unavailable", "Indisponible"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="trainer_profile",
    )

    specialite = models.CharField(max_length=200, blank=True, default="")
    biographie = models.TextField(blank=True, default="")

    photo = models.ImageField(upload_to="formation/trainers/photos/", blank=True, null=True)
    cv = models.FileField(upload_to="formation/trainers/cv/", blank=True, null=True)

    annees_experience = models.PositiveIntegerField(default=0)
    competences = models.TextField(blank=True, default="")

    linkedin = models.URLField(blank=True, null=True)

    disponible = models.CharField(
        max_length=20,
        choices=Disponibilite.choices,
        default=Disponibilite.AVAILABLE,
        db_index=True,
    )

    class Meta:
        verbose_name = "Formateur"
        verbose_name_plural = "Formateurs"

    def __str__(self) -> str:
        return self.user.full_name


class FormationSession(TimeStampedModel):
    class Statut(models.TextChoices):
        DRAFT = "draft", "Brouillon"
        PUBLISHED = "published", "Publié"
        OPEN = "open", "Ouverte"
        CLOSED = "closed", "Fermée"
        CANCELED = "canceled", "Annulée"

    formation = models.ForeignKey(
        Formation,
        on_delete=models.CASCADE,
        related_name="sessions",
    )

    formateur = models.ForeignKey(
        Trainer,
        on_delete=models.PROTECT,
        related_name="sessions",
    )

    # Salle: intégration avec l’app reservation/coworking (optionnel dans ce sprint)
    # On stocke l’ID pour permettre une intégration ultérieure sans casser la prod.
    salle_reference = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Référence interne de salle (future intégration)",
    )

    date_debut = models.DateField(db_index=True)
    date_fin = models.DateField(db_index=True)
    heure_debut = models.TimeField()
    heure_fin = models.TimeField()

    nombre_maximum = models.PositiveIntegerField(help_text="Nombre maximum de places")

    statut = models.CharField(
        max_length=30,
        choices=Statut.choices,
        default=Statut.OPEN,
        db_index=True,
    )

    # Cache indicatif (calculé par services)
    places_restantes = models.IntegerField(default=0, db_index=True)

    class Meta:
        verbose_name = "Session de formation"
        verbose_name_plural = "Sessions de formation"
        indexes = [
            models.Index(fields=["formation", "statut"]),
            models.Index(fields=["date_debut", "statut"]),
        ]

    def __str__(self) -> str:
        return f"{self.formation.titre} - {self.date_debut}"

    def is_active(self) -> bool:
        return self.statut in {self.Statut.PUBLISHED, self.Statut.OPEN}

    from django.utils import timezone


    def update_status(self):

        today = timezone.now().date()


        # Ne jamais écraser ces états
        if self.statut in [
            self.Statut.DRAFT,
            self.Statut.CANCELED,
        ]:
            return


        # Formation terminée
        if self.date_fin < today:
            self.statut = self.Statut.CLOSED


        # Plus de places
        elif self.places_restantes <= 0:
            self.statut = self.Statut.CLOSED


        # Session disponible
        elif self.date_debut >= today:
            self.statut = self.Statut.OPEN


        self.save(update_fields=["statut"])

    def save(self, *args, **kwargs):

            if self.nombre_maximum and self.places_restantes == 0:
                self.places_restantes = self.nombre_maximum

            super().save(*args, **kwargs)

            self.update_status()


    
        


class FormationRegistration(TimeStampedModel):
    class Statut(models.TextChoices):
        PENDING = "pending", "En attente"
        CONFIRMED = "confirmed", "Confirmée"
        CANCELED = "canceled", "Annulée"
        REFUSED = "refused", "Refusée"

    membre = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="formation_registrations",
    )

    entreprise = models.ForeignKey(
        "accounts.Company",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="formation_registrations",
    )

    formation = models.ForeignKey(
        Formation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="registrations",
        help_text="Formation liée (utile quand session est null)",
    )

    session = models.ForeignKey(
        FormationSession,
        on_delete=models.CASCADE,
        related_name="registrations",
        null=True,
        blank=True,
    )

    numero = models.CharField(max_length=64, unique=True, db_index=True)

    statut = models.CharField(
        max_length=30,
        choices=Statut.choices,
        default=Statut.PENDING,
        db_index=True,
    )

    date = models.DateTimeField(default=timezone.now, db_index=True)

    commentaire = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = "Inscription"
        verbose_name_plural = "Inscriptions"
        constraints = [
            models.UniqueConstraint(
                fields=["membre", "session"],
                name="formation_registration_unique_member_session",
                condition=models.Q(session__isnull=False),
            ),
        ]
        indexes = [
            models.Index(fields=["session", "statut"]),
            models.Index(fields=["membre", "statut"]),
        ]

    def __str__(self) -> str:
        return f"{self.numero} ({self.membre})"


class FormationQuote(TimeStampedModel):
    class Statut(models.TextChoices):
        DRAFT = "draft", "Brouillon"
        READY = "ready", "Prêt"
        SENT = "sent", "Envoyé"
        CANCELED = "canceled", "Annulé"

    inscription = models.OneToOneField(
        FormationRegistration,
        on_delete=models.CASCADE,
        related_name="quote",
    )

    montant = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"), db_index=True)

    pdf = models.FileField(upload_to="formation/quotes/pdfs/", blank=True, null=True)

    statut = models.CharField(max_length=30, choices=Statut.choices, default=Statut.DRAFT, db_index=True)

    date = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        verbose_name = "Devis"
        verbose_name_plural = "Devis"

    def __str__(self) -> str:
        return f"Devis - {self.inscription.numero}"


class FormationContract(TimeStampedModel):
    class StatutSignature(models.TextChoices):
        PENDING = "pending", "En attente"
        SIGNED = "signed", "Signé"
        CANCELED = "canceled", "Annulé"

    devis = models.OneToOneField(
        FormationQuote,
        on_delete=models.CASCADE,
        related_name="contract",
    )

    contrat_pdf = models.FileField(upload_to="formation/contracts/pdfs/", blank=True, null=True)

    signature_docuseal = models.TextField(blank=True, default="")

    signé = models.BooleanField(default=False, db_index=True)

    date = models.DateTimeField(default=timezone.now, db_index=True)

    statut = models.CharField(
        max_length=30,
        choices=StatutSignature.choices,
        default=StatutSignature.PENDING,
        db_index=True,
    )

    class Meta:
        verbose_name = "Contrat"
        verbose_name_plural = "Contrats"

    def __str__(self) -> str:
        return f"Contrat - {self.devis.inscription.numero}"


class FormationPayment(TimeStampedModel):
    class Methode(models.TextChoices):
        CARD = "card", "Carte"
        BANK = "bank", "Virement"
        CASH = "cash", "Espèces"
        OTHER = "other", "Autre"

    class Statut(models.TextChoices):
        PENDING = "pending", "En attente"
        PAID = "paid", "Payé"
        FAILED = "failed", "Échoué"
        CANCELED = "canceled", "Annulé"

    inscription = models.OneToOneField(
        FormationRegistration,
        on_delete=models.CASCADE,
        related_name="payment",
    )

    montant = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"), db_index=True)

    méthode = models.CharField(max_length=30, choices=Methode.choices, default=Methode.CARD, db_index=True)

    statut = models.CharField(max_length=30, choices=Statut.choices, default=Statut.PENDING, db_index=True)

    reference = models.CharField(max_length=100, blank=True, default="", db_index=True)

    class Meta:
        verbose_name = "Paiement"
        verbose_name_plural = "Paiements"

    def __str__(self) -> str:
        return f"Paiement - {self.inscription.numero}"


class FormationCertificate(TimeStampedModel):
    inscription = models.OneToOneField(
        FormationRegistration,
        on_delete=models.CASCADE,
        related_name="certificate",
    )

    certificat_pdf = models.FileField(upload_to="formation/certificates/pdfs/", blank=True, null=True)

    date = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        verbose_name = "Attestation"
        verbose_name_plural = "Attestations"

    def __str__(self) -> str:
        return f"Certificat - {self.inscription.numero}"


class FormationAccessCode(TimeStampedModel):
    """Code d'accès aux cours en ligne donné par le formateur après paiement."""

    inscription = models.OneToOneField(
        FormationRegistration,
        on_delete=models.CASCADE,
        related_name="access_code",
    )

    code = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text="Code d'accès unique généré ou saisi par le formateur",
    )

    actif = models.BooleanField(default=True, db_index=True)

    attribue_le = models.DateTimeField(null=True, blank=True)
    expire_le = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Code d'accès cours"
        verbose_name_plural = "Codes d'accès cours"

    def __str__(self) -> str:
        return f"Accès {self.code} - {self.inscription.numero}"


class FormationReview(TimeStampedModel):
    membre = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="formation_reviews",
    )

    note = models.PositiveSmallIntegerField(help_text="Note de 1 à 5")
    commentaire = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = "Avis"
        verbose_name_plural = "Avis"
        constraints = [
            models.CheckConstraint(
                condition=Q(note__gte=1, note__lte=5),
                name="formation_review_note_range",
            ),
        ]
        indexes = [
            models.Index(fields=["membre"]),
        ]

    def __str__(self) -> str:
        return f"Avis - {self.membre} ({self.note}/5)"


class FormationPedagogicalDocument(TimeStampedModel):
    """Documents pédagogiques associés à une formation.

    Objectif (UI backoffice): Ajouter / Modifier / Supprimer.
    """

    formation = models.ForeignKey(
        Formation,
        on_delete=models.CASCADE,
        related_name="pedagogical_documents",
    )

    titre = models.CharField(max_length=250)
    description = models.TextField(blank=True, default="")

    # Fichier (PDF/Word/Slides...).
    fichier = models.FileField(upload_to="formation/pedagogical_documents/", blank=True, null=True)

    class Meta:
        verbose_name = "Document pédagogique"
        verbose_name_plural = "Documents pédagogiques"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["formation"]),
        ]

    def __str__(self) -> str:
        return f"{self.formation.titre} - {self.titre}"


