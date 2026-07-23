from __future__ import annotations

from django.contrib import admin, messages
from django.db.models import QuerySet

from .models import (
    DomiciliationContract,
    DomiciliationDocument,
    DomiciliationInvoice,
    DomiciliationLog,
    DomiciliationPlan,
    DomiciliationRenewal,
    DomiciliationRequest,
)
from .services import (
    activer_domiciliation,
    generer_contrat_pour_demande,
    generer_facture_pour_demande,
    envoyer_en_signature,
    refuser_demande,
    valider_demande,
    renouveler_domiciliation,
)


@admin.register(DomiciliationPlan)
class DomiciliationPlanAdmin(admin.ModelAdmin):
    list_display = ("nom", "slug", "prix", "durée", "actif", "ordre")
    list_filter = ("actif", "durée", "prix")
    search_fields = ("nom", "slug")
    prepopulated_fields = {"slug": ("nom",)}
    ordering = ("ordre", "nom")

    fieldsets = (
        (
            "Informations",
            {
                "fields": ("nom", "slug", "description"),
            },
        ),
        (
            "Tarification",
            {
                "fields": ("prix", "durée", "avantages", "actif", "ordre"),
            },
        ),
    )


def _get_selected_queryset(modeladmin, request, queryset: QuerySet):
    return queryset


@admin.register(DomiciliationRequest)
class DomiciliationRequestAdmin(admin.ModelAdmin):
    list_display = (
        "numero_demande",
        "entreprise",
        "utilisateur",
        "formule",
        "statut",
        "date_debut",
        "date_fin",
        "date_creation",
    )
    list_filter = ("statut", "formule", "utilisateur", "entreprise", "date_creation", "date_fin")
    search_fields = ("numero_demande", "adresse_domiciliation", "observations", "entreprise__company_name")
    autocomplete_fields = ("utilisateur", "entreprise", "formule")
    readonly_fields = ("date_creation", "derniere_modification")

    actions = (
        "action_valider",
        "action_refuser",
        "action_generer_contrat",
        "action_generer_facture",
        "action_envoyer_signature",
        "action_activer",
        "action_renouveler",
    )

    fieldsets = (
        (
            "Demande",
            {
                "fields": (
                    "numero_demande",
                    "utilisateur",
                    "entreprise",
                    "formule",
                    "statut",
                ),
            },
        ),
        (
            "Dates",
            {
                "fields": ("date_debut", "date_fin"),
            },
        ),
        (
            "Adresse & Observations",
            {
                "fields": ("adresse_domiciliation", "observations"),
            },
        ),
        (
            "Traçabilité",
            {
                "fields": ("date_creation", "derniere_modification"),
            },
        ),
    )

    @admin.action(description="Valider une demande")
    def action_valider(self, request, queryset: QuerySet):
        queryset = _get_selected_queryset(self, request, queryset)
        for demande in queryset:
            try:
                valider_demande(demande=demande, par=request.user)
                messages.success(request, f"Demande {demande.numero_demande} validée.")
            except Exception as exc:
                messages.error(request, f"Impossible de valider {demande.numero_demande}: {exc}")

    @admin.action(description="Refuser une demande")
    def action_refuser(self, request, queryset: QuerySet):
        queryset = _get_selected_queryset(self, request, queryset)
        for demande in queryset:
            try:
                refuser_demande(demande=demande, par=request.user)
                messages.success(request, f"Demande {demande.numero_demande} refusée.")
            except Exception as exc:
                messages.error(request, f"Impossible de refuser {demande.numero_demande}: {exc}")

    @admin.action(description="Générer le contrat PDF")
    def action_generer_contrat(self, request, queryset: QuerySet):
        queryset = _get_selected_queryset(self, request, queryset)
        for demande in queryset:
            try:
                generer_contrat_pour_demande(demande=demande)
                messages.success(request, f"Contrat généré pour {demande.numero_demande}.")
            except Exception as exc:
                messages.error(request, f"Impossible de générer le contrat pour {demande.numero_demande}: {exc}")

    @admin.action(description="Générer la facture PDF")
    def action_generer_facture(self, request, queryset: QuerySet):
        queryset = _get_selected_queryset(self, request, queryset)
        for demande in queryset:
            try:
                generer_facture_pour_demande(demande=demande)
                messages.success(request, f"Facture générée pour {demande.numero_demande}.")
            except Exception as exc:
                messages.error(request, f"Impossible de générer la facture pour {demande.numero_demande}: {exc}")

    @admin.action(description="Envoyer en signature Docuseal")
    def action_envoyer_signature(self, request, queryset: QuerySet):
        queryset = _get_selected_queryset(self, request, queryset)
        for demande in queryset:
            try:
                envoyer_en_signature(demande=demande, par=request.user)
                messages.success(request, f"Signature envoyée pour {demande.numero_demande}.")
            except Exception as exc:
                messages.error(request, f"Impossible d’envoyer en signature pour {demande.numero_demande}: {exc}")

    @admin.action(description="Activer la domiciliation")
    def action_activer(self, request, queryset: QuerySet):
        queryset = _get_selected_queryset(self, request, queryset)
        for demande in queryset:
            try:
                activer_domiciliation(demande=demande, par=request.user)
                messages.success(request, f"Domiciliation activée pour {demande.numero_demande}.")
            except Exception as exc:
                messages.error(request, f"Impossible d’activer {demande.numero_demande}: {exc}")

    @admin.action(description="Créer un renouvellement")
    def action_renouveler(self, request, queryset: QuerySet):
        queryset = _get_selected_queryset(self, request, queryset)
        for demande in queryset:
            try:
                renouveler_domiciliation(demande=demande, par=request.user)
                messages.success(request, f"Renouvellement créé pour {demande.numero_demande}.")
            except Exception as exc:
                messages.error(request, f"Impossible de renouveler {demande.numero_demande}: {exc}")


@admin.register(DomiciliationDocument)
class DomiciliationDocumentAdmin(admin.ModelAdmin):
    list_display = ("type", "demande", "validé", "created_at")
    list_filter = ("type", "validé", "created_at")
    search_fields = ("demande__numero_demande", "commentaire")
    autocomplete_fields = ("demande",)
    readonly_fields = ("created_at",)


@admin.register(DomiciliationContract)
class DomiciliationContractAdmin(admin.ModelAdmin):
    list_display = ("numero", "demande", "signé", "date_signature", "created_at")
    list_filter = ("signé", "date_signature", "created_at")
    search_fields = ("numero", "demande__numero_demande")
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("demande",)


@admin.register(DomiciliationInvoice)
class DomiciliationInvoiceAdmin(admin.ModelAdmin):
    list_display = ("numero", "demande", "montant", "statut", "created_at")
    list_filter = ("statut", "created_at")
    search_fields = ("numero", "demande__numero_demande")
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("demande",)


@admin.register(DomiciliationRenewal)
class DomiciliationRenewalAdmin(admin.ModelAdmin):
    list_display = ("demande", "nouvelle_periode", "montant", "statut", "created_at")
    list_filter = ("statut", "created_at")
    search_fields = ("demande__numero_demande",)
    autocomplete_fields = ("demande",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(DomiciliationLog)
class DomiciliationLogAdmin(admin.ModelAdmin):
    list_display = ("demande", "utilisateur", "action", "created_at")
    list_filter = ("action", "created_at")
    search_fields = ("demande__numero_demande", "details")
    autocomplete_fields = ("demande", "utilisateur")
    readonly_fields = ("created_at",)

