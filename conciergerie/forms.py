from django import forms
from .models import DemandeConciergerie


class DemandeConciergerieForm(forms.ModelForm):

    class Meta:
        model = DemandeConciergerie

        fields = [
            "civilite",
            "nom",
            "fonction",
            "entreprise",
            "email",
            "telephone",
            "secteur",
            "service",
            "participants",
            "date_debut",
            "duree",
            "budget",
            "horaires",
            "commentaire",
        ]

        labels = {
            "civilite": "Civilité",
            "nom": "Nom complet",
            "fonction": "Fonction",
            "entreprise": "Entreprise",
            "email": "Email professionnel",
            "telephone": "Téléphone",
            "secteur": "Secteur d'activité",
            "service": "Type de service souhaité",
            "participants": "Nombre de personnes",
            "date_debut": "Date de début souhaitée",
            "duree": "Durée souhaitée",
            "budget": "Budget mensuel estimé",
            "horaires": "Horaires d'utilisation",
            "commentaire": "Demande particulière",
        }

        widgets = {
            "date_debut": forms.DateInput(
                attrs={"type": "date"}
            ),
            "commentaire": forms.Textarea(
                attrs={"rows": 4, "placeholder": "Décrivez vos besoins spécifiques, contraintes ou demandes particulières..."}
            ),
        }
