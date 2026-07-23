from __future__ import annotations

import uuid
from decimal import Decimal
from django.db import models
from django.utils import timezone
from django.conf import settings


class PaymentProvider(models.Model):

    PROVIDER_CHOICES = (
        ("cinetpay", "CinetPay"),
        ("paypal", "PayPal"),
        ("orange", "Orange Money"),
        ("wave", "Wave"),
        ("mtn", "MTN Mobile Money"),
        ("moov", "Moov Money"),
        ("visa", "Visa / Mastercard"),
        ("stripe", "Stripe"),
        ("manual", "Paiement manuel"),
    )

    name = models.CharField(max_length=100, verbose_name="Nom du fournisseur")

    code = models.CharField(
        max_length=50,
        choices=PROVIDER_CHOICES,
        unique=True,
        verbose_name="Code fournisseur",
    )

    description = models.TextField(
        blank=True, default="", verbose_name="Description"
    )

    api_key = models.CharField(
        max_length=255, blank=True, default="", verbose_name="Clé API"
    )

    api_secret = models.CharField(
        max_length=255, blank=True, default="", verbose_name="Secret API"
    )

    merchant_id = models.CharField(
        max_length=255, blank=True, default="", verbose_name="Identifiant marchand"
    )

    endpoint_url = models.CharField(
        max_length=500,
        blank=True,
        default="",
        verbose_name="URL de l'endpoint",
        help_text="URL de l'API pour les appels en production",
    )

    sandbox_mode = models.BooleanField(
        default=True,
        verbose_name="Mode test (sandbox)",
        help_text="Utiliser l'environnement de test au lieu de la production",
    )

    sandbox_endpoint = models.CharField(
        max_length=500,
        blank=True,
        default="",
        verbose_name="URL sandbox",
        help_text="URL de l'API pour les appels en mode test",
    )

    config_json = models.JSONField(
        blank=True,
        default=dict,
        verbose_name="Configuration supplémentaire (JSON)",
        help_text="Paramètres additionnels au format JSON",
    )

    is_active = models.BooleanField(
        default=True, verbose_name="Actif", db_index=True
    )

    display_order = models.PositiveIntegerField(
        default=0, verbose_name="Ordre d'affichage", db_index=True
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Dernière modification")

    class Meta:
        verbose_name = "Fournisseur de paiement"
        verbose_name_plural = "Fournisseurs de paiement"
        ordering = ["display_order", "name"]

    def __str__(self):
        return f"{self.name} ({self.get_code_display()})"

    def get_endpoint(self) -> str:
        """Retourne l'URL de l'API selon le mode sandbox ou production."""
        if self.sandbox_mode and self.sandbox_endpoint:
            return self.sandbox_endpoint
        return self.endpoint_url


class PaymentTransaction(models.Model):

    STATUS_CHOICES = (
        ("pending", "En attente"),
        ("processing", "En cours de traitement"),
        ("success", "Réussi"),
        ("failed", "Échoué"),
        ("cancelled", "Annulé"),
        ("refunded", "Remboursé"),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payment_transactions",
        verbose_name="Utilisateur",
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    reservation = models.ForeignKey(
        "reservation.Reservation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payment_transactions",
        verbose_name="Réservation",
    )

    provider = models.ForeignKey(
        PaymentProvider,
        on_delete=models.SET_NULL,
        null=True,
        related_name="transactions",
        verbose_name="Fournisseur de paiement",
    )

    transaction_id = models.CharField(
        max_length=255, unique=True, verbose_name="ID Transaction"
    )

    reference = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Référence locale",
        db_index=True,
    )

    amount = models.DecimalField(
        max_digits=14, decimal_places=2, verbose_name="Montant"
    )

    currency = models.CharField(
        max_length=10, default="XOF", verbose_name="Devise"
    )

    phone_number = models.CharField(
        max_length=30, blank=True, default="", verbose_name="Numéro de téléphone"
    )

    email = models.EmailField(
        blank=True, default="", verbose_name="Email du payeur"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
        db_index=True,
        verbose_name="Statut",
    )

    provider_data = models.JSONField(
        blank=True, default=dict, verbose_name="Données du fournisseur"
    )

    error_message = models.TextField(
        blank=True, default="", verbose_name="Message d'erreur"
    )

    payment_date = models.DateTimeField(
        null=True, blank=True, verbose_name="Date de paiement"
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Dernière modification")

    class Meta:
        verbose_name = "Transaction de paiement"
        verbose_name_plural = "Transactions de paiement"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["transaction_id"]),
            models.Index(fields=["reference"]),
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"Transaction {self.transaction_id} - {self.amount} {self.currency} ({self.get_status_display()})"

    def mark_success(self) -> None:
        self.status = "success"
        self.payment_date = timezone.now()
        self.save(update_fields=["status", "payment_date", "updated_at"])

    def mark_failed(self, error: str = "") -> None:
        self.status = "failed"
        self.error_message = error
        self.save(update_fields=["status", "error_message", "updated_at"])

    def mark_refunded(self) -> None:
        self.status = "refunded"
        self.save(update_fields=["status", "updated_at"])
