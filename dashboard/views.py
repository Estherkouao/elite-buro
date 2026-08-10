from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.shortcuts import render, get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import TemplateView

from accounts.models import User, Company, Profile
from django.shortcuts import get_object_or_404, redirect
from coworking.models import CoworkingSpace, Workspace, WorkspaceAvailability, Category, Equipment, WorkspaceImage

from coworking.forms import CategoryForm, EquipmentForm, WorkspaceForm, WorkspaceImageForm

from formation.models import Formation, FormationSession, FormationRegistration

from reservation.models import Reservation, ReservationLog
from domiciliation.models import DomiciliationRequest, ChangementGerant
from conciergerie.models import DemandeConciergerie

from .permissions import is_admin_or_manager
from .services import get_admin_stats, get_space_availability_summary, get_recent_activity
from .forms import UserAdminForm, CompanyAdminForm
from .models import Testimonial
from django.db.models.deletion import ProtectedError
from django.contrib import messages
from django.utils import timezone



def admin_permission_guard(request: HttpRequest):

    if not is_admin_or_manager(request.user):
        raise PermissionDenied


class AdminBaseView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/admin/index.html"

    def dispatch(self, request: HttpRequest, *args, **kwargs):
        try:
            admin_permission_guard(request)
        except PermissionDenied:
            return HttpResponseForbidden("Accès réservé au back-office.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Disponible dans toutes les pages de l'admin
        context["stats"] = get_admin_stats()
        context["availability_summary"] = get_space_availability_summary(limit=8)
        context["recent_activity"] = get_recent_activity(limit=8)

# Nombre de messages de contact non lus
        from core.models import ContactMessage
        context["contact_unread_count"] = ContactMessage.objects.filter(lu=False).count()

        # Derniers messages de contact (5 max) pour le panneau admin
        context["contact_messages"] = ContactMessage.objects.all().order_by("-created_at")[:5]

        # Nombre de nouvelles demandes conciergerie pour le badge sidebar
        context["nouvelle_count"] = DemandeConciergerie.objects.filter(statut="nouvelle").count()

        # Nombre de changements de gérant en attente pour le badge sidebar
        context["changement_gerant_count"] = ChangementGerant.objects.filter(statut="EN_ATTENTE").count()

        return context


class AdminContactMessagesListView(AdminBaseView):
    """Liste de tous les messages de contact avec pagination."""
    template_name = "dashboard/admin/contact_messages_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from core.models import ContactMessage
        context["active_section"] = "contact_messages"
        messages_qs = ContactMessage.objects.all().order_by("-created_at")

        # Filtre par statut
        statut_filter = self.request.GET.get("statut", "")
        if statut_filter == "non_lu":
            messages_qs = messages_qs.filter(lu=False)
        elif statut_filter == "lu":
            messages_qs = messages_qs.filter(lu=True)

        context["contact_messages"] = messages_qs
        context["total_count"] = ContactMessage.objects.count()
        context["unread_count"] = ContactMessage.objects.filter(lu=False).count()
        context["current_filter"] = statut_filter
        return context


class AdminContactMessageDetailView(AdminBaseView):
    """Détail d'un message de contact."""
    template_name = "dashboard/admin/contact_message_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from core.models import ContactMessage
        context["active_section"] = "contact_messages"
        msg = get_object_or_404(ContactMessage, id=kwargs.get("message_id"))
        context["message"] = msg
        return context

    def get(self, request, message_id, *args, **kwargs):
        from core.models import ContactMessage
        msg = get_object_or_404(ContactMessage, id=message_id)
        # Marquer comme lu automatiquement
        if not msg.lu:
            msg.lu = True
            msg.lu_le = timezone.now()
            msg.save(update_fields=["lu", "lu_le"])
        return render(request, self.template_name, {"message": msg})


class AdminContactMessageMarkReadView(AdminBaseView):
    """Marque un message comme lu."""

    def post(self, request, message_id, *args, **kwargs):
        from core.models import ContactMessage
        msg = get_object_or_404(ContactMessage, id=message_id)
        msg.lu = True
        msg.lu_le = timezone.now()
        msg.save(update_fields=["lu", "lu_le"])
        messages.success(request, "Message marqué comme lu.")
        return redirect("dashboard_admin:contact_messages")


class AdminContactMessageMarkUnreadView(AdminBaseView):
    """Marque un message comme non lu."""

    def post(self, request, message_id, *args, **kwargs):
        from core.models import ContactMessage
        msg = get_object_or_404(ContactMessage, id=message_id)
        msg.lu = False
        msg.lu_le = None
        msg.save(update_fields=["lu", "lu_le"])
        messages.success(request, "Message marqué comme non lu.")
        return redirect("dashboard_admin:contact_messages")


class AdminContactMessageDeleteView(AdminBaseView):
    """Supprime un message de contact."""

    def post(self, request, message_id, *args, **kwargs):
        from core.models import ContactMessage
        msg = get_object_or_404(ContactMessage, id=message_id)
        msg.delete()
        messages.success(request, "Message supprimé avec succès.")
        return redirect("dashboard_admin:contact_messages")


class AdminIndexView(AdminBaseView):
    template_name = "dashboard/admin/index.html"


class AdminUsersView(AdminBaseView):
    template_name = "dashboard/admin/users.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["users"] = User.objects.all().order_by("-created_at")
        return context


class AdminUserCreateView(AdminBaseView):
    template_name = "dashboard/admin/create_user.html"

    def post(self, request: HttpRequest, *args, **kwargs):
        form = UserAdminForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save(commit=False)
            # Hash du mot de passe pour que la connexion fonctionne.
            raw_password = form.cleaned_data.get("password")
            if raw_password:
                user.set_password(raw_password)
            else:
                user.set_unusable_password()
            user.save()
            return redirect("dashboard_admin:users")
        return render(request, self.template_name, {"form": form})


    def get(self, request: HttpRequest, *args, **kwargs):
        return render(request, self.template_name, {"form": UserAdminForm()})


class AdminUserUpdateView(AdminBaseView):
    template_name = "dashboard/admin/edit_user.html"

    def get_object(self, user_id):
        return get_object_or_404(User, id=user_id)

    def post(self, request: HttpRequest, user_id, *args, **kwargs):
        target_user = self.get_object(user_id)
        form = UserAdminForm(request.POST, request.FILES, instance=target_user)
        if form.is_valid():
            user = form.save(commit=False)

            raw_password = form.cleaned_data.get("password")
            if raw_password:
                user.set_password(raw_password)

            user.save()

            return redirect("dashboard_admin:users")
        return render(request, self.template_name, {"form": form, "target_user": target_user})

    def get(self, request: HttpRequest, user_id, *args, **kwargs):
        target_user = self.get_object(user_id)
        return render(request, self.template_name, {"form": UserAdminForm(instance=target_user), "target_user": target_user})



class AdminUserDeactivateView(AdminBaseView):
    template_name = "dashboard/admin/delete_user_confirm.html"

    def post(self, request: HttpRequest, user_id, *args, **kwargs):
        print(f"[AdminUserDeactivateView] POST user_id={user_id}")
        target_user = get_object_or_404(User, id=user_id)
        target_user.is_active = False
        target_user.save(update_fields=["is_active"])
        return redirect("dashboard_admin:users")




class AdminUserReactivateView(AdminBaseView):
    template_name = "dashboard/admin/delete_user_confirm.html"

    def post(self, request: HttpRequest, user_id, *args, **kwargs):
        print(f"[AdminUserReactivateView] POST user_id={user_id}")
        target_user = get_object_or_404(User, id=user_id)
        target_user.is_active = True
        target_user.save(update_fields=["is_active"])
        return redirect("dashboard_admin:users")




class AdminUserDeleteView(AdminBaseView):
    template_name = "dashboard/admin/delete_user_confirm.html"

    def get_object(self, user_id):
        return get_object_or_404(User, id=user_id)

    def post(self, request: HttpRequest, user_id, *args, **kwargs):
        print(f"[AdminUserDeleteView] POST user_id={user_id}")
        target_user = self.get_object(user_id)
        target_user.delete()
        return redirect("dashboard_admin:users")


    def get(self, request: HttpRequest, user_id, *args, **kwargs):
        target_user = self.get_object(user_id)
        return render(request, self.template_name, {"target_user": target_user})


class AdminCompanyView(AdminBaseView):
    template_name = "dashboard/admin/company.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["companies"] = Company.objects.all().order_by("company_name")
        return context

class AdminCompanyCreateView(AdminBaseView):

    template_name = "dashboard/admin/create_company.html"


    def get(self, request, *args, **kwargs):

        form = CompanyAdminForm()

        return render(
            request,
            self.template_name,
            {
                "form": form
            }
        )



    def post(self, request, *args, **kwargs):

        form = CompanyAdminForm(
            request.POST,
            request.FILES
        )


        if form.is_valid():

            company = form.save()


            messages.success(
                request,
                "Entreprise créée avec succès."
            )


            return redirect(
                "dashboard_admin:companies"
            )


        return render(
            request,
            self.template_name,
            {
                "form": form
            }
        )


class AdminCompanyUpdateView(AdminBaseView):
    template_name = "dashboard/admin/edit_company.html"

    def get_object(self, company_id):
        return get_object_or_404(Company, id=company_id)

    def get(self, request: HttpRequest, company_id, *args, **kwargs):
        target_company = self.get_object(company_id)
        return render(
            request,
            self.template_name,
            {"form": CompanyAdminForm(instance=target_company), "target_company": target_company},
        )

    def post(self, request: HttpRequest, company_id, *args, **kwargs):
        target_company = self.get_object(company_id)
        form = CompanyAdminForm(request.POST, request.FILES, instance=target_company)
        if form.is_valid():
            form.save()
            return redirect("dashboard_admin:companies")
        return render(request, self.template_name, {"form": form, "target_company": target_company})


class AdminCompanyDeleteView(AdminBaseView):
    template_name = "dashboard/admin/delete_company_confirm.html"

    def get_object(self, company_id):
        return get_object_or_404(Company, id=company_id)

    def get(self, request: HttpRequest, company_id, *args, **kwargs):
        target_company = self.get_object(company_id)
        return render(request, self.template_name, {"target_company": target_company})

    def post(self, request: HttpRequest, company_id, *args, **kwargs):
        target_company = self.get_object(company_id)
        target_company.delete()
        return redirect("dashboard_admin:companies")



class AdminCoworkingView(AdminBaseView):
    template_name = "dashboard/admin/coworking.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Toutes les entités coworking pour affichage back-office
        context["coworking_spaces"] = CoworkingSpace.objects.all().order_by("nom")
        context["categories"] = Category.objects.all().order_by("nom")
        context["equipments"] = Equipment.objects.all().order_by("nom")
        context["workspace_images"] = WorkspaceImage.objects.select_related("workspace").all().order_by("id")
        context["workspace_images_count"] = len(context["workspace_images"])

        # Workspaces (catalogue / réservation)
        context["spaces"] = (
            Workspace.objects.select_related("espace", "categorie")
            .all()
            .order_by("nom")
        )

        # Disponibilités : nombre de workspaces marqués comme disponibles
        context["availability_count"] = Workspace.objects.filter(disponible=True).count()

        return context




class AdminReservationsView(AdminBaseView):
    template_name = "dashboard/admin/reservations.html"


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["reservations"] = (
            Reservation.objects.select_related("utilisateur", "entreprise", "espace")
            .order_by("-created_at")
        )
        return context



class AdminFormationsView(AdminBaseView):
    template_name = "dashboard/admin/formations.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["formations"] = Formation.objects.select_related("category").order_by("-created_at")
        context["sessions"] = FormationSession.objects.count()
        context["registrations"] = FormationRegistration.objects.count()
        return context


class AdminDomiciliationView(AdminBaseView):
    template_name = "dashboard/admin/domiciliation.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["requests"] = DomiciliationRequest.objects.select_related(
            "entreprise", "utilisateur", "formule"
        ).order_by("-date_creation")
        return context


# --- Back-office Demandes (CRUD) ---
class AdminDomiciliationRequestsListView(AdminBaseView):

    template_name = "dashboard/admin/domiciliation_requests.html"


    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)


        context["requests"] = (
            DomiciliationRequest.objects
            .select_related(
                "entreprise",
                "utilisateur",
                "formule",
            )
            .order_by("-date_creation")
        )


        context["types"] = (
            DomiciliationRequest.TypeDemande.choices
        )


        return context


class AdminDomiciliationRequestEditView(AdminBaseView):
    template_name = "dashboard/admin/domiciliation_request_edit.html"

    def get_object(self, request_id):
        return get_object_or_404(DomiciliationRequest, id=request_id)

    def get(self, request: HttpRequest, request_id: str, *args, **kwargs):
        from domiciliation.forms import DomiciliationRequestForm

        obj = self.get_object(request_id)
        return render(
            request,
            self.template_name,
            {
                "form": DomiciliationRequestForm(instance=obj),
                "request": obj,
            },
        )

    def post(self, request: HttpRequest, request_id: str, *args, **kwargs):
        from domiciliation.forms import DomiciliationRequestForm

        obj = self.get_object(request_id)
        form = DomiciliationRequestForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            return redirect("dashboard_admin:domiciliation_requests")
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "request": obj,
            },
        )


class AdminDomiciliationRequestValidateView(AdminBaseView):

    def post(self, request: HttpRequest, request_id: str, *args, **kwargs):

        from domiciliation.models import DomiciliationLog
        from domiciliation.services import generer_facture_pour_demande

        obj = get_object_or_404(
            DomiciliationRequest,
            id=request_id
        )

        # Génère la facture et passe le statut à "Paiement en attente"
        generer_facture_pour_demande(demande=obj)

        DomiciliationLog.objects.create(
            demande=obj,
            utilisateur=request.user,
            action="VALIDATION",
            details="Demande acceptée. Prière de procéder au paiement.",
        )

        # Envoie un email au demandeur l'invitant à payer
        self._send_payment_request_email(obj)

        messages.success(
            request,
            "La demande a été acceptée. Le demandeur a été invité à payer."
        )

        return redirect(
            "dashboard_admin:domiciliation_detail",
            request_id=obj.id
        )

    def _send_payment_request_email(self, demande):
        """Envoie un email HTML au demandeur pour l'inviter à procéder au paiement."""
        from django.conf import settings
        from django.urls import reverse
        from notification.services import send_html_email

        paiement_url = (
            f"{settings.SITE_URL}/paiement/"
            f"?domiciliation_id={demande.id}"
            f"&amount={demande.formule.prix}"
            f"&description={demande.numero_demande}"
        )

        subject = f"💳 Paiement requis - Domiciliation {demande.numero_demande}"

        send_html_email(
            subject=subject,
            recipient_email=demande.utilisateur.email,
            template_name="emails/domiciliation_payment_request.html",
            context={
                "demande": demande,
                "paiement_url": paiement_url,
            },
            fail_silently=True,
        )


class AdminDomiciliationRequestRefuseView(AdminBaseView):
    def post(self, request: HttpRequest, request_id: str, *args, **kwargs):
        from domiciliation.models import DomiciliationLog

        obj = get_object_or_404(DomiciliationRequest, id=request_id)
        motif = (request.POST.get("motif") or "").strip()
        obj.statut = DomiciliationRequest.Status.REFUSÉE
        obj.save(update_fields=["statut"])

        DomiciliationLog.objects.create(
            demande=obj,
            utilisateur=request.user,
            action="REFUS",
            details=motif or "Demande refusée par l’admin.",
        )

        return redirect("dashboard_admin:domiciliation_requests")


class AdminDomiciliationPlansListView(AdminBaseView):
    template_name = "dashboard/admin/domiciliation_plans.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from domiciliation.models import DomiciliationPlan

        context["plans"] = DomiciliationPlan.objects.all().order_by("ordre", "nom")
        return context


class AdminDomiciliationPlanCreateView(AdminBaseView):
    template_name = "dashboard/admin/domiciliation_plan_create.html"

    def get(self, request: HttpRequest, *args, **kwargs):
        from domiciliation.forms import DomiciliationPlanForm

        return render(request, self.template_name, {"form": DomiciliationPlanForm()})

    def post(self, request: HttpRequest, *args, **kwargs):
        from django.contrib import messages

        from domiciliation.forms import DomiciliationPlanForm

        form = DomiciliationPlanForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Formule créée.")
            return redirect("dashboard_admin:domiciliation_plans")
        return render(request, self.template_name, {"form": form})


class AdminDomiciliationPlanEditView(AdminBaseView):
    template_name = "dashboard/admin/domiciliation_plan_edit.html"

    def get_object(self, plan_id: int):
        from domiciliation.models import DomiciliationPlan

        return get_object_or_404(DomiciliationPlan, id=plan_id)

    def get(self, request: HttpRequest, plan_id: int, *args, **kwargs):
        from domiciliation.forms import DomiciliationPlanForm

        plan = self.get_object(plan_id)
        return render(request, self.template_name, {"form": DomiciliationPlanForm(instance=plan), "plan": plan})

    def post(self, request: HttpRequest, plan_id: int, *args, **kwargs):
        from django.contrib import messages

        from domiciliation.forms import DomiciliationPlanForm

        plan = self.get_object(plan_id)
        form = DomiciliationPlanForm(request.POST, instance=plan)
        if form.is_valid():
            form.save()
            messages.success(request, "Formule modifiée.")
            return redirect("dashboard_admin:domiciliation_plans")
        return render(request, self.template_name, {"form": form, "plan": plan})


class AdminDomiciliationPlanDeleteView(AdminBaseView):
    template_name = "dashboard/admin/domiciliation_plan_delete.html"

    def get_object(self, plan_id: int):
        from domiciliation.models import DomiciliationPlan

        return get_object_or_404(DomiciliationPlan, id=plan_id)

    def get(self, request: HttpRequest, plan_id: int, *args, **kwargs):
        plan = self.get_object(plan_id)
        return render(request, self.template_name, {"plan": plan})

    def post(self, request: HttpRequest, plan_id: int, *args, **kwargs):
        from django.contrib import messages

        plan = self.get_object(plan_id)
        plan.delete()
        messages.success(request, "Formule supprimée.")
        return redirect("dashboard_admin:domiciliation_plans")



class AdminProfileView(AdminBaseView):

    template_name = "dashboard/admin/profile_view.html"

    def get(self, request, *args, **kwargs):

        profile_user = request.user

        profile, created = Profile.objects.get_or_create(
            user=profile_user
        )

        return render(
            request,
            self.template_name,
            {
                "profile_user": profile_user,
                "profile": profile
            }
        )


class AdminProfileEditView(AdminBaseView):
    template_name = "dashboard/admin/profile_edit.html"

    def get(self, request: HttpRequest, *args, **kwargs):
        profile_user = get_object_or_404(User, id=kwargs.get("user_id")) if "user_id" in kwargs else request.user
        profile = get_object_or_404(Profile, user=profile_user)

        class _ProfileForm(forms.ModelForm):
            class Meta:
                model = Profile
                fields = [
                    "gender",
                    "nationality",
                    "profession",
                    "biography",
                    "linkedin",
                    "facebook",
                    "instagram",
                    "twitter",
                    "emergency_contact_name",
                    "emergency_contact_phone",
                ]

        form = _ProfileForm(instance=profile)
        return render(request, self.template_name, {"form": form, "profile_user": profile_user})

    def post(self, request: HttpRequest, *args, **kwargs):
        profile_user = get_object_or_404(User, id=kwargs.get("user_id")) if "user_id" in kwargs else request.user
        profile = get_object_or_404(Profile, user=profile_user)

        class _ProfileForm(forms.ModelForm):
            class Meta:
                model = Profile
                fields = [
                    "gender",
                    "nationality",
                    "profession",
                    "biography",
                    "linkedin",
                    "facebook",
                    "instagram",
                    "twitter",
                    "emergency_contact_name",
                    "emergency_contact_phone",
                ]

        form = _ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            return redirect("dashboard_admin:profile_view")
        return render(request, self.template_name, {"form": form, "profile_user": profile_user})


class AdminCoworkingCategoryCreateView(AdminBaseView):

    template_name = "dashboard/admin/coworking_category_create.html"

    def get(self, request: HttpRequest, *args, **kwargs):
        return render(request, self.template_name, {"form": CategoryForm()})

    def post(self, request: HttpRequest, *args, **kwargs):
        form = CategoryForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect("dashboard_admin:coworking")
        return render(request, self.template_name, {"form": form})


class AdminCoworkingCategoryEditView(AdminBaseView):
    template_name = "dashboard/admin/coworking_category_edit.html"

    def get_object(self, category_id):
        return get_object_or_404(Category, id=category_id)

    def get(self, request: HttpRequest, category_id, *args, **kwargs):
        target_category = self.get_object(category_id)
        return render(request, self.template_name, {"form": CategoryForm(instance=target_category), "target_category": target_category})

    def post(self, request: HttpRequest, category_id, *args, **kwargs):
        target_category = self.get_object(category_id)
        form = CategoryForm(request.POST, request.FILES, instance=target_category)
        if form.is_valid():
            form.save()
            return redirect("dashboard_admin:coworking")
        return render(request, self.template_name, {"form": form, "target_category": target_category})


class AdminCoworkingCategoryDeleteView(AdminBaseView):

    template_name = "dashboard/admin/coworking_category_delete.html"


    def get_object(self, category_id):
        return get_object_or_404(
            Category,
            id=category_id
        )


    def get(self, request: HttpRequest, category_id, *args, **kwargs):

        target_category = self.get_object(category_id)

        return render(
            request,
            self.template_name,
            {
                "target_category": target_category
            }
        )


    def post(self, request: HttpRequest, category_id, *args, **kwargs):

        target_category = self.get_object(category_id)


        try:

            target_category.delete()

            messages.success(
                request,
                "✅ La catégorie a été supprimée avec succès."
            )


        except ProtectedError as e:

            objets_bloquants = len(e.protected_objects)

            messages.error(
                request,
                f"⚠ Suppression impossible : cette catégorie est encore utilisée "
                f"par {objets_bloquants} élément(s) (bureaux ou réservations)."
            )


        return redirect(
            "dashboard_admin:coworking"
        )


class AdminCoworkingEquipmentCreateView(AdminBaseView):
    template_name = "dashboard/admin/coworking_equipment_create.html"

    def get(self, request: HttpRequest, *args, **kwargs):
        return render(request, self.template_name, {"form": EquipmentForm()})

    def post(self, request: HttpRequest, *args, **kwargs):
        form = EquipmentForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect("dashboard_admin:coworking")
        return render(request, self.template_name, {"form": form})


class AdminCoworkingEquipmentEditView(AdminBaseView):
    template_name = "dashboard/admin/coworking_equipment_edit.html"

    def get_object(self, equipment_id):
        return get_object_or_404(Equipment, id=equipment_id)

    def get(self, request: HttpRequest, equipment_id, *args, **kwargs):
        target_equipment = self.get_object(equipment_id)
        return render(request, self.template_name, {"form": EquipmentForm(instance=target_equipment), "target_equipment": target_equipment})

    def post(self, request: HttpRequest, equipment_id, *args, **kwargs):
        target_equipment = self.get_object(equipment_id)
        form = EquipmentForm(request.POST, request.FILES, instance=target_equipment)
        if form.is_valid():
            form.save()
            return redirect("dashboard_admin:coworking")
        return render(request, self.template_name, {"form": form, "target_equipment": target_equipment})


class AdminCoworkingEquipmentDeleteView(AdminBaseView):
    template_name = "dashboard/admin/coworking_equipment_delete.html"

    def get_object(self, equipment_id):
        return get_object_or_404(Equipment, id=equipment_id)

    def get(self, request: HttpRequest, equipment_id, *args, **kwargs):
        target_equipment = self.get_object(equipment_id)
        return render(request, self.template_name, {"target_equipment": target_equipment})

    def post(self, request: HttpRequest, equipment_id, *args, **kwargs):
        target_equipment = self.get_object(equipment_id)
        target_equipment.delete()
        return redirect("dashboard_admin:coworking")


class AdminCoworkingWorkspaceCreateView(AdminBaseView):

    template_name = "dashboard/admin/coworking_workspace_create.html"


    def get(self, request, *args, **kwargs):

        return render(
            request,
            self.template_name,
            {
                "form": WorkspaceForm()
            }
        )


    def post(self, request, *args, **kwargs):

        form = WorkspaceForm(
            request.POST,
            request.FILES
        )


        print("DONNEES FORM :", request.POST)


        if form.is_valid():

            workspace = form.save(commit=False)


            # attribution automatique de l'agence
            workspace.espace = CoworkingSpace.objects.first()


            workspace.save()


            print("WORKSPACE CREE :", workspace)


            return redirect(
                "dashboard_admin:coworking"
            )


        print("ERREURS :", form.errors)


        return render(
            request,
            self.template_name,
            {
                "form": form
            }
        )
class AdminCoworkingWorkspaceEditView(AdminBaseView):
    template_name = "dashboard/admin/coworking_workspace_edit.html"

    def get_object(self, workspace_id):
        return get_object_or_404(Workspace, id=workspace_id)

    def get(self, request: HttpRequest, workspace_id, *args, **kwargs):
        target_workspace = self.get_object(workspace_id)
        return render(request, self.template_name, {"form": WorkspaceForm(instance=target_workspace), "target_workspace": target_workspace})

    def post(self, request: HttpRequest, workspace_id, *args, **kwargs):
        target_workspace = self.get_object(workspace_id)
        form = WorkspaceForm(request.POST, request.FILES, instance=target_workspace)
        if form.is_valid():
            form.save()
            return redirect("dashboard_admin:coworking")
        return render(request, self.template_name, {"form": form, "target_workspace": target_workspace})


class AdminCoworkingWorkspaceDeleteView(AdminBaseView):

    template_name = "dashboard/admin/coworking_workspace_delete.html"


    def get_object(self, workspace_id):
        return get_object_or_404(
            Workspace,
            id=workspace_id
        )


    def get(self, request: HttpRequest, workspace_id, *args, **kwargs):

        target_workspace = self.get_object(workspace_id)

        return render(
            request,
            self.template_name,
            {
                "target_workspace": target_workspace
            }
        )


    def post(self, request: HttpRequest, workspace_id, *args, **kwargs):

        target_workspace = self.get_object(workspace_id)


        try:

            target_workspace.delete()

            messages.success(
                request,
                "✅ Le bureau a été supprimé avec succès."
            )


        except ProtectedError as e:

            objets_bloquants = len(e.protected_objects)

            messages.error(
                 request,
                f"⚠ Suppression impossible : ce bureau est encore utilisé "
                f"par {objets_bloquants} élément(s) "
                f"(réservations associées)."
            )


        return redirect(
            "dashboard_admin:coworking"
        )

class AdminCoworkingWorkspaceImageAddView(AdminBaseView):
    template_name = "dashboard/admin/coworking_workspaceimage_add.html"

    def get(self, request: HttpRequest, *args, **kwargs):
        return render(request, self.template_name, {"form": WorkspaceImageForm()})

    def post(self, request: HttpRequest, *args, **kwargs):
        form = WorkspaceImageForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect("dashboard_admin:coworking")
        return render(request, self.template_name, {"form": form})


class AdminCoworkingWorkspaceImageDeleteView(AdminBaseView):
    template_name = "dashboard/admin/coworking_workspaceimage_delete.html"


    def get_object(self, image_id):
        return get_object_or_404(WorkspaceImage, id=image_id)

    def get(self, request: HttpRequest, image_id, *args, **kwargs):
        target_image = self.get_object(image_id)
        return render(request, self.template_name, {"target_image": target_image})

    def post(self, request: HttpRequest, image_id, *args, **kwargs):
        target_image = self.get_object(image_id)
        target_image.delete()
        return redirect("dashboard_admin:coworking")



from django.views.generic import DetailView, UpdateView
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages

from reservation.models import Reservation
from reservation.services import (
    admin_confirm_reservation,
    admin_cancel_reservation,
)


class AdminReservationDetailView(AdminBaseView, DetailView):

    model = Reservation
    template_name = "dashboard/admin/reservation_detail.html"
    context_object_name = "reservation"
    pk_url_kwarg = "reservation_id"







from django.views.generic import UpdateView
from django.shortcuts import get_object_or_404
from reservation.models import Reservation
from reservation.forms import ReservationForm


class AdminReservationEditView(AdminBaseView, View):

    template_name = "dashboard/admin/reservation_edit.html"


    def get(self, request, reservation_id):

        reservation = get_object_or_404(
            Reservation,
            id=reservation_id
        )


        form = ReservationForm(
            instance=reservation,
            request=request
        )


        return render(
            request,
            self.template_name,
            {
                "form": form,
                "reservation": reservation,
            }
        )



    def post(self, request, reservation_id):

        reservation = get_object_or_404(
            Reservation,
            id=reservation_id
        )


        form = ReservationForm(
            request.POST,
            instance=reservation,
            request=request
        )


        if form.is_valid():


            reservation = form.save(commit=False)


            reservation.save()



            ReservationLog.objects.create(

                reservation=reservation,

                action=ReservationLog.ActionType.UPDATED,

                acteur=request.user,

                detail="Modification de la réservation par l'administration."

            )



            messages.success(
                request,
                "Réservation modifiée avec succès."
            )


            return redirect(
                "dashboard_admin:reservation_detail",
                reservation_id=reservation.id
            )



        messages.error(
            request,
            "Veuillez corriger les erreurs."
        )


        return render(
            request,
            self.template_name,
            {
                "form": form,
                "reservation": reservation,
            }
        )


class AdminReservationConfirmView(AdminBaseView):

    def get(self, request, reservation_id):

        reservation = get_object_or_404(
            Reservation,
            id=reservation_id
        )

        admin_confirm_reservation(
            request.user,
            reservation
        )


        messages.success(
            request,
            "Réservation confirmée."
        )


        return redirect(
            "dashboard_admin:reservations"
        )



class AdminReservationCancelView(AdminBaseView):

    def get(self, request, reservation_id):

        reservation = get_object_or_404(
            Reservation,
            id=reservation_id
        )

        admin_cancel_reservation(
            request.user,
            reservation
        )


        messages.success(
            request,
            "Réservation annulée."
        )


        return redirect(
            "dashboard_admin:reservations"
        )



class AdminReservationRefuseView(AdminBaseView):

    def get(self, request, reservation_id):

        reservation = get_object_or_404(
            Reservation,
            id=reservation_id
        )


        reservation.statut = "CANCELED"
        reservation.save()


        messages.warning(
            request,
            "Réservation refusée."
        )


        return redirect(
            "dashboard_admin:reservations"
        )

from django.views.generic import DetailView
from formation.models import Formation
from formation.models import Formation, Trainer


class FormationDetailView(LoginRequiredMixin, DetailView):
    model = Formation
    template_name = "dashboard/admin/formations_detail.html"
    context_object_name = "formation"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        formation = self.object

        context["sessions"] = formation.sessions.all()
        context["documents"] = formation.pedagogical_documents.all()
        context["trainers"] = Trainer.objects.filter(
            sessions__formation=formation
        ).distinct()
        context["inscriptions"] = formation.registrations.all()

        return context        


from django.views.generic import DetailView
from formation.models import Trainer

class TrainerDetailView(LoginRequiredMixin, DetailView):
    model = Trainer
    pk_url_kwarg = "id"
    context_object_name = "trainer"
    template_name = "dashboard/admin/trainers_detail.html"


class AdminCoworkingSpaceCreateView(AdminBaseView):
    template_name = "dashboard/admin/coworking_space_create.html"

    def get(self, request, *args, **kwargs):
        from coworking.forms import CoworkingSpaceForm
        return render(request, self.template_name, {"form": CoworkingSpaceForm()})

    def post(self, request, *args, **kwargs):
        from coworking.forms import CoworkingSpaceForm
        form = CoworkingSpaceForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Agence CoworkingSpace créée avec succès.")
            return redirect("dashboard_admin:coworking")
        return render(request, self.template_name, {"form": form})


class AdminCoworkingSpaceEditView(AdminBaseView):
    template_name = "dashboard/admin/coworking_space_edit.html"

    def get_object(self, space_id):
        return get_object_or_404(CoworkingSpace, id=space_id)

    def get(self, request, space_id, *args, **kwargs):
        from coworking.forms import CoworkingSpaceForm
        target = self.get_object(space_id)
        return render(request, self.template_name, {"form": CoworkingSpaceForm(instance=target), "target": target})

    def post(self, request, space_id, *args, **kwargs):
        from coworking.forms import CoworkingSpaceForm
        target = self.get_object(space_id)
        form = CoworkingSpaceForm(request.POST, request.FILES, instance=target)
        if form.is_valid():
            form.save()
            messages.success(request, "Agence CoworkingSpace modifiée.")
            return redirect("dashboard_admin:coworking")
        return render(request, self.template_name, {"form": form, "target": target})





# ===== AVIS CLIENTS (TESTIMONIALS) ADMIN =====

class AdminTestimonialListView(AdminBaseView):
    """Liste tous les avis clients avec statut de modération."""
    template_name = "dashboard/admin/testimonials_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["testimonials"] = Testimonial.objects.select_related("utilisateur").order_by("-created_at")
        context["pending_count"] = Testimonial.objects.filter(approuvé=False).count()
        context["approved_count"] = Testimonial.objects.filter(approuvé=True).count()
        return context


class AdminTestimonialApproveView(AdminBaseView):
    """Approuve un avis client pour publication sur la page d'accueil."""

    def post(self, request, testimonial_id, *args, **kwargs):
        testimonial = get_object_or_404(Testimonial, id=testimonial_id)
        testimonial.approuvé = True
        testimonial.approuvé_le = timezone.now()
        testimonial.save(update_fields=["approuvé", "approuvé_le"])
        messages.success(request, f"Avis de {testimonial.utilisateur.full_name} approuvé et publié sur la page d'accueil.")
        return redirect("dashboard_admin:testimonials_list")


class AdminTestimonialRejectView(AdminBaseView):
    """Supprime un avis client (rejet)."""

    def post(self, request, testimonial_id, *args, **kwargs):
        testimonial = get_object_or_404(Testimonial, id=testimonial_id)
        user_name = testimonial.utilisateur.full_name
        testimonial.delete()
        messages.warning(request, f"Avis de {user_name} supprimé (rejeté).")
        return redirect("dashboard_admin:testimonials_list")


class AdminDevisFormationListView(AdminBaseView):
    """Liste des demandes de devis formation pour l'admin."""
    template_name = "dashboard/admin/devis_formation_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from formation.models import DevisFormation

        context["active_section"] = "devis_formation"
        devis_qs = DevisFormation.objects.all().order_by("-created_at")

        # Filtre par statut
        statut_filter = self.request.GET.get("statut", "")
        if statut_filter == "non_lu":
            devis_qs = devis_qs.filter(lu=False)
        elif statut_filter == "lu":
            devis_qs = devis_qs.filter(lu=True)

        context["devis_list"] = devis_qs
        context["total_count"] = DevisFormation.objects.count()
        context["unread_count"] = DevisFormation.objects.filter(lu=False).count()
        context["current_filter"] = statut_filter
        return context


class AdminDevisMarkReadView(AdminBaseView):
    """Marque une demande de devis comme lue."""

    def post(self, request, devis_id, *args, **kwargs):
        from formation.models import DevisFormation
        devis = get_object_or_404(DevisFormation, id=devis_id)
        devis.lu = True
        devis.lu_le = timezone.now()
        devis.save(update_fields=["lu", "lu_le"])
        messages.success(request, "Demande marquée comme lue.")
        return redirect("dashboard_admin:devis_formation_list")


class AdminDevisMarkUnreadView(AdminBaseView):
    """Marque une demande de devis comme non lue."""

    def post(self, request, devis_id, *args, **kwargs):
        from core.models import DevisFormation
        devis = get_object_or_404(DevisFormation, id=devis_id)
        devis.lu = False
        devis.lu_le = None
        devis.save(update_fields=["lu", "lu_le"])
        messages.success(request, "Demande marquée comme non lue.")
        return redirect("dashboard_admin:devis_formation_list")


class AdminCoworkingSpaceDeleteView(AdminBaseView):

    template_name = "dashboard/admin/coworking_space_delete.html"


    def get_object(self, space_id):
        return get_object_or_404(
            CoworkingSpace,
            id=space_id
        )


    def get(self, request, space_id, *args, **kwargs):

        target = self.get_object(space_id)

        return render(
            request,
            self.template_name,
            {
                "target": target
            }
        )


    def post(self, request, space_id, *args, **kwargs):

        target = self.get_object(space_id)

        try:
            target.delete()

            messages.success(
                request,
                "✅ L'espace coworking a été supprimé avec succès."
            )


        except ProtectedError as e:

            messages.error(
                request,
                "⚠ Impossible de supprimer cet espace "
                "car il possède encore des bureaux ou réservations."
            )


        return redirect(
            "dashboard_admin:coworking"
        )


# ═══════════════════════════════════════════════════════════
#  CONCIERGERIE — Gestion des demandes (Dashboard Admin)
# ═══════════════════════════════════════════════════════════

class AdminConciergerieListView(AdminBaseView):
    """Liste toutes les demandes de conciergerie."""
    template_name = "dashboard/admin/conciergerie_requests.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_section"] = "conciergerie"

        statut_filter = self.request.GET.get("statut", "")
        qs = DemandeConciergerie.objects.all().order_by("-created_at")
        if statut_filter:
            qs = qs.filter(statut=statut_filter)

        context["demandes"] = qs
        context["total_count"] = DemandeConciergerie.objects.count()
        context["nouvelle_count"] = DemandeConciergerie.objects.filter(statut="nouvelle").count()
        context["current_filter"] = statut_filter
        return context


class AdminConciergerieDetailView(AdminBaseView):
    """Détail d'une demande de conciergerie."""
    template_name = "dashboard/admin/conciergerie_request_detail.html"

    def get(self, request, demande_id, *args, **kwargs):
        demande = get_object_or_404(DemandeConciergerie, id=demande_id)
        return render(request, self.template_name, {"demande": demande, "active_section": "conciergerie"})


class AdminConciergerieValidateView(AdminBaseView):
    """Valide une demande (passe en 'acceptee')."""

    def post(self, request, demande_id, *args, **kwargs):
        demande = get_object_or_404(DemandeConciergerie, id=demande_id)
        demande.statut = "acceptee"
        demande.save(update_fields=["statut"])
        messages.success(request, f"Demande {demande.reference} acceptée.")
        return redirect("dashboard_admin:conciergerie_list")


class AdminConciergerieRefuseView(AdminBaseView):
    """Refuse une demande."""

    def post(self, request, demande_id, *args, **kwargs):
        demande = get_object_or_404(DemandeConciergerie, id=demande_id)
        demande.statut = "refusee"
        demande.save(update_fields=["statut"])
        messages.warning(request, f"Demande {demande.reference} refusée.")
        return redirect("dashboard_admin:conciergerie_list")

from django.shortcuts import render, get_object_or_404

from domiciliation.models import DomiciliationRequest


def domiciliation_detail(request, request_id):

    demande = get_object_or_404(
        DomiciliationRequest,
        id=request_id
    )

    documents = demande.documents.all().order_by("created_at")

    return render(
        request,
        "dashboard/admin/domiciliation_detail.html",
        {
            "demande": demande,
            "documents": documents,
        }
    )


def domiciliation_contract_view(request, request_id):
    """Aperçu / téléchargement du contrat pour l'administrateur."""
    from django.http import FileResponse, Http404

    demande = get_object_or_404(DomiciliationRequest, id=request_id)
    contract = getattr(demande, "contrat", None)
    if not contract or not contract.fichier_pdf:
        from django.contrib import messages
        messages.error(request, "Aucun contrat généré pour cette demande.")
        return redirect("dashboard_admin:domiciliation_detail", request_id=request_id)

    response = FileResponse(
        contract.fichier_pdf.open("rb"),
        content_type="application/pdf",
    )
    response["Content-Disposition"] = f'inline; filename="{contract.numero}.pdf"'
    return response


def domiciliation_contract_send(request, request_id):
    """Envoie le contrat de domiciliation par email à l'utilisateur."""
    from django.contrib import messages
    from django.core.mail import EmailMessage
    from django.conf import settings

    from notification.models import NotificationType
    from notification.services import NotificationService

    from domiciliation.models import DomiciliationContract, DomiciliationLog

    demande = get_object_or_404(DomiciliationRequest, id=request_id)
    contract = getattr(demande, "contrat", None)
    if not contract or not contract.fichier_pdf:
        messages.error(request, "Aucun contrat généré. Impossible d'envoyer.")
        return redirect("dashboard_admin:domiciliation_detail", request_id=request_id)

    # Lien vers l'espace membre
    espace_url = (
        f"{settings.SITE_URL}{reverse('domiciliation:request_detail', args=[str(demande.id)])}"
    )

    subject = f"📄 Votre contrat de domiciliation {demande.numero_demande}"
    body = (
        f"Bonjour {demande.utilisateur.get_full_name()},\n\n"
        f"Votre contrat de domiciliation est disponible en pièce jointe.\n"
        f"Vous pouvez également le télécharger depuis votre espace client :\n"
        f"{espace_url}\n\n"
        f"Cordialement,\nL'équipe EliteBuro"
    )

    email = EmailMessage(
        subject=subject,
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[demande.utilisateur.email],
    )
    # Pièce jointe PDF
    email.attach(
        f"{contract.numero}.pdf",
        contract.fichier_pdf.read(),
        "application/pdf",
    )
    email.send(fail_silently=False)

    # Envoyer aussi une notification HTML (plus jolie)
    NotificationService.notify(
        user=demande.utilisateur,
        title=subject,
        message=(
            f"Bonjour {demande.utilisateur.get_full_name()},\n\n"
            f"Votre contrat de domiciliation {demande.numero_demande} a été généré "
            f"et vous est envoyé par email.\n"
            f"Vous pouvez aussi le consulter dans votre espace client :\n{espace_url}"
        ),
        notification_type=NotificationType.EMAIL,
    )

    # Journaliser l'envoi
    DomiciliationLog.objects.create(
        demande=demande,
        utilisateur=request.user,
        action="CONTRAT_ENVOYE",
        details="Contrat envoyé par email à l'utilisateur.",
    )

    demande.statut = DomiciliationRequest.Status.CONTRAT_ENVOYÉ
    demande.save(update_fields=["statut", "derniere_modification"])

    messages.success(
        request,
        f"Le contrat a été envoyé à {demande.utilisateur.email}.",
    )
    return redirect("dashboard_admin:domiciliation_detail", request_id=request_id)


from django.http import FileResponse, HttpResponse
from django.core.mail import EmailMessage


def domiciliation_contract_view(request, request_id):
    """Génère (si nécessaire) puis affiche/retourne le contrat PDF de la demande.

    L'admin clique sur « Contrat » depuis le détail de la demande : le fichier
    est créé automatiquement s'il n'existe pas encore, puis ouvert (inline).
    """
    from domiciliation.services import generer_contrat_pour_demande

    demande = get_object_or_404(
        DomiciliationRequest.objects.select_related("utilisateur", "entreprise", "formule"),
        id=request_id,
    )

    contract = generer_contrat_pour_demande(demande=demande)

    if not contract.fichier_pdf:
        messages.error(request, "Le contrat n'a pas pu être généré.")
        return redirect("dashboard_admin:domiciliation_detail", request_id=demande.id)

    response = FileResponse(
        contract.fichier_pdf.open("rb"),
        content_type="application/pdf",
    )
    response["Content-Disposition"] = (
        f'inline; filename="{contract.numero}.pdf"'
    )
    return response


from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.urls import reverse


def domiciliation_contract_send(request, request_id):
    """
    Génère le contrat PDF puis l'envoie par email au demandeur.
    Le corps du mail est généré à partir du template HTML :
    templates/emails/domiciliation_contract.html
    """

    from domiciliation.services import generer_contrat_pour_demande
    from domiciliation.models import DomiciliationLog

    demande = get_object_or_404(
        DomiciliationRequest.objects.select_related(
            "utilisateur",
            "entreprise",
            "formule",
        ),
        id=request_id,
    )

    # Génération du contrat
    contract = generer_contrat_pour_demande(demande=demande)

    if not contract.fichier_pdf:
        messages.error(
            request,
            "Le contrat n'a pas pu être généré."
        )
        return redirect(
            "dashboard_admin:domiciliation_detail",
            request_id=demande.id,
        )

    # URL de l'espace membre
    espace_url = request.build_absolute_uri(
        reverse(
            "domiciliation:request_detail",
            args=[demande.id],
        )
    )

    sujet = (
        f"📄 Votre contrat de domiciliation "
        f"{demande.numero_demande}"
    )

    # ==========================
    # Email HTML
    # ==========================

    html_message = render_to_string(
        "emails/domiciliation_contract.html",
        {
            "demande": demande,
            "contract": contract,
            "espace_url": espace_url,
            "entreprise": demande.entreprise,
        },
    )

    # Version texte (pour Outlook, Gmail...)
    text_message = strip_tags(html_message)

    email = EmailMessage(
        subject=sujet,
        body=text_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[demande.utilisateur.email],
    )

    # Remplacer le corps par le HTML
    email.content_subtype = "html"
    email.body = html_message

    # ==========================
    # Pièce jointe PDF
    # ==========================

    contract.fichier_pdf.open("rb")

    email.attach(
        f"{contract.numero}.pdf",
        contract.fichier_pdf.read(),
        "application/pdf",
    )

    contract.fichier_pdf.close()

    # Envoi
    email.send(fail_silently=False)

    # Journalisation
    DomiciliationLog.objects.create(
        demande=demande,
        utilisateur=request.user,
        action="CONTRAT_ENVOYE",
        details=(
            f"Contrat {contract.numero} envoyé "
            f"à {demande.utilisateur.email}"
        ),
    )

    messages.success(
        request,
        f"Le contrat a été envoyé à {demande.utilisateur.email}.",
    )

    return redirect(
        "dashboard_admin:domiciliation_detail",
        request_id=demande.id,
    )


from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.core.mail import EmailMessage
from django.conf import settings
from django.utils import timezone

from formation.models import DevisFormation




def send_devis_email(request, pk):

    devis = get_object_or_404(
        DevisFormation,
        id=pk
    )

    # Vérification
    if not devis.montant_propose:
        messages.error(
            request,
            "Veuillez renseigner le montant proposé avant l'envoi."
        )

        return redirect(
            "dashboard_trainer:devis_formation_detail",
            pk=pk
        )

    sujet = "Votre devis de formation EliteBuro"

    message = f"""
Bonjour {devis.nom},

Nous avons le plaisir de vous transmettre en pièce jointe votre devis de formation.



Veuillez trouver le devis PDF en pièce jointe.

Cordialement,

L'équipe EliteBuro Formation
"""

    # Génération du PDF
    pdf_bytes = generer_devis_pdf(devis)

    email = EmailMessage(
        subject=sujet,
        body=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[devis.email],
    )

    email.attach(
        f"{devis.numero_devis}.pdf",
        pdf_bytes,
        "application/pdf"
    )

    email.send(fail_silently=False)

    devis.statut = DevisFormation.Statut.DEVIS_ENVOYE
    devis.date_envoi = timezone.now()

    devis.save(
        update_fields=[
            "statut",
            "date_envoi"
        ]
    )

    messages.success(
        request,
        "Le devis PDF a été envoyé au client."
    )

    return redirect(
        "dashboard_trainer:devis_formation_detail",
        pk=pk
    )

# ============================================================
# PDF DEVIS FORMATION ELITEBURO - PARTIE 1
# Imports + styles + en-tête
# ============================================================

from io import BytesIO
from decimal import Decimal

from django.http import HttpResponse
from django.conf import settings
from django.utils import timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image,
    Table,
    TableStyle,
    PageBreak
)

from reportlab.lib.units import cm


# ============================================================
# COULEURS CHARTE ELITEBURO
# ============================================================

ORANGE = colors.HexColor("#FF8000")
ORANGE_LIGHT = colors.HexColor("#FDE8D0")

NOIR = colors.HexColor("#1A1A1A")
GRIS = colors.HexColor("#666666")
GRIS_CLAIR = colors.HexColor("#F5F5F5")

BLANC = colors.white


# ============================================================
# GENERATION PDF DEVIS FORMATION
# ============================================================

def generer_devis_pdf(devis):

    from formation.models import DevisFormation

    # devis est déjà l'objet DevisFormation
    pass


    # --------------------------------------------------------
    # Création du fichier PDF en mémoire
    # --------------------------------------------------------

    buffer = BytesIO()


    pdf = SimpleDocTemplate(
        buffer,
        pagesize=A4,

        rightMargin=1.5*cm,
        leftMargin=1.5*cm,
        topMargin=1.5*cm,
        bottomMargin=1.5*cm
    )



    elements = []



    # ========================================================
    # STYLES
    # ========================================================

    styles = getSampleStyleSheet()



    style_title = ParagraphStyle(
        "TitleElite",
        parent=styles["Heading1"],

        fontName="Helvetica-Bold",
        fontSize=18,

        textColor=ORANGE,

        alignment=TA_RIGHT,

        spaceAfter=10
    )



    style_subtitle = ParagraphStyle(
        "SubtitleElite",

        parent=styles["Normal"],

        fontSize=10,

        textColor=GRIS,

        alignment=TA_RIGHT
    )



    style_normal = ParagraphStyle(

        "NormalElite",

        parent=styles["Normal"],

        fontName="Helvetica",

        fontSize=9,

        leading=13,

        textColor=NOIR
    )



    style_client = ParagraphStyle(

        "ClientElite",

        parent=style_normal,

        fontSize=10,

        leading=15
    )



    style_section = ParagraphStyle(

        "SectionElite",

        parent=styles["Heading3"],

        fontSize=11,

        textColor=BLANC,

        backColor=ORANGE,

        leftIndent=5,

        spaceBefore=10,

        spaceAfter=8
    )



    # ========================================================
    # EN-TETE ENTREPRISE
    # ========================================================


    logo_path = None


    try:

        logo_path = settings.BASE_DIR / "media" / "ELITE BURO LOG1.jpg"

    except:

        pass



    header_data = []



    # Logo

    if logo_path and logo_path.exists():

        logo = Image(
            str(logo_path),
            width=3*cm,
            height=1.3*cm
        )


    else:

        logo = Paragraph(
            "<b>ELITEBURO</b>",
            style_title
        )



    # Informations entreprise

    company_info = Paragraph(

        """
        <b>ELITEBURO</b><br/>
        Solutions professionnelles pour entreprises<br/>
        Domiciliation • Formation • Conciergerie<br/><br/>

        Abidjan, Côte d'Ivoire<br/>
        Téléphone : +225 XX XX XX XX XX<br/>
        Email : contact@eliteburo.com
        """,

        style_normal

    )



    devis_info = Paragraph(

        f"""
        <font size="18">
        <b>DEVIS</b>
        </font><br/><br/>

        <b>N° :</b> {devis.numero_devis}<br/>

        <b>Date :</b>
        {timezone.now().strftime("%d/%m/%Y")}

        """,

        style_subtitle

    )




    header_table = Table(

        [
            [
                logo,
                company_info,
                devis_info
            ]
        ],

        colWidths=[
            4*cm,
            7*cm,
            4*cm
        ]

    )



    header_table.setStyle(

        TableStyle(

            [

                (
                    "VALIGN",
                    (0,0),
                    (-1,-1),
                    "TOP"
                ),

                (
                    "LINEBELOW",
                    (0,0),
                    (-1,-1),
                    1,
                    ORANGE
                ),

                (
                    "BOTTOMPADDING",
                    (0,0),
                    (-1,-1),
                    15
                )

            ]

        )

    )



    elements.append(
        header_table
    )


    elements.append(
        Spacer(1,20)
    )



    # ========================================================
    # INFORMATIONS CLIENT
    # ========================================================


    elements.append(

        Paragraph(
            "INFORMATIONS CLIENT",
            style_section
        )

    )



    client_table = Table(

        [

            [

                Paragraph(
                    f"""
                    <b>Entreprise :</b>
                    {devis.company_name or "-"}<br/>

                    <b>RCCM :</b>
                    {devis.rccm or "-"}<br/>

                    <b>Contact :</b>
                    {devis.nom or "-"}<br/>

                    <b>Fonction :</b>
                    {devis.fonction or "-"}<br/>

                    <b>Email :</b>
                    {devis.email or "-"}<br/>

                    <b>Téléphone :</b>
                    {devis.telephone or "-"}
                    """,

                    style_client
                ),


                Paragraph(
                    f"""
                    <b>Secteur :</b>
                    {devis.secteur or "-"}<br/>

                    <b>Taille :</b>
                    {devis.taille or "-"}<br/>

                    <b>Adresse :</b>
                    {devis.adresse or "-"}<br/>

                    <b>Participants :</b>
                    {devis.participants}<br/>

                    <b>Durée :</b>
                    {devis.duree or "-"}
                    """,

                    style_client
                )

            ]

        ],


        colWidths=[
            8*cm,
            7*cm
        ]

    )



    client_table.setStyle(

        TableStyle(

            [

                (
                    "BACKGROUND",
                    (0,0),
                    (-1,-1),
                    GRIS_CLAIR
                ),

                (
                    "BOX",
                    (0,0),
                    (-1,-1),
                    0.5,
                    colors.lightgrey
                ),

                (
                    "VALIGN",
                    (0,0),
                    (-1,-1),
                    "TOP"
                ),

                (
                    "PADDING",
                    (0,0),
                    (-1,-1),
                    10
                )

            ]

        )

    )



    elements.append(
        client_table
    )


    elements.append(
        Spacer(1,20)
    )



    # La suite arrive dans PARTIE 2 :
    # - tableau formation
    # - calcul HT
    # - TVA
    # - TTC
    # - total en lettres
    # ============================================================
# PDF DEVIS FORMATION ELITEBURO - PARTIE 2
# Tableau prestation + TVA + Total
# ============================================================


    # ========================================================
    # DESIGNATION DE LA PRESTATION
    # ========================================================


    elements.append(

        Paragraph(
            "DETAIL DE LA PRESTATION",
            style_section
        )

    )



    # Récupération des valeurs du devis

    # ========================================================
    # DESIGNATION DE LA PRESTATION
    # ========================================================

    designation = "Formation professionnelle EliteBuro"

    if devis.programme:
        designation = devis.programme

    elif devis.objectifs:
        designation = devis.objectifs[:200]



    # Prix

    prix_ht = Decimal(
        devis.montant_propose or 0
    )


    quantite = devis.participants or 1



    total_ht = prix_ht * quantite



    # TVA Côte d'Ivoire 18%

    taux_tva = Decimal("18")


    montant_tva = (
        total_ht * taux_tva / 100
    )



    total_ttc = (
        total_ht + montant_tva
    )




    # ========================================================
    # TABLEAU PRINCIPAL
    # ========================================================


    prestation_table = Table(

        [

            [

                Paragraph(
                    "<b>Désignation</b>",
                    style_normal
                ),

                Paragraph(
                    "<b>Qté</b>",
                    style_normal
                ),

                Paragraph(
                    "<b>Prix HT</b>",
                    style_normal
                ),

                Paragraph(
                    "<b>Total HT</b>",
                    style_normal
                )

            ],


            [

                Paragraph(
                    designation,
                    style_normal
                ),


                Paragraph(
                    str(quantite),
                    style_normal
                ),


                Paragraph(
                    f"{prix_ht:,.0f} FCFA",
                    style_normal
                ),


                Paragraph(
                    f"{total_ht:,.0f} FCFA",
                    style_normal
                )

            ]

        ],


        colWidths=[

            8*cm,
            1.5*cm,
            3*cm,
            3*cm

        ]

    )



    prestation_table.setStyle(

        TableStyle(

            [

                (
                    "BACKGROUND",
                    (0,0),
                    (-1,0),
                    ORANGE
                ),


                (
                    "TEXTCOLOR",
                    (0,0),
                    (-1,0),
                    BLANC
                ),


                (
                    "ALIGN",
                    (1,0),
                    (-1,-1),
                    "CENTER"
                ),


                (
                    "GRID",
                    (0,0),
                    (-1,-1),
                    0.5,
                    colors.lightgrey
                ),


                (
                    "VALIGN",
                    (0,0),
                    (-1,-1),
                    "MIDDLE"
                ),


                (
                    "PADDING",
                    (0,0),
                    (-1,-1),
                    8
                )

            ]

        )

    )



    elements.append(

        prestation_table

    )



    elements.append(

        Spacer(
            1,
            15
        )

    )



    # ========================================================
    # RECAPITULATIF FINANCIER
    # ========================================================



    total_table = Table(

        [

            [

                Paragraph(
                    "Total HT",
                    style_normal
                ),

                Paragraph(
                    f"{total_ht:,.0f} FCFA",
                    style_normal
                )

            ],


            [

                Paragraph(
                    f"TVA ({taux_tva}%)",
                    style_normal
                ),

                Paragraph(
                    f"{montant_tva:,.0f} FCFA",
                    style_normal
                )

            ],


            [

                Paragraph(
                    "<b>TOTAL TTC</b>",
                    style_normal
                ),

                Paragraph(
                    f"<b>{total_ttc:,.0f} FCFA</b>",
                    style_normal
                )

            ]

        ],


        colWidths=[

            10*cm,
            5.5*cm

        ]

    )



    total_table.setStyle(

        TableStyle(

            [

                (
                    "BACKGROUND",
                    (0,2),
                    (-1,2),
                    ORANGE_LIGHT
                ),


                (
                    "BOX",
                    (0,0),
                    (-1,-1),
                    0.8,
                    ORANGE
                ),


                (
                    "LINEBELOW",
                    (0,0),
                    (-1,1),
                    0.3,
                    colors.grey
                ),


                (
                    "ALIGN",
                    (1,0),
                    (-1,-1),
                    "RIGHT"
                ),


                (
                    "PADDING",
                    (0,0),
                    (-1,-1),
                    10
                )

            ]

        )

    )



    elements.append(

        total_table

    )


    elements.append(

        Spacer(
            1,
            20
        )

    )



    # ========================================================
    # DESCRIPTION FORMATION
    # ========================================================


    elements.append(

        Paragraph(
            "DESCRIPTION",
            style_section
        )

    )



    description = devis.objectifs or devis.programme or "Formation professionnelle EliteBuro."



    elements.append(

        Paragraph(

            description,

            style_normal

        )

    )



    elements.append(

        Spacer(
            1,
            20
        )

    )

    # ============================================================
# PDF DEVIS FORMATION ELITEBURO - PARTIE 3
# Pied de page + signature + génération finale
# ============================================================



    # ========================================================
    # CONDITIONS DE REGLEMENT
    # ========================================================


    elements.append(

        Paragraph(
            "CONDITIONS DE REGLEMENT",
            style_section
        )

    )



    conditions = """

    <b>Modalités :</b><br/>

    • Paiement à effectuer selon les conditions convenues avec EliteBuro.<br/>
    • Le devis est valable pendant 30 jours à compter de sa date d'émission.<br/>
    • Toute prestation commencée est due.<br/>
    • Les formations sont accessibles après validation administrative et financière.

    """



    elements.append(

        Paragraph(
            conditions,
            style_normal
        )

    )



    elements.append(

        Spacer(
            1,
            20
        )

    )




    # ========================================================
    # COORDONNEES BANCAIRES
    # ========================================================


    elements.append(

        Paragraph(
            "COORDONNEES BANCAIRES",
            style_section
        )

    )



    banque = """

    <b>ELITEBURO</b><br/>

    Banque : ...............................................<br/>

    IBAN : .................................................<br/>

    Code SWIFT : ...........................................<br/>

    Mobile Money : +225 XX XX XX XX XX

    """



    elements.append(

        Paragraph(
            banque,
            style_normal
        )

    )



    elements.append(

        Spacer(
            1,
            25
        )

    )




    # ========================================================
    # SIGNATURES
    # ========================================================


    signature_table = Table(

        [

            [

                Paragraph(

                    """
                    <b>ELITEBURO</b><br/><br/>

                    Signature et cachet<br/><br/><br/>


                    ______________________

                    """,

                    style_normal

                ),



                Paragraph(

                    """
                    <b>CLIENT</b><br/><br/>

                    Bon pour accord<br/><br/><br/>


                    ______________________

                    """,

                    style_normal

                )

            ]

        ],


        colWidths=[

            7.5*cm,
            7.5*cm

        ]

    )



    signature_table.setStyle(

        TableStyle(

            [

                (
                    "VALIGN",
                    (0,0),
                    (-1,-1),
                    "TOP"
                ),


                (
                    "ALIGN",
                    (0,0),
                    (-1,-1),
                    "CENTER"
                ),


                (
                    "BOX",
                    (0,0),
                    (-1,-1),
                    0.5,
                    colors.lightgrey
                ),


                (
                    "PADDING",
                    (0,0),
                    (-1,-1),
                    15
                )

            ]

        )

    )



    elements.append(

        signature_table

    )



    elements.append(

        Spacer(
            1,
            20
        )

    )





    # ========================================================
    # PIED DE PAGE
    # ========================================================


    def footer_page(canvas, doc):


        canvas.saveState()


        canvas.setFont(
            "Helvetica",
            8
        )


        canvas.setFillColor(
            GRIS
        )


        canvas.drawCentredString(

            A4[0] / 2,

            1 * cm,

            "EliteBuro - Solutions professionnelles | Abidjan Côte d'Ivoire"

        )


        canvas.drawRightString(

            A4[0] - 1.5*cm,

            1*cm,

            f"Page {doc.page}"

        )


        canvas.restoreState()




    # ========================================================
    # GENERATION DU PDF
    # ========================================================


    pdf.build(

        elements,

        onFirstPage=footer_page,

        onLaterPages=footer_page

    )



    pdf_value = buffer.getvalue()


    buffer.close()



    return pdf_value


def devis_formation_pdf(request, devis_id):

    devis = get_object_or_404(
        DevisFormation,
        id=devis_id
    )

    pdf = generer_devis_pdf(devis)


    response = HttpResponse(
        pdf,
        content_type="application/pdf"
    )


    response["Content-Disposition"] = (
        f'attachment; filename="devis_{devis.numero_devis}.pdf"'
    )


    return response


# ============================================================
#  CHANGEMENT DE GÉRANT — BACK-OFFICE ADMIN
# ============================================================

class AdminChangementGerantListView(AdminBaseView):
    """Liste toutes les demandes de changement de gérant."""
    template_name = "dashboard/admin/changement_gerant_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_section"] = "changement_gerant"

        statut_filter = self.request.GET.get("statut", "")
        qs = ChangementGerant.objects.all().select_related(
            "demandeur", "entreprise"
        ).order_by("-date_creation")

        if statut_filter:
            qs = qs.filter(statut=statut_filter)

        context["demandes"] = qs
        context["total_count"] = ChangementGerant.objects.count()
        context["en_attente_count"] = ChangementGerant.objects.filter(statut="EN_ATTENTE").count()
        context["current_filter"] = statut_filter
        context["statut_choices"] = ChangementGerant.Statut.choices
        return context


class AdminChangementGerantDetailView(AdminBaseView):
    """Détail d'une demande de changement de gérant."""
    template_name = "dashboard/admin/changement_gerant_detail.html"

    def get(self, request, demande_id, *args, **kwargs):
        demande = get_object_or_404(
            ChangementGerant.objects.select_related("demandeur", "entreprise"),
            id=demande_id
        )
        return render(
            request,
            self.template_name,
            {
                "demande": demande,
                "active_section": "changement_gerant",
            }
        )


class AdminChangementGerantValidateView(AdminBaseView):
    """Valide une demande de changement de gérant."""

    def post(self, request, demande_id, *args, **kwargs):
        demande = get_object_or_404(ChangementGerant, id=demande_id)
        commentaire = (request.POST.get("commentaire_admin") or "").strip()

        demande.statut = ChangementGerant.Statut.VALIDE
        demande.commentaire_admin = commentaire
        demande.date_validation = timezone.now()
        demande.save(update_fields=["statut", "commentaire_admin", "date_validation", "date_modification"])

        messages.success(request, f"Demande #{demande.pk} validée avec succès.")
        return redirect("dashboard_admin:changement_gerant_list")


class AdminChangementGerantRefuseView(AdminBaseView):
    """Refuse une demande de changement de gérant."""

    def post(self, request, demande_id, *args, **kwargs):
        demande = get_object_or_404(ChangementGerant, id=demande_id)
        commentaire = (request.POST.get("commentaire_admin") or "").strip()

        demande.statut = ChangementGerant.Statut.REJETE
        demande.commentaire_admin = commentaire
        demande.save(update_fields=["statut", "commentaire_admin", "date_modification"])

        messages.warning(request, f"Demande #{demande.pk} refusée.")
        return redirect("dashboard_admin:changement_gerant_list")


class AdminChangementGerantTerminateView(AdminBaseView):
    """Termine le traitement d'une demande de changement de gérant."""

    def post(self, request, demande_id, *args, **kwargs):
        demande = get_object_or_404(ChangementGerant, id=demande_id)
        commentaire = (request.POST.get("commentaire_admin") or "").strip()

        demande.statut = ChangementGerant.Statut.TERMINE
        demande.commentaire_admin = commentaire
        demande.date_terminaison = timezone.now()
        demande.save(update_fields=["statut", "commentaire_admin", "date_terminaison", "date_modification"])

        messages.success(request, f"Demande #{demande.pk} marquée comme terminée.")
        return redirect("dashboard_admin:changement_gerant_list")


