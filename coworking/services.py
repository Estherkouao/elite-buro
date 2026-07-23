from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from django.db.models import Exists, OuterRef, Q, QuerySet
from django.utils import timezone

from .models import (
    Category,
    CoworkingSpace,
    FavoriteWorkspace,
    Workspace,
    WorkspaceAvailability,
    WorkspacePrice,
)


@dataclass(frozen=True)
class WorkspaceSearchFilters:
    city: str | None = None
    category_slug: str | None = None
    min_price: Decimal | None = None
    q: str | None = None


def get_coworking_spaces() -> QuerySet[CoworkingSpace]:
    return CoworkingSpace.objects.filter(statut=CoworkingSpace.STATUS_ACTIVE).order_by("nom")


def get_categories() -> QuerySet[Category]:
    return Category.objects.all().order_by("nom")


def get_featured_workspaces(limit: int = 6) -> QuerySet[Workspace]:
    return (
        Workspace.objects.select_related("espace", "categorie")
        .filter(vedette=True, disponible=True)
        .order_by("created_at")
        .prefetch_related("images")[:limit]
    )


def search_workspaces(filters: WorkspaceSearchFilters) -> QuerySet[Workspace]:
    qs = (
        Workspace.objects.select_related("espace", "categorie")
        .filter(disponible=True)
        .prefetch_related("images")
    )

    if filters.city:
        qs = qs.filter(espace__ville__icontains=filters.city)

    if filters.category_slug:
        qs = qs.filter(categorie__slug=filters.category_slug)

    if filters.min_price is not None:
        qs = qs.filter(prix_heure__gte=filters.min_price)

    if filters.q:
        q = filters.q.strip()
        if q:
            qs = qs.filter(Q(nom__icontains=q) | Q(description__icontains=q) | Q(categorie__nom__icontains=q))

    return qs.order_by("created_at")


def list_workspace_availabilities(workspace: Workspace, days: int = 30) -> QuerySet[WorkspaceAvailability]:
    start_date = timezone.localdate()
    end_date = start_date + timezone.timedelta(days=days)
    return (
        WorkspaceAvailability.objects.filter(espace=workspace, date__gte=start_date, date__lte=end_date)
        .order_by("date")
    )


def is_workspace_available_on(workspace: Workspace, date, start_time, end_time) -> bool:
    return WorkspaceAvailability.objects.filter(
        espace=workspace,
        date=date,
        heure_debut=start_time,
        heure_fin=end_time,
        disponible=True,
    ).exists()


def get_user_favorites(user) -> QuerySet[Workspace]:
    if not user or not user.is_authenticated:
        return Workspace.objects.none()

    favs = FavoriteWorkspace.objects.filter(utilisateur=user).values_list("espace_id", flat=True)
    return Workspace.objects.filter(id__in=favs).select_related("espace", "categorie").prefetch_related("images")


def get_workspace_price_matrix(workspace: Workspace) -> dict[str, Decimal]:
    """Retourne les tarifs applicables.

    - WorkspacePrice a priorité (si présent)
    - Sinon utilise les champs Workspace

    (La structure est volontairement simple pour réutilisation dans les vues.)
    """

    try:
        special = workspace.prices.get()
    except WorkspacePrice.DoesNotExist:
        special = None

    if special:
        return {
            "prix_heure": special.prix_heure if special.prix_heure is not None else workspace.prix_heure,
            "prix_demi_journee": special.prix_demi_journee if special.prix_demi_journee is not None else workspace.prix_demi_journee,
            "prix_journee": special.prix_journee if special.prix_journee is not None else workspace.prix_journee,
            "prix_semaine": special.prix_semaine if special.prix_semaine is not None else workspace.prix_semaine,
            "prix_mois": special.prix_mois if special.prix_mois is not None else workspace.prix_mois,
        }

    return {
        "prix_heure": workspace.prix_heure,
        "prix_demi_journee": workspace.prix_demi_journee,
        "prix_journee": workspace.prix_journee,
        "prix_semaine": workspace.prix_semaine,
        "prix_mois": workspace.prix_mois,
    }

