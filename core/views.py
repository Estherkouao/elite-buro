from __future__ import annotations

from datetime import date, time, timedelta
from decimal import Decimal
from typing import Any

from django.contrib import messages
from django.db.models import Count, Q, Case, When, Value, BooleanField
from django.shortcuts import redirect, render

from coworking.models import CoworkingSpace, Workspace, WorkspaceEquipment, Category
from dashboard.models import Testimonial
from domiciliation.models import DomiciliationPlan
from reservation.models import Reservation, ReservationStatus


# ──────────────────────────────────────────────
#  Constantes pour les catégories
# ──────────────────────────────────────────────
CAT_PRIVATE_OFFICE = "Bureau Privé"
CAT_HOT_DESK = "Hot Desk"
CAT_MEETING_ROOM = "Salle de Réunion"
CAT_TRAINING_ROOM = "Salle de Formation"


def _get_or_create_fallback_space() -> CoworkingSpace:
    """Retourne ou crée CoworkingSpace par défaut."""
    space, _ = CoworkingSpace.objects.get_or_create(
        nom="Elite Buro - Riviera Palmeraie",
        defaults={
            "slug": "elite-buro-riviera-palmeraie",
            "description": "SAS Elite Buro Coworking – Riviera Palmeraie, Cocody, Abidjan",
            "adresse": "Riviera Palmeraie, Cocody",
            "ville": "Abidjan",
            "pays": "Côte d'Ivoire",
            "telephone": "+225 07 XX XX XX XX",
            "email": "contact@eliteburo.com",
            "statut": CoworkingSpace.STATUS_ACTIVE,
        },
    )
    return space


def _get_or_create_categories():
    """Crée les catégories si besoin."""
    cats = {}
    for nom in [
        CAT_PRIVATE_OFFICE,
        CAT_HOT_DESK,
        CAT_MEETING_ROOM,
        CAT_TRAINING_ROOM,
    ]:
        cat, _ = Category.objects.get_or_create(
            nom=nom,
            defaults={
                "slug": nom.lower().replace(" ", "-"),
                "description": f"Catégorie {nom}",
            },
        )
        cats[nom] = cat
    return cats


def get_workspace_statuses(workspace_ids: list[int]) -> tuple[set[int], set[int]]:
    """
    Retourne les IDs des espaces avec une réservation active aujourd'hui
    et ceux avec une réservation commençant demain.
    """
    today = date.today()
    tomorrow = today + timedelta(days=1)

    active_statuses = [
        ReservationStatus.CONFIRMED,
        ReservationStatus.IN_PROGRESS,
        ReservationStatus.PENDING,
    ]

    reservations = Reservation.objects.filter(
        espace_id__in=workspace_ids,
        date_fin__gte=today,
        statut__in=active_statuses
    ).values("espace_id", "date_debut")

    active_ids = {r["espace_id"] for r in reservations if r["date_debut"] <= today}
    upcoming_ids = {r["espace_id"] for r in reservations if r["date_debut"] == tomorrow}

    return active_ids, upcoming_ids


def _get_active_reservation_dates(espace_ids: list) -> set:
    """Retourne les IDs des espaces avec une réservation active aujourd'hui."""
    today = date.today()
    active_ids = set(
        Reservation.objects.filter(
            espace_id__in=espace_ids,
            date_debut__lte=today,
            date_fin__gte=today,
            statut__in=[
                ReservationStatus.CONFIRMED,
                ReservationStatus.IN_PROGRESS,
                ReservationStatus.PENDING,
            ],
        ).values_list("espace_id", flat=True)
    )
    return active_ids


def _get_upcoming_reservation_dates(espace_ids: list) -> set:
    """Retourne les IDs des espaces qui seront libres bientôt (réservés à partir de demain)."""
    today = date.today()
    tomorrow = today + timedelta(days=1)
    upcoming_ids = set(
        Reservation.objects.filter(
            espace_id__in=espace_ids,
            date_debut=tomorrow,
            statut__in=[
                ReservationStatus.CONFIRMED,
                ReservationStatus.IN_PROGRESS,
                ReservationStatus.PENDING,
            ],
        ).values_list("espace_id", flat=True)
    )
    return upcoming_ids


def build_workspace_status(workspace, active_ids, upcoming_ids) -> str:
    """Détermine le statut d'un workspace."""
    if workspace.id in active_ids:
        return "occupied"
    if not workspace.disponible:
        return "maintenance"
    if workspace.id in upcoming_ids:
        return "soon_free"
    return "available"


def format_price(price: Decimal) -> str:
    """Formate un prix en FCFA."""
    if price is None:
        return "—"
    return f"{int(price):,} F / jour".replace(",", " ")


def home(request):
    """Page d'accueil avec données dynamiques pour le pôle Coworking."""

    space = _get_or_create_fallback_space()
    cats = _get_or_create_categories()

    # ── Fallback si pas de données en DB ────────
    if not Workspace.objects.filter(espace=space).exists():
        return render(request, "core/home.html", {"STATIC_FALLBACK": True})

    # ── Workspaces ──────────────────────────────
    workspaces_ids = list(Workspace.objects.filter(espace=space).values_list("id", flat=True))
    active_ids, upcoming_ids = get_workspace_statuses(workspaces_ids)

    all_workspaces = Workspace.objects.select_related("categorie").filter(espace=space).annotate(
        is_occupied=Case(When(id__in=active_ids, then=Value(True)), default=Value(False), output_field=BooleanField()),
        is_maintenance=Case(When(disponible=False, then=Value(True)), default=Value(False), output_field=BooleanField()),
        is_soon_free=Case(When(id__in=upcoming_ids, then=Value(True)), default=Value(False), output_field=BooleanField()),
    ).order_by("numero", "nom")

    # ── Enrichir chaque workspace avec status et prix formaté ──
    all_workspaces_list = list(all_workspaces)
    for w in all_workspaces_list:
        w._status = build_workspace_status(w, active_ids, upcoming_ids)
        w.formatted_price = format_price(w.prix_journee)
        w.is_available = w._status == "available"
        w.is_occupied = w.id in active_ids
        w.is_maintenance = not w.disponible
        w.is_soon_free = w.id in upcoming_ids

    # ── Catégoriser ─────────────────────────────
    private_offices = [w for w in all_workspaces_list if w.categorie.nom == CAT_PRIVATE_OFFICE]
    hot_desks = [w for w in all_workspaces_list if w.categorie.nom == CAT_HOT_DESK]
    meeting_rooms_qs = [w for w in all_workspaces_list if w.categorie.nom == CAT_MEETING_ROOM]

    # ── Stats ───────────────────────────────────
    total_offices = len(private_offices)
    available_offices = sum(1 for w in private_offices if w.is_available)
    hot_desk_total = len(hot_desks)
    hot_desk_available = sum(1 for w in hot_desks if w.is_available)
    meeting_room_count = len(meeting_rooms_qs)

    # ── Bureau vedette pour la carte flottante ───
    featured_workspace = next((w for w in private_offices if w.is_available), None)
    if featured_workspace is None and private_offices:
        featured_workspace = private_offices[0]

    # ── Équipements pour salles de réunion ──────
    meeting_rooms_data = []
    for w in meeting_rooms_qs:
        equipments = list(
            WorkspaceEquipment.objects.filter(workspace=w).select_related("equipment")
        )
        meeting_rooms_data.append({
            "workspace": w,
            "equipments": [e.equipment.nom for e in equipments],
            "status": w._status,
        })

    # ── Fallback si pas de données en DB ────────
    if total_offices == 0 and hot_desk_total == 0:
        return _render_static_fallback(request)

    # ── Domiciliation Plans ─────────────────────
    plans = DomiciliationPlan.objects.filter(actif=True).order_by("ordre")
    domiciliation_plans = []
    for plan in plans:
        avantages_list = [a.strip() for a in plan.avantages.split("\n") if a.strip()]
        domiciliation_plans.append({
            "id": plan.id,
            "nom": plan.nom,
            "slug": plan.slug,
            "description": plan.description,
            "prix": int(plan.prix),
            "duree": plan.durée,
            "avantages": avantages_list,
            "ordre": plan.ordre,
        })

    # ── Témoignages approuvés ───────────────────
    approved_testimonials = Testimonial.objects.filter(approuvé=True).select_related("utilisateur").order_by("-created_at")[:6]

    context: dict[str, Any] = {
        "total_offices": total_offices,
        "available_offices": available_offices,
        "hot_desk_total": hot_desk_total,
        "hot_desk_available": hot_desk_available,
        "hot_desk_available_today": hot_desk_available,
        "meeting_room_count": meeting_room_count,
        "private_offices": private_offices,
        "hot_desks": hot_desks,
        "meeting_rooms": meeting_rooms_data,
        "active_ids": active_ids,
        "upcoming_ids": upcoming_ids,
        "domiciliation_plans": domiciliation_plans,
        "testimonials": approved_testimonials,
        "featured_workspace": featured_workspace,
    }

    return render(request, "core/home.html", context)


def _render_static_fallback(request):
    """Fallback avec les valeurs statiques originales si pas de données en DB."""
    # Toujours envoyer les formules de domiciliation disponibles
    plans = DomiciliationPlan.objects.filter(actif=True).order_by("ordre")
    domiciliation_plans = []
    for plan in plans:
        avantages_list = [a.strip() for a in plan.avantages.split("\n") if a.strip()]
        domiciliation_plans.append({
            "id": plan.id,
            "nom": plan.nom,
            "slug": plan.slug,
            "description": plan.description,
            "prix": int(plan.prix),
            "duree": plan.durée,
            "avantages": avantages_list,
            "ordre": plan.ordre,
        })
# Témoignages approuvés même en fallback
    approved_testimonials = Testimonial.objects.filter(approuvé=True).select_related("utilisateur").order_by("-created_at")[:6]
    return render(request, "core/home.html", {
        "STATIC_FALLBACK": True,
        "domiciliation_plans": domiciliation_plans,
        "testimonials": approved_testimonials,
    })





def contact(request):
    """Page de contact avec formulaire."""
    if request.method == "POST":
        nom = request.POST.get("nom", "").strip()
        email = request.POST.get("email", "").strip()
        telephone = request.POST.get("telephone", "").strip()
        sujet = request.POST.get("sujet", "").strip()
        message = request.POST.get("message", "").strip()

        if not nom or not email or not sujet or not message:
            messages.error(request, "Veuillez remplir tous les champs obligatoires.")
            return redirect("core:contact")

        # Sauvegarde en base de données
        from core.models import ContactMessage
        ContactMessage.objects.create(
            nom=nom,
            email=email,
            telephone=telephone,
            sujet=sujet,
            message=message,
        )

        messages.success(
            request,
            f"Merci {nom} ! Votre message a été envoyé avec succès. Nous vous répondrons dans les plus brefs délais."
        )
        return redirect("core:contact")

    return render(request, "core/contact.html")

from django.shortcuts import render, get_object_or_404
from django.db.models import Q

from .models import Ressource





def ressource(request):
    return render(
        request,
        "core/resource.html"
    )