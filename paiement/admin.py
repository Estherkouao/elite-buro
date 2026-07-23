from __future__ import annotations

from django.contrib import admin

from paiement.models import PaymentProvider, PaymentTransaction


@admin.register(PaymentProvider)
class PaymentProviderAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "code",
        "is_active",
        "sandbox_mode",
        "display_order",
        "created_at",
    ]
    list_filter = ["is_active", "sandbox_mode", "code"]
    search_fields = ["name", "code"]
    ordering = ["display_order", "name"]
    list_editable = ["is_active", "display_order", "sandbox_mode"]
    fieldsets = (
        (
            "Informations générales",
            {
                "fields": ("name", "code", "description", "is_active", "display_order")
            },
        ),
        (
            "Clés API",
            {
                "fields": ("api_key", "api_secret", "merchant_id"),
                "classes": ("wide",),
            },
        ),
        (
            "Endpoints",
            {
                "fields": (
                    "endpoint_url",
                    "sandbox_mode",
                    "sandbox_endpoint",
                ),
                "classes": ("wide",),
            },
        ),
        (
            "Configuration avancée",
            {
                "fields": ("config_json",),
                "classes": ("wide",),
            },
        ),
    )


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = [
        "transaction_id",
        "provider",
        "amount",
        "currency",
        "status",
        "payment_date",
        "created_at",
    ]
    list_filter = ["status", "provider", "currency", "created_at"]
    search_fields = ["transaction_id", "reference", "phone_number", "email"]
    ordering = ["-created_at"]
    readonly_fields = ["transaction_id", "created_at", "updated_at"]
    fieldsets = (
        (
            "Références",
            {
                "fields": (
                    "transaction_id",
                    "reference",
                    "provider",
                    "reservation",
                )
            },
        ),
        (
            "Montant",
            {"fields": ("amount", "currency")},
        ),
        (
            "Client",
            {"fields": ("phone_number", "email")},
        ),
        (
            "Statut",
            {"fields": ("status", "error_message", "payment_date")},
        ),
        (
            "Données",
            {
                "fields": ("provider_data",),
                "classes": ("wide",),
            },
        ),
    )

