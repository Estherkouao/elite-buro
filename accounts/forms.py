from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.forms import PasswordChangeForm

from .models import (
    User,
    Profile,
    Company,
)


class RegisterForm(UserCreationForm):


    class Meta:


        model = User

        fields = (

            "first_name",

            "last_name",

            "email",

            "phone",

            "company_name",

            "job_title",

            "password1",

            "password2",

        )

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        for field in self.fields.values():

            field.widget.attrs.update({

                "class": "w-full rounded-xl border border-gray-300 px-4 py-3 focus:ring-2 focus:ring-blue-600"

            })

        self.fields["first_name"].widget.attrs["placeholder"] = "Prénom"

        self.fields["last_name"].widget.attrs["placeholder"] = "Nom"

        self.fields["email"].widget.attrs["placeholder"] = "Adresse email"

        self.fields["phone"].widget.attrs["placeholder"] = "Téléphone"

        self.fields["company_name"].widget.attrs["placeholder"] = "Entreprise"

        self.fields["job_title"].widget.attrs["placeholder"] = "Fonction"

        self.fields["password1"].widget.attrs["placeholder"] = "Mot de passe"

        self.fields["password2"].widget.attrs["placeholder"] = "Confirmer le mot de passe"




class LoginForm(AuthenticationForm):

    username = forms.EmailField(

        widget=forms.EmailInput(

            attrs={

                "class":"w-full rounded-xl border border-gray-300 px-4 py-3",

                "placeholder":"Adresse email"

            }

        )

    )

    password = forms.CharField(

        widget=forms.PasswordInput(

            attrs={

                "class":"w-full rounded-xl border border-gray-300 px-4 py-3",

                "placeholder":"Mot de passe"

            }

        )

    )


class ProfileForm(forms.ModelForm):

    class Meta:

        model = User

        fields = (

            "first_name",

            "last_name",

            "phone",

            "birth_date",

            "gender",

            "website",

            "bio",

            "avatar",

        )

    def __init__(self,*args,**kwargs):

        super().__init__(*args,**kwargs)

        for field in self.fields.values():

            field.widget.attrs.update({

                "class":"w-full rounded-xl border px-4 py-3"

            })



class UserProfileForm(forms.ModelForm):

    class Meta:

        model = Profile

        fields = (

            "profession",

            "nationality",

            "biography",

            "linkedin",

            "facebook",

            "instagram",

            "twitter",

            "emergency_contact_name",

            "emergency_contact_phone",

        )

    def __init__(self,*args,**kwargs):

        super().__init__(*args,**kwargs)

        for field in self.fields.values():

            field.widget.attrs.update({

                "class":"w-full rounded-xl border px-4 py-3"

            })


class CompanyForm(forms.ModelForm):

    class Meta:

        model = Company

        exclude = (

            "owner",

            "created_at",

            "updated_at",

        )

    def __init__(self,*args,**kwargs):

        super().__init__(*args,**kwargs)

        for field in self.fields.values():

            field.widget.attrs.update({

                "class":"w-full rounded-xl border px-4 py-3"

            })



class CustomPasswordChangeForm(PasswordChangeForm):

    def __init__(self,*args,**kwargs):

        super().__init__(*args,**kwargs)

        for field in self.fields.values():

            field.widget.attrs.update({

                "class":"w-full rounded-xl border px-4 py-3"

            })