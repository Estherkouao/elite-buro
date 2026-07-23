from __future__ import annotations

from django.contrib import messages
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import TemplateView

from reservation.models import (
    PaymentMethod,
    Reservation,
    ReservationInvoice,
    ReservationReceipt,
)
from reservation.permissions import (
    can_cancel_reservation,
    can_export_invoice,
    can_view_reservation,
)
from reservation.services import (
    admin_cancel_reservation,
    export_reservation_invoice_pdf,
)

from .permissions import is_admin_or_manager


def admin_guard(request: HttpRequest) -> None:
    if not is_admin_or_manager(request.user):
        raise Http404("Page introuvable")


class AdminPaymentsBaseView(View):
    template_name: str = ""

    def dispatch(self, request: HttpRequest, *args, **kwargs):
        admin_guard(request)
        return super().dispatch(request, *args, **kwargs)


class AdminPaymentsListView(AdminPaymentsBaseView):
    template_name = "dashboard/admin/payments/index.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        payments = Reservation.objects.select_related("espace", "utilisateur", "entreprise", "invoice").all()
        # For now we show reservations that have an invoice.
        invoices = [getattr(r, "invoice", None) for r in payments]
        invoices = [i for i in invoices if i is not None]
        return render(
            request,
            self.template_name,
            {
                "invoices": invoices,
            },
        )


class AdminPaymentsReservationView(AdminPaymentsBaseView):
    template_name = "dashboard/admin/payments/reservation_detail.html"

    def get(self, request: HttpRequest, reservation_id) -> HttpResponse:
        reservation = get_object_or_404(
            Reservation.objects.select_related("invoice", "utilisateur", "entreprise", "espace"),
            id=reservation_id,
        )
        if not can_view_reservation(request.user, reservation):
            raise Http404("Réservation introuvable")
        invoice = getattr(reservation, "invoice", None)
        receipt = None
        if invoice:
            receipt = invoice.receipts.first() if hasattr(invoice, "receipts") else None
        return render(
            request,
            self.template_name,
            {"reservation": reservation, "invoice": invoice, "receipt": receipt},
        )


class AdminPaymentConfirmView(AdminPaymentsBaseView):
    def post(self, request: HttpRequest, reservation_id) -> HttpResponse:
        # Confirm reservation invoice (simple): mark reservation confirmed and export invoice.
        reservation = get_object_or_404(Reservation, id=reservation_id)
        if not can_view_reservation(request.user, reservation):
            raise Http404("Réservation introuvable")

        # For now we only export invoice PDF and rely on reservation admin service for status changes.
        # This is close to the requested “Confirmer”.
        from reservation.services import admin_confirm_reservation, export_reservation_invoice_pdf

        admin_confirm_reservation(request.user, reservation)
        export_reservation_invoice_pdf(reservation=reservation)

        messages.success(request, "Réservation confirmée et facture exportée.")
        return redirect(reverse("dashboard_admin:payments"))



class AdminPaymentCancelView(AdminPaymentsBaseView):
    def post(self, request: HttpRequest, reservation_id) -> HttpResponse:
        reservation = get_object_or_404(Reservation, id=reservation_id)
        if not can_cancel_reservation(request.user, reservation):
            raise Http404("Réservation introuvable")
        admin_cancel_reservation(request.user, reservation)
        messages.success(request, "Réservation annulée.")
        return redirect(reverse("dashboard_admin:payments"))


class AdminPaymentRefundView(AdminPaymentsBaseView):
    def post(self, request: HttpRequest, reservation_id) -> HttpResponse:
        # Refund placeholder: if receipt exists, mark refunded and export receipt.
        reservation = get_object_or_404(Reservation, id=reservation_id)
        if not can_cancel_reservation(request.user, reservation):
            # Use cancel permission as a conservative guard.
            raise Http404("Réservation introuvable")

        invoice = getattr(reservation, "invoice", None)
        receipt = None
        if invoice and hasattr(invoice, "receipts"):
            receipt = invoice.receipts.first()

        if receipt is None:
            # Create receipt in DRAFT as a placeholder.
            from reservation.models import ReservationReceipt
            receipt = ReservationReceipt.objects.create(
                invoice=invoice,
                numero=f"RCPT-{reservation.reservation_number}",
                montant=getattr(invoice, "montant", 0),
                statut=ReservationReceipt.ReceiptStatus.REFUNDED,
            )

        else:
            receipt.statut = receipt.ReceiptStatus.REFUNDED
            receipt.save(update_fields=["statut"])

        messages.success(request, "Remboursement marqué comme effectué (placeholder).")
        return redirect(reverse("dashboard_admin:payments"))



class AdminInvoicesDownloadView(AdminPaymentsBaseView):
    def get(self, request: HttpRequest, invoice_id) -> HttpResponse:
        invoice = get_object_or_404(ReservationInvoice, id=invoice_id)
        # Use file field to serve.
        if not invoice.pdf:
            raise Http404("PDF introuvable")
        # Let Django handle file response.
        return redirect(invoice.pdf.url)


class AdminReceiptDownloadView(AdminPaymentsBaseView):
    def get(self, request: HttpRequest, receipt_id) -> HttpResponse:
        receipt = get_object_or_404(ReservationReceipt, id=receipt_id)
        if not receipt.pdf:
            raise Http404("PDF introuvable")
        return redirect(receipt.pdf.url)


# Payment methods CRUD (simple Model CRUD)
class AdminPaymentMethodListView(AdminPaymentsBaseView):
    template_name = "dashboard/admin/payments/payment_methods/index.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        methods = PaymentMethod.objects.all().order_by("ordre", "nom")
        return render(request, self.template_name, {"methods": methods})


class AdminPaymentMethodCreateView(AdminPaymentsBaseView):
    template_name = "dashboard/admin/payments/payment_methods/create.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        return render(request, self.template_name)

    def post(self, request: HttpRequest) -> HttpResponse:
        nom = request.POST.get("nom", "").strip()
        code = request.POST.get("code", "").strip()
        ordre = int(request.POST.get("ordre", "0") or 0)
        if not nom or not code:
            messages.error(request, "Nom et code sont requis.")
            return redirect(reverse("dashboard_admin:payment_methods_create"))
        PaymentMethod.objects.create(nom=nom, code=code, ordre=ordre, actif=True)
        messages.success(request, "Méthode créée.")
        return redirect(reverse("dashboard_admin:payment_methods"))


class AdminPaymentMethodEditView(AdminPaymentsBaseView):
    template_name = "dashboard/admin/payments/payment_methods/edit.html"

    def get(self, request: HttpRequest, method_id: int) -> HttpResponse:
        method = get_object_or_404(PaymentMethod, id=method_id)
        return render(request, self.template_name, {"method": method})

    def post(self, request: HttpRequest, method_id: int) -> HttpResponse:
        method = get_object_or_404(PaymentMethod, id=method_id)
        nom = request.POST.get("nom", "").strip()
        code = request.POST.get("code", "").strip()
        ordre = int(request.POST.get("ordre", "0") or 0)
        if not nom or not code:
            messages.error(request, "Nom et code sont requis.")
            return redirect(reverse("dashboard_admin:payment_methods_edit", kwargs={"method_id": method_id}))
        method.nom = nom
        method.code = code
        method.ordre = ordre
        method.save(update_fields=["nom", "code", "ordre"])
        messages.success(request, "Méthode modifiée.")
        return redirect(reverse("dashboard_admin:payment_methods"))


class AdminPaymentMethodDeleteView(AdminPaymentsBaseView):
    template_name = "dashboard/admin/payments/payment_methods/delete.html"

    def get(self, request: HttpRequest, method_id: int) -> HttpResponse:
        method = get_object_or_404(PaymentMethod, id=method_id)
        return render(request, self.template_name, {"method": method})

    def post(self, request: HttpRequest, method_id: int) -> HttpResponse:
        method = get_object_or_404(PaymentMethod, id=method_id)
        method.delete()
        messages.success(request, "Méthode supprimée.")
        return redirect(reverse("dashboard_admin:payment_methods"))

