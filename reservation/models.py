from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Optional
from django.conf import settings
from django.db import models
from django.db.models import UniqueConstraint
from django.utils import timezone

from coworking.models import Workspace


class ReservationType(models.TextChoices):
    PRIVATE_OFFICE = "private_office", "Bureau privé"
    HOT_DESK = "hot_desk", "Hot desk"
    MEETING_ROOM = "meeting_room", "Salle de réunion"
    TRAINING_ROOM = "training_room", "Salle de formation"
    CONFERENCE_ROOM = "conference_room", "Salle de conférence"


class ReservationStatus(models.TextChoices):
    DRAFT = "draft", "Brouillon"
    PENDING = "pending", "En attente"
    AWAITING_PAYMENT = "awaiting_payment", "En attente de paiement"
    CONFIRMED = "confirmed", "Confirmée"
    IN_PROGRESS = "in_progress", "En cours"
    FINISHED = "finished", "Terminée"
    CANCELED = "canceled", "Annulée"
    REFUSED = "refused", "Refusée"
    EXPIRED = "expired", "Expirée"


class Reservation(models.Model):
    """Réservation principale."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    reservation_number = models.CharField(max_length=64, unique=True, db_index=True)

    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reservation_items",
    )


    entreprise = models.ForeignKey(
        "accounts.Company",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reservations",
    )

    espace = models.ForeignKey(
        Workspace,
        on_delete=models.PROTECT,
        related_name="reservations",
    )

    type_reservation = models.CharField(
        max_length=50,
        choices=ReservationType.choices,
        db_index=True,
    )

    date_debut = models.DateField(db_index=True)
    date_fin = models.DateField(db_index=True)

    heure_debut = models.TimeField(null=True, blank=True)
    heure_fin = models.TimeField(null=True, blank=True)

    nombre_participants = models.PositiveIntegerField(default=1)

    # Durée (minutes) calculée pour les réservations horaires
    duree_minutes = models.PositiveIntegerField(default=0)

    # Prix
    prix_unitaire = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    remise = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    taxes = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    montant_total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))

    # Commentaire
    commentaire = models.TextField(blank=True, default="")

    statut = models.CharField(
        max_length=20,
        choices=ReservationStatus.choices,
        default=ReservationStatus.DRAFT,
        db_index=True,
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):

        if not self.reservation_number:

            today = timezone.now().strftime("%Y%m%d")


            last = Reservation.objects.filter(
                reservation_number__startswith=f"RES-{today}"
            ).order_by("-created_at").first()


            if last:

                number = int(
                    last.reservation_number.split("-")[-1]
                ) + 1

            else:

                number = 1


            self.reservation_number = (
                f"RES-{today}-{number:04d}"
            )


        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Reservation"
        verbose_name_plural = "Reservations"
        indexes = [
            models.Index(fields=["espace", "date_debut", "date_fin"]),
            models.Index(fields=["utilisateur", "statut"]),
            models.Index(fields=["entreprise", "statut"]),
        ]
        constraints = [
            UniqueConstraint(fields=["reservation_number"], name="reservation_reservation_number_unique"),
        ]

    @property
    def est_active(self) -> bool:
        return self.statut in {
            ReservationStatus.PENDING,
            ReservationStatus.CONFIRMED,
            ReservationStatus.IN_PROGRESS,
        }

    def __str__(self) -> str:
        return f"Reservation {self.reservation_number}"


    def update_status(self):

        """
        Mise à jour automatique du statut selon le workflow.
        """

        now = timezone.localtime()


        # Les statuts terminaux ne doivent pas être écrasés
        if self.statut in [
            ReservationStatus.CANCELED,
            ReservationStatus.REFUSED,
        ]:
            return



        debut = timezone.make_aware(
            timezone.datetime.combine(
                self.date_debut,
                self.heure_debut or timezone.datetime.min.time()
            )
        )


        fin = timezone.make_aware(
            timezone.datetime.combine(
                self.date_fin,
                self.heure_fin or timezone.datetime.max.time()
            )
        )



        # Avant le début
        if now < debut:

            if self.statut != ReservationStatus.CONFIRMED:

                self.statut = ReservationStatus.PENDING



        # Pendant la réservation
        elif debut <= now <= fin:

            self.statut = ReservationStatus.IN_PROGRESS



        # Après la réservation
        elif now > fin:

            self.statut = ReservationStatus.FINISHED



        self.save(
            update_fields=[
                "statut"
            ]
        )   


class ReservationParticipant(models.Model):
    """Participants liés à une réservation."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    reservation = models.ForeignKey(
        Reservation,
        on_delete=models.CASCADE,
        related_name="participants",
    )

    nom = models.CharField(max_length=120)
    prenom = models.CharField(max_length=120)
    email = models.EmailField()
    telephone = models.CharField(max_length=30)

    class Meta:
        verbose_name = "ReservationParticipant"
        verbose_name_plural = "ReservationParticipants"
        indexes = [
            models.Index(fields=["reservation"]),
            models.Index(fields=["email"]),
        ]

    def __str__(self) -> str:
        return f"{self.prenom} {self.nom}"

        


class ReservationInvoice(models.Model):
    """Facture."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    reservation = models.OneToOneField(
        Reservation,
        on_delete=models.CASCADE,
        related_name="invoice",
    )

    numero = models.CharField(max_length=64, unique=True, db_index=True)
    pdf = models.FileField(upload_to="reservation/invoices/pdfs/")

    montant = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))

    class InvoiceStatus(models.TextChoices):
        DRAFT = "draft", "Brouillon"
        ISSUED = "issued", "Émise"
        PAID = "paid", "Payée"
        CANCELED = "canceled", "Annulée"
        REFUNDED = "refunded", "Remboursée"

    statut = models.CharField(
        max_length=20,
        choices=InvoiceStatus.choices,
        default=InvoiceStatus.DRAFT,
    )


    date = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "ReservationInvoice"
        verbose_name_plural = "ReservationInvoices"

    def __str__(self) -> str:
        return f"Invoice {self.numero}"


class ReservationLog(models.Model):
    """Historique des actions."""

    class ActionType(models.TextChoices):
        CREATED = "created", "Création"
        UPDATED = "updated", "Modification"
        VALIDATED = "validated", "Validation"
        PAYMENT = "payment", "Paiement"
        CANCELED = "canceled", "Annulation"
        CONFIRMED = "confirmed", "Confirmation"
        FINISHED = "finished", "Clôture"
        EXPORTED = "exported", "Export PDF"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    reservation = models.ForeignKey(
        Reservation,
        on_delete=models.CASCADE,
        related_name="logs",
    )

    action = models.CharField(max_length=30, choices=ActionType.choices, db_index=True)
    detail = models.TextField(blank=True, default="")

    acteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reservation_logs",
    )

    date_creation = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        verbose_name = "ReservationLog"
        verbose_name_plural = "ReservationLogs"
        indexes = [
            models.Index(fields=["reservation", "date_creation"]),
        ]

    def __str__(self) -> str:
        return f"{self.reservation.reservation_number} - {self.action}"


class PaymentMethod(models.Model):
    class Meta:
        verbose_name = "Méthode de paiement"
        verbose_name_plural = "Méthodes de paiement"

    id = models.AutoField(primary_key=True)

    nom = models.CharField(max_length=120, unique=True)
    code = models.CharField(max_length=30, unique=True)
    ordre = models.PositiveIntegerField(default=0, db_index=True)
    actif = models.BooleanField(default=True, db_index=True)

    def __str__(self):
        return self.nom


class ReservationReceipt(models.Model):
    class ReceiptStatus(models.TextChoices):
        DRAFT = "draft", "Brouillon"
        ISSUED = "issued", "Émis"
        PAID = "paid", "Payé"
        CANCELED = "canceled", "Annulé"
        REFUNDED = "refunded", "Remboursé"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    invoice = models.ForeignKey(
        "ReservationInvoice",
        on_delete=models.CASCADE,
        related_name="receipts",
    )

    numero = models.CharField(max_length=80, unique=True, db_index=True)

    pdf = models.FileField(upload_to="reservation/receipts/pdfs/")

    montant = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))

    statut = models.CharField(
        max_length=20,
        choices=ReceiptStatus.choices,
        default=ReceiptStatus.DRAFT,
        db_index=True,
    )

    date = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Reçu"
        verbose_name_plural = "Reçus"

    def __str__(self):
        return f"Reçu {self.numero}"


class ReservationReminder(models.Model):
    """Rappels automatiques."""

    class ReminderType(models.TextChoices):
        CREATED = "created", "Réservation créée"
        CONFIRMED = "confirmed", "Réservation confirmée"
        MODIFIED = "modified", "Réservation modifiée"
        CANCELED = "canceled", "Réservation annulée"
        BEFORE = "before", "Rappel avant la réservation"
        FINISHED = "finished", "Réservation terminée"

    class Channel(models.TextChoices):
        EMAIL = "email", "Email"
        SMS = "sms", "SMS"
        INTERNAL = "internal", "Notification interne"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    reservation = models.ForeignKey(
        Reservation,
        on_delete=models.CASCADE,
        related_name="reminders",
    )

    type = models.CharField(max_length=20, choices=ReminderType.choices, db_index=True)
    channel = models.CharField(max_length=20, choices=Channel.choices, default=Channel.EMAIL)

    date_envoi = models.DateTimeField(db_index=True)
    envoyé = models.BooleanField(default=False)

    # Destinataires
    destination = models.CharField(max_length=255, blank=True, default="")

    # Contenu
    titre = models.CharField(max_length=255, blank=True, default="")
    message = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = "ReservationReminder"
        verbose_name_plural = "ReservationReminders"
        indexes = [
            models.Index(fields=["reservation", "date_envoi"]),
            models.Index(fields=["type", "envoyé"]),
        ]

    def __str__(self) -> str:
        return f"Reminder {self.type} ({self.reservation.reservation_number})"

