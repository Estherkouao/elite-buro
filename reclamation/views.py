from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import CreateView, DetailView, ListView

from .models import Reclamation


def is_admin(user) -> bool:
    # On utilise is_staff pour le back-office.
    return bool(user and user.is_staff)


# =============================================================================
# VUES MEMBRE (côté utilisateur connecté)
# =============================================================================

class MemberReclamationCreateView(LoginRequiredMixin, CreateView):
    """Permet à un membre de créer une nouvelle réclamation."""
    model = Reclamation
    template_name = "reclamation/member_create.html"
    fields = ["objet", "description"]

    def form_valid(self, form):
        form.instance.auteur = self.request.user
        messages.success(self.request, "Votre réclamation a été soumise avec succès. Nous la traiterons dans les plus brefs délais.")

        # Notification à l'admin
        from notification.services import NotificationService
        from django.contrib.auth import get_user_model
        User = get_user_model()
        admins = User.objects.filter(is_staff=True)
        for admin in admins:
            NotificationService.notify(
                user=admin,
                title="Nouvelle réclamation",
                message=f"Un membre a soumis une nouvelle réclamation : {form.instance.objet}",
            )

        return super().form_valid(form)

    def get_success_url(self):
        return reverse("reclamation:member_list")


class MemberReclamationListView(LoginRequiredMixin, ListView):
    """Affiche la liste des réclamations du membre connecté."""
    model = Reclamation
    template_name = "reclamation/member_list.html"
    context_object_name = "reclamations"
    paginate_by = 10

    def get_queryset(self):
        return Reclamation.objects.filter(auteur=self.request.user).order_by("-created_at")


class MemberReclamationDetailView(LoginRequiredMixin, DetailView):
    """Affiche le détail d'une réclamation du membre connecté."""
    model = Reclamation
    template_name = "reclamation/member_detail.html"
    context_object_name = "reclamation"

    def get_queryset(self):
        # Sécurité : le membre ne voit que ses propres réclamations
        return Reclamation.objects.filter(auteur=self.request.user)



@method_decorator(user_passes_test(is_admin, login_url="/accounts/login/"), name="dispatch")
class AdminReclamationListView(ListView):
    model = Reclamation
    template_name = "reclamation/admin_list.html"
    context_object_name = "reclamations"
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(objet__icontains=q)
                | Q(description__icontains=q)
                | Q(auteur__username__icontains=q)
            )
        statut = self.request.GET.get("statut")
        if statut in dict(Reclamation.Status.choices):
            qs = qs.filter(statut=statut)
        return qs.select_related("auteur")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["statuts"] = Reclamation.Status.values
        return ctx


@method_decorator(user_passes_test(is_admin, login_url="/accounts/login/"), name="dispatch")
class AdminReclamationDetailView(DetailView):
    model = Reclamation
    template_name = "reclamation/admin_detail.html"
    context_object_name = "reclamation"
    pk_url_kwarg = "reclamation_id"


@method_decorator(user_passes_test(is_admin, login_url="/accounts/login/"), name="dispatch")
class AdminReclamationEditView(View):
    template_name = "reclamation/admin_edit.html"

    def dispatch(self, request, *args, **kwargs):
        self.reclamation = get_object_or_404(Reclamation, pk=kwargs["reclamation_id"])
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, reclamation_id, *args, **kwargs):
        return render(
            request,
            self.template_name,
            {"reclamation": self.reclamation, "statuts": Reclamation.Status.choices},
        )

    def post(self, request, reclamation_id, *args, **kwargs):
        reclamation = self.reclamation
        reclamation.objet = request.POST.get("objet", reclamation.objet)
        reclamation.description = request.POST.get("description", reclamation.description)
        # le statut est géré via les endpoints dédiés (close/reopen) mais on le laisse éditable
        statut = request.POST.get("statut")
        if statut in Reclamation.Status.values:
            reclamation.statut = statut

        reponse_admin = request.POST.get("reponse_admin")
        had_response_before = bool(reclamation.reponse_admin)
        reclamation.reponse_admin = reponse_admin if reponse_admin else None

        if reclamation.statut == Reclamation.Status.CLOTUREE and reclamation.closed_at is None:
            reclamation.closed_at = reclamation.updated_at
        if reclamation.statut == Reclamation.Status.OUVERTE:
            reclamation.closed_at = None

        reclamation.save()

        # Notification au membre si l'admin a répondu
        if reclamation.reponse_admin and not had_response_before:
            from notification.services import NotificationService
            NotificationService.notify(
                user=reclamation.auteur,
                title="Réponse à votre réclamation",
                message=f"L'équipe EliteBuro a répondu à votre réclamation : {reclamation.objet}. Cliquez pour voir la réponse.",
            )

        return redirect("reclamation_admin:detail", reclamation_id=reclamation.id)


@method_decorator(user_passes_test(is_admin, login_url="/accounts/login/"), name="dispatch")
class AdminReclamationCloseView(View):
    def post(self, request, reclamation_id, *args, **kwargs):
        reclamation = get_object_or_404(Reclamation, pk=reclamation_id)
        reclamation.statut = Reclamation.Status.CLOTUREE
        reclamation.closed_at = reclamation.updated_at
        reclamation.save()
        return redirect("reclamation_admin:detail", reclamation_id=reclamation.id)


@method_decorator(user_passes_test(is_admin, login_url="/accounts/login/"), name="dispatch")
class AdminReclamationReopenView(View):
    def post(self, request, reclamation_id, *args, **kwargs):
        reclamation = get_object_or_404(Reclamation, pk=reclamation_id)
        reclamation.statut = Reclamation.Status.OUVERTE
        reclamation.closed_at = None
        reclamation.save()
        return redirect("reclamation_admin:detail", reclamation_id=reclamation.id)

