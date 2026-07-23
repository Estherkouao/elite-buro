from __future__ import annotations

from django.contrib import messages
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from django.views import View
from django.views.generic import TemplateView

from accounts.models import User
from formation.models import (
    Formation,
    FormationCategory,
    FormationSession,
    FormationRegistration,
    FormationQuote,
    FormationPedagogicalDocument,
    Trainer,
)
from formation.forms import (
    FormationForm,
    TrainerForm,
    FormationSessionForm,
    RegistrationForm,
    QuoteForm,
    ContractForm,
)

from .permissions import is_admin_or_manager
from formation.permissions import FormationAccess


def admin_guard(request: HttpRequest) -> None:
    if not is_admin_or_manager(request.user):
        raise Http404("Page introuvable")


class FormationAdminBaseView(TemplateView):
    template_name = ""

    def dispatch(self, request: HttpRequest, *args, **kwargs):
        admin_guard(request)
        return super().dispatch(request, *args, **kwargs)

    def access(self) -> FormationAccess:
        return FormationAccess(user=self.request.user)


# --- Dashboard (overview) ---
class AdminFormationDashboardView(FormationAdminBaseView):
    template_name = "dashboard/admin/formations_list.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        formations = Formation.objects.select_related("category").order_by("-created_at")
        categories = FormationCategory.objects.order_by("name")
        sessions_count = FormationSession.objects.count()
        trainers_count = Trainer.objects.count()
        registrations = FormationRegistration.objects.select_related("session__formation", "session__formateur").order_by("-date")[:20]
        quotes_count = FormationQuote.objects.count()
        documents_count = FormationPedagogicalDocument.objects.count()

        return render(
            request,
            self.template_name,
            {
                "formations": formations,
                "categories": categories,
                "sessions_count": sessions_count,
                "trainers_count": trainers_count,
                "registrations": registrations,
                "quotes_count": quotes_count,
                "documents_count": documents_count,
            },
        )


# --- FormationCategory CRUD ---
class AdminFormationCategoryListView(FormationAdminBaseView):
    template_name = "dashboard/admin/formation_categories_list.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        categories = FormationCategory.objects.all().order_by("name")
        return render(request, self.template_name, {"categories": categories})


class AdminFormationCategoryCreateView(FormationAdminBaseView):
    template_name = "dashboard/admin/formation_categories_create.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        from django import forms

        class _F(forms.ModelForm):
            class Meta:
                model = FormationCategory
                fields = ["name"]

        return render(self.request, self.template_name, {"form": _F()})

    def post(self, request: HttpRequest) -> HttpResponse:
        from django import forms

        class _F(forms.ModelForm):
            class Meta:
                model = FormationCategory
                fields = ["name"]

        form = _F(request.POST, request.FILES)

        if form.is_valid():
            category = form.save(commit=False)

            # création automatique du slug
            category.save()

            messages.success(request, "Catégorie créée.")
            return redirect(
                reverse("dashboard_admin:formations_category_list")
            )

        return render(request, self.template_name, {"form": form})

class AdminFormationCategoryEditView(FormationAdminBaseView):
    template_name = "dashboard/admin/formation_categories_edit.html"

    def get_object(self, category_id: int) -> FormationCategory:
        return get_object_or_404(FormationCategory, id=category_id)

    def get(self, request: HttpRequest, category_id: int) -> HttpResponse:
        obj = self.get_object(category_id)
        from django import forms

        class _F(forms.ModelForm):
            class Meta:
                model = FormationCategory
                fields = ["name", "slug"]

        return render(request, self.template_name, {"form": _F(instance=obj), "category": obj})

    def post(self, request: HttpRequest, category_id: int) -> HttpResponse:
        obj = self.get_object(category_id)
        from django import forms

        class _F(forms.ModelForm):
            class Meta:
                model = FormationCategory
                fields = ["name", "slug"]

        form = _F(request.POST, request.FILES, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Catégorie modifiée.")
            return redirect(reverse("dashboard_admin:formations_category_list"))
        return render(request, self.template_name, {"form": form, "category": obj})


class AdminFormationCategoryDeleteView(FormationAdminBaseView):
    template_name = "dashboard/admin/formation_categories_delete.html"

    def get_object(self, category_id: int) -> FormationCategory:
        return get_object_or_404(FormationCategory, id=category_id)

    def get(self, request: HttpRequest, category_id: int) -> HttpResponse:
        obj = self.get_object(category_id)
        return render(request, self.template_name, {"category": obj})

    def post(self, request: HttpRequest, category_id: int) -> HttpResponse:
        obj = self.get_object(category_id)
        obj.delete()
        messages.success(request, "Catégorie supprimée.")
        return redirect(reverse("dashboard_admin:formations_category_list"))


# --- Formation CRUD ---
class AdminFormationsListView(FormationAdminBaseView):
    template_name = "dashboard/admin/formations_list.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        formations = Formation.objects.select_related("category").order_by("-created_at")
        return render(request, self.template_name, {"formations": formations})


class AdminFormationCreateView(FormationAdminBaseView):
    template_name = "dashboard/admin/formations_create.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        return render(request, self.template_name, {"form": FormationForm()})

    def post(self, request: HttpRequest) -> HttpResponse:
        form = FormationForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Formation créée.")
            return redirect(reverse("dashboard_admin:formations_list"))
        return render(request, self.template_name, {"form": form})


class AdminFormationEditView(FormationAdminBaseView):
    template_name = "dashboard/admin/formations_edit.html"

    def get_object(self, formation_id: int) -> Formation:
        return get_object_or_404(Formation, id=formation_id)

    def get(self, request: HttpRequest, formation_id: int) -> HttpResponse:
        obj = self.get_object(formation_id)
        return render(request, self.template_name, {"form": FormationForm(instance=obj), "formation": obj})

    def post(self, request: HttpRequest, formation_id: int) -> HttpResponse:
        obj = self.get_object(formation_id)
        form = FormationForm(request.POST, request.FILES, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Formation modifiée.")
            return redirect(reverse("dashboard_admin:formations_list"))
        return render(request, self.template_name, {"form": form, "formation": obj})


class AdminFormationDeleteView(FormationAdminBaseView):
    template_name = "dashboard/admin/formations_delete.html"

    def get_object(self, formation_id: int) -> Formation:
        return get_object_or_404(Formation, id=formation_id)

    def get(self, request: HttpRequest, formation_id: int) -> HttpResponse:
        obj = self.get_object(formation_id)
        return render(request, self.template_name, {"formation": obj})

    def post(self, request: HttpRequest, formation_id: int) -> HttpResponse:
        obj = self.get_object(formation_id)
        obj.delete()
        messages.success(request, "Formation supprimée.")
        return redirect(reverse("dashboard_admin:formations_list"))


# --- FormationSession CRUD ---
class AdminSessionsListView(FormationAdminBaseView):
    template_name = "dashboard/admin/sessions_list.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        sessions = (
            FormationSession.objects.select_related("formation", "formateur")
            .order_by("-date_debut", "-heure_debut")
        )
        return render(request, self.template_name, {"sessions": sessions})


class AdminSessionCreateView(FormationAdminBaseView):
    template_name = "dashboard/admin/sessions_create.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        return render(request, self.template_name, {"form": FormationSessionForm()})

    def post(self, request: HttpRequest) -> HttpResponse:
        form = FormationSessionForm(request.POST, request.FILES)
        if form.is_valid():
            session = form.save(commit=False)
            session.places_restantes = session.places_restantes or 0
            session.save()
            messages.success(request, "Session créée.")
            return redirect(reverse("dashboard_admin:sessions_list"))
        return render(request, self.template_name, {"form": form})


class AdminSessionEditView(FormationAdminBaseView):
    template_name = "dashboard/admin/sessions_edit.html"

    def get_object(self, session_id: int) -> FormationSession:
        return get_object_or_404(FormationSession, id=session_id)

    def get(self, request: HttpRequest, session_id: int) -> HttpResponse:
        obj = self.get_object(session_id)
        return render(request, self.template_name, {"form": FormationSessionForm(instance=obj), "session": obj})

    def post(self, request: HttpRequest, session_id: int) -> HttpResponse:
        obj = self.get_object(session_id)
        form = FormationSessionForm(request.POST, request.FILES, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Session modifiée.")
            return redirect(reverse("dashboard_admin:sessions_list"))
        return render(request, self.template_name, {"form": form, "session": obj})


class AdminSessionDeleteView(FormationAdminBaseView):
    template_name = "dashboard/admin/sessions_delete.html"

    def get_object(self, session_id: int) -> FormationSession:
        return get_object_or_404(FormationSession, id=session_id)

    def get(self, request: HttpRequest, session_id: int) -> HttpResponse:
        obj = self.get_object(session_id)
        return render(request, self.template_name, {"session": obj})

    def post(self, request: HttpRequest, session_id: int) -> HttpResponse:
        obj = self.get_object(session_id)
        obj.delete()
        messages.success(request, "Session supprimée.")
        return redirect(reverse("dashboard_admin:sessions_list"))


# --- Trainer CRUD (Back-office) ---
class AdminTrainersListView(FormationAdminBaseView):
    template_name = "dashboard/admin/trainers_list.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        trainers = Trainer.objects.select_related("user").order_by("user__last_name", "user__first_name")
        return render(request, self.template_name, {"trainers": trainers})


class AdminTrainersCreateView(FormationAdminBaseView):

    template_name = "dashboard/admin/trainers_create.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        from django import forms

        class TrainerCreateForm(forms.Form):
            user_email = forms.EmailField(
                label="Adresse e-mail",
                required=True
            )

            user_password = forms.CharField(
                label="Mot de passe",
                required=False,
                widget=forms.PasswordInput
            )

            user_first_name = forms.CharField(
                label="Prénom",
                required=True
            )

            user_last_name = forms.CharField(
                label="Nom",
                required=True
            )

            specialite = forms.CharField(
                label="Spécialité",
                required=False
            )

            biographie = forms.CharField(
                label="Biographie",
                required=False,
                widget=forms.Textarea
            )

            annees_experience = forms.IntegerField(
                label="Années d'expérience",
                required=False,
                min_value=0
            )

            disponible = forms.ChoiceField(
                label="Disponibilité",
                required=False,
                choices=Trainer.Disponibilite.choices,
                initial=Trainer.Disponibilite.AVAILABLE
            )

            photo = forms.ImageField(
                label="Photo",
                required=False
            )

            cv = forms.FileField(
                label="Curriculum Vitae (CV)",
                required=False
            )

            competences = forms.CharField(
                label="Compétences",
                required=False,
                widget=forms.Textarea
            )

            linkedin = forms.URLField(
                label="Profil LinkedIn",
                required=False
            )
        return render(request, self.template_name, {"form": TrainerCreateForm()})

    def post(self, request: HttpRequest) -> HttpResponse:
        from django import forms

        class TrainerCreateForm(forms.Form):
            user_email = forms.EmailField(required=True)
            user_password = forms.CharField(required=False, widget=forms.PasswordInput)
            user_first_name = forms.CharField(required=True)
            user_last_name = forms.CharField(required=True)

            specialite = forms.CharField(required=False)
            biographie = forms.CharField(required=False, widget=forms.Textarea())
            annees_experience = forms.IntegerField(required=False, min_value=0)
            disponible = forms.ChoiceField(required=False, choices=Trainer.Disponibilite.choices, initial=Trainer.Disponibilite.AVAILABLE)

            photo = forms.ImageField(required=False)
            cv = forms.FileField(required=False)
            competences = forms.CharField(required=False, widget=forms.Textarea())
            linkedin = forms.URLField(required=False)

        form = TrainerCreateForm(request.POST, request.FILES)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form})

        email = form.cleaned_data["user_email"]
        if User.objects.filter(email=email).exists():
            form.add_error("user_email", "Un compte avec cet email existe déjà.")
            return render(request, self.template_name, {"form": form})

        user = User(
            email=email,
            first_name=form.cleaned_data["user_first_name"],
            last_name=form.cleaned_data["user_last_name"],
            role=User.Role.TRAINER,
            is_active=True,
        )
        raw_password = form.cleaned_data.get("user_password")
        user.set_password(raw_password) if raw_password else user.set_unusable_password()
        user.save()

        Trainer.objects.create(
            user=user,
            specialite=form.cleaned_data.get("specialite") or "",
            biographie=form.cleaned_data.get("biographie") or "",
            annees_experience=form.cleaned_data.get("annees_experience") or 0,
            competences=form.cleaned_data.get("competences") or "",
            linkedin=form.cleaned_data.get("linkedin"),
            disponible=form.cleaned_data.get("disponible") or Trainer.Disponibilite.AVAILABLE,
            photo=form.cleaned_data.get("photo"),
            cv=form.cleaned_data.get("cv"),
        )

        messages.success(request, "Formateur créé.")
        return redirect(reverse("dashboard_admin:formations_trainers_list"))


class AdminTrainersEditView(FormationAdminBaseView):
    template_name = "dashboard/admin/trainers_edit.html"

    def get_object(self, trainer_id: int) -> Trainer:
        return get_object_or_404(Trainer, id=trainer_id)

    def get(self, request: HttpRequest, trainer_id: int) -> HttpResponse:
        from django import forms

        trainer = self.get_object(trainer_id)

        class TrainerEditForm(forms.Form):
            user_email = forms.EmailField(required=True)
            user_password = forms.CharField(required=False, widget=forms.PasswordInput)
            user_first_name = forms.CharField(required=True)
            user_last_name = forms.CharField(required=True)

            specialite = forms.CharField(required=False)
            biographie = forms.CharField(required=False, widget=forms.Textarea())
            annees_experience = forms.IntegerField(required=False, min_value=0)
            disponible = forms.ChoiceField(required=False, choices=Trainer.Disponibilite.choices)

            photo = forms.ImageField(required=False)
            cv = forms.FileField(required=False)
            competences = forms.CharField(required=False, widget=forms.Textarea())
            linkedin = forms.URLField(required=False)

        initial = {
            "user_email": trainer.user.email,
            "user_first_name": trainer.user.first_name,
            "user_last_name": trainer.user.last_name,
            "specialite": trainer.specialite,
            "biographie": trainer.biographie,
            "annees_experience": trainer.annees_experience,
            "disponible": trainer.disponible,
            "competences": trainer.competences,
            "linkedin": trainer.linkedin,
        }

        form = TrainerEditForm(initial=initial)
        return render(request, self.template_name, {"form": form, "trainer": trainer})

    def post(self, request: HttpRequest, trainer_id: int) -> HttpResponse:
        from django import forms

        trainer = self.get_object(trainer_id)

        class TrainerEditForm(forms.Form):
            user_email = forms.EmailField(required=True)
            user_password = forms.CharField(required=False, widget=forms.PasswordInput)
            user_first_name = forms.CharField(required=True)
            user_last_name = forms.CharField(required=True)

            specialite = forms.CharField(required=False)
            biographie = forms.CharField(required=False, widget=forms.Textarea())
            annees_experience = forms.IntegerField(required=False, min_value=0)
            disponible = forms.ChoiceField(required=False, choices=Trainer.Disponibilite.choices)

            photo = forms.ImageField(required=False)
            cv = forms.FileField(required=False)
            competences = forms.CharField(required=False, widget=forms.Textarea())
            linkedin = forms.URLField(required=False)

        form = TrainerEditForm(request.POST, request.FILES)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form, "trainer": trainer})

        # email unique
        new_email = form.cleaned_data["user_email"]
        if User.objects.exclude(id=trainer.user.id).filter(email=new_email).exists():
            form.add_error("user_email", "Cet email est déjà utilisé.")
            return render(request, self.template_name, {"form": form, "trainer": trainer})

        trainer.user.email = new_email
        trainer.user.first_name = form.cleaned_data["user_first_name"]
        trainer.user.last_name = form.cleaned_data["user_last_name"]

        raw_password = form.cleaned_data.get("user_password")
        if raw_password:
            trainer.user.set_password(raw_password)

        trainer.user.save(update_fields=["email", "first_name", "last_name"])

        trainer.specialite = form.cleaned_data.get("specialite") or ""
        trainer.biographie = form.cleaned_data.get("biographie") or ""
        trainer.annees_experience = form.cleaned_data.get("annees_experience") or 0
        trainer.disponible = form.cleaned_data.get("disponible") or Trainer.Disponibilite.AVAILABLE
        trainer.competences = form.cleaned_data.get("competences") or ""
        trainer.linkedin = form.cleaned_data.get("linkedin")

        if form.cleaned_data.get("photo"):
            trainer.photo = form.cleaned_data.get("photo")
        if form.cleaned_data.get("cv"):
            trainer.cv = form.cleaned_data.get("cv")

        trainer.save()

        messages.success(request, "Formateur modifié.")
        return redirect(reverse("dashboard_admin:formations_trainers_list"))


class AdminTrainersDeleteView(FormationAdminBaseView):
    template_name = "dashboard/admin/trainers_delete.html"

    def get_object(self, trainer_id: int) -> Trainer:
        return get_object_or_404(Trainer, id=trainer_id)

    def get(self, request: HttpRequest, trainer_id: int) -> HttpResponse:
        trainer = self.get_object(trainer_id)
        return render(request, self.template_name, {"trainer": trainer})

    def post(self, request: HttpRequest, trainer_id: int) -> HttpResponse:
        trainer = self.get_object(trainer_id)
        user = trainer.user
        trainer.delete()
        # On supprime aussi l’utilisateur (car on a créé user+trainer ensemble)
        user.delete()
        messages.success(request, "Formateur supprimé.")
        return redirect(reverse("dashboard_admin:formations_trainers_list"))

from django.shortcuts import render, get_object_or_404
from django.views.generic import DetailView



class FormationDetailView(DetailView):

    model = Formation
    template_name = "dashboard/admin/formations/detail.html"
    context_object_name = "formation"

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        formation = self.object

        context["sessions"] = formation.formationsession_set.all()

        return context