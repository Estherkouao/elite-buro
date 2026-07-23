from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .models import (
    Category,
    CoworkingSpace,
    FavoriteWorkspace,
    Workspace,
    WorkspaceAvailability,
)


def index(request):
    """Landing Coworking."""
    categories = Category.objects.all().order_by("nom")[:6]
    vedettes = (
        Workspace.objects.select_related("espace", "categorie")
        .filter(vedette=True, disponible=True)
        .order_by("created_at")
        .prefetch_related("images")[:6]
    )
    return render(
        request,
        "coworking/index.html",
        {
            "categories": categories,
            "vedettes": vedettes,
        },
    )



def workspace_list(request):
    """Liste des espaces (catalogue)."""
    qs = (
        Workspace.objects.select_related("espace", "categorie")
        .filter(disponible=True)
        .order_by("created_at")
        .prefetch_related("images")
    )

    city = request.GET.get("ville")
    if city:
        qs = qs.filter(espace__ville__icontains=city)

    category_slug = request.GET.get("categorie")
    if category_slug:
        qs = qs.filter(categorie__slug=category_slug)

    min_price = request.GET.get("prix")
    if min_price:
        try:
            qs = qs.filter(prix_heure__gte=min_price)
        except (TypeError, ValueError):
            pass

    q = request.GET.get("q")
    if q:
        qs = qs.filter(Q(nom__icontains=q) | Q(description__icontains=q))

    return render(request, "coworking/workspace_list.html", {"workspaces": qs})


def workspace_detail(request, slug: str):
    workspace = get_object_or_404(
        Workspace.objects.select_related("espace", "categorie"),
        slug=slug,
    )

    images = workspace.images.all()
    availability = WorkspaceAvailability.objects.filter(espace=workspace).order_by("date")[:30]

    return render(
        request,
        "coworking/workspace_detail.html",
        {
            "workspace": workspace,
            "images": images,
            "availability": availability,
        },
    )


def category_list(request):
    categories = Category.objects.all().order_by("nom")
    return render(request, "coworking/filters.html", {"categories": categories})


def favorites(request):
    if not request.user.is_authenticated:
        return redirect("accounts:login")

    favs = (
        FavoriteWorkspace.objects.filter(utilisateur=request.user)
        .select_related("espace")
        .order_by("id")
    )

    workspaces = Workspace.objects.filter(favorites__in=favs).select_related("espace", "categorie")

    return render(request, "coworking/favorites.html", {"favorites": workspaces})


def search(request):
    q = request.GET.get("q", "").strip()
    if not q:
        return redirect("coworking:workspace_list")

    workspaces = (
        Workspace.objects.select_related("espace", "categorie")
        .filter(disponible=True)
        .filter(Q(nom__icontains=q) | Q(description__icontains=q) | Q(categorie__nom__icontains=q))
        .order_by("created_at")
        .prefetch_related("images")
    )

    return render(request, "coworking/search.html", {"workspaces": workspaces, "q": q})

