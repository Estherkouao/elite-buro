from __future__ import annotations

from datetime import date

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, TemplateView, UpdateView

from .forms import (
    CompanyForm,
    LoginForm,
    ProfileForm,
    RegisterForm,
    UserProfileForm,
    CustomPasswordChangeForm,
    EmailChangeForm,
)
from .models import Company, User

from dashboard.models import Testimonial, Notification as DashNotification, Payment as DashPayment
from reservation.models import Reservation
from coworking.models import Workspace as CoworkingWorkspace
from domiciliation.models import DomiciliationRequest
from reclamation.models import Reclamation
from formation.models import FormationRegistration


class CustomLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def get_success_url(self):
        # Si un paramètre ?next= est présent (ex: @login_required),
        # rediriger vers cette URL plutôt que la valeur par défaut
        next_url = self.request.GET.get("next")
        if next_url:
            return next_url
        user = self.request.user
        if getattr(user, "role", None) in {user.Role.ADMIN, user.Role.MANAGER}:
            return reverse_lazy("dashboard_admin:index")
        if getattr(user, "role", None) == user.Role.TRAINER:
            return reverse_lazy("dashboard_trainer:index")
        return reverse_lazy("accounts:dashboard")


class RegisterView(CreateView):
    model = User
    form_class = RegisterForm
    template_name = "accounts/register.html"
    success_url = reverse_lazy("accounts:login")

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        messages.success(self.request, "Votre compte a été créé avec succès.")
        return response


@login_required
def logout_view(request):
    logout(request)
    messages.success(request, "Vous êtes maintenant déconnecté.")
    return redirect("accounts:login")


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/dashboard.html"
    login_url = "accounts:login"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context["user"] = user

        # ===== IMPORTS =====
        from reservation.models import Reservation as RealReservation
        from dashboard.models import Notification as DashNotification
        from dashboard.models import Payment as DashPayment
        from dashboard.models import Testimonial
        from domiciliation.models import DomiciliationRequest
        from coworking.models import Workspace as CoworkingWorkspace

        # ===== RÉSERVATIONS =====
        reservations_qs = (
            RealReservation.objects.filter(utilisateur=user)
            .select_related("espace", "espace__categorie")
            .order_by("-created_at")
        )
        reservations_count = reservations_qs.count()

        # Dernières 5 réservations
        context["reservations"] = reservations_qs[:5]
        context["reservations_count"] = reservations_count

        # ===== PAIEMENTS =====
        payments_count = DashPayment.objects.filter(utilisateur=user).count()
        context["payments_count"] = payments_count

        # ===== DOMICILIATIONS =====
        domiciliation_qs = DomiciliationRequest.objects.filter(
            utilisateur=user
        ).order_by("-date_creation")
        domiciliation_count = domiciliation_qs.count()
        context["domiciliation_count"] = domiciliation_count
        context["domiciliation_requests"] = domiciliation_qs

        # ===== FORMATIONS =====
        formation_qs = FormationRegistration.objects.filter(membre=user).order_by("-date")
        formation_count = formation_qs.count()
        context["formation_count"] = formation_count
        context["formation_registrations"] = formation_qs

        # ===== NOTIFICATIONS =====
        notifications_qs = DashNotification.objects.filter(utilisateur=user).order_by("-date_creation")[:5]
        notifications_count = DashNotification.objects.filter(utilisateur=user, lu=False).count()
        context["notifications"] = notifications_qs
        context["notifications_count"] = notifications_count

        # ===== PROCHAINES RÉSERVATIONS =====
        today = date.today()
        upcoming_qs = (
            RealReservation.objects.filter(utilisateur=user)
            .exclude(statut__in=["canceled", "refused", "finished"])
            .filter(date_debut__gte=today)
            .select_related("espace")
            .order_by("date_debut")[:5]
        )
        context["upcoming_reservations"] = upcoming_qs

        # ===== RECOMMANDATIONS (Espaces en vedette) =====
        recommended_spaces = CoworkingWorkspace.objects.filter(vedette=True).select_related("categorie")[:3]
        context["recommended_spaces"] = recommended_spaces

        # ===== RÉCLAMATIONS =====
        reclamations_count = Reclamation.objects.filter(auteur=user).count()
        context["reclamations_count"] = reclamations_count

        # ===== RÉSERVATIONS EN COURS =====
        reservations_en_cours = reservations_qs.filter(
            statut__in=["pending", "confirmed", "in_progress"]
        )[:3]
        context["reservations_en_cours"] = reservations_en_cours

        # ===== AVIS EXISTANT =====
        context["existing_testimonial"] = Testimonial.objects.filter(utilisateur=user).first()

        # ===== STATUT CARTES (gardé pour compatibilité) =====
        context["status_cards"] = [
            {
                "icon": "✓",
                "label": "Statut du Compte",
                "value": "Actif",
                "detail": f"Membre depuis {user.created_at.strftime('%d/%m/%Y') if user.created_at else '—'}",
            },
            {
                "icon": "💰",
                "label": "Solde de Crédits",
                "value": "",
                "detail": "Crédits disponibles",
            },
            {
                "icon": "📅",
                "label": "Abonnement Actif",
                "value": "PREMIUM",
                "detail": "Expire le 15 Août 2026",
            },
            {
                "icon": "⚠️",
                "label": "Alertes",
                "value": str(notifications_count),
                "detail": "Notifications non lues",
            },
        ]

        return context

    def post(self, request, *args, **kwargs):
        note = request.POST.get("note", 5)
        commentaire = request.POST.get("commentaire", "").strip()

        if not commentaire:
            messages.error(request, "Veuillez écrire un commentaire.")
            return redirect("accounts:dashboard")

        existing = Testimonial.objects.filter(utilisateur=request.user).first()
        if existing:
            messages.warning(request, "Vous avez déjà soumis un avis. Merci !")
            return redirect("accounts:dashboard")

        Testimonial.objects.create(
            utilisateur=request.user,
            note=note,
            commentaire=commentaire,
        )

        messages.success(request, "Merci pour votre avis ! Il sera publié après modération.")
        return redirect("accounts:dashboard")


class ProfileView(LoginRequiredMixin, DetailView):
    model = User
    template_name = "accounts/profile.html"
    context_object_name = "member"

    def get_object(self):
        return self.request.user


class UpdateProfileView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = ProfileForm
    template_name = "accounts/edit_profile.html"
    success_url = reverse_lazy("accounts:profile")

    def get_object(self):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, "Profil mis à jour avec succès.")
        return super().form_valid(form)


class UpdateProfileInformationView(LoginRequiredMixin, UpdateView):
    form_class = UserProfileForm
    template_name = "accounts/edit_profile_information.html"
    success_url = reverse_lazy("accounts:profile")

    def get_object(self):
        return self.request.user.profile

    def form_valid(self, form):
        messages.success(self.request, "Informations mises à jour.")
        return super().form_valid(form)


class CompanyUpdateView(LoginRequiredMixin, UpdateView):
    model = Company
    form_class = CompanyForm
    template_name = "accounts/company.html"
    success_url = reverse_lazy("accounts:profile")

    def get_object(self):
        return Company.objects.filter(owner=self.request.user).first()

    def form_valid(self, form):
        messages.success(self.request, "Entreprise mise à jour.")
        return super().form_valid(form)


class ChangePasswordView(LoginRequiredMixin, PasswordChangeView):
    form_class = CustomPasswordChangeForm
    template_name = "accounts/change_password.html"
    success_url = reverse_lazy("accounts:profile")

    def form_valid(self, form):
        messages.success(self.request, "Votre mot de passe a été modifié avec succès.")
        return super().form_valid(form)


class UpdateEmailView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = EmailChangeForm
    template_name = "accounts/change_email.html"
    success_url = reverse_lazy("accounts:profile")

    def get_object(self):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, "Votre adresse email a été mise à jour avec succès.")
        return super().form_valid(form)
