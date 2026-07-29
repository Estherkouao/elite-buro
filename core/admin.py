from django.contrib import admin
from .models import ContactMessage


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



