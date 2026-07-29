from django.contrib import admin
from django.db.models import Count
from django.utils.html import format_html

from .models import (
    Formation,
    FormationCategory,
    FormationCertificate,
    FormationContract,
    FormationPayment,
    FormationQuote,
    FormationRegistration,
    FormationReview,
    FormationSession,
    Trainer,
)


@admin.register(FormationCategory)
class FormationCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("name",)


@admin.register(Formation)
class FormationAdmin(admin.ModelAdmin):
    list_display = ("titre", "category", "actif", "prix", "niveau", "slug", "created_at")
    list_filter = ("actif", "niveau", "category")
    search_fields = ("titre", "slug", "description_courte")
    autocomplete_fields = ("category",)
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (
            "Identité",
            {
                "fields": (
                    "category",
                    "titre",
                    "slug",
                    "actif",
                )
            },
        ),
        (
            "Descriptions",
            {
                "fields": (
                    "description_courte",
                    "description_complete",
                    "objectifs",
                    "programme",
                    "prerequis",
                    "niveau",
                    "duree",
                    "prix",
                )
            },
        ),
        (
            "Médias",
            {
                "fields": (
                    "image",
                    "video_url",
                    "certificat",
                )
            },
        ),
        (
            "Audit",
            {
                "fields": ("created_at", "updated_at"),
            },
        ),
    )
    prepopulated_fields = {"slug": ("titre",)}

    actions = ["mark_active", "mark_inactive"]

    @admin.action(description="Publier (activer) les formations")
    def mark_active(self, request, queryset):
        queryset.update(actif=True)

    @admin.action(description="Dépublier (désactiver) les formations")
    def mark_inactive(self, request, queryset):
        queryset.update(actif=False)


@admin.register(Trainer)
class TrainerAdmin(admin.ModelAdmin):
    list_display = ("user", "specialite", "disponible", "annees_experience")
    list_filter = ("disponible", "specialite")
    search_fields = ("user__email", "user__first_name", "user__last_name", "specialite", "linkedin")
    autocomplete_fields = ("user",)
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (
            "Identité",
            {
                "fields": ("user", "specialite", "annees_experience", "disponible"),
            },
        ),
        (
            "Biographie",
            {
                "fields": ("biographie", "competences", "linkedin"),
            },
        ),
        (
            "Documents",
            {
                "fields": ("photo", "cv"),
            },
        ),
        (
            "Audit",
            {
                "fields": ("created_at", "updated_at"),
            },
        ),
    )


@admin.register(FormationSession)
class FormationSessionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "formation",
        "formateur",
        "date_debut",
        "date_fin",
        "heure_debut",
        "heure_fin",
        "nombre_maximum",
        "places_restantes",
        "statut",
    )
    list_filter = ("statut", "formation", "formateur")
    search_fields = ("formation__titre", "formateur__user__email", "formateur__specialite")
    autocomplete_fields = ("formation", "formateur")
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (
            "Planning",
            {
                "fields": (
                    "formation",
                    "formateur",
                    "salle_reference",
                    "date_debut",
                    "date_fin",
                    "heure_debut",
                    "heure_fin",
                    "nombre_maximum",
                    "statut",
                    "places_restantes",
                ),
            },
        ),
        (
            "Audit",
            {
                "fields": ("created_at", "updated_at"),
            },
        ),
    )

    actions = ["publier", "ouvrir", "fermer", "recalculer_places"]

    @admin.action(description="Publier (statut=published) les sessions")
    def publier(self, request, queryset):
        queryset.update(statut=FormationSession.Statut.PUBLISHED)

    @admin.action(description="Ouvrir (statut=open) les sessions")
    def ouvrir(self, request, queryset):
        queryset.update(statut=FormationSession.Statut.OPEN)

    @admin.action(description="Fermer (statut=closed) les sessions")
    def fermer(self, request, queryset):
        queryset.update(statut=FormationSession.Statut.CLOSED)

    @admin.action(description="Recalculer les places restantes")
    def recalculer_places(self, request, queryset):
        # Recalcul simple côté admin (aucune logique métier lourde ici)
        for session in queryset.select_related("formation"):
            confirmed = (
                session.registrations.filter(statut__in=[FormationRegistration.Statut.CONFIRMED, FormationRegistration.Statut.PENDING])
                .count()
            )
            remaining = max(session.nombre_maximum - confirmed, 0)
            session.places_restantes = remaining
            session.save(update_fields=["places_restantes"])


@admin.register(FormationRegistration)
class FormationRegistrationAdmin(admin.ModelAdmin):
    list_display = (
        "numero",
        "membre",
        "entreprise",
        "session",
        "statut",
        "date",
        "commentaire",
    )
    list_filter = ("statut", "session__formation", "session__formateur", "entreprise")
    search_fields = ("numero", "membre__email", "membre__first_name", "membre__last_name")
    autocomplete_fields = ("session", "membre", "entreprise")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (
            "Inscription",
            {
                "fields": ("numero", "membre", "entreprise", "session", "statut", "date", "commentaire"),
            },
        ),
        (
            "Audit",
            {
                "fields": ("created_at", "updated_at"),
            },
        ),
    )


class _FileLinkMixin:
    def _file_link(self, obj, field_name: str, label: str):
        f = getattr(obj, field_name)
        if not f:
            return "—"
        return format_html('<a href="{}" target="_blank" rel="noopener">{}</a>', f.url, label)


@admin.register(FormationQuote)
class FormationQuoteAdmin(_FileLinkMixin, admin.ModelAdmin):
    list_display = ("inscription", "montant", "statut", "date", "pdf_link")
    list_filter = ("statut", "date")
    search_fields = ("inscription__numero", "inscription__membre__email")
    autocomplete_fields = ("inscription",)
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (
            "Devis",
            {
                "fields": ("inscription", "montant", "statut", "pdf", "date"),
            },
        ),
        (
            "Audit",
            {
                "fields": ("created_at", "updated_at"),
            },
        ),
    )

    def pdf_link(self, obj: FormationQuote):
        return self._file_link(obj, "pdf", "PDF")

    pdf_link.short_description = "PDF"


@admin.register(FormationContract)
class FormationContractAdmin(_FileLinkMixin, admin.ModelAdmin):
    list_display = ("devis", "statut", "signé", "date", "contrat_link")
    list_filter = ("statut", "signé", "date")
    search_fields = ("devis__inscription__numero", "devis__inscription__membre__email")
    autocomplete_fields = ("devis",)
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (
            "Contrat",
            {
                "fields": ("devis", "contrat_pdf", "signature_docuseal", "signé", "statut", "date"),
            },
        ),
        (
            "Audit",
            {
                "fields": ("created_at", "updated_at"),
            },
        ),
    )

    def contrat_link(self, obj: FormationContract):
        return self._file_link(obj, "contrat_pdf", "Contrat")

    contrat_link.short_description = "Contrat"

    actions = ["generer_contrat_pdf_placeholder"]

    @admin.action(description="Marquer le contrat comme signé (placeholder)")
    def generer_contrat_pdf_placeholder(self, request, queryset):
        queryset.update(signé=True, statut=FormationContract.StatutSignature.SIGNED)


@admin.register(FormationPayment)
class FormationPaymentAdmin(admin.ModelAdmin):
    list_display = ("inscription", "montant", "méthode", "statut", "reference", "created_at")
    list_filter = ("statut", "méthode")
    search_fields = ("inscription__numero", "reference")
    autocomplete_fields = ("inscription",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(FormationCertificate)
class FormationCertificateAdmin(_FileLinkMixin, admin.ModelAdmin):
    list_display = ("inscription", "date", "certificat_link")
    list_filter = ("date",)
    search_fields = ("inscription__numero", "inscription__membre__email")
    autocomplete_fields = ("inscription",)
    readonly_fields = ("created_at", "updated_at")

    def certificat_link(self, obj: FormationCertificate):
        return self._file_link(obj, "certificat_pdf", "Certificat")

    certificat_link.short_description = "Certificat"


@admin.register(FormationReview)
class FormationReviewAdmin(admin.ModelAdmin):
    list_display = ("membre", "note", "commentaire", "created_at")
    list_filter = ("note",)
    search_fields = ("membre__email", "commentaire")
    autocomplete_fields = ("membre",)
    readonly_fields = ("created_at", "updated_at")


from django.contrib import admin
from .models import DevisFormation


@admin.register(DevisFormation)
class DevisFormationAdmin(admin.ModelAdmin):
    list_display = (
        "company_name",
        "nom",
        "telephone",
        "email",
        "statut",
        "lu",
        "created_at",
    )

    list_filter = (
        "statut",
        "lu",
        "created_at",
    )

    search_fields = (
        "company_name",
        "nom",
        "email",
        "telephone",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

