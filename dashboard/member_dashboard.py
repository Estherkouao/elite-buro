from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponseForbidden
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views import View

from accounts.models import User
from domiciliation.models import DomiciliationRequest
from coworking.models import Workspace
from reclamation.models import Reclamation

from .models import Notification, Testimonial, Reservation, Payment
from .permissions import is_member


@dataclass(frozen=True)
class StatusCard:
    icon: str
    label: str
    value: str
    detail: str | None = None


def _format_credits(value: int | Decimal) -> str:
    try:
        return f"{int(value):,}".replace(",", " ") + " F"
    except Exception:
        return "-"


class MemberDashboardView(LoginRequiredMixin, View):
    """Affiche le dashboard membre."""

    template_name = "dashboard/dashboard.html"

    def get(self, request: HttpRequest, *args, **kwargs):
        if not is_member(request.user):
            return HttpResponseForbidden("Accès réservé aux membres.")

        # Statistiques réelles
        reservations_count = Reservation.objects.filter(utilisateur=request.user).count()
        payments_count = Payment.objects.filter(utilisateur=request.user).count()
        domiciliation_count = DomiciliationRequest.objects.filter(utilisateur=request.user).count()
        reclamations_count = Reclamation.objects.filter(auteur=request.user).count()

        # Notifications réelles
        notifications = Notification.objects.filter(utilisateur=request.user).order_by("-date_creation")[:5]
        notifications_unread = Notification.objects.filter(utilisateur=request.user, lu=False).count()

        # Réservations récentes
        reservations = Reservation.objects.filter(utilisateur=request.user).select_related("espace").order_by("-created_at")[:5]

        # Réservations à venir
        today = timezone.localdate()
        upcoming_reservations = []

        # Espaces recommandés
        recommended_spaces = Workspace.objects.all()[:3]

        # Compte / abonnement
        account_status = "Actif" if request.user.is_active else "Inactif"
        credits_available = _format_credits(125000)
        subscription_name = "PREMIUM"
        subscription_expire = timezone.datetime(2026, 8, 15, tzinfo=timezone.utc).date()
        subscription_detail = f"Expire le {subscription_expire.strftime('%d %B %Y')}".replace("  ", " ")

        notifications_qs = Notification.objects.filter(utilisateur=request.user).order_by("-date_creation")
        latest_unread = list(notifications_qs.filter(lu=False)[:2])
        latest_unread_text = "; ".join([n.titre for n in latest_unread]) if latest_unread else "Aucune alerte non lue."

        status_cards = [
            StatusCard(icon="✅", label="Statut du Compte", value=account_status),
            StatusCard(icon="💰", label="Solde de Crédits", value=credits_available, detail="Crédits disponibles"),
            StatusCard(icon="📅", label="Abonnement Actif", value=subscription_name, detail=subscription_detail),
            StatusCard(icon="⚠️", label="Alertes", value=str(notifications_qs.count()), detail=f"À consulter: {latest_unread_text}"),
        ]

        # Vérifier si l'utilisateur a déjà soumis un avis
        existing_testimonial = Testimonial.objects.filter(utilisateur=request.user).first()

        return render(
            request,
            self.template_name,
            {
                "status_cards": status_cards,
                "reservations_count": reservations_count,
                "payments_count": payments_count,
                "domiciliation_count": domiciliation_count,
                "reclamations_count": reclamations_count,
                "notifications_count": notifications_unread,
                "notifications": notifications,
                "reservations": reservations,
                "upcoming_reservations": upcoming_reservations,
                "recommended_spaces": recommended_spaces,
                "existing_testimonial": existing_testimonial,
            },
        )

    def post(self, request: HttpRequest, *args, **kwargs):
        if not is_member(request.user):
            return HttpResponseForbidden("Accès réservé aux membres.")

        note = request.POST.get("note", 5)
        commentaire = request.POST.get("commentaire", "").strip()

        if not commentaire:
            messages.error(request, "Veuillez écrire un commentaire.")
            return redirect("dashboard_admin:member_dashboard")

        # Éviter les doublons (un seul avis par membre)
        existing = Testimonial.objects.filter(utilisateur=request.user).first()
        if existing:
            messages.warning(request, "Vous avez déjà soumis un avis. Merci !")
            return redirect("dashboard_admin:member_dashboard")

        Testimonial.objects.create(
            utilisateur=request.user,
            note=note,
            commentaire=commentaire,
        )

        messages.success(request, "Merci pour votre avis ! Il sera publié après modération.")
        return redirect("dashboard_admin:member_dashboard")
