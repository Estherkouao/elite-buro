from __future__ import annotations

from typing import Any

from django import forms

from accounts.models import Company, User
from coworking.models import Workspace

from .forms import ReservationFilterForm
from .models import Reservation


class ReservationFilter:
    """Filtre compatible avec les templates existants.

    Expose un objet avec les attributs attendus par la vue et le template :
    - `qs` : queryset filtré
    - `form` : formulaire de filtres Django
    - `data` : données brutes du GET
    """

    def __init__(self, data: dict[str, Any] | None, queryset):
        self.data = data or {}
        self.form = ReservationFilterForm(self.data)
        self.qs = self._apply_filters(queryset)

    def _apply_filters(self, queryset):
        qs = queryset

        if self.form.is_valid():
            cleaned = self.form.cleaned_data

            espace = cleaned.get("espace")
            if espace:
                qs = qs.filter(espace_id=espace.id)

            entreprise = cleaned.get("entreprise")
            if entreprise:
                qs = qs.filter(entreprise_id=entreprise.id)

            membre = cleaned.get("membre")
            if membre:
                qs = qs.filter(utilisateur_id=membre.id)


            statut = cleaned.get("statut")
            if statut:
                qs = qs.filter(statut=statut)

            type_reservation = cleaned.get("type_reservation")
            if type_reservation:
                qs = qs.filter(type_reservation=type_reservation)

            date_debut_gte = cleaned.get("date_debut")
            if date_debut_gte:
                qs = qs.filter(date_debut__gte=date_debut_gte)

            date_fin_lte = cleaned.get("date_fin")
            if date_fin_lte:
                qs = qs.filter(date_fin__lte=date_fin_lte)

            montant_min = cleaned.get("montant_min")
            if montant_min is not None:
                qs = qs.filter(total__gte=montant_min)

        return qs


