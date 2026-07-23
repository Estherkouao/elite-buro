from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import (
    Reservation,
    ReservationInvoice,
    ReservationLog,
    ReservationParticipant,
    ReservationReminder,
)
from .services import (
    admin_confirm_reservation,
    admin_cancel_reservation,
    admin_finish_reservation,
    export_reservation_invoice_pdf,
)


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = (
        "reservation_number",
        "utilisateur",
        "entreprise",
        "espace",
        "type_reservation",
        "date_debut",
        "date_fin",
        "heure_debut",
        "heure_fin",
        "nombre_participants",
        "montant_total",
        "statut",
        "created_at",
        "updated_at",
    )
    list_filter = (
        "statut",
        "type_reservation",
        "espace",
        "entreprise",
        "utilisateur",
        "date_debut",
        "date_fin",
    )
    search_fields = (
        "reservation_number",
        "utilisateur__email",
        "utilisateur__first_name",
        "utilisateur__last_name",
        "entreprise__company_name",
        "espace__nom",
        "commentaire",
    )
    autocomplete_fields = ("utilisateur", "entreprise", "espace")

    readonly_fields = (
        "created_at",
        "updated_at",
        "reservation_number",
        "prix_unitaire",
        "montant_total",
    )

    fieldsets = (
        (
            "Informations",
            {
                "fields": (
                    "reservation_number",
                    "utilisateur",
                    "entreprise",
                    "espace",
                    "type_reservation",
                    "statut",
                    "commentaire",
                )
            },
        ),
        (
            "Période",
            {
                "fields": (
                    "date_debut",
                    "date_fin",
                    "heure_debut",
                    "heure_fin",
                    "nombre_participants",
                )
            },
        ),
        (
            "Tarification",
            {
                "fields": (
                    "prix_unitaire",
                    "remise",
                    "taxes",
                    "montant_total",
                )
            },
        ),
        (
            "Audit",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    actions = [
        "action_confirm",
        "action_cancel",
        "action_finish",
        "action_export_pdf",
    ]

    @admin.action(description=_("Confirmer la réservation"))
    def action_confirm(self, request, queryset):
        for obj in queryset.select_related("utilisateur", "entreprise", "espace").all():
            admin_confirm_reservation(request.user, obj)

    @admin.action(description=_("Annuler la réservation"))
    def action_cancel(self, request, queryset):
        for obj in queryset.select_related("utilisateur", "entreprise", "espace").all():
            admin_cancel_reservation(request.user, obj)

    @admin.action(description=_("Terminer la réservation"))
    def action_finish(self, request, queryset):
        for obj in queryset.select_related("utilisateur", "entreprise", "espace").all():
            admin_finish_reservation(request.user, obj)

    @admin.action(description=_("Exporter la facture (PDF)"))
    def action_export_pdf(self, request, queryset):
        for obj in queryset.select_related("invoice").all():
            export_reservation_invoice_pdf(obj)


@admin.register(ReservationParticipant)
class ReservationParticipantAdmin(admin.ModelAdmin):
    list_display = (
        "reservation",
        "prenom",
        "nom",
        "email",
        "telephone",
    )
    search_fields = ("reservation__reservation_number", "email", "nom", "prenom")
    autocomplete_fields = ("reservation",)


@admin.register(ReservationInvoice)
class ReservationInvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "numero",
        "reservation",
        "statut",
        "montant",
        "date",
    )
    list_filter = ("statut", "date")
    search_fields = ("numero", "reservation__reservation_number", "reservation__utilisateur__email")
    autocomplete_fields = ("reservation",)
    readonly_fields = ("date",)


@admin.register(ReservationLog)
class ReservationLogAdmin(admin.ModelAdmin):
    list_display = ("reservation", "action", "acteur", "date_creation")
    list_filter = ("action", "date_creation")
    search_fields = ("reservation__reservation_number", "action", "acteur__email", "detail")
    autocomplete_fields = ("reservation", "acteur")
    readonly_fields = ("date_creation",)


@admin.register(ReservationReminder)
class ReservationReminderAdmin(admin.ModelAdmin):
    list_display = (
        "reservation",
        "type",
        "channel",
        "date_envoi",
        "envoye",
    )
    list_filter = ("type", "channel", "date_envoi")
    search_fields = ("reservation__reservation_number", "destination")
    autocomplete_fields = ("reservation",)
    readonly_fields = ()

    @admin.display(boolean=True, description="Envoyé")
    def envoye(self, obj: ReservationReminder) -> bool:
        return bool(getattr(obj, "envoye", False))


