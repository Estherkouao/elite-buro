from __future__ import annotations

from datetime import datetime, date
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Sum, Avg, Q
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseForbidden
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView

from accounts.models import User, Profile
from formation.models import (
    Trainer,
    Formation,
    FormationSession,
    FormationRegistration,
    FormationPayment,
    FormationReview,
    FormationPedagogicalDocument,
    FormationCategory,
    FormationQuote,
    FormationContract,
    FormationCertificate,
)
from formation.services import notify_member_registration_confirmed
from dashboard.models import Notification as DashNotification

from .permissions import is_trainer
from formation.forms import FormationSessionForm


class TrainerDashboardView(LoginRequiredMixin, View):
    """Dashboard pour les formateurs (TRAINER)."""

    template_name = "dashboard/trainer/trainer_dasbord.html"

    def dispatch(self, request: HttpRequest, *args, **kwargs):
        if not is_trainer(request.user):
            return HttpResponseForbidden("Accès réservé aux formateurs.")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request: HttpRequest, *args, **kwargs):
        user = request.user
        import datetime as dt_module

        try:
            trainer = Trainer.objects.select_related("user").get(user=user)
        except Trainer.DoesNotExist:
            trainer = None

        sessions_all = FormationSession.objects.filter(formateur=trainer) if trainer else FormationSession.objects.none()
        sessions_count = sessions_all.count()

        now = timezone.now()
        first_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        sessions_this_month = sessions_all.filter(date_debut__gte=first_of_month).count()

        if first_of_month.month == 1:
            first_of_last_month = first_of_month.replace(year=first_of_month.year - 1, month=12)
        else:
            first_of_last_month = first_of_month.replace(month=first_of_month.month - 1)
        sessions_last_month = sessions_all.filter(
            date_debut__gte=first_of_last_month,
            date_debut__lt=first_of_month,
        ).count()

        if sessions_last_month > 0:
            sessions_trend = round(((sessions_this_month - sessions_last_month) / sessions_last_month) * 100)
        else:
            sessions_trend = 0

        registrations = FormationRegistration.objects.filter(
            session__formateur=trainer
        ) if trainer else FormationRegistration.objects.none()
        total_students = registrations.count()

        students_this_month = registrations.filter(
            date__gte=first_of_month
        ).count()

        students_last_month = registrations.filter(
            date__gte=first_of_last_month,
            date__lt=first_of_month,
        ).count()
        if students_last_month > 0:
            students_trend = round(((students_this_month - students_last_month) / students_last_month) * 100)
        else:
            students_trend = 0

        payments = FormationPayment.objects.filter(
            inscription__session__formateur=trainer,
            statut=FormationPayment.Statut.PAID,
        ) if trainer else FormationPayment.objects.none()

        total_revenue = payments.aggregate(total=Sum("montant"))["total"] or Decimal("0.00")

        revenue_this_month = payments.filter(
            inscription__date__gte=first_of_month
        ).aggregate(total=Sum("montant"))["total"] or Decimal("0.00")

        revenue_last_month = payments.filter(
            inscription__date__gte=first_of_last_month,
            inscription__date__lt=first_of_month,
        ).aggregate(total=Sum("montant"))["total"] or Decimal("0.00")
        if revenue_last_month > 0:
            revenue_trend = round(float(((revenue_this_month - revenue_last_month) / revenue_last_month) * 100))
        else:
            revenue_trend = 0

        formations_ids = list(
            FormationSession.objects.filter(formateur=trainer)
            .values_list("formation_id", flat=True)
            .distinct()
        ) if trainer else []

        reviews = FormationReview.objects.filter(
            membre__formation_registrations__session__formation_id__in=formations_ids
        )

        avg_rating = reviews.aggregate(avg=Avg("note"))["avg"] or 0.0
        avg_rating = round(avg_rating, 1)
        total_reviews = reviews.count()

        if total_reviews > 0:
            satisfaction_rate = round(
                (reviews.filter(note__gte=4).count() / total_reviews) * 100
            )
        else:
            satisfaction_rate = 0

        recent_sessions = (
            sessions_all
            .select_related("formation", "formateur__user")
            .order_by("-date_debut", "-heure_debut")[:5]
        )

        session_data = []
        for s in recent_sessions:
            reg_count = FormationRegistration.objects.filter(
                session=s,
                statut__in=[FormationRegistration.Statut.CONFIRMED, FormationRegistration.Statut.PENDING]
            ).count()

            session_data.append({
                "session": s,
                "registrations_count": reg_count,
                "formation_title": s.formation.titre,
                "module": s.formation.description_courte or "",
            })

        today = timezone.now().date()
        upcoming_sessions = (
            sessions_all
            .filter(date_debut__gte=today, statut__in=["published", "open"])
            .select_related("formation")
            .order_by("date_debut", "heure_debut")[:5]
        )

        upcoming_data = []
        for s in upcoming_sessions:
            reg_count = FormationRegistration.objects.filter(
                session=s,
                statut__in=[FormationRegistration.Statut.CONFIRMED, FormationRegistration.Statut.PENDING]
            ).count()

            upcoming_data.append({
                "session": s,
                "registrations_count": reg_count,
                "formation_title": s.formation.titre,
                "day": s.date_debut.day,
                "month": s.date_debut.strftime("%b"),
                "time": f"{s.heure_debut.strftime('%H:%M')} – {s.heure_fin.strftime('%H:%M')}",
                "room": s.salle_reference or "Salle non définie",
            })

        months_labels = []
        months_revenue_data = []
        months_sessions_data = []
        for i in range(5, -1, -1):
            if now.month - i <= 0:
                m = now.month - i + 12
                y = now.year - 1
            else:
                m = now.month - i
                y = now.year
            month_start = datetime(y, m, 1, tzinfo=dt_module.timezone.utc)
            if m == 12:
                month_end = datetime(y + 1, 1, 1, tzinfo=dt_module.timezone.utc)
            else:
                month_end = datetime(y, m + 1, 1, tzinfo=dt_module.timezone.utc)

            month_rev = payments.filter(
                inscription__date__gte=month_start,
                inscription__date__lt=month_end,
            ).aggregate(total=Sum("montant"))["total"] or Decimal("0.00")

            month_sess = sessions_all.filter(
                date_debut__gte=month_start.date(),
                date_debut__lt=month_end.date(),
            ).count()

            months_labels.append(month_start.strftime("%b"))
            months_revenue_data.append(float(month_rev))
            months_sessions_data.append(month_sess)

        max_revenue = max(months_revenue_data) if months_revenue_data else 1
        max_sessions = max(months_sessions_data) if months_sessions_data else 1
        global_max = max(max_revenue, max_sessions)

        months_data = []
        for i in range(6):
            rev_pct = (months_revenue_data[i] / global_max * 100) if global_max > 0 else 0
            sess_pct = (months_sessions_data[i] / global_max * 100) if global_max > 0 else 0
            months_data.append({
                "label": months_labels[i],
                "revenue_pct": rev_pct,
                "sessions_pct": sess_pct,
                "is_current": i == 5,
            })

        recent_registrations = registrations.select_related(
            "membre", "session__formation"
        ).order_by("-date")[:10]

        activity_data = []
        for reg in recent_registrations:
            activity_data.append({
                "type": "registration",
                "icon_type": "blue" if reg.statut == reg.Statut.CONFIRMED else "gold",
                "text": f"<strong>{reg.membre.full_name}</strong> inscrit à {reg.session.formation.titre}",
                "time": self._format_time_ago(reg.date),
            })

        # Ajouter des activités de paiement
        recent_payments = payments.select_related(
            "inscription__membre", "inscription__session__formation"
        ).order_by("-created_at")[:5]

        for p in recent_payments:
            activity_data.append({
                "type": "payment",
                "icon_type": "green",
                "text": f"<strong>Paiement reçu</strong> — {int(p.montant):,} FCFA de {p.inscription.membre.full_name}".replace(",", " "),
                "time": self._format_time_ago(p.created_at),
            })

        # Trier par date (approximatif)
        activity_data = sorted(activity_data, key=lambda x: x["time"], reverse=True)[:8]

        # ---- Notifications ----
        notifications = DashNotification.objects.filter(
            utilisateur=user
        ).order_by("-date_creation")[:5]
        notifications_count = DashNotification.objects.filter(
            utilisateur=user, lu=False
        ).count()

        # ---- Performance des modules (formations) ----
        formations_list = Formation.objects.filter(
            id__in=formations_ids
        ) if formations_ids else Formation.objects.none()

        performance_data = []
        for f in formations_list[:4]:
            total_regs = FormationRegistration.objects.filter(
                session__formation=f,
                session__formateur=trainer,
            ).count()
            if total_regs > 0:
                completed = FormationRegistration.objects.filter(
                    session__formation=f,
                    session__formateur=trainer,
                    statut=FormationRegistration.Statut.CONFIRMED,
                ).count()
                completion_pct = round((completed / total_regs) * 100)
            else:
                completion_pct = 0

            performance_data.append({
                "title": f.titre,
                "pct": completion_pct,
                "color": self._get_color(completion_pct),
            })

# ---- Nombre de formations enseignées ----
        formations_count = len(formations_ids)

# ---- Réservations actives ----
        from reservation.models import ReservationStatus
        from reservation.models import Reservation as ReservationModel
        active_reservations_count = ReservationModel.objects.filter(
            utilisateur=user,
            statut__in=[
                ReservationStatus.PENDING,
                ReservationStatus.CONFIRMED,
                ReservationStatus.IN_PROGRESS,
            ]
        ).count()

        context = {
            "user": user,
            "trainer": trainer,
            # Stats globales
            "sessions_count": sessions_count,
            "sessions_this_month": sessions_this_month,
            "sessions_trend": sessions_trend,
            "total_students": total_students,
            "students_this_month": students_this_month,
            "students_trend": students_trend,
            "total_revenue": total_revenue,
            "revenue_this_month": revenue_this_month,
            "revenue_trend": revenue_trend,
            "avg_rating": avg_rating,
            "total_reviews": total_reviews,
            "satisfaction_rate": satisfaction_rate,
            "formations_count": formations_count,
            # Sessions récentes
            "recent_sessions": session_data,
            # Prochaines sessions
            "upcoming_sessions": upcoming_data,
            # Données du graphique
            "months_data": months_data,
            # Activité récente
            "activity_data": activity_data,
            # Notifications
            "notifications": notifications,
            "notifications_count": notifications_count,
            # Performance des modules
            "performance_data": performance_data,
            # URLs
            "active_reservations_count": active_reservations_count,
            "trainer_name": user.full_name,
            "trainer_initials": self._get_initials(user),
            # Liste des inscrits récents pour le tableau
            "recent_registrations": recent_registrations,
        }

        return render(request, self.template_name, context)

    def _format_time_ago(self, dt: datetime) -> str:
        if not dt:
            return ""
        now = timezone.now()
        diff = now - dt
        if diff.days > 7:
            return dt.strftime("%d %b, %H:%M")
        elif diff.days > 0:
            return f"Il y a {diff.days} jour{'s' if diff.days > 1 else ''}"
        elif diff.seconds >= 3600:
            hours = diff.seconds // 3600
            return f"Il y a {hours} heure{'s' if hours > 1 else ''}"
        elif diff.seconds >= 60:
            minutes = diff.seconds // 60
            return f"Il y a {minutes} minute{'s' if minutes > 1 else ''}"
        else:
            return "À l'instant"

    def _get_initials(self, user: User) -> str:
        first = (user.first_name or "")[:1].upper()
        last = (user.last_name or "")[:1].upper()
        return f"{first}{last}" if first and last else "AK"

    def _get_color(self, pct: int) -> str:
        if pct >= 90:
            return "var(--gold)"
        elif pct >= 75:
            return "var(--navy)"
        elif pct >= 60:
            return "var(--success)"
        else:
            return "var(--info)"


# ───────────────────────────────────────────────
#  BASE VIEW (check trainer)
# ───────────────────────────────────────────────
class TrainerBaseView(LoginRequiredMixin, View):
    """Base view for all trainer pages."""

    def dispatch(self, request: HttpRequest, *args, **kwargs):
        if not is_trainer(request.user):
            return HttpResponseForbidden("Accès réservé aux formateurs.")
        return super().dispatch(request, *args, **kwargs)

    def _get_trainer(self, user):
        try:
            return Trainer.objects.select_related("user").get(user=user)
        except Trainer.DoesNotExist:
            return None

    def _get_initials(self, user: User) -> str:
        first = (user.first_name or "")[:1].upper()
        last = (user.last_name or "")[:1].upper()
        return f"{first}{last}" if first and last else "AK"

    def _get_base_context(self, request):
        user = request.user
        trainer = self._get_trainer(user)
        sessions_count = FormationSession.objects.filter(formateur=trainer).count() if trainer else 0
        total_students = FormationRegistration.objects.filter(session__formateur=trainer).count() if trainer else 0
        formations_ids = list(FormationSession.objects.filter(formateur=trainer).values_list("formation_id", flat=True).distinct()) if trainer else []
        return {
            "user": user,
            "trainer": trainer,
            "sessions_count": sessions_count,
            "total_students": total_students,
            "formations_count": len(formations_ids),
            "trainer_initials": self._get_initials(user),
        }


# ───────────────────────────────────────────────
#  MES SESSIONS
# ───────────────────────────────────────────────
class TrainerSessionsView(TrainerBaseView):
    template_name = "dashboard/trainer/sessions.html"

    def get(self, request: HttpRequest, *args, **kwargs):
        context = self._get_base_context(request)
        trainer = context["trainer"]

        # All sessions for this trainer
        all_sessions = FormationSession.objects.filter(formateur=trainer).select_related("formation").order_by("-date_debut", "-heure_debut") if trainer else FormationSession.objects.none()

        # Filter by status if provided
        statut_filter = request.GET.get("statut", "")
        if statut_filter:
            all_sessions = all_sessions.filter(statut=statut_filter)

        # Count registrations per session
        sessions_list = []
        for s in all_sessions:
            regs = FormationRegistration.objects.filter(session=s)
            regs_confirmed = regs.filter(statut=FormationRegistration.Statut.CONFIRMED).count()
            regs_pending = regs.filter(statut=FormationRegistration.Statut.PENDING).count()
            regs_total = regs.count()
            sessions_list.append({
                "session": s,
                "formation_title": s.formation.titre,
                "regs_confirmed": regs_confirmed,
                "regs_pending": regs_pending,
                "regs_total": regs_total,
                "capacity": s.nombre_maximum,
            })

        context["sessions"] = sessions_list
        context["statut_filter"] = statut_filter
        context["page_title"] = "Mes sessions"
        return render(request, self.template_name, context)


# ───────────────────────────────────────────────
#  CRÉER UNE SESSION (formateur)
# ───────────────────────────────────────────────
class TrainerSessionCreateView(TrainerBaseView):
    """Permet au formateur de créer une session depuis son dashboard."""

    template_name = "dashboard/trainer/session_create.html"

    def get(self, request: HttpRequest, *args, **kwargs):
        context = self._get_base_context(request)
        trainer = context["trainer"]
        if not trainer:
            messages.error(request, "Profil formateur introuvable.")
            return redirect("dashboard_trainer:sessions")

        # Filtrer les formations auxquelles le formateur est associé
        formations_ids = list(
            FormationSession.objects.filter(formateur=trainer)
            .values_list("formation_id", flat=True)
            .distinct()
        )
        # Ajouter toutes les formations actives pour que le formateur puisse choisir
        queryset = Formation.objects.filter(actif=True)

        form = FormationSessionForm(initial={"formateur": trainer})
        form.fields["formation"].queryset = queryset
        # Rendre le champ formateur en lecture seule
        form.fields["formateur"].widget.attrs["disabled"] = True
        form.fields["formateur"].widget.attrs["class"] = form.fields["formateur"].widget.attrs.get("class", "") + " disabled-input"

        context["form"] = form
        context["trainer"] = trainer
        context["page_title"] = "Nouvelle session"
        return render(request, self.template_name, context)

    def post(self, request: HttpRequest, *args, **kwargs):
        context = self._get_base_context(request)
        trainer = context["trainer"]
        if not trainer:
            messages.error(request, "Profil formateur introuvable.")
            return redirect("dashboard_trainer:sessions")

        form = FormationSessionForm(request.POST)
        form.fields["formation"].queryset = Formation.objects.filter(actif=True)

        if not form.is_valid():
            context["form"] = form
            context["page_title"] = "Nouvelle session"
            return render(request, self.template_name, context)

        session = form.save(commit=False)
        session.formateur = trainer
        session.places_restantes = session.nombre_maximum
        session.statut = FormationSession.Statut.DRAFT
        session.save()

        messages.success(request, "Session créée avec succès.")
        return redirect("dashboard_trainer:sessions")


# ───────────────────────────────────────────────
#  MODIFIER UNE SESSION (formateur)
# ───────────────────────────────────────────────
class TrainerSessionEditView(TrainerBaseView):
    """Permet au formateur de modifier une session existante."""

    template_name = "dashboard/trainer/session_edit.html"

    def get(self, request: HttpRequest, session_id: int, *args, **kwargs):
        context = self._get_base_context(request)
        trainer = context["trainer"]
        if not trainer:
            messages.error(request, "Profil formateur introuvable.")
            return redirect("dashboard_trainer:sessions")

        session = get_object_or_404(
            FormationSession.objects.select_related("formation", "formateur"),
            id=session_id,
            formateur=trainer,
        )

        form = FormationSessionForm(instance=session)
        form.fields["formation"].queryset = Formation.objects.filter(actif=True)

        context["form"] = form
        context["session"] = session
        context["page_title"] = "Modifier la session"
        return render(request, self.template_name, context)

    def post(self, request: HttpRequest, session_id: int, *args, **kwargs):
        context = self._get_base_context(request)
        trainer = context["trainer"]
        if not trainer:
            messages.error(request, "Profil formateur introuvable.")
            return redirect("dashboard_trainer:sessions")

        session = get_object_or_404(
            FormationSession,
            id=session_id,
            formateur=trainer,
        )

        form = FormationSessionForm(request.POST, instance=session)
        form.fields["formation"].queryset = Formation.objects.filter(actif=True)

        if not form.is_valid():
            context["form"] = form
            context["session"] = session
            context["page_title"] = "Modifier la session"
            return render(request, self.template_name, context)

        form.save()

        # Recalculer les places restantes si le nombre max a changé
        if session.places_restantes > session.nombre_maximum:
            session.places_restantes = session.nombre_maximum
            session.save(update_fields=["places_restantes"])

        messages.success(request, "Session modifiée avec succès.")
        return redirect("dashboard_trainer:sessions")


# ───────────────────────────────────────────────
#  MES APPRENANTS
# ───────────────────────────────────────────────
class TrainerStudentsView(TrainerBaseView):
    """Liste des apprenants inscrits aux formations du formateur."""

    template_name = "dashboard/trainer/students.html"

    def get(self, request: HttpRequest, *args, **kwargs):
        context = self._get_base_context(request)
        trainer = context["trainer"]

        registrations = FormationRegistration.objects.filter(
            session__formateur=trainer
        ).select_related(
            "membre", "session__formation", "entreprise"
        ).order_by("-date") if trainer else FormationRegistration.objects.none()

        search = request.GET.get("q", "").strip()
        if search:
            registrations = registrations.filter(
                Q(membre__first_name__icontains=search) |
                Q(membre__last_name__icontains=search) |
                Q(membre__email__icontains=search)
            )

        context["registrations"] = registrations
        context["search"] = search
        context["page_title"] = "Mes apprenants"
        return render(request, self.template_name, context)


# ───────────────────────────────────────────────
#  MES REVENUS
# ───────────────────────────────────────────────
class TrainerRevenueView(TrainerBaseView):
    template_name = "dashboard/trainer/revenue.html"

    def get(self, request: HttpRequest, *args, **kwargs):
        context = self._get_base_context(request)
        trainer = context["trainer"]
        import datetime as dt_module

        payments = FormationPayment.objects.filter(
            inscription__session__formateur=trainer,
            statut=FormationPayment.Statut.PAID,
        ).select_related("inscription__session__formation", "inscription__membre").order_by("-created_at") if trainer else FormationPayment.objects.none()

        total_revenue = payments.aggregate(total=Sum("montant"))["total"] or Decimal("0.00")

        # Monthly breakdown (last 12 months)
        now = timezone.now()
        monthly_data = []
        for i in range(11, -1, -1):
            if now.month - i <= 0:
                m = now.month - i + 12
                y = now.year - 1
            else:
                m = now.month - i
                y = now.year
            month_start = datetime(y, m, 1, tzinfo=dt_module.timezone.utc)
            if m == 12:
                month_end = datetime(y + 1, 1, 1, tzinfo=dt_module.timezone.utc)
            else:
                month_end = datetime(y, m + 1, 1, tzinfo=dt_module.timezone.utc)

            month_rev = payments.filter(
                created_at__gte=month_start,
                created_at__lt=month_end,
            ).aggregate(total=Sum("montant"))["total"] or Decimal("0.00")

            monthly_data.append({
                "label": month_start.strftime("%b %Y"),
                "amount": float(month_rev),
            })

        context["payments"] = payments[:50]
        context["total_revenue"] = total_revenue
        context["monthly_data"] = monthly_data
        context["payments_count"] = payments.count()
        context["page_title"] = "Mes revenus"
        return render(request, self.template_name, context)


# ───────────────────────────────────────────────
#  MES FORMATIONS
# ───────────────────────────────────────────────
class TrainerFormationsView(TrainerBaseView):
    template_name = "dashboard/trainer/formations.html"

    def get(self, request: HttpRequest, *args, **kwargs):
        context = self._get_base_context(request)
        trainer = context["trainer"]

        formations_ids = list(FormationSession.objects.filter(
            formateur=trainer
        ).values_list("formation_id", flat=True).distinct()) if trainer else []

        formations = Formation.objects.filter(id__in=formations_ids).select_related("category").order_by("-created_at") if formations_ids else Formation.objects.none()

        # Count sessions per formation
        formations_list = []
        for f in formations:
            sessions_count = FormationSession.objects.filter(formation=f, formateur=trainer).count()
            total_regs = FormationRegistration.objects.filter(session__formation=f, session__formateur=trainer).count()
            formations_list.append({
                "formation": f,
                "sessions_count": sessions_count,
                "total_regs": total_regs,
            })

        context["formations"] = formations_list
        context["page_title"] = "Mes formations"
        return render(request, self.template_name, context)


# ───────────────────────────────────────────────
#  DOCUMENTS PÉDAGOGIQUES
# ───────────────────────────────────────────────
class TrainerDocumentsView(TrainerBaseView):
    template_name = "dashboard/trainer/documents.html"

    def get(self, request: HttpRequest, *args, **kwargs):
        context = self._get_base_context(request)
        trainer = context["trainer"]

        formations_ids = list(FormationSession.objects.filter(
            formateur=trainer
        ).values_list("formation_id", flat=True).distinct()) if trainer else []

        documents = FormationPedagogicalDocument.objects.filter(
            formation_id__in=formations_ids
        ).select_related("formation").order_by("-created_at") if formations_ids else FormationPedagogicalDocument.objects.none()

        context["documents"] = documents
        context["formations"] = Formation.objects.filter(id__in=formations_ids) if formations_ids else Formation.objects.none()
        context["page_title"] = "Documents"
        return render(request, self.template_name, context)


# ───────────────────────────────────────────────
#  ÉVALUATIONS
# ───────────────────────────────────────────────
class TrainerReviewsView(TrainerBaseView):
    template_name = "dashboard/trainer/reviews.html"

    def get(self, request: HttpRequest, *args, **kwargs):
        context = self._get_base_context(request)
        trainer = context["trainer"]

        formations_ids = list(FormationSession.objects.filter(
            formateur=trainer
        ).values_list("formation_id", flat=True).distinct()) if trainer else []

        reviews = FormationReview.objects.filter(
            membre__formation_registrations__session__formation_id__in=formations_ids
        ).select_related("membre").order_by("-created_at") if formations_ids else FormationReview.objects.none()

        avg_rating = reviews.aggregate(avg=Avg("note"))["avg"] or 0.0
        avg_rating = round(avg_rating, 1)
        total_reviews = reviews.count()

        # Distribution
        dist = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
        for r in reviews:
            dist[r.note] = dist.get(r.note, 0) + 1

        context["reviews"] = reviews[:50]
        context["avg_rating"] = avg_rating
        context["total_reviews"] = total_reviews
        context["distribution"] = dist
        context["page_title"] = "Évaluations"
        return render(request, self.template_name, context)


# ───────────────────────────────────────────────
#  PARAMÈTRES
# ───────────────────────────────────────────────
class TrainerSettingsView(TrainerBaseView):
    template_name = "dashboard/trainer/settings.html"

    def get(self, request: HttpRequest, *args, **kwargs):
        context = self._get_base_context(request)
        trainer = context["trainer"]
        profile, _ = Profile.objects.get_or_create(user=request.user)
        context["profile"] = profile
        context["page_title"] = "Paramètres"
        return render(request, self.template_name, context)

    def post(self, request: HttpRequest, *args, **kwargs):
        context = self._get_base_context(request)
        trainer = context["trainer"]

        # Update trainer profile
        if trainer:
            trainer.specialite = request.POST.get("specialite", trainer.specialite)
            trainer.biographie = request.POST.get("biographie", trainer.biographie)
            trainer.competences = request.POST.get("competences", trainer.competences)
            trainer.annees_experience = int(request.POST.get("annees_experience", 0) or 0)
            trainer.linkedin = request.POST.get("linkedin", "") or ""
            if request.FILES.get("photo"):
                trainer.photo = request.FILES["photo"]
            if request.FILES.get("cv"):
                trainer.cv = request.FILES["cv"]
            trainer.save()

        # Update user
        user = request.user
        user.first_name = request.POST.get("first_name", user.first_name)
        user.last_name = request.POST.get("last_name", user.last_name)
        user.phone = request.POST.get("phone", user.phone)
        user.save()

        messages.success(request, "Paramètres mis à jour avec succès.")
        return redirect("dashboard_trainer:settings")


# ───────────────────────────────────────────────
#  DÉTAILS D'UN APPRENANT
# ───────────────────────────────────────────────
class TrainerStudentDetailView(TrainerBaseView):
    """Affiche les détails complets d'un apprenant inscrit à une formation du formateur."""

    template_name = "dashboard/trainer/student_detail.html"

    def get(self, request: HttpRequest, inscription_id: int, *args, **kwargs):
        context = self._get_base_context(request)
        trainer = context["trainer"]

        registration = get_object_or_404(
            FormationRegistration.objects.select_related(
                "membre",
                "entreprise",
                "session__formation",
                "session__formateur__user",
            ),
            id=inscription_id,
            session__formateur=trainer,
        )

        # Récupérer les autres inscriptions du même membre
        other_registrations = FormationRegistration.objects.filter(
            membre=registration.membre,
            session__formateur=trainer,
        ).exclude(id=registration.id).select_related(
            "session__formation"
        ).order_by("-date")[:5]

        # Récupérer le paiement, devis, contrat, certificat
        try:
            payment = registration.payment
        except FormationPayment.DoesNotExist:
            payment = None

        try:
            quote = registration.quote
        except FormationQuote.DoesNotExist:
            quote = None

        try:
            contract = getattr(quote, "contract", None) if quote else None
        except FormationContract.DoesNotExist:
            contract = None

        try:
            certificate = registration.certificate
        except FormationCertificate.DoesNotExist:
            certificate = None

        try:
            access_code = registration.access_code
        except Exception:
            access_code = None

        # Statistiques du membre chez ce formateur
        total_regs = FormationRegistration.objects.filter(
            membre=registration.membre,
            session__formateur=trainer,
        ).count()
        confirmed_regs = FormationRegistration.objects.filter(
            membre=registration.membre,
            session__formateur=trainer,
            statut=FormationRegistration.Statut.CONFIRMED,
        ).count()

        context["registration"] = registration
        context["member"] = registration.membre
        context["entreprise"] = registration.entreprise
        context["other_registrations"] = other_registrations
        context["payment"] = payment
        context["quote"] = quote
        context["contract"] = contract
        context["certificate"] = certificate
        context["access_code"] = access_code
        context["total_regs"] = total_regs
        context["confirmed_regs"] = confirmed_regs
        context["page_title"] = f"Détails - {registration.membre.full_name}"
        return render(request, self.template_name, context)


# ───────────────────────────────────────────────
#  VALIDER UNE INSCRIPTION
# ───────────────────────────────────────────────
class TrainerStudentValidateView(TrainerBaseView):
    """Valide une inscription en attente et notifie le membre."""

    def post(self, request: HttpRequest, inscription_id: int, *args, **kwargs):
        trainer = self._get_trainer(request.user)
        if not trainer:
            messages.error(request, "Profil formateur introuvable.")
            return redirect("dashboard_trainer:students")

        registration = get_object_or_404(
            FormationRegistration,
            id=inscription_id,
            session__formateur=trainer,
        )

        if registration.statut != FormationRegistration.Statut.PENDING:
            messages.error(request, "Seules les inscriptions en attente peuvent être validées.")
            return redirect("dashboard_trainer:students")

        registration.statut = FormationRegistration.Statut.CONFIRMED
        registration.save(update_fields=["statut"])

        # Notifier le membre par email
        try:
            notify_member_registration_confirmed(registration)
        except Exception as e:
            # Ne pas bloquer si l'email échoue
            pass

        messages.success(
            request,
            f"Inscription {registration.numero} de {registration.membre.full_name} validée avec succès. "
            f"Le membre a été notifié par email.",
        )
        return redirect("dashboard_trainer:students")


# ───────────────────────────────────────────────
#  REFUSER UNE INSCRIPTION
# ───────────────────────────────────────────────
class TrainerStudentRefuseView(TrainerBaseView):
    """Refuse une inscription en attente."""

    def post(self, request: HttpRequest, inscription_id: int, *args, **kwargs):
        trainer = self._get_trainer(request.user)
        if not trainer:
            messages.error(request, "Profil formateur introuvable.")
            return redirect("dashboard_trainer:students")

        registration = get_object_or_404(
            FormationRegistration,
            id=inscription_id,
            session__formateur=trainer,
        )

        if registration.statut != FormationRegistration.Statut.PENDING:
            messages.error(request, "Seules les inscriptions en attente peuvent être refusées.")
            return redirect("dashboard_trainer:students")

        registration.statut = FormationRegistration.Statut.REFUSED
        registration.save(update_fields=["statut"])

        messages.success(
            request,
            f"Inscription {registration.numero} de {registration.membre.full_name} refusée.",
        )
        return redirect("dashboard_trainer:students")


from formation.forms import FormationPedagogicalDocumentForm
from formation.models import FormationPedagogicalDocument, Formation

from django.contrib import messages
from django.shortcuts import redirect, render


def add_document(request):

    trainer = request.user.trainer_profile


    formations = Formation.objects.filter(
        sessions__formateur=trainer
    ).distinct()


    if request.method == "POST":

        form = FormationPedagogicalDocumentForm(
            request.POST,
            request.FILES
        )


        if form.is_valid():

            document = form.save(commit=False)


            # sécurité :
            if document.formation not in formations:
                messages.error(
                    request,
                    "Vous ne pouvez pas ajouter un document à cette formation."
                )
                return redirect("trainer_documents")


            document.save()


            messages.success(
                request,
                "Document ajouté avec succès."
            )

            return redirect(
                "dashboard_trainer:documents"
            )


    else:

        form = FormationPedagogicalDocumentForm()


    # limiter les choix dans le select
    form.fields["formation"].queryset = formations


    return render(
        request,
        "dashboard/trainer/add_document.html",
        {
            "form": form
        }
    )

from django.views.generic import DetailView
from formation.models import Formation


class TrainerFormationDetailView(DetailView):

    model = Formation
    template_name = "dashboard/trainer/formation_detail.html"
    context_object_name = "formation"

    def get_queryset(self):
        trainer = self.request.user.trainer_profile

        return Formation.objects.filter(
            sessions__formateur=trainer
        ).distinct()


    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        formation = self.object

        context["sessions"] = formation.sessions.all()

        context["documents"] = formation.pedagogical_documents.all()

        context["inscrits"] = FormationRegistration.objects.filter(
            session__formation=formation
        ).count()

        return context 


from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from formation.models import FormationSession


def TrainerSessionDeleteView(request, session_id):

    trainer = request.user.trainer_profile

    session = get_object_or_404(
        FormationSession,
        id=session_id,
        formateur=trainer
    )

    if request.method == "POST":

        session.delete()

        messages.success(
            request,
            "La session a été supprimée avec succès."
        )

        return redirect("dashboard_trainer:sessions")

    return redirect("dashboard_trainer:sessions")

from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from formation.models import FormationPedagogicalDocument


def delete_document(request, document_id):

    trainer = request.user.trainer_profile

    document = get_object_or_404(
        FormationPedagogicalDocument,
        id=document_id,
        formation__sessions__formateur=trainer
    )

    if request.method == "POST":

        # Supprimer aussi le fichier physique
        if document.fichier:
            document.fichier.delete()

        document.delete()

        messages.success(
            request,
            "Le document pédagogique a été supprimé avec succès."
        )

    return redirect("dashboard_trainer:documents")


# ═══════════════════════════════════════════════════════════════
#  DEMANDES DE DEVIS FORMATION (formateur)
# ═══════════════════════════════════════════════════════════════

class TrainerDevisFormationView(TrainerBaseView):
    """Liste des demandes de devis formation (lecture seule pour les formateurs)."""
    template_name = "dashboard/trainer/devis_formation_list.html"

    def get(self, request: HttpRequest, *args, **kwargs):
        context = self._get_base_context(request)
        from core.models import DevisFormation

        devis_qs = DevisFormation.objects.all().order_by("-created_at")

        # Filtre par statut
        statut_filter = request.GET.get("statut", "")
        if statut_filter == "non_lu":
            devis_qs = devis_qs.filter(lu=False)
        elif statut_filter == "lu":
            devis_qs = devis_qs.filter(lu=True)

        context["devis_list"] = devis_qs
        context["total_count"] = DevisFormation.objects.count()
        context["unread_count"] = DevisFormation.objects.filter(lu=False).count()
        context["current_filter"] = statut_filter
        context["page_title"] = "Demandes de devis"
        return render(request, self.template_name, context)


# ═══════════════════════════════════════════════════════════════
#  RÉSERVATIONS DU FORMATEUR
# ═══════════════════════════════════════════════════════════════

from reservation.models import Reservation as ReservationModel, ReservationLog, ReservationStatus
from reservation.permissions import can_view_reservation, can_cancel_reservation
from reservation.forms import ReservationForm
from reservation.services import (
    check_availability_conflict,
    create_invoice_for_reservation,
    calculate_amount_for_workspace,
)
from coworking.models import Workspace


class TrainerReservationCreateView(TrainerBaseView):
    """Permet au formateur de créer une réservation depuis son dashboard."""
    
    template_name = "dashboard/trainer/reservation_create.html"
    
    def get(self, request: HttpRequest, *args, **kwargs):
        context = self._get_base_context(request)
        form = ReservationForm(request=request)
        workspaces = Workspace.objects.filter(disponible=True).select_related("espace", "categorie")
        context["form"] = form
        context["workspaces"] = workspaces
        context["page_title"] = "Nouvelle réservation"
        return render(request, self.template_name, context)
    
    def post(self, request: HttpRequest, *args, **kwargs):
        context = self._get_base_context(request)
        form = ReservationForm(request.POST, request=request)
        
        if not form.is_valid():
            context["form"] = form
            context["workspaces"] = Workspace.objects.filter(disponible=True).select_related("espace", "categorie")
            context["page_title"] = "Nouvelle réservation"
            return render(request, self.template_name, context, status=400)
        
        data = form.cleaned_data
        entreprise = data.get("entreprise")
        espace = data["espace"]
        nombre_participants = data.get("nombre_participants", 1)
        
        montant_bd = calculate_amount_for_workspace(
            espace=espace,
            type_reservation=data["type_reservation"],
            date_debut=data["date_debut"],
            date_fin=data["date_fin"],
            heure_debut=data.get("heure_debut"),
            heure_fin=data.get("heure_fin"),
            nombre_personnes=nombre_participants,
        )
        
        try:
            # Vérifier les conflits de disponibilité
            from reservation.models import Reservation as ResModel
            provisional = ResModel(
                espace=espace,
                date_debut=data["date_debut"],
                date_fin=data["date_fin"],
                statut=ReservationStatus.PENDING,
            )
            if data.get("heure_debut"):
                provisional.heure_debut = data["heure_debut"]
            if data.get("heure_fin"):
                provisional.heure_fin = data["heure_fin"]
            check_availability_conflict(reservation=provisional)
        except Exception as exc:
            messages.error(request, f"⚠️ {exc}")
            context["form"] = form
            context["workspaces"] = Workspace.objects.filter(disponible=True).select_related("espace", "categorie")
            context["page_title"] = "Nouvelle réservation"
            return render(request, self.template_name, context, status=409)
        
        try:
            # Créer la réservation
            reservation = form.save(commit=False)
            reservation.utilisateur = request.user
            reservation.entreprise = entreprise
            reservation.prix_unitaire = montant_bd.montant
            reservation.remise = montant_bd.remise
            reservation.taxes = montant_bd.taxe
            reservation.montant_total = montant_bd.total
            reservation.nombre_participants = nombre_participants
            reservation.statut = ReservationStatus.PENDING
            reservation.save()
            
            # Log
            ReservationLog.objects.create(
                reservation=reservation,
                action=ReservationLog.ActionType.CREATED,
                acteur=request.user,
                detail=f"Création réservation {reservation.reservation_number}",
            )
            
            # Facture
            create_invoice_for_reservation(reservation)
            
            messages.success(request, f"Réservation {reservation.reservation_number} créée avec succès.")
            return redirect("dashboard_trainer:trainer_reservations")
            
        except Exception as exc:
            messages.error(request, f"Erreur lors de la création : {exc}")
            context["form"] = form
            context["workspaces"] = Workspace.objects.filter(disponible=True).select_related("espace", "categorie")
            context["page_title"] = "Nouvelle réservation"
            return render(request, self.template_name, context, status=500)


class TrainerReservationsView(TrainerBaseView):
    """Liste des réservations personnelles du formateur."""

    template_name = "dashboard/trainer/reservations.html"

    def get(self, request: HttpRequest, *args, **kwargs):
        context = self._get_base_context(request)

        # Filtrer les réservations appartenant au formateur connecté
        reservations = ReservationModel.objects.filter(
            utilisateur=request.user
        ).select_related(
            "espace", "entreprise"
        ).order_by("-created_at")

        # Filtres optionnels
        statut = request.GET.get("statut", "")
        if statut:
            reservations = reservations.filter(statut=statut)

        search = request.GET.get("q", "").strip()
        if search:
            reservations = reservations.filter(
                Q(reservation_number__icontains=search) |
                Q(espace__nom__icontains=search)
            )

        # Compter les réservations actives
        active_count = reservations.filter(
            statut__in=[
                ReservationStatus.PENDING,
                ReservationStatus.CONFIRMED,
                ReservationStatus.IN_PROGRESS,
            ]
        ).count()

        context["reservations"] = reservations
        context["active_count"] = active_count
        context["statut_filter"] = statut
        context["search"] = search
        context["page_title"] = "Mes réservations"
        return render(request, self.template_name, context)


class TrainerReservationDetailView(TrainerBaseView):
    """Détail d'une réservation du formateur."""

    template_name = "dashboard/trainer/reservation_detail.html"

    def get(self, request: HttpRequest, reservation_id, *args, **kwargs):
        context = self._get_base_context(request)

        reservation = get_object_or_404(
            ReservationModel.objects.select_related(
                "espace", "utilisateur", "entreprise"
            ).prefetch_related("participants", "logs"),
            id=reservation_id,
            utilisateur=request.user,
        )

        context["reservation"] = reservation
        context["page_title"] = f"Réservation {reservation.reservation_number}"
        return render(request, self.template_name, context)


class TrainerReservationCancelView(TrainerBaseView):
    """Annuler une réservation depuis le dashboard formateur."""

    def post(self, request: HttpRequest, reservation_id, *args, **kwargs):
        reservation = get_object_or_404(
            ReservationModel,
            id=reservation_id,
            utilisateur=request.user,
        )

        if not can_cancel_reservation(request.user, reservation):
            messages.error(request, "Vous ne pouvez pas annuler cette réservation.")
            return redirect("dashboard_trainer:trainer_reservations")

        reservation.statut = ReservationStatus.CANCELED
        reservation.save(update_fields=["statut"])

        ReservationLog.objects.create(
            reservation=reservation,
            action=ReservationLog.ActionType.CANCELED,
            acteur=request.user,
            detail="Annulation depuis le dashboard formateur",
        )

        messages.success(request, f"Réservation {reservation.reservation_number} annulée.")
        return redirect("dashboard_trainer:trainer_reservations")

