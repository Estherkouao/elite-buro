from __future__ import annotations

from django import forms

from .models import (
    DomiciliationPlan,
    DomiciliationRequest,
    DomiciliationDocument,
    DomiciliationContract,
    DomiciliationRenewal,
)


class TailwindWidgetMixin:
    """Ajoute des classes Tailwind minimales aux widgets."""

    def _apply_tailwind(self, widget, extra_classes: str = ""):
        classes = widget.attrs.get("class", "")
        merged = " ".join([c for c in [classes, extra_classes] if c]).strip()
        widget.attrs["class"] = merged
        return widget


class DomiciliationPlanForm(TailwindWidgetMixin, forms.ModelForm):
    class Meta:
        model = DomiciliationPlan
        fields = (
            "nom",
            "description",
            "prix",
            "durée",
            "avantages",
            "actif",
            "ordre",
        )
        widgets = {
            "nom": forms.TextInput(attrs={"class": "w-full rounded-lg border-gray-200"}),
            "description": forms.Textarea(attrs={"class": "w-full min-h-[100px] rounded-lg border-gray-200"}),
            "prix": forms.NumberInput(attrs={"class": "w-full rounded-lg border-gray-200"}),
            "durée": forms.NumberInput(attrs={"class": "w-full rounded-lg border-gray-200"}),
            "avantages": forms.Textarea(attrs={"class": "w-full min-h-[80px] rounded-lg border-gray-200"}),
            "actif": forms.CheckboxInput(attrs={"class": "rounded"}),
            "ordre": forms.NumberInput(attrs={"class": "w-full rounded-lg border-gray-200"}),
        }


class DomiciliationRequestForm(TailwindWidgetMixin, forms.ModelForm):
    class Meta:
        model = DomiciliationRequest
        fields = ("formule", "entreprise", "observations", "adresse_domiciliation")
        widgets = {
            "observations": forms.Textarea(attrs={
                "class": "w-full rounded-xl border-gray-200 focus:border-[#C9A02C] focus:ring-[#C9A02C]",
                "rows": 4,
                "placeholder": "Informations complémentaires (optionnel)...",
            }),
            "formule": forms.RadioSelect(),
            "adresse_domiciliation": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if self.user:
            entreprises = self.user.companies.all()
            self.fields["entreprise"].queryset = entreprises
            self.fields["entreprise"].empty_label = None
            # Si une seule entreprise, présélectionner
            if entreprises.count() == 1:
                self.fields["entreprise"].initial = entreprises.first()
            self.fields["entreprise"].widget.attrs.update({
                "class": "w-full rounded-xl border-gray-200 focus:border-[#C9A02C] focus:ring-[#C9A02C]",
            })
            self.fields["formule"].queryset = DomiciliationPlan.objects.filter(actif=True)
            self.fields["formule"].widget.attrs.update({
                "class": "peer hidden",
            })
            self.fields["formule"].empty_label = None
            # Valeur par défaut de l'adresse
            self.fields["adresse_domiciliation"].initial = "Cocody Riviera Palmeraie, Abidjan"

    def clean_adresse_domiciliation(self):
        value = (self.cleaned_data.get("adresse_domiciliation") or "").strip()
        if not value:
            return "Cocody Riviera Palmeraie, Abidjan"
        return value


class DocumentUploadForm(TailwindWidgetMixin, forms.Form):
    type = forms.ChoiceField(choices=DomiciliationDocument.Type.choices, required=True)
    fichiers = forms.FileField(required=True)



    commentaire = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "w-full min-h-[60px] rounded-lg border-gray-200"}),
    )

    def clean_fichiers(self):
        files = self.files.getlist("fichiers")
        if not files:
            raise forms.ValidationError("Veuillez sélectionner au moins un fichier.")
        if len(files) > 10:
            raise forms.ValidationError("Limite : 10 fichiers par upload.")
        for f in files:
            if f.size > 10 * 1024 * 1024:
                raise forms.ValidationError("Un fichier dépasse 10 Mo.")
        return files


class ContractForm(TailwindWidgetMixin, forms.ModelForm):
    class Meta:
        model = DomiciliationContract
        fields = ("numero", "fichier_pdf", "signature_docuseal", "signé", "date_signature")
        widgets = {
            "numero": forms.TextInput(attrs={"class": "w-full rounded-lg border-gray-200"}),
            "fichier_pdf": forms.FileInput(attrs={"class": "w-full"}),
            "signature_docuseal": forms.TextInput(attrs={"class": "w-full rounded-lg border-gray-200"}),
            "signé": forms.CheckboxInput(attrs={"class": "rounded"}),
            "date_signature": forms.DateTimeInput(attrs={"class": "w-full rounded-lg border-gray-200"}),
        }


class RenewalForm(TailwindWidgetMixin, forms.ModelForm):
    class Meta:
        model = DomiciliationRenewal
        fields = ("nouvelle_periode", "montant", "statut")
        widgets = {
            "nouvelle_periode": forms.NumberInput(attrs={"class": "w-full rounded-lg border-gray-200"}),
            "montant": forms.NumberInput(attrs={"class": "w-full rounded-lg border-gray-200"}),
            "statut": forms.TextInput(attrs={"class": "w-full rounded-lg border-gray-200"}),
        }

    def clean_nouvelle_periode(self):
        value = self.cleaned_data.get("nouvelle_periode")
        if not value or value <= 0:
            raise forms.ValidationError("La nouvelle période doit être supérieure à 0.")
        if value > 60:
            raise forms.ValidationError("La nouvelle période ne peut pas dépasser 60 mois.")
        return value

