from django.contrib import admin

# Register your models here.
from django.contrib import admin
from django.utils import timezone

from .models import (
    Notification,
    NotificationTemplate,
    NotificationLog,
)


@admin.action(description="Marquer comme envoyées")
def mark_as_sent(modeladmin, request, queryset):
    queryset.update(
        status="SENT",
        sent_at=timezone.now()
    )


@admin.action(description="Marquer comme lues")
def mark_as_read(modeladmin, request, queryset):
    queryset.update(
        status="READ",
        is_read=True,
        read_at=timezone.now()
    )


@admin.action(description="Remettre en attente")
def mark_as_pending(modeladmin, request, queryset):
    queryset.update(
        status="PENDING",
        is_read=False,
        read_at=None,
        sent_at=None,
    )


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "recipient",
        "notification_type",
        "priority",
        "status",
        "is_read",
        "created_at",
    )

    list_filter = (
        "notification_type",
        "priority",
        "status",
        "is_read",
        "created_at",
    )

    search_fields = (
        "title",
        "message",
        "recipient__email",
        "recipient__first_name",
        "recipient__last_name",
    )

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
        "sent_at",
        "read_at",
    )

    ordering = (
        "-created_at",
    )

    autocomplete_fields = (
        "recipient",
    )

    actions = (
        mark_as_sent,
        mark_as_read,
        mark_as_pending,
    )

    fieldsets = (

        (
            "Informations générales",
            {
                "fields": (
                    "recipient",
                    "notification_type",
                    "priority",
                    "status",
                )
            },
        ),

        (
            "Contenu",
            {
                "fields": (
                    "title",
                    "message",
                )
            },
        ),

        (
            "Lecture",
            {
                "fields": (
                    "is_read",
                    "read_at",
                )
            },
        ),

        (
            "Envoi",
            {
                "fields": (
                    "sent_at",
                    "error_message",
                )
            },
        ),

        (
            "Métadonnées",
            {
                "classes": ("collapse",),
                "fields": (
                    "id",
                    "created_at",
                    "updated_at",
                ),
            },
        ),
    )


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "notification_type",
        "active",
        "created_at",
    )

    list_filter = (
        "notification_type",
        "active",
    )

    search_fields = (
        "name",
        "subject",
        "content",
    )

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )

    ordering = (
        "name",
    )

    fieldsets = (

        (
            "Informations",
            {
                "fields": (
                    "name",
                    "notification_type",
                    "active",
                )
            },
        ),

        (
            "Message",
            {
                "fields": (
                    "subject",
                    "content",
                )
            },
        ),

        (
            "Métadonnées",
            {
                "classes": ("collapse",),
                "fields": (
                    "id",
                    "created_at",
                    "updated_at",
                ),
            },
        ),
    )


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):

    list_display = (
        "notification",
        "action",
        "created_at",
    )

    list_filter = (
        "created_at",
    )

    search_fields = (
        "action",
        "details",
    )

    readonly_fields = (
        "id",
        "notification",
        "action",
        "details",
        "created_at",
    )

    ordering = (
        "-created_at",
    )

    autocomplete_fields = (
        "notification",
    )