from __future__ import annotations

from django.contrib import messages
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View

from formation.models import FormationRegistration
from formation.services import (
    notify_member_registration_confirmed,
    notify_trainer_registration_confirmed,
)

from .permissions import is_admin_or_manager
from formation.permissions import FormationAccess


def admin_guard(request: HttpRequest) -> None:
    if not is_admin_or_manager(request.user):
        raise Http404("Page introuvable")


class FormationInscriptionsAdminBaseView(View):
    template_name: str = ""

    def dispatch(self, request: HttpRequest, *args, **kwargs):
        admin_guard(request)
        return super().dispatch(request, *args, **kwargs)

    def access(self) -> FormationAccess:
        return FormationAccess(user=self.request.user)


class AdminInscriptionsListView(FormationInscriptionsAdminBaseView):
    template_name = "dashboard/admin/inscriptions_list.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        registrations = (
            FormationRegistration.objects.select_related(
                "membre",
                "entreprise",
                "session__formation",
                "session__formateur",
            )
            .order_by("-date")
        )
        return render(request, self.template_name, {"inscriptions": registrations})


def _transition_registration(reg: FormationRegistration, target: str) -> None:
    if target == "confirmed":
        reg.statut = FormationRegistration.Statut.CONFIRMED
        reg.save(update_fields=["statut"])
        # Envoyer un email au membre pour l'inviter à payer
        try:
            notify_member_registration_confirmed(reg)
        except Exception:
            pass
        # Envoyer un email au formateur avec la liste des inscrits
        try:
            notify_trainer_registration_confirmed(reg)
        except Exception:
            pass
        return

    if target == "refused":
        # Règle métier (validée): admin refuse uniquement depuis pending
        if reg.statut != FormationRegistration.Statut.PENDING:
            raise ValueError("Refus interdit: statut actuel non autorisé")
        reg.statut = FormationRegistration.Statut.REFUSED
        reg.save(update_fields=["statut"])
        return

    if target == "canceled":
        # Règle métier (validée): annuler uniquement depuis pending
        if reg.statut != FormationRegistration.Statut.PENDING:
            raise ValueError("Annulation interdite: statut actuel non autorisé")
        reg.statut = FormationRegistration.Statut.CANCELED
        reg.save(update_fields=["statut"])
        return

    raise ValueError("Transition inconnue")


class AdminInscriptionActionView(FormationInscriptionsAdminBaseView):
    template_name = ""
    action: str = ""

    def get_registration(self, inscription_id: int) -> FormationRegistration:
        return get_object_or_404(FormationRegistration, id=inscription_id)

    def post(self, request: HttpRequest, inscription_id: int) -> HttpResponse:
        reg = self.get_registration(inscription_id)

        try:
            _transition_registration(reg, self.action)
        except ValueError as e:
            messages.error(request, str(e))
            return redirect(reverse("dashboard_admin:inscriptions_list"))

        messages.success(request, "Inscription mise à jour.")
        return redirect(reverse("dashboard_admin:inscriptions_list"))


class AdminInscriptionValidateView(AdminInscriptionActionView):
    action = "confirmed"


class AdminInscriptionRefuseView(AdminInscriptionActionView):
    action = "refused"


class AdminInscriptionCancelView(AdminInscriptionActionView):
    action = "canceled"

