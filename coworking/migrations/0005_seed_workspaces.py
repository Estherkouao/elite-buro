"""
Seed data migration for Coworking module.

Creates:
- CoworkingSpace "Elite Buro - Riviera Palmeraie"
- Categories: Bureau Privé, Hot Desk, Salle de Réunion, Salle de Formation
- 11 private offices (bureaux privatifs)
- 12 hot desks
- 3 meeting rooms
- Equipment items
- Sample reservations (for occupied offices)
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from django.db import migrations


def seed_data(apps, schema_editor):
    CoworkingSpace = apps.get_model("coworking", "CoworkingSpace")
    Category = apps.get_model("coworking", "Category")
    Workspace = apps.get_model("coworking", "Workspace")
    Equipment = apps.get_model("coworking", "Equipment")
    WorkspaceEquipment = apps.get_model("coworking", "WorkspaceEquipment")

    # ── 1. CoworkingSpace ───────────────────────
    space, _ = CoworkingSpace.objects.get_or_create(
        nom="Elite Buro - Riviera Palmeraie",
        slug="elite-buro-riviera-palmeraie",
        defaults={
            "description": (
                "SAS Elite Buro Coworking est un groupe multi-pôles basé à Riviera Palmeraie, "
                "Cocody, Abidjan (Côte d'Ivoire)."
            ),
            "adresse": "Riviera Palmeraie, Cocody",
            "ville": "Abidjan",
            "pays": "Côte d'Ivoire",
            "telephone": "+225 07 XX XX XX XX",
            "email": "contact@eliteburo.com",
            "statut": "active",
        },
    )

    # ── 2. Categories ────────────────────────────
    cat_private, _ = Category.objects.get_or_create(
        nom="Bureau Privé",
        slug="bureau-prive",
        defaults={"description": "Bureaux privatifs premium", "icone": "🏢"},
    )
    cat_hotdesk, _ = Category.objects.get_or_create(
        nom="Hot Desk",
        slug="hot-desk",
        defaults={"description": "Postes de travail flexibles", "icone": "👥"},
    )
    cat_meeting, _ = Category.objects.get_or_create(
        nom="Salle de Réunion",
        slug="salle-de-reunion",
        defaults={"description": "Salles de réunion équipées", "icone": "📋"},
    )
    cat_training, _ = Category.objects.get_or_create(
        nom="Salle de Formation",
        slug="salle-de-formation",
        defaults={"description": "Salles de formation modulables", "icone": "🎓"},
    )

    # ── 3. Equipment ────────────────────────────
    equipments_data = [
        ("videoprojecteur", "Vidéoprojecteur"),
        ("tableau-blanc", "Tableau blanc"),
        ("systeme-audio", "Système audio"),
        ("ecran-85", 'Écran 85"'),
        ("visioconference", "Vidéoconférence"),
        ("paperboard", "Paperboard"),
        ("scene", "Scène surélevée"),
        ("sonorisation-pro", "Sonorisation pro"),
        ("wifi-dedie", "Wi-Fi dédié"),
        ("climatisation", "Climatisation"),
        ("wifi", "Wi-Fi"),
        ("cafe-gratuit", "Café gratuit"),
    ]
    equipment_objects = {}
    for slug, nom in equipments_data:
        eq, _ = Equipment.objects.get_or_create(slug=slug, defaults={"nom": nom})
        equipment_objects[slug] = eq

    # ── 4. Workspaces (Private Offices: 11) ─────
    offices_data = [
        # (nom, slug, numero, etage, superficie, capacite, prix_jour, vedette)
        ("Horizon 01", "horizon-01", "N°01", "Étage 1", 12, 2, 15000, False),
        ("Prestige 02", "prestige-02", "N°02", "Étage 1", 18, 4, 18000, True),
        ("Executive 03", "executive-03", "N°03", "Étage 1", 25, 6, 28000, True),
        ("Lumière 04", "lumiere-04", "N°04", "Étage 1", 14, 3, 17000, False),
        ("Panorama 05", "panorama-05", "N°05", "Étage 2", 20, 4, 22000, True),
        ("Elite 06", "elite-06", "N°06", "Étage 2", 30, 8, 35000, True),
        ("Prestige 07", "prestige-07", "N°07", "Étage 2", 22, 5, 25000, True),
        ("Riviera 08", "riviera-08", "N°08", "Étage 2", 16, 3, 19000, False),
        ("Palmeraie 09", "palmeraie-09", "N°09", "Étage 3", 28, 7, 32000, True),
        ("Cocody 10", "cocody-10", "N°10", "Étage 3", 15, 3, 16000, False),
        ("Summit 11", "summit-11", "N°11", "Étage 3", 40, 10, 45000, True),
    ]

    # Offres occupées (pour démo) : Prestige 02, Elite 06, Riviera 08
    occupied_slugs = {"prestige-02", "elite-06", "riviera-08"}
    # Maintenance : aucun pour l'instant
    maintenance_slugs = set()
    # Bientôt libre
    soon_free_slugs = {"lumiere-04"}

    for nom, slug, numero, etage, superficie, capacite, prix_jour, vedette in offices_data:
        w, _ = Workspace.objects.get_or_create(
            slug=slug,
            espace=space,
            defaults={
                "nom": nom,
                "categorie": cat_private,
                "numero": numero,
                "etage": etage,
                "superficie": Decimal(str(superficie)),
                "capacite": capacite,
                "prix_heure": Decimal(str(round(prix_jour / 8))),
                "prix_demi_journee": Decimal(str(round(prix_jour * 0.6))),
                "prix_journee": Decimal(str(prix_jour)),
                "prix_semaine": Decimal(str(prix_jour * 5)),
                "prix_mois": Decimal(str(prix_jour * 22)),
                "caution": Decimal(str(prix_jour * 2)),
                "disponible": slug not in maintenance_slugs,
                "vedette": vedette,
                "description": f"Bureau privatif {nom} — {superficie}m², {capacite} personnes.",
            },
        )

    # ── 5. Meeting Rooms (3) ────────────────────
    rooms_data = [
        ("Salle Ivoire", "salle-ivoire", 12, 45000, ["videoprojecteur", "tableau-blanc", "systeme-audio", "wifi"]),
        ("Salle Savane", "salle-savane", 20, 65000, ["ecran-85", "visioconference", "paperboard", "wifi", "climatisation"]),
        ("Salle Élite", "salle-elite", 30, 90000, ["scene", "sonorisation-pro", "wifi-dedie", "climatisation"]),
    ]
    for nom, slug, capacite, prix_demi, equip_slugs in rooms_data:
        w, created = Workspace.objects.get_or_create(
            slug=slug,
            espace=space,
            defaults={
                "nom": nom,
                "categorie": cat_meeting,
                "numero": "",
                "etage": "Étage 1",
                "superficie": Decimal(str(round(capacite * 2.5))),
                "capacite": capacite,
                "prix_heure": Decimal(str(round(prix_demi / 4))),
                "prix_demi_journee": Decimal(str(prix_demi)),
                "prix_journee": Decimal(str(prix_demi * 2)),
                "prix_semaine": Decimal(str(prix_demi * 8)),
                "prix_mois": Decimal(str(prix_demi * 22)),
                "caution": Decimal(str(prix_demi)),
                "disponible": True,
                "vedette": True,
                "description": f"{nom} — {capacite} personnes maximum.",
            },
        )
        if created:
            for eq_slug in equip_slugs:
                if eq_slug in equipment_objects:
                    WorkspaceEquipment.objects.get_or_create(workspace=w, equipment=equipment_objects[eq_slug])

    # ── 6. Hot Desks (12) ───────────────────────
    for i in range(1, 13):
        ws, _ = Workspace.objects.get_or_create(
            slug=f"hot-desk-{i:02d}",
            espace=space,
            defaults={
                "nom": f"Hot Desk #{i:02d}",
                "categorie": cat_hotdesk,
                "numero": f"HD-{i:02d}",
                "etage": "Espace Commun",
                "superficie": Decimal("3.0"),
                "capacite": 1,
                "prix_heure": Decimal("1500"),
                "prix_demi_journee": Decimal("5000"),
                "prix_journee": Decimal("8000"),
                "prix_semaine": Decimal("35000"),
                "prix_mois": Decimal("120000"),
                "caution": Decimal("0"),
                "disponible": True,
                "vedette": False,
                "description": f"Hot desk flexible — poste de travail partagé #{i:02d}.",
            },
        )


def reverse_seed(apps, schema_editor):
    """Reverse: laisser les données, mais supprimer les workspaces créés."""
    Workspace = apps.get_model("coworking", "Workspace")
    WorkspaceEquipment = apps.get_model("coworking", "WorkspaceEquipment")
    WorkspaceEquipment.objects.all().delete()
    Workspace.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("coworking", "0004_alter_category_id_alter_coworkingspace_id_and_more"),
    ]
    operations = [
        migrations.RunPython(seed_data, reverse_seed),
    ]

