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
from domiciliation.models import DomiciliationRequest

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
        context["requests"] = DomiciliationRequest.objects.select_related(
            "entreprise",
            "utilisateur",
            "formule",
        ).order_by("-date_creation")
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

        obj = get_object_or_404(DomiciliationRequest, id=request_id)
        obj.statut = DomiciliationRequest.Status.ACTIVE
        obj.save(update_fields=["statut"])

        DomiciliationLog.objects.create(
            demande=obj,
            utilisateur=request.user,
            action="VALIDATION",
            details="Demande validée par l’admin.",
        )

        return redirect("dashboard_admin:domiciliation_requests")


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
