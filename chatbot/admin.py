from django.contrib import admin

# Register your models here.
from django.contrib import admin

from .models import (
    ChatConversation,
    ChatMessage,
    KnowledgeBase,
    QuickReply,
    ChatLead,
)


@admin.register(KnowledgeBase)
class KnowledgeBaseAdmin(admin.ModelAdmin):

    list_display = (
        "titre",
        "actif",
        "ordre",
    )

    list_filter = (
        "actif",
    )

    search_fields = (
        "titre",
        "mots_cles",
        "reponse",
    )

    ordering = (
        "ordre",
    )


@admin.register(QuickReply)
class QuickReplyAdmin(admin.ModelAdmin):

    list_display = (
        "texte",
        "ordre",
        "actif",
    )

    list_editable = (
        "ordre",
        "actif",
    )

    ordering = (
        "ordre",
    )

class ChatMessageInline(admin.TabularInline):

    model = ChatMessage

    extra = 0

    readonly_fields = (
        "role",
        "message",
        "date_creation",
    )

    can_delete = False


@admin.register(ChatConversation)
class ChatConversationAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "nom",
        "email",
        "telephone",
        "utilisateur",
        "date_creation",
        "est_terminee",
    )

    list_filter = (
        "est_terminee",
        "date_creation",
    )

    search_fields = (
        "nom",
        "email",
        "telephone",
    )

    readonly_fields = (
        "date_creation",
        "derniere_activite",
    )

    inlines = [
        ChatMessageInline,
    ]


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):

    list_display = (
        "conversation",
        "role",
        "message_court",
        "date_creation",
    )

    list_filter = (
        "role",
    )

    search_fields = (
        "message",
    )

    readonly_fields = (
        "date_creation",
    )

    def message_court(self, obj):
        return obj.message[:80]


@admin.register(ChatLead)
class ChatLeadAdmin(admin.ModelAdmin):

    list_display = (
        "nom",
        "telephone",
        "email",
        "traite",
        "date_creation",
    )

    list_filter = (
        "traite",
    )

    search_fields = (
        "nom",
        "telephone",
        "email",
    )

    list_editable = (
        "traite",
    )



