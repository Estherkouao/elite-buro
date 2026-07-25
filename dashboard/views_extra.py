from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import TemplateView

from .models import Favorite, Notification, Payment, Reservation, Workspace
from .permissions import is_member

from reservation.models import ReservationInvoice, Reservation
from reservation.services import export_reservation_invoice_pdf


def member_guard(user):
    if not is_member(user):
        raise PermissionError("Accès réservé aux membres.")


@method_decorator(login_required, name="dispatch")
class MemberFavoritesView(TemplateView):
    template_name = "dashboard/favorites.html"

    def get(self, request, *args, **kwargs):
        if not is_member(request.user):
            return HttpResponseForbidden("Accès réservé aux membres.")
        favorites = Favorite.objects.filter(utilisateur=request.user).select_related("espace")
        return render(request, self.template_name, {"favorites": favorites})


@method_decorator(login_required, name="dispatch")
class MemberPaymentsView(TemplateView):
    """Affiche toutes les factures du membre connecté."""

    template_name = "dashboard/payments.html"

    def get(self, request, *args, **kwargs):
        if not is_member(request.user):
            return HttpResponseForbidden("Accès réservé aux membres.")

        # Récupérer les réservations de l'utilisateur, avec leurs factures
        reservations = Reservation.objects.filter(
            utilisateur=request.user
        ).select_related("invoice", "espace").order_by("-created_at")

        # Récupérer les factures existantes
        invoices = []
        for r in reservations:
            if hasattr(r, "invoice") and r.invoice is not None:
                invoices.append(r.invoice)

        return render(request, self.template_name, {"invoices": invoices})


@method_decorator(login_required, name="dispatch")
class MemberNotificationsView(TemplateView):
    template_name = "dashboard/notifications.html"

    def get(self, request, *args, **kwargs):
        if not is_member(request.user):
            return HttpResponseForbidden("Accès réservé aux membres.")
        notifications = Notification.objects.filter(utilisateur=request.user).order_by("-date_creation")
        return render(request, self.template_name, {"notifications": notifications})


@method_decorator(login_required, name="dispatch")
class MemberNotificationMarkReadView(View):
    def post(self, request, *args, **kwargs):
        if not is_member(request.user):
            return HttpResponseForbidden("Accès réservé aux membres.")
        notif_id = request.POST.get("notification_id")
        notification = get_object_or_404(Notification, id=notif_id, utilisateur=request.user)
        notification.lu = True
        notification.save(update_fields=["lu"])
        return redirect("dashboard:notifications")


@method_decorator(login_required, name="dispatch")
class MemberReservationDetailView(TemplateView):
    template_name = "dashboard/reservation_detail.html"

    def get(self, request, reservation_id, *args, **kwargs):
        if not is_member(request.user):
            return HttpResponseForbidden("Accès réservé aux membres.")
        reservation = get_object_or_404(Reservation, id=reservation_id, utilisateur=request.user)
        payment = Payment.objects.filter(utilisateur=request.user, reservation=reservation).first()

        # NOTE: PDF/QR not implemented yet; template provides placeholders.
        return render(
            request,
            self.template_name,
            {
                "reservation": reservation,
                "payment": payment,
            },
        )

