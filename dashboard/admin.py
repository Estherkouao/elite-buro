from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.utils import timezone

from accounts.models import User
from .models import Testimonial


class RoleRestrictedAdminMixin:
    """Admin protection basé sur les rôles (ADMIN, MANAGER).

    IMPORTANT:
    - Ce fichier ne déclare aucun @admin.register(...)
    - Les modèles métiers sont déjà enregistrés par leurs apps.
    """

    allowed_roles = {User.Role.ADMIN, User.Role.MANAGER}

    def _check_permission(self, request):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            raise PermissionDenied
        if getattr(user, "role", None) not in self.allowed_roles:
            raise PermissionDenied

    def has_module_permission(self, request):
        try:
            self._check_permission(request)
        except PermissionDenied:
            return False
        return True

    def has_view_permission(self, request, obj=None):
        try:
            self._check_permission(request)
        except PermissionDenied:
            return False
        return True

    def has_add_permission(self, request):
        try:
            self._check_permission(request)
        except PermissionDenied:
            return False
        return True

    def has_change_permission(self, request, obj=None):
        try:
            self._check_permission(request)
        except PermissionDenied:
            return False
        return True

    def has_delete_permission(self, request, obj=None):
        try:
            self._check_permission(request)
        except PermissionDenied:
            return False
        return True


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ("utilisateur", "note", "approuvé", "approuvé_le", "created_at")
    list_filter = ("approuvé", "note")
    search_fields = ("utilisateur__first_name", "utilisateur__last_name", "utilisateur__email", "commentaire")
    readonly_fields = ("created_at",)

    actions = ["approuver_avis"]

    def approuver_avis(self, request, queryset):
        queryset.update(approuvé=True, approuvé_le=timezone.now())
        self.message_user(request, f"{queryset.count()} avis approuvé(s).")
    approuver_avis.short_description = "Approuver les avis sélectionnés"

