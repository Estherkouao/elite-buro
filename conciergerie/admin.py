from django.contrib import admin
from .models import DemandeConciergerie



@admin.register(DemandeConciergerie)
class DemandeConciergerieAdmin(admin.ModelAdmin):


    list_display = (

        "reference",
        "nom",
        "entreprise",
        "service",
        "statut",
        "created_at",

    )


    list_filter = (

        "statut",
        "service",
        "created_at",

    )


    search_fields = (

        "reference",
        "nom",
        "entreprise",
        "email",

    )


    list_editable = (

        "statut",

    )


    readonly_fields = (

        "reference",
        "created_at",
        "updated_at",

    )
