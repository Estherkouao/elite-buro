from django.urls import path
from django.contrib.auth import views as auth_views
from .views import (
    CustomLoginView,
    RegisterView,
    logout_view,
    DashboardView,
    ProfileView,
    UpdateProfileView,
    UpdateProfileInformationView,
    CompanyUpdateView,
    ChangePasswordView,
    UpdateEmailView,
)

app_name = "accounts"

urlpatterns = [

    # Auth
    path("login/", CustomLoginView.as_view(), name="login"),
    path("register/", RegisterView.as_view(), name="register"),
    path("logout/", logout_view, name="logout"),

    # Password Reset
    path("password-reset/",
         auth_views.PasswordResetView.as_view(
             template_name="accounts/forgot_password.html",
             email_template_name="accounts/password_reset_email.txt",
             html_email_template_name="accounts/password_reset_email.html",
             subject_template_name="accounts/password_reset_subject.txt",
             success_url="/accounts/password-reset/done/"
         ),
         name="password_reset"),
    path("password-reset/done/",
         auth_views.PasswordResetDoneView.as_view(
             template_name="accounts/password_reset_done.html"
         ),
         name="password_reset_done"),
    path("password-reset/<uidb64>/<token>/",
         auth_views.PasswordResetConfirmView.as_view(
             template_name="accounts/reset_password.html",
             success_url="/accounts/password-reset/complete/"
         ),
         name="password_reset_confirm"),
    path("password-reset/complete/",
         auth_views.PasswordResetCompleteView.as_view(
             template_name="accounts/password_reset_complete.html"
         ),
         name="password_reset_complete"),

    # Dashboard
    path("dashboard/", DashboardView.as_view(), name="dashboard"),

    # Profile
    path("profile/", ProfileView.as_view(), name="profile"),
    path("profile/edit/", UpdateProfileView.as_view(), name="profile_edit"),
    path("profile/info/edit/", UpdateProfileInformationView.as_view(), name="profile_info_edit"),

    # Company
    path("company/edit/", CompanyUpdateView.as_view(), name="company_edit"),

    # Security & Login Credentials
    path("profile/change-password/", ChangePasswordView.as_view(), name="change_password"),
    path("profile/change-email/", UpdateEmailView.as_view(), name="change_email"),
]
