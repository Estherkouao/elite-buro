from django.contrib import admin

from .models import (
    Category,
    CoworkingSpace,
    Equipment,
    FavoriteWorkspace,
    Workspace,
    WorkspaceAvailability,
    WorkspaceEquipment,
    WorkspaceImage,
    WorkspacePrice,
    WorkspaceReview,
)


@admin.register(CoworkingSpace)
class CoworkingSpaceAdmin(admin.ModelAdmin):
    list_display = ("nom", "ville", "statut", "created_at", "updated_at")
    search_fields = ("nom", "slug", "ville", "pays", "email", "telephone")
    list_filter = ("statut", "ville", "pays")
    prepopulated_fields = {"slug": ("nom",)}
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (
            "Informations",
            {
                "fields": (
                    "nom",
                    "slug",
                    "description",
                    "adresse",
                    "ville",
                    "pays",
                    "telephone",
                    "email",
                )
            },
        ),
        (
            "Localisation",
            {
                "fields": ("latitude", "longitude"),
            },
        ),
        (
            "Médias & horaires",
            {
                "fields": ("image_principale", "logo", "horaires"),
            },
        ),
        (
            "Statut",
            {
                "fields": ("statut",),
            },
        ),
    )
    autocomplete_fields = ()


class WorkspaceImageInline(admin.TabularInline):
    model = WorkspaceImage
    extra = 1


class WorkspaceEquipmentInline(admin.TabularInline):
    model = WorkspaceEquipment
    extra = 1


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("nom", "slug", "created_at", "updated_at")
    search_fields = ("nom", "slug", "description")
    list_filter = ()
    prepopulated_fields = {"slug": ("nom",)}
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (
            "Détails",
            {
                "fields": ("nom", "slug", "description", "icone", "image"),
            },
        ),
    )


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ("nom", "slug", "created_at", "updated_at")
    search_fields = ("nom", "slug")
    list_filter = ()
    prepopulated_fields = {"slug": ("nom",)}
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (
            "Équipement",
            {
                "fields": ("nom", "slug"),
            },
        ),
    )


@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    list_display = (
        "nom",
        "espace",
        "categorie",
        "disponible",
        "vedette",
        "created_at",
        "updated_at",
    )
    search_fields = ("nom", "slug", "description", "espace__nom", "categorie__nom")
    list_filter = ("disponible", "vedette", "espace", "categorie")
    prepopulated_fields = {"slug": ("nom",)}
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("espace", "categorie")
    fieldsets = (
        (
            "Identité",
            {
                "fields": (
                    "espace",
                    "categorie",
                    "nom",
                    "slug",
                    "description",
                    "image_principale",
                )
            },
        ),
        (
            "Caractéristiques",
            {
                "fields": (
                    "capacite",
                    "superficie",
                    "etage",
                    "numero",
                    "caution",
                )
            },
        ),
        (
            "Tarifs",
            {
                "fields": (
                    "prix_heure",
                    "prix_demi_journee",
                    "prix_journee",
                    "prix_semaine",
                    "prix_mois",
                )
            },
        ),
        (
            "Disponibilité",
            {
                "fields": (
                    "disponible",
                    "vedette",
                )
            },
        ),
    )
    inlines = [WorkspaceImageInline, WorkspaceEquipmentInline]


@admin.register(WorkspaceImage)
class WorkspaceImageAdmin(admin.ModelAdmin):
    list_display = ("workspace", "image")
    search_fields = ("workspace__nom",)
    autocomplete_fields = ("workspace",)


@admin.register(WorkspaceEquipment)
class WorkspaceEquipmentAdmin(admin.ModelAdmin):
    list_display = ("workspace", "equipment")
    search_fields = ("workspace__nom", "equipment__nom")
    autocomplete_fields = ("workspace", "equipment")


@admin.register(WorkspaceAvailability)
class WorkspaceAvailabilityAdmin(admin.ModelAdmin):
    list_display = ("espace", "date", "heure_debut", "heure_fin", "disponible", "created_at")
    search_fields = ("espace__nom",)
    list_filter = ("disponible", "date")
    autocomplete_fields = ("espace",)

    @admin.display(description="Espace")
    def espace(self, obj):
        return obj.espace


@admin.register(WorkspacePrice)
class WorkspacePriceAdmin(admin.ModelAdmin):
    list_display = ("espace", "created_at", "updated_at")
    search_fields = ("espace__nom",)
    autocomplete_fields = ("espace",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(WorkspaceReview)
class WorkspaceReviewAdmin(admin.ModelAdmin):
    list_display = ("espace", "utilisateur", "note", "date", "created_at", "updated_at")
    search_fields = ("espace__nom", "utilisateur__username", "utilisateur__email")
    list_filter = ("note", "date")
    autocomplete_fields = ("espace", "utilisateur")
    readonly_fields = ("created_at", "updated_at")


@admin.register(FavoriteWorkspace)
class FavoriteWorkspaceAdmin(admin.ModelAdmin):
    list_display = ("utilisateur", "espace")
    search_fields = ("utilisateur__username", "utilisateur__email", "espace__nom")
    autocomplete_fields = ("utilisateur", "espace")

