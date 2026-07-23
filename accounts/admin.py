from django.contrib import admin

# Register your models here.

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    User,
    Profile,
    Company,
    Address,
    UserPreference,
    EmailVerification,
    PhoneVerification,
)


# -----------------------------
# Profile Inline
# -----------------------------
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    extra = 0


class AddressInline(admin.StackedInline):
    model = Address
    can_delete = False
    extra = 0


class PreferenceInline(admin.StackedInline):
    model = UserPreference
    can_delete = False
    extra = 0


# -----------------------------
# User
# -----------------------------
@admin.register(User)
class CustomUserAdmin(UserAdmin):

    ordering = ("-created_at",)

    list_display = (
        "email",
        "full_name",
        "phone",
        "role",
        "is_active",
        "is_staff",
        "is_email_verified",
    )

    list_filter = (
        "role",
        "is_staff",
        "is_active",
        "is_email_verified",
        "created_at",
    )

    search_fields = (
        "email",
        "first_name",
        "last_name",
        "phone",
    )

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
        "last_login",
    )

    fieldsets = (

        ("Informations personnelles", {
            "fields": (
                "id",
                "avatar",
                "first_name",
                "last_name",
                "email",
                "phone",
                "birth_date",
                "gender",
                "bio",
                "website",
            )
        }),

        ("Entreprise", {
            "fields": (
                "company_name",
                "job_title",
            )
        }),

        ("Authentification", {
            "fields": (
                "password",
            )
        }),

        ("Notifications", {
            "fields": (
                "receive_email_notification",
                "receive_sms_notification",
                "receive_whatsapp_notification",
            )
        }),

        ("Permissions", {
            "fields": (
                "role",
                "is_active",
                "is_staff",
                "is_superuser",
                "groups",
                "user_permissions",
            )
        }),

        ("Historique", {
            "fields": (
                "last_login",
                "last_activity",
                "created_at",
                "updated_at",
            )
        }),

    )

    add_fieldsets = (

        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "password1",
                    "password2",
                    "first_name",
                    "last_name",
                    "phone",
                    "role",
                    "is_staff",
                    "is_active",
                ),
            },
        ),
    )

    inlines = (
        ProfileInline,
        AddressInline,
        PreferenceInline,
    )


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):

    list_display = (
        "company_name",
        "owner",
        "phone",
        "email",
    )

    search_fields = (
        "company_name",
        "phone",
        "email",
    )

    list_filter = (
        "created_at",
    )

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "profession",
        "nationality",
    )

    search_fields = (
        "user__first_name",
        "user__last_name",
    )


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "city",
        "country",
    )

    search_fields = (
        "city",
        "country",
    )

@admin.register(UserPreference)
class PreferenceAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "dark_mode",
        "newsletter",
    )

@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "verified",
        "created_at",
        "expires_at",
    )

    readonly_fields = (
        "token",
    )


@admin.register(PhoneVerification)
class PhoneVerificationAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "verified",
        "expires_at",
    )

            
