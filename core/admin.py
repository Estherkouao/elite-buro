from django.contrib import admin
from .models import ContactMessage, DevisFormation


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("nom", "email", "sujet", "lu", "created_at")
    list_filter = ("lu", "created_at")
    search_fields = ("nom", "email", "sujet", "message")
    readonly_fields = ("created_at",)
    actions = ["mark_as_read"]

    @admin.action(description="Marquer comme lu")
    def mark_as_read(self, request, queryset):
        queryset.update(lu=True)


@admin.register(DevisFormation)
class DevisFormationAdmin(admin.ModelAdmin):
    list_display = ("company_name", "nom_complet", "email", "telephone", "lu", "created_at")
    list_filter = ("lu", "secteur", "taille_entreprise", "created_at")
    search_fields = ("company_name", "nom_complet", "email", "telephone", "objectifs")
    readonly_fields = ("created_at",)
    actions = ["mark_as_read"]

    @admin.action(description="Marquer comme lu")
    def mark_as_read(self, request, queryset):
        queryset.update(lu=True)
