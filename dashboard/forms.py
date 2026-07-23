from __future__ import annotations

from django import forms
from django.core.exceptions import ValidationError

from accounts.models import User, Company, Profile
from coworking.models import Category, CoworkingSpace, Equipment, Workspace, WorkspaceAvailability, WorkspacePrice

from formation.models import (
    Formation,
    FormationCategory,
    FormationSession,
    FormationRegistration,
    Trainer,
    FormationPayment,
    FormationQuote,
    FormationContract,
    FormationCertificate,
    FormationReview,
)
from reservation.models import (
    Reservation,
    ReservationStatus,
    ReservationInvoice,
    ReservationReminder,
    ReservationLog,
)
from domiciliation.models import (
    DomiciliationRequest,
    DomiciliationPlan,
    DomiciliationDocument,
    DomiciliationContract,
    DomiciliationInvoice,
    DomiciliationRenewal,
    DomiciliationLog,
)


class AdminRoleChangeForm(forms.Form):
    user_id = forms.UUIDField(required=True)
    role = forms.ChoiceField(choices=User.Role.choices)


class UserAdminForm(forms.ModelForm):

    password = forms.CharField(
        label="Mot de passe",
        widget=forms.PasswordInput,
        required=False
    )


    class Meta:
        model = User

        fields = [
            "email",
            "password",
            "first_name",
            "last_name",
            "phone",
            "role",
            "is_active",
            "company_name",
            "job_title",
            "birth_date",
            "bio",
            "language",
            "timezone",
            "is_email_verified",
            "is_phone_verified",
            "receive_email_notification",
            "receive_sms_notification",
            "receive_whatsapp_notification",
        ]


        labels = {

            "email": "Adresse email",

            "first_name": "Prénom",

            "last_name": "Nom",

            "phone": "Téléphone",

            "role": "Rôle",

            "is_active": "Compte actif",

            "company_name": "Entreprise",

            "job_title": "Poste",

            "birth_date": "Date de naissance",

            "bio": "Biographie",

            "language": "Langue",

            "timezone": "Fuseau horaire",

            "is_email_verified": "Email vérifié",

            "is_phone_verified": "Téléphone vérifié",

            "receive_email_notification": "Recevoir les emails",

            "receive_sms_notification": "Recevoir les SMS",

            "receive_whatsapp_notification": "Recevoir WhatsApp",

        }


class CompanyAdminForm(forms.ModelForm):

    class Meta:

        model = Company

        fields = [
            "owner",
            "company_name",
            "phone",
            "email",
            "description",
            "logo",
        ]


        labels = {

            "owner": "Propriétaire",

            "company_name": "Nom de l'entreprise",

            "phone": "Téléphone",

            "email": "Adresse email",

            "description": "Description",

            "logo": "Logo de l'entreprise",

        }




class CoworkingSpaceForm(forms.ModelForm):
    class Meta:
        model = CoworkingSpace
        fields = [
            "nom",
            "slug",
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
        ]


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["nom", "slug", "description", "icone", "image"]


class WorkspaceForm(forms.ModelForm):
    class Meta:
        model = Workspace
        fields = [
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
        ]


class WorkspaceAvailabilityForm(forms.ModelForm):
    class Meta:
        model = WorkspaceAvailability
        fields = ["espace", "date", "heure_debut", "heure_fin", "disponible"]


class WorkspacePriceForm(forms.ModelForm):
    class Meta:
        model = WorkspacePrice
        fields = ["espace", "prix_heure", "prix_demi_journee", "prix_journee", "prix_semaine", "prix_mois"]


class EquipmentForm(forms.ModelForm):
    class Meta:
        model = Equipment
        fields = ["nom", "slug"]


class ReservationAdminForm(forms.ModelForm):
    class Meta:
        model = Reservation
        fields = "__all__"



class ReservationStatusUpdateForm(forms.Form):
    reservation_id = forms.UUIDField(required=True)
    statut = forms.ChoiceField(choices=ReservationStatus.choices)
    commentaire = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))



class FormationAdminForm(forms.ModelForm):

    class Meta:
        model = Formation
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for name, field in self.fields.items():

            field.widget.attrs["class"] = "admin-input"

        # Grandes zones de texte
        for name in [
            "description_courte",
            "description_complete",
            "objectifs",
            "programme",
            "prerequis",
        ]:
            self.fields[name].widget.attrs.update({
                "rows": 5,
                "class": "admin-input"
            })

        # Prix
        self.fields["prix"].widget.attrs["placeholder"] = "0 FCFA"

        # Durée
        self.fields["duree"].widget.attrs["placeholder"] = "Ex : 40 heures"

        # Lien vidéo
        self.fields["video_url"].widget.attrs["placeholder"] = "https://www.youtube.com/watch?v=..."

        # Images et documents
        for name in ["image", "video", "pdf"]:
            self.fields[name].widget.attrs["class"] = "admin-input"


class FormationSessionAdminForm(forms.ModelForm):
    class Meta:
        model = FormationSession
        fields = [
            "formation",
            "formateur",
            "salle_reference",
            "date_debut",
            "date_fin",
            "heure_debut",
            "heure_fin",
            "nombre_maximum",
            "statut",
            "places_restantes",
        ]


class FormationRegistrationAdminForm(forms.ModelForm):
    class Meta:
        model = FormationRegistration
        fields = ["membre", "entreprise", "session", "numero", "statut", "date", "commentaire"]


class FormationPaymentAdminForm(forms.ModelForm):
    class Meta:
        model = FormationPayment
        fields = ["inscription", "montant", "méthode", "statut", "reference"]


class DomiciliationAdminRequestForm(forms.ModelForm):
    class Meta:
        model = DomiciliationRequest
        fields = [
            "numero_demande",
            "utilisateur",
            "entreprise",
            "formule",
            "statut",
            "date_debut",
            "date_fin",
            "adresse_domiciliation",
            "observations",
        ]


class DomiciliationPlanAdminForm(forms.ModelForm):
    class Meta:
        model = DomiciliationPlan
        fields = ["nom", "slug", "description", "prix", "durée", "avantages", "actif", "ordre"]


class DomiciliationDocumentAdminForm(forms.ModelForm):
    class Meta:
        model = DomiciliationDocument
        fields = ["demande", "type", "fichier", "validé", "commentaire"]


class DomiciliationContractAdminForm(forms.ModelForm):
    class Meta:
        model = DomiciliationContract
        fields = ["demande", "numero", "fichier_pdf", "signature_docuseal", "signé", "date_signature"]


class DomiciliationInvoiceAdminForm(forms.ModelForm):
    class Meta:
        model = DomiciliationInvoice
        fields = ["demande", "numero", "montant", "fichier_pdf", "statut"]


class DomiciliationRenewalAdminForm(forms.ModelForm):
    class Meta:
        model = DomiciliationRenewal
        fields = ["demande", "nouvelle_periode", "montant", "statut"]


# Actions (suspendre / valider / annuler) - formulaires dédiés


class UpdateReservationActionForm(forms.Form):
    reservation_id = forms.UUIDField(required=True)
    action = forms.ChoiceField(
        choices=[
            ("confirm", "Valider"),
            ("cancel", "Annuler"),
        ]
    )
    commentaire = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))


class UpdateDomiciliationStatusForm(forms.Form):
    request_id = forms.UUIDField(required=True)
    statut = forms.ChoiceField(choices=DomiciliationRequest.Status.choices)
    commentaire = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))

