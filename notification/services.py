from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone

from .models import (
    Notification,
    NotificationStatus,
    NotificationType,
)


def send_html_email(
    subject,
    recipient_email,
    template_name,
    context=None,
    from_email=None,
    fail_silently=False,
):
    """
    Envoie un email HTML avec fallback texte brut.
    
    Args:
        subject: Sujet de l'email
        recipient_email: Email du destinataire
        template_name: Nom du template HTML (ex: 'emails/reservation_payment_request.html')
        context: Dictionnaire de contexte pour le template
        from_email: Expéditeur (par défaut DEFAULT_FROM_EMAIL)
        fail_silently: Ne pas lever d'exception en cas d'échec
    
    Returns:
        True si envoyé, False sinon
    """
    if context is None:
        context = {}

    if from_email is None:
        from_email = settings.DEFAULT_FROM_EMAIL

    try:
        # Rendre le template HTML
        html_content = render_to_string(template_name, context)

        # Créer un message avec alternative HTML et texte brut
        email = EmailMultiAlternatives(
            subject=subject,
            body=f"Veuillez activer le format HTML pour visualiser cet email.",
            from_email=from_email,
            to=[recipient_email],
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=fail_silently)

        return True

    except Exception as e:
        if not fail_silently:
            raise e
        return False


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
    def send_html_notification(
        notification,
        template_name,
        context=None,
    ):
        """
        Envoie une notification par email en utilisant un template HTML.
        """
        if context is None:
            context = {}

        # Ajouter des infos de base au contexte
        context.setdefault("user", notification.recipient)
        context.setdefault("title", notification.title)
        context.setdefault("message", notification.message)

        try:
            success = send_html_email(
                subject=notification.title,
                recipient_email=notification.recipient.email,
                template_name=template_name,
                context=context,
                fail_silently=False,
            )

            if success:
                notification.status = NotificationStatus.SENT
                notification.sent_at = timezone.now()
            else:
                notification.status = NotificationStatus.FAILED
                notification.error_message = "Erreur d'envoi"

            notification.save(update_fields=["status", "sent_at", "error_message"])

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
