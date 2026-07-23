from django.db import models

# Create your models here.
from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid


class NotificationType(models.TextChoices):
    EMAIL = "EMAIL", "Email"
    SMS = "SMS", "SMS"
    WHATSAPP = "WHATSAPP", "WhatsApp"
    SYSTEM = "SYSTEM", "Notification interne"


class NotificationStatus(models.TextChoices):
    PENDING = "PENDING", "En attente"
    SENT = "SENT", "Envoyée"
    FAILED = "FAILED", "Échec"
    READ = "READ", "Lue"


class NotificationPriority(models.TextChoices):
    LOW = "LOW", "Faible"
    NORMAL = "NORMAL", "Normale"
    HIGH = "HIGH", "Élevée"
    URGENT = "URGENT", "Urgente"


class Notification(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications"
    )

    notification_type = models.CharField(
        max_length=20,
        choices=NotificationType.choices,
        default=NotificationType.SYSTEM
    )

    priority = models.CharField(
        max_length=20,
        choices=NotificationPriority.choices,
        default=NotificationPriority.NORMAL
    )

    title = models.CharField(
        max_length=255
    )

    message = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=NotificationStatus.choices,
        default=NotificationStatus.PENDING
    )

    is_read = models.BooleanField(
        default=False
    )

    read_at = models.DateTimeField(
        null=True,
        blank=True
    )

    sent_at = models.DateTimeField(
        null=True,
        blank=True
    )

    error_message = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"

    def __str__(self):
        return f"{self.title} ({self.recipient})"

    def mark_as_read(self):
        self.is_read = True
        self.status = NotificationStatus.READ
        self.read_at = timezone.now()
        self.save(update_fields=["is_read", "status", "read_at"])


class NotificationTemplate(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    name = models.CharField(
        max_length=150,
        unique=True
    )

    notification_type = models.CharField(
        max_length=20,
        choices=NotificationType.choices
    )

    subject = models.CharField(
        max_length=255,
        blank=True
    )

    content = models.TextField()

    active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Modèle de notification"
        verbose_name_plural = "Modèles de notification"

    def __str__(self):
        return self.name


class NotificationLog(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        related_name="logs"
    )

    action = models.CharField(
        max_length=100
    )

    details = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Journal de notification"
        verbose_name_plural = "Journal des notifications"

    def __str__(self):
        return self.action
        
                        