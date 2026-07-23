from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone

from .models import (
    Notification,
    NotificationStatus,
    NotificationType,
)


class NotificationService:

    @staticmethod
    def notify(
        user,
        title,
        message,
        notification_type=NotificationType.SYSTEM,
        priority="NORMAL",
    ):
        """
        Crée une notification dans la base.
        """

        notification = Notification.objects.create(
            recipient=user,
            title=title,
            message=message,
            notification_type=notification_type,
            priority=priority,
        )

        if notification_type == NotificationType.EMAIL:
            NotificationService.send_email(notification)

        elif notification_type == NotificationType.SMS:
            NotificationService.send_sms(notification)

        elif notification_type == NotificationType.WHATSAPP:
            NotificationService.send_whatsapp(notification)

        return notification

    @staticmethod
    def send_email(notification):

        try:

            send_mail(
                subject=notification.title,
                message=notification.message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[notification.recipient.email],
                fail_silently=False,
            )

            notification.status = NotificationStatus.SENT
            notification.sent_at = timezone.now()
            notification.save(update_fields=["status", "sent_at"])

        except Exception as e:

            notification.status = NotificationStatus.FAILED
            notification.error_message = str(e)
            notification.save(update_fields=["status", "error_message"])

    @staticmethod
    def send_sms(notification):
        """
        Le code SMS sera ajouté plus tard.
        """
        pass

    @staticmethod
    def send_whatsapp(notification):
        """
        Le code WhatsApp sera ajouté plus tard.
        """
        pass