from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict

from django.contrib.auth import get_user_model
from django.db.models import Count, Q, Sum
from django.utils import timezone

from accounts.models import User
from coworking.models import CoworkingSpace, Workspace, WorkspaceAvailability
from formation.models import Formation, FormationRegistration
from reservation.models import Reservation
from domiciliation.models import DomiciliationRequest


@dataclass(frozen=True)
class DashboardStats:
    users: int
    reservations: int
    income_total: Decimal
    formations: int
    domiciliation_requests: int


def _today_range():
    now = timezone.now()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timezone.timedelta(days=1)
    return start, end


def get_admin_stats() -> DashboardStats:
    """Stats agrégées pour la page back-office.

    NOTE: Le dashboard n’est pas censé stocker la data métier. On agrège directement via ORM.
    """

    user_count = User.objects.count()

    reservation_count = Reservation.objects.count()

    # Le projet ne centralise pas forcément un modèle Paiement unifié admin.
    # On évite d’inventer : on calcule uniquement ce qui est disponible.
    # IMPORTANT METIER:
    # Le CA ne doit PAS augmenter à la création / demande de réservation.
    # On ne compte que les réservations validées (CONFIRMED).
    income_total = (
        Reservation.objects.filter(statut="confirmed").aggregate(total=Sum("montant_total")).get("total")
        or Decimal("0")
    )



    formation_count = Formation.objects.count()

    domiciliation_count = DomiciliationRequest.objects.count()

    return DashboardStats(
        users=user_count,
        reservations=reservation_count,
        income_total=income_total,
        formations=formation_count,
        domiciliation_requests=domiciliation_count,
    )


def get_space_availability_summary(limit: int = 10) -> list[Dict[str, Any]]:
    """Résumé des espaces disponibles par catégorie (bureau, salle de formation, etc.).

    Le KPI “disponible” reflète les espaces par type, indépendamment des CoworkingSpaces.
    On se base sur le champ `Workspace.disponible`.
    """

    total = Workspace.objects.count()
    available = Workspace.objects.filter(disponible=True).count()

    top = (
        Workspace.objects.select_related("categorie")
        .values("categorie__nom")
        .annotate(
            count=Count("id"),
            available_count=Count("id", filter=Q(disponible=True)),
        )
        .order_by("-available_count")[:limit]
    )

    return list(top)




def get_recent_activity(limit: int = 10):
    """Activité récente agrégée (réservation, formation, domiciliation)."""

    # On renvoie des tuples (label, date, url_name) pour simplifier le rendu.
    reservations = Reservation.objects.order_by("-created_at")[:limit]
    formations = Formation.objects.order_by("-created_at")[:limit]
    domiciliations = DomiciliationRequest.objects.order_by("-date_creation")[:limit]

    items = []
    for r in reservations:
        items.append(("Réservation", r.created_at, "dashboard_admin:reservations"))
    for f in formations:
        items.append(("Formation", f.created_at, "dashboard_admin:formations"))
    for d in domiciliations:
        items.append(("Domiciliation", d.date_creation, "dashboard_admin:domiciliation"))

    items.sort(key=lambda x: x[1], reverse=True)
    return items[:limit]

