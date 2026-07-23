from django import forms
from django.core.exceptions import ValidationError

from .models import (
    Category,
    CoworkingSpace,
    Equipment,
    Workspace,
    WorkspaceAvailability,
    WorkspaceEquipment,
    WorkspaceImage,
    WorkspacePrice,
    WorkspaceReview,
)


class CoworkingSpaceForm(forms.ModelForm):
    class Meta:
        model = CoworkingSpace
        fields = (
            "nom",
            "description",
            "adresse",
            "ville",
            "pays",
            "telephone",
            "email",
            "latitude",
            "longitude",
            "image_principale",
            "logo",
            "horaires",
            "statut",
        )
        widgets = {
            "nom": forms.TextInput(attrs={"class": "w-full border border-navy/10 rounded-md px-3 py-2"}),
            "description": forms.Textarea(attrs={"class": "w-full border border-navy/10 rounded-md px-3 py-2", "rows": 4}),
            "adresse": forms.TextInput(attrs={"class": "w-full border border-navy/10 rounded-md px-3 py-2"}),
            "ville": forms.TextInput(attrs={"class": "w-full border border-navy/10 rounded-md px-3 py-2"}),
            "pays": forms.TextInput(attrs={"class": "w-full border border-navy/10 rounded-md px-3 py-2"}),
            "telephone": forms.TextInput(attrs={"class": "w-full border border-navy/10 rounded-md px-3 py-2"}),
            "email": forms.EmailInput(attrs={"class": "w-full border border-navy/10 rounded-md px-3 py-2"}),
            "latitude": forms.NumberInput(attrs={"class": "w-full border border-navy/10 rounded-md px-3 py-2", "step": "0.0000001"}),
            "longitude": forms.NumberInput(attrs={"class": "w-full border border-navy/10 rounded-md px-3 py-2", "step": "0.0000001"}),
            "horaires": forms.Textarea(attrs={"class": "w-full border border-navy/10 rounded-md px-3 py-2", "rows": 3}),
            "statut": forms.Select(attrs={"class": "w-full border border-navy/10 rounded-md px-3 py-2"}),
        }

    def clean_slug(self):
        slug = self.cleaned_data.get("slug")
        if slug:
            return slug
        return slug


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ("nom", "slug", "description", "icone", "image")
        widgets = {
            "nom": forms.TextInput(attrs={"class": "w-full border border-navy/10 rounded-md px-3 py-2"}),
            "slug": forms.TextInput(attrs={"class": "w-full border border-navy/10 rounded-md px-3 py-2"}),
            "description": forms.Textarea(attrs={"class": "w-full border border-navy/10 rounded-md px-3 py-2", "rows": 4}),
            "icone": forms.TextInput(attrs={"class": "w-full border border-navy/10 rounded-md px-3 py-2"}),
        }


class EquipmentForm(forms.ModelForm):
    class Meta:
        model = Equipment
        fields = ("nom", "slug")
        widgets = {
            "nom": forms.TextInput(attrs={"class": "w-full border border-navy/10 rounded-md px-3 py-2"}),
            "slug": forms.TextInput(attrs={"class": "w-full border border-navy/10 rounded-md px-3 py-2"}),
        }


class WorkspaceForm(forms.ModelForm):
    class Meta:
        model = Workspace
        fields = (
            "categorie",
            "nom",
            "description",
            "capacite",
            "superficie",
            "etage",
            "numero",
            "prix_heure",
            "prix_demi_journee",
            "prix_journee",
            "prix_semaine",
            "prix_mois",
            "caution",
            "disponible",
            "vedette",
            "image_principale",
        )
        widgets = {
            "description": forms.Textarea(attrs={"class": "w-full border border-navy/10 rounded-md px-3 py-2", "rows": 4}),
            "capacite": forms.NumberInput(attrs={"class": "w-full border border-navy/10 rounded-md px-3 py-2"}),
            "superficie": forms.NumberInput(attrs={"class": "w-full border border-navy/10 rounded-md px-3 py-2"}),
            "prix_heure": forms.NumberInput(attrs={"class": "w-full border border-navy/10 rounded-md px-3 py-2", "step": "0.01"}),
            "prix_demi_journee": forms.NumberInput(attrs={"class": "w-full border border-navy/10 rounded-md px-3 py-2", "step": "0.01"}),
            "prix_journee": forms.NumberInput(attrs={"class": "w-full border border-navy/10 rounded-md px-3 py-2", "step": "0.01"}),
            "prix_semaine": forms.NumberInput(attrs={"class": "w-full border border-navy/10 rounded-md px-3 py-2", "step": "0.01"}),
            "prix_mois": forms.NumberInput(attrs={"class": "w-full border border-navy/10 rounded-md px-3 py-2", "step": "0.01"}),
            "caution": forms.NumberInput(attrs={"class": "w-full border border-navy/10 rounded-md px-3 py-2", "step": "0.01"}),
            "etage": forms.TextInput(attrs={"class": "w-full border border-navy/10 rounded-md px-3 py-2"}),
            "numero": forms.TextInput(attrs={"class": "w-full border border-navy/10 rounded-md px-3 py-2"}),
            "nom": forms.TextInput(attrs={"class": "w-full border border-navy/10 rounded-md px-3 py-2"}),
        }

    def clean(self):
        cleaned = super().clean()
        prix_heure = cleaned.get("prix_heure")
        if prix_heure is not None and prix_heure < 0:
            self.add_error("prix_heure", "Le prix heure doit être positif.")
        return cleaned


class WorkspaceAvailabilityForm(forms.ModelForm):
    class Meta:
        model = WorkspaceAvailability
        fields = ("espace", "date", "heure_debut", "heure_fin", "disponible")
        widgets = {
            "date": forms.DateInput(attrs={"class": "w-full border border-navy/10 rounded-md px-3 py-2"}),
            "heure_debut": forms.TimeInput(attrs={"class": "w-full border border-navy/10 rounded-md px-3 py-2"}),
            "heure_fin": forms.TimeInput(attrs={"class": "w-full border border-navy/10 rounded-md px-3 py-2"}),
        }

    def clean(self):
        cleaned = super().clean()
        h_debut = cleaned.get("heure_debut")
        h_fin = cleaned.get("heure_fin")
        if h_debut and h_fin and h_fin <= h_debut:
            self.add_error("heure_fin", "L'heure de fin doit être strictement supérieure à l'heure de début.")
        return cleaned


class WorkspacePriceForm(forms.ModelForm):
    class Meta:
        model = WorkspacePrice
        fields = (
            "espace",
            "prix_heure",
            "prix_demi_journee",
            "prix_journee",
            "prix_semaine",
            "prix_mois",
        )
        widgets = {
            "prix_heure": forms.NumberInput(attrs={"class": "w-full border border-navy/10 rounded-md px-3 py-2", "step": "0.01"}),
            "prix_demi_journee": forms.NumberInput(attrs={"class": "w-full border border-navy/10 rounded-md px-3 py-2", "step": "0.01"}),
            "prix_journee": forms.NumberInput(attrs={"class": "w-full border border-navy/10 rounded-md px-3 py-2", "step": "0.01"}),
            "prix_semaine": forms.NumberInput(attrs={"class": "w-full border border-navy/10 rounded-md px-3 py-2", "step": "0.01"}),
            "prix_mois": forms.NumberInput(attrs={"class": "w-full border border-navy/10 rounded-md px-3 py-2", "step": "0.01"}),
        }


class WorkspaceImageForm(forms.ModelForm):
    class Meta:
        model = WorkspaceImage
        fields = ("workspace", "image")


class WorkspaceEquipmentForm(forms.ModelForm):
    class Meta:
        model = WorkspaceEquipment
        fields = ("workspace", "equipment")


class WorkspaceReviewForm(forms.ModelForm):
    class Meta:
        model = WorkspaceReview
        fields = ("espace", "note", "commentaire")

    def clean_note(self):
        note = self.cleaned_data["note"]
        if note < 1 or note > 5:
            raise ValidationError("La note doit être comprise entre 1 et 5.")
        return note

