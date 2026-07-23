from django.contrib import admin

from .models import Reclamation


@admin.register(Reclamation)
class ReclamationAdmin(admin.ModelAdmin):
    list_display = ("objet", "auteur", "statut", "created_at", "closed_at")
    list_filter = ("statut", "created_at")
    search_fields = ("objet", "description", "auteur__username", "auteur__email")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-created_at",)

