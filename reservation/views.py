
from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, TemplateView

from coworking.models import Workspace, Category
from dashboard.models import Testimonial

from .filters import ReservationFilter
from .forms import ReservationCancelForm, ReservationForm, ReservationUpdateForm
from .models import Reservation, ReservationLog, ReservationStatus
from .permissions import can_cancel_reservation, can_change_reservation, can_export_invoice, can_view_reservation
from .services import (
    check_availability_conflict,
    create_invoice_for_reservation,
    export_reservation_invoice_pdf,
    generate_calendar_update,
    calculate_amount_for_workspace,
)


class ReservationLandingView(TemplateView):
    template_name = "reservation/landing.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        categories = Category.objects.all().order_by("nom")
        context["categories"] = categories

        popular_spaces = Workspace.objects.select_related(
            "categorie", "espace"
        ).filter(
            vedette=True, disponible=True
        ).order_by("created_at")[:6]
        context["popular_spaces"] = popular_spaces

        context["advantages"] = [
            {"icon": "📶", "title": "Wi-Fi Haut Débit", "description": "Une connexion fibre optique sécurisée et ultra-rapide pour tous vos besoins."},
            {"icon": "❄️", "title": "Climatisation", "description": "Un environnement tempéré pour un confort de travail optimal toute l'année."},
            {"icon": "☕", "title": "Café offert", "description": "Une sélection de cafés et thés premium en libre-service pour nos membres."},
            {"icon": "🔒", "title": "Sécurité 24h/24", "description": "Contrôle d'accès biométrique et surveillance permanente de vos biens."},
            {"icon": "🖨️", "title": "Équipements pro", "description": "Imprimantes, scanners et projecteurs dernière génération à disposition."},
            {"icon": "🧹", "title": "Ménage inclus", "description": "Entretien quotidien de votre espace de travail par notre équipe."},
        ]

        # Vrais témoignages approuvés depuis la base de données
        approved_testimonials = Testimonial.objects.filter(
            approuvé=True
        ).select_related("utilisateur").order_by("-created_at")[:6]
        context["testimonials"] = approved_testimonials
        return context


class ReservationListView(LoginRequiredMixin, View):
    def get(self, request: HttpRequest) -> HttpResponse:
        qs = Reservation.objects.select_related("espace", "utilisateur", "entreprise").all()
        reservation_filter = ReservationFilter(request.GET or None, queryset=qs)

        role = getattr(request.user, "role", None)
        if role in {"MEMBER", "TRAINER"}:
            reservation_filter.qs = reservation_filter.qs.filter(utilisateur=request.user)

        return render(
            request,
            "reservation/index.html",
            {"filter": reservation_filter, "reservations": reservation_filter.qs},
        )


class ReservationCreateView(LoginRequiredMixin, View):

    def get_template_name(self, request):
        if request.user.is_staff or request.user.is_superuser:
            return "dashboard/admin/reservation_create.html"
        return "reservation/create.html"

    def get(self, request):
        form = ReservationForm(request=request)
        return render(request, self.get_template_name(request), {"form": form})

    def post(self, request):
        form = ReservationForm(request.POST, request=request)
        template = self.get_template_name(request)

        if not form.is_valid():
            return render(request, template, {"form": form}, status=400)

        data = form.cleaned_data
        entreprise = data.get("entreprise")
        espace = data["espace"]
        nombre_participants = data.get("nombre_participants", 1)

        montant_bd = calculate_amount_for_workspace(
            espace=espace,
            type_reservation=data["type_reservation"],
            date_debut=data["date_debut"],
            date_fin=data["date_fin"],
            heure_debut=data.get("heure_debut"),
            heure_fin=data.get("heure_fin"),
            nombre_personnes=nombre_participants,
        )

        provisional = Reservation(
            utilisateur=request.user,
            entreprise=entreprise,
            espace=espace,
            type_reservation=data["type_reservation"],
            date_debut=data["date_debut"],
            date_fin=data["date_fin"],
            heure_debut=data.get("heure_debut"),
            heure_fin=data.get("heure_fin"),
            nombre_participants=nombre_participants,
            prix_unitaire=montant_bd.montant,
            remise=montant_bd.remise,
            taxes=montant_bd.taxe,
            montant_total=montant_bd.total,
            statut=ReservationStatus.PENDING,
        )

        try:
            check_availability_conflict(reservation=provisional)
        except Exception as exc:
            messages.error(request, f"⚠️ {exc}")
            return render(request, template, {"form": form}, status=409)

        try:
            reservation = form.save(commit=False)
            reservation.utilisateur = request.user
            reservation.entreprise = entreprise
            reservation.prix_unitaire = montant_bd.montant
            reservation.remise = montant_bd.remise
            reservation.taxes = montant_bd.taxe
            reservation.montant_total = montant_bd.total
            reservation.nombre_participants = nombre_participants
            reservation.statut = ReservationStatus.PENDING
            reservation.save()

            ReservationLog.objects.create(
                reservation=reservation,
                action=ReservationLog.ActionType.CREATED,
                acteur=request.user,
                detail=f"Création réservation {reservation.reservation_number}",
            )

            create_invoice_for_reservation(reservation)

        except Exception as exc:
            messages.error(request, f"Erreur lors de la création : {exc}")
            return render(request, template, {"form": form}, status=500)

        messages.success(request, "Réservation créée avec succès.")

        if request.user.is_staff or request.user.is_superuser:
            return redirect("dashboard_admin:reservations")
        return redirect("reservation:detail", reservation_id=reservation.id)


class ReservationDetailView(LoginRequiredMixin, DetailView):
    model = Reservation
    template_name = "reservation/detail.html"
    context_object_name = "reservation"
    pk_url_kwarg = "reservation_id"

    def get_object(self):
        reservation = get_object_or_404(
            Reservation.objects.select_related("espace", "utilisateur", "entreprise"),
            id=self.kwargs["reservation_id"],
        )
        if not can_view_reservation(self.request.user, reservation):
            raise Http404("Réservation introuvable")
        return reservation


class ReservationUpdateView(LoginRequiredMixin, View):
    def get(self, request: HttpRequest, reservation_id) -> HttpResponse:
        reservation = get_object_or_404(Reservation, id=reservation_id)
        if not can_change_reservation(request.user, reservation):
            raise Http404("Réservation introuvable")

        form = ReservationUpdateForm(request=request, instance=reservation)
        return render(request, "reservation/edit.html", {"form": form, "reservation": reservation})

    def post(self, request: HttpRequest, reservation_id) -> HttpResponse:
        reservation = get_object_or_404(Reservation, id=reservation_id)
        if not can_change_reservation(request.user, reservation):
            raise Http404("Réservation introuvable")

        form = ReservationUpdateForm(request.POST, request=request, instance=reservation)
        if not form.is_valid():
            return render(request, "reservation/edit.html", {"form": form, "reservation": reservation}, status=400)

        updated = form.save(commit=False)

        bd = calculate_amount_for_workspace(
            espace=updated.espace,
            type_reservation=updated.type_reservation,
            date_debut=updated.date_debut,
            date_fin=updated.date_fin,
            heure_debut=updated.heure_debut,
            heure_fin=updated.heure_fin,
            nombre_personnes=updated.nombre_personnes,
        )
        updated.montant = bd.montant
        updated.remise = bd.remise
        updated.taxe = bd.taxe
        updated.total = bd.total
        updated.updated_at = timezone.now()
        updated.statut = Reservation.Status.PENDING

        try:
            check_availability_conflict(reservation=updated, ignore_reservation_id=reservation.id)
        except Exception as exc:
            messages.error(request, f"Conflit / indisponibilité: {exc}")
            return render(request, "reservation/edit.html", {"form": form, "reservation": reservation}, status=409)

        updated.save()

        ReservationLog.objects.create(
            reservation=updated,
            action=ReservationLog.ActionType.UPDATED,
            acteur=request.user,
            detail="Modification réservation",
        )

        messages.success(request, "Réservation mise à jour.")
        return redirect(reverse("reservation:detail", kwargs={"reservation_id": updated.id}))


class ReservationCancelView(LoginRequiredMixin, View):
    def get(self, request: HttpRequest, reservation_id) -> HttpResponse:
        reservation = get_object_or_404(Reservation, id=reservation_id)
        if not can_cancel_reservation(request.user, reservation):
            raise Http404("Réservation introuvable")

        form = ReservationCancelForm()
        return render(request, "reservation/cancel.html", {"form": form, "reservation": reservation})

    def post(self, request: HttpRequest, reservation_id) -> HttpResponse:
        reservation = get_object_or_404(Reservation, id=reservation_id)
        if not can_cancel_reservation(request.user, reservation):
            raise Http404("Réservation introuvable")

        form = ReservationCancelForm(request.POST)
        if not form.is_valid():
            return render(request, "reservation/cancel.html", {"form": form, "reservation": reservation}, status=400)

        reservation.statut = ReservationStatus.CANCELED
        reservation.commentaire = form.cleaned_data.get("commentaire", "")
        reservation.updated_at = timezone.now()
        reservation.save(update_fields=["statut", "commentaire", "updated_at"])

        ReservationLog.objects.create(
            reservation=reservation,
            action=ReservationLog.ActionType.CANCELED,
            acteur=request.user,
            detail="Annulation réservation",
        )

        messages.success(request, "Réservation annulée.")
        return redirect(reverse("reservation:list"))


class ReservationInvoiceView(LoginRequiredMixin, View):

    def get(self, request: HttpRequest, reservation_id) -> HttpResponse:

        reservation = get_object_or_404(
            Reservation.objects.select_related("invoice"),
            id=reservation_id
        )

        if not can_export_invoice(request.user, reservation):
            raise Http404("Facture introuvable")


        try:
            invoice = reservation.invoice

        except ReservationInvoice.DoesNotExist:
            invoice = create_invoice_for_reservation(reservation)


        pdf_path = export_reservation_invoice_pdf(
            reservation=reservation
        )


        return render(
            request,
            "reservation/invoice.html",
            {
                "reservation": reservation,
                "invoice": invoice,
                "pdf_path": pdf_path
            }
        )


class ReservationCalendarView(LoginRequiredMixin, View):
    def get(self, request: HttpRequest) -> HttpResponse:
        espace_id = request.GET.get("espace_id")
        from_date = request.GET.get("from")
        days = int(request.GET.get("days", "14"))

        if not espace_id:
            return render(request, "reservation/calendar.html", {"slots": [], "error": "espace_id requis"}, status=400)

        return render(request, "reservation/calendar.html", {"slots": [], "espace_id": espace_id, "from": from_date, "days": days})


class ReservationHistoryView(LoginRequiredMixin, View):
    def get(self, request: HttpRequest) -> HttpResponse:
        role = getattr(request.user, "role", None)
        if role == "MEMBER":
            reservations = Reservation.objects.filter(utilisateur=request.user).prefetch_related("status_history", "logs")
        else:
            reservations = Reservation.objects.all().prefetch_related("status_history", "logs")

        return render(request, "reservation/history.html", {"reservations": reservations})


class ReservationSearchView(LoginRequiredMixin, View):
    def get(self, request: HttpRequest) -> HttpResponse:
        reservation_filter = ReservationFilter(
            request.GET or None,
            queryset=Reservation.objects.select_related("espace", "utilisateur", "entreprise"),
        )
        return render(
            request,
            "reservation/search.html",
            {"filter": reservation_filter, "reservations": reservation_filter.qs},
        )
