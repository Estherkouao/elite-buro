from __future__ import annotations

import datetime

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import (
    Formation,
    FormationCategory,
    FormationCertificate,
    FormationContract,
    FormationPayment,
    FormationQuote,
    FormationRegistration,
    FormationSession,
    Trainer,
    FormationReview,
)


class TailwindMixin:
    def _set_common_attrs(self, widget: forms.Widget, extra_classes: str = "") -> forms.Widget:
        classes = widget.attrs.get("class", "")
        if extra_classes:
            widget.attrs["class"] = f"{classes} {extra_classes}".strip()
        return widget


class FormationForm(TailwindMixin, forms.ModelForm):
    class Meta:
        model = Formation
        exclude = ("slug", "created_at", "updated_at")
        widgets = {
            "titre": forms.TextInput(attrs={"class": "w-full rounded border px-3 py-2"}),
            "description_courte": forms.Textarea(attrs={"class": "w-full rounded border px-3 py-2", "rows": 3}),
            "description_complete": forms.Textarea(attrs={"class": "w-full rounded border px-3 py-2", "rows": 8}),
            "objectifs": forms.Textarea(attrs={"class": "w-full rounded border px-3 py-2", "rows": 5}),
            "programme": forms.Textarea(attrs={"class": "w-full rounded border px-3 py-2", "rows": 6}),
            "prerequis": forms.Textarea(attrs={"class": "w-full rounded border px-3 py-2", "rows": 5}),
            "duree": forms.NumberInput(attrs={"class": "w-full rounded border px-3 py-2"}),
            "niveau": forms.Select(attrs={"class": "w-full rounded border px-3 py-2"}),
            "prix": forms.NumberInput(attrs={"class": "w-full rounded border px-3 py-2"}),
            "category": forms.Select(attrs={"class": "w-full rounded border px-3 py-2"}),
            "image": forms.ClearableFileInput(attrs={"class": "w-full"}),
            "video_url": forms.URLInput(attrs={"class": "w-full rounded border px-3 py-2"}),
            "certificat": forms.CheckboxInput(attrs={"class": "rounded"}),
            "actif": forms.CheckboxInput(attrs={"class": "rounded"}),
        }

    def clean(self):
        cleaned = super().clean()
        titre = cleaned.get("titre")
        if not titre:
            raise ValidationError("Le titre est requis.")
        duree = cleaned.get("duree")
        if duree is not None and duree <= 0:
            raise ValidationError("La durée doit être > 0 (en heures).")
        prix = cleaned.get("prix")
        if prix is not None and prix < 0:
            raise ValidationError("Le prix ne peut pas être négatif.")
        return cleaned


class TrainerForm(TailwindMixin, forms.ModelForm):

    linkedin = forms.URLField(
        required=False,
        label="Profil LinkedIn",
        widget=forms.URLInput(
            attrs={
                "class": "w-full rounded border px-3 py-2",
                "placeholder": "https://linkedin.com/in/votre-profil"
            }
        )
    )

    class Meta:
        model = Trainer
        exclude = ("created_at", "updated_at")

        labels = {
            "user": "Utilisateur",
            "specialite": "Spécialité",
            "biographie": "Biographie",
            "photo": "Photo",
            "cv": "Curriculum Vitae (CV)",
            "annees_experience": "Années d'expérience",
            "competences": "Compétences",
            "linkedin": "Profil LinkedIn",
            "disponible": "Disponibilité",
        }

        widgets = {
            "user": forms.Select(attrs={
                "class": "w-full rounded border px-3 py-2"
            }),

            "specialite": forms.TextInput(attrs={
                "class": "w-full rounded border px-3 py-2"
            }),

            "biographie": forms.Textarea(attrs={
                "class": "w-full rounded border px-3 py-2",
                "rows": 6,
            }),

            "photo": forms.ClearableFileInput(attrs={
                "class": "w-full"
            }),

            "cv": forms.ClearableFileInput(attrs={
                "class": "w-full"
            }),

            "annees_experience": forms.NumberInput(attrs={
                "class": "w-full rounded border px-3 py-2",
            }),

            "competences": forms.Textarea(attrs={
                "class": "w-full rounded border px-3 py-2",
                "rows": 4,
            }),

            "disponible": forms.Select(attrs={
                "class": "w-full rounded border px-3 py-2"
            }),
        }


class FormationSessionForm(TailwindMixin, forms.ModelForm):
    class Meta:
        model = FormationSession
        exclude = ("places_restantes", "created_at", "updated_at","statut")
        widgets = {
            "formation": forms.Select(attrs={"class": "w-full rounded border px-3 py-2"}),
            "formateur": forms.Select(attrs={"class": "w-full rounded border px-3 py-2"}),
            "salle_reference": forms.TextInput(attrs={"class": "w-full rounded border px-3 py-2"}),
            "date_debut": forms.DateInput(attrs={"class": "w-full rounded border px-3 py-2", "type": "date"}),
            "date_fin": forms.DateInput(attrs={"class": "w-full rounded border px-3 py-2", "type": "date"}),
            "heure_debut": forms.TimeInput(attrs={"class": "w-full rounded border px-3 py-2", "type": "time"}),
            "heure_fin": forms.TimeInput(attrs={"class": "w-full rounded border px-3 py-2", "type": "time"}),
            "nombre_maximum": forms.NumberInput(attrs={"class": "w-full rounded border px-3 py-2"}),

        }

    def clean(self):
        cleaned = super().clean()
        date_debut = cleaned.get("date_debut")
        date_fin = cleaned.get("date_fin")
        if date_debut and date_fin and date_fin < date_debut:
            raise ValidationError("La date de fin doit être >= à la date de début.")

        heure_debut = cleaned.get("heure_debut")
        heure_fin = cleaned.get("heure_fin")
        if heure_debut and heure_fin and heure_fin <= heure_debut:
            raise ValidationError("L'heure de fin doit être > l'heure de début.")

        nombre_maximum = cleaned.get("nombre_maximum")
        if nombre_maximum is not None and nombre_maximum <= 0:
            raise ValidationError("Le nombre maximum de places doit être > 0.")

        return cleaned


class RegistrationForm(TailwindMixin, forms.ModelForm):
    class Meta:
        model = FormationRegistration
        exclude = ("numero", "created_at", "updated_at")
        widgets = {
            "membre": forms.Select(attrs={"class": "w-full rounded border px-3 py-2"}),
            "entreprise": forms.Select(attrs={"class": "w-full rounded border px-3 py-2"}),
            "session": forms.Select(attrs={"class": "w-full rounded border px-3 py-2"}),
            "statut": forms.Select(attrs={"class": "w-full rounded border px-3 py-2"}),
            "commentaire": forms.Textarea(attrs={"class": "w-full rounded border px-3 py-2", "rows": 4}),
            "date": forms.DateTimeInput(attrs={"class": "w-full rounded border px-3 py-2", "type": "datetime-local"}),
        }

    def clean_date(self):
        d = self.cleaned_data.get("date")
        if d and d > timezone.now() + datetime.timedelta(days=3650):
            raise ValidationError("La date de l'inscription semble invalide.")
        return d


class QuoteForm(TailwindMixin, forms.ModelForm):
    class Meta:
        model = FormationQuote
        exclude = ("created_at", "updated_at",)
        widgets = {
            "inscription": forms.Select(attrs={"class": "w-full rounded border px-3 py-2"}),
            "montant": forms.NumberInput(attrs={"class": "w-full rounded border px-3 py-2"}),
            "pdf": forms.ClearableFileInput(attrs={"class": "w-full"}),
            "statut": forms.Select(attrs={"class": "w-full rounded border px-3 py-2"}),
            "date": forms.DateTimeInput(attrs={"class": "w-full rounded border px-3 py-2", "type": "datetime-local"}),
        }

    def clean_montant(self):
        v = self.cleaned_data.get("montant")
        if v is not None and v < 0:
            raise ValidationError("Le montant ne peut pas être négatif.")
        return v


class ContractForm(TailwindMixin, forms.ModelForm):
    class Meta:
        model = FormationContract
        exclude = ("created_at", "updated_at")
        widgets = {
            "devis": forms.Select(attrs={"class": "w-full rounded border px-3 py-2"}),
            "contrat_pdf": forms.ClearableFileInput(attrs={"class": "w-full"}),
            "signature_docuseal": forms.Textarea(attrs={"class": "w-full rounded border px-3 py-2", "rows": 6}),
            "signé": forms.CheckboxInput(attrs={"class": "rounded"}),
            "statut": forms.Select(attrs={"class": "w-full rounded border px-3 py-2"}),
            "date": forms.DateTimeInput(attrs={"class": "w-full rounded border px-3 py-2", "type": "datetime-local"}),
        }


class ReviewForm(TailwindMixin, forms.ModelForm):
    class Meta:
        model = FormationReview
        exclude = ("created_at", "updated_at")
        widgets = {
            "membre": forms.Select(attrs={"class": "w-full rounded border px-3 py-2"}),
            "note": forms.NumberInput(attrs={"class": "w-full rounded border px-3 py-2"}),
            "commentaire": forms.Textarea(attrs={"class": "w-full rounded border px-3 py-2", "rows": 5}),
        }

    def clean_note(self):
        note = self.cleaned_data.get("note")
        if note is None:
            raise ValidationError("La note est requise.")
        if note < 1 or note > 5:
            raise ValidationError("La note doit être comprise entre 1 et 5.")
        return note


class ReviewFormPublic(ReviewForm):
    """Alias pour compatibilité future.

    Conserve la même implémentation.
    """


class InscriptionFormationForm(forms.Form):
    """Formulaire d'inscription multi-étapes pour une formation."""

    # Étape 1 — Formation & Session
    formation = forms.ModelChoiceField(
        queryset=Formation.objects.filter(actif=True),
        empty_label="— Sélectionnez une formation —",
        widget=forms.Select(attrs={"class": "form-input", "id": "formationSelect"}),
        label="Formation souhaitée",
        error_messages={"required": "Veuillez sélectionner une formation"},
    )
    session = forms.ModelChoiceField(
        required=False,
        queryset=FormationSession.objects.none(),
        empty_label="— Sélectionnez une session (optionnel) —",
        widget=forms.Select(attrs={"class": "form-input", "id": "sessionSelect"}),
        label="Session",
    )
    code_promo = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Entrez votre code promo"}),
        label="Code promo (optionnel)",
    )

    # Étape 2 — Informations personnelles
    prenom = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Votre prénom"}),
        label="Prénom",
    )
    nom = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Votre nom"}),
        label="Nom",
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"class": "form-input", "placeholder": "votre@email.com"}),
        label="Email",
    )
    telephone = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "+225 07 00 00 00 00"}),
        label="Téléphone",
    )
    date_naissance = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"class": "form-input", "type": "date"}),
        label="Date de naissance",
    )
    genre = forms.ChoiceField(
        required=False,
        choices=[("", "— Sélectionnez —"), ("M", "Masculin"), ("F", "Féminin")],
        widget=forms.Select(attrs={"class": "form-input"}),
        label="Genre",
    )
    niveau_qualification = forms.ChoiceField(
        choices=[
            ("", "— Sélectionnez votre niveau —"),
            ("bac", "BAC"),
            ("bac2", "BAC+2 (DUT, BTS, DEUG)"),
            ("bac3", "BAC+3 (Licence, LMD)"),
            ("bac5", "BAC+5 (Master, MBA)"),
            ("doc", "Doctorat"),
            ("autre", "Autre"),
        ],
        widget=forms.Select(attrs={"class": "form-input"}),
        label="Niveau de qualification",
    )
    organisation = forms.CharField(
        required=False,
        max_length=255,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Nom de votre entreprise (si applicable)"}),
        label="Organisation / Entreprise",
    )

    # Étape 3 — Préférences
    modules = forms.MultipleChoiceField(
        required=False,
        choices=[
            ("certification", "Certification professionnelle"),
            ("mentorat", "Mentorat individuel"),
            ("coaching", "Coaching post-formation"),
            ("materiel", "Kit matériel inclus"),
            ("reseau", "Accès réseau alumni"),
            ("enligne", "Accès plateforme en ligne"),
        ],
        widget=forms.CheckboxSelectMultiple(attrs={"class": "checkbox-group"}),
        label="Modules supplémentaires souhaités",
    )
    moyen_paiement = forms.ChoiceField(
        choices=[
            ("mobile", "Mobile Money"),
            ("card", "Carte bancaire"),
            ("virement", "Virement bancaire"),
        ],
        widget=forms.RadioSelect(attrs={"class": "checkbox-group"}),
        label="Moyen de paiement préféré",
        initial="mobile",
    )
    type_paiement = forms.ChoiceField(
        choices=[
            ("total", "Paiement total"),
            ("partiel_50", "50% maintenant, 50% plus tard"),
            ("partiel_30", "30% maintenant, 70% plus tard"),
        ],
        widget=forms.RadioSelect(attrs={"class": "checkbox-group"}),
        label="Modalité de paiement",
        initial="total",
    )
    provenance = forms.ChoiceField(
        required=False,
        choices=[
            ("web", "Site web"),
            ("social", "Réseaux sociaux"),
            ("boca", "Bouche à oreille"),
            ("evenement", "Événement"),
            ("email", "Email / Newsletter"),
            ("autre", "Autre"),
        ],
        widget=forms.RadioSelect(attrs={"class": "checkbox-group"}),
        label="Comment avez-vous entendu parler de nous ?",
    )
    objectifs = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "form-input", "placeholder": "Décrivez brièvement vos objectifs..."}),
        label="Objectifs de formation",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Initialiser le queryset des sessions si formation est sélectionnée
        formation_id = self.data.get("formation") or self.initial.get("formation")
        if formation_id:
            try:
                formation_id = int(formation_id)
                self.fields["session"].queryset = FormationSession.objects.filter(
                    formation_id=formation_id, statut__in=["published", "open"]
                ).order_by("date_debut")
            except (ValueError, TypeError):
                pass

    def clean_telephone(self):
        tel = self.cleaned_data.get("telephone", "")
        # Nettoyer le numéro de téléphone
        tel = tel.strip().replace(" ", "")
        return tel


class PaymentForm(TailwindMixin, forms.ModelForm):
    class Meta:
        model = FormationPayment
        exclude = ("created_at", "updated_at")
        widgets = {
            "inscription": forms.Select(attrs={"class": "w-full rounded border px-3 py-2"}),
            "montant": forms.NumberInput(attrs={"class": "w-full rounded border px-3 py-2"}),
            "méthode": forms.Select(attrs={"class": "w-full rounded border px-3 py-2"}),
            "statut": forms.Select(attrs={"class": "w-full rounded border px-3 py-2"}),
            "reference": forms.TextInput(attrs={"class": "w-full rounded border px-3 py-2"}),
        }

    def clean_montant(self):
        v = self.cleaned_data.get("montant")
        if v is not None and v < 0:
            raise ValidationError("Le montant ne peut pas être négatif.")
        return v


class CertificateForm(TailwindMixin, forms.ModelForm):
    class Meta:
        model = FormationCertificate
        exclude = ("created_at", "updated_at")
        widgets = {
            "inscription": forms.Select(attrs={"class": "w-full rounded border px-3 py-2"}),
            "certificat_pdf": forms.ClearableFileInput(attrs={"class": "w-full"}),
            "date": forms.DateTimeInput(attrs={"class": "w-full rounded border px-3 py-2", "type": "datetime-local"}),
        }


class ContractFormAdmin(ContractForm):
    class Meta(ContractForm.Meta):
        model = FormationContract


from django import forms
from .models import FormationPedagogicalDocument


class FormationPedagogicalDocumentForm(forms.ModelForm):

    class Meta:
        model = FormationPedagogicalDocument

        fields = [
            "formation",
            "titre",
            "description",
            "fichier",
        ]

        widgets = {
            "formation": forms.Select(attrs={
                "class": "form-control"
            }),

            "titre": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Titre du document"
            }),

            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Description du document"
            }),

            "fichier": forms.ClearableFileInput(attrs={
                "class": "form-control"
            }),
        }