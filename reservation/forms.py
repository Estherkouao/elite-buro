from __future__ import annotations

from django import forms
from django.utils import timezone
from django.core.exceptions import ValidationError

from coworking.models import Workspace
from accounts.models import Company, User

from .models import Reservation, ReservationType, ReservationStatus


class TailwindMixin:
    def _tailwind_attrs(self, attrs=None):
        base = {
            "class": "w-full rounded-xl border border-navy/20 bg-white px-3 py-2 text-sm text-navy/90 shadow-sm focus:outline-none focus:ring-2 focus:ring-gold/60",
        }
        if attrs:
            base.update(attrs)
        return base


class ReservationForm(TailwindMixin, forms.ModelForm):
    class Meta:
        model = Reservation
        fields = (
            "utilisateur",
            "entreprise",
            "espace",
            "type_reservation",
            "date_debut",
            "date_fin",
            "heure_debut",
            "heure_fin",
            "nombre_participants",
            "commentaire",
        )
        widgets = {
            "utilisateur": forms.Select(attrs=TailwindMixin()._tailwind_attrs()),
            "entreprise": forms.Select(attrs=TailwindMixin()._tailwind_attrs()),
            "espace": forms.Select(attrs=TailwindMixin()._tailwind_attrs()),
            "type_reservation": forms.Select(attrs=TailwindMixin()._tailwind_attrs()),
            "date_debut": forms.DateInput(attrs={"type": "date", **TailwindMixin()._tailwind_attrs()}),
            "date_fin": forms.DateInput(attrs={"type": "date", **TailwindMixin()._tailwind_attrs()}),
            "heure_debut": forms.TimeInput(attrs={"type": "time", **TailwindMixin()._tailwind_attrs()}),
            "heure_fin": forms.TimeInput(attrs={"type": "time", **TailwindMixin()._tailwind_attrs()}),
            "nombre_participants": forms.NumberInput(attrs={"min": 1, **TailwindMixin()._tailwind_attrs()}),
            "commentaire": forms.Textarea(attrs={"rows": 3, **TailwindMixin()._tailwind_attrs()}),
           
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        self.fields["espace"].queryset = Workspace.objects.all().select_related("espace").distinct()

        # Request peut être un WSGIRequest (tests) sans attribut user.
        user = getattr(self.request, "user", None)
        if user is not None and getattr(user, "is_authenticated", False):
            self.fields["utilisateur"].queryset = User.objects.filter(pk=user.pk)
            if self.instance and self.instance.pk is None:
                self.fields["utilisateur"].initial = user


    def clean(self):
        cleaned = super().clean()

        date_debut = cleaned.get("date_debut")
        date_fin = cleaned.get("date_fin")
        heure_debut = cleaned.get("heure_debut")
        heure_fin = cleaned.get("heure_fin")
        type_reservation = cleaned.get("type_reservation")

        if date_debut and date_fin and date_fin < date_debut:
            self.add_error("date_fin", "La date de fin doit être égale ou postérieure à la date de début.")

        if heure_debut and heure_fin:
            if heure_fin <= heure_debut:
                self.add_error("heure_fin", "L'heure de fin doit être strictement après l'heure de début.")

        if not type_reservation:
            self.add_error("type_reservation", "Type de réservation obligatoire.")

        nombre_participants = cleaned.get("nombre_participants")
        if nombre_participants is not None and nombre_participants < 1:
            self.add_error("nombre_participants", "Le nombre de participants doit être au moins 1.")

        if date_debut and date_debut < timezone.localdate():
            self.add_error("date_debut", "La date de début ne peut pas être antérieure à aujourd'hui.")

        horaires_types = {
            ReservationType.HOT_DESK,
            ReservationType.PRIVATE_OFFICE,
            ReservationType.MEETING_ROOM,
            ReservationType.TRAINING_ROOM,
            ReservationType.CONFERENCE_ROOM,
        }

        # Si on renseigne heure_debut/heure_fin, on calcule la durée en minutes si possible.
        if heure_debut and heure_fin:
            minutes = (
                (timezone.datetime.combine(timezone.localdate(), heure_fin) - timezone.datetime.combine(timezone.localdate(), heure_debut))
                .total_seconds()
                / 60
            )
            if minutes < 0:
                self.add_error("duree_minutes", "Durée invalide.")
            else:
                cleaned["duree_minutes"] = int(minutes)

        if type_reservation in horaires_types:
            if not heure_debut or not heure_fin:
                self.add_error("heure_debut", "Les heures de début et de fin sont requises pour ce type.")

        return cleaned


class ReservationUpdateForm(ReservationForm):
    class Meta(ReservationForm.Meta):
        fields = (
            "utilisateur",
            "entreprise",
            "espace",
            "type_reservation",
            "date_debut",
            "date_fin",
            "heure_debut",
            "heure_fin",
            "nombre_participants",
            "duree_minutes",
            "commentaire",
            "statut",
        )

    reservation_number = forms.CharField(widget=forms.TextInput(attrs={"readonly": "readonly"}))


class ReservationCancelForm(TailwindMixin, forms.Form):
    commentaire = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3, **TailwindMixin()._tailwind_attrs()}),
        help_text="Optionnel : ajoutez une justification.",
    )


class ReservationFilterForm(TailwindMixin, forms.Form):
    espace = forms.ModelChoiceField(
        queryset=Workspace.objects.all(),
        required=False,
        empty_label="Tous",
        widget=forms.Select(attrs=TailwindMixin()._tailwind_attrs()),
    )
    entreprise = forms.ModelChoiceField(
        queryset=Company.objects.all(),
        required=False,
        empty_label="Toutes",
        widget=forms.Select(attrs=TailwindMixin()._tailwind_attrs()),
    )
    utilisateur = forms.ModelChoiceField(
        queryset=User.objects.all(),
        required=False,
        empty_label="Tous",
        widget=forms.Select(attrs=TailwindMixin()._tailwind_attrs()),
    )

    statut = forms.ChoiceField(
        required=False,
        choices=[("", "Tous")] + list(ReservationStatus.choices),
        widget=forms.Select(attrs=TailwindMixin()._tailwind_attrs()),
    )

    type_reservation = forms.ChoiceField(
        required=False,
        choices=[("", "Tous")] + list(ReservationType.choices),
        widget=forms.Select(attrs=TailwindMixin()._tailwind_attrs()),
    )

    date_debut = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date", **TailwindMixin()._tailwind_attrs()}),
    )
    date_fin = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date", **TailwindMixin()._tailwind_attrs()}),
    )

    montant_min = forms.DecimalField(
        required=False,
        min_value=0,
        max_digits=14,
        decimal_places=2,
        widget=forms.NumberInput(attrs={"placeholder": "Min", **TailwindMixin()._tailwind_attrs()}),
    )

    def clean(self):
        cleaned = super().clean()
        d1 = cleaned.get("date_debut")
        d2 = cleaned.get("date_fin")
        if d1 and d2 and d2 < d1:
            raise ValidationError("La période est invalide : la date de fin doit être >= date de début.")
        return cleaned

