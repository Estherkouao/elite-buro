from django.urls import path
from .views import (
    CustomLoginView,
    RegisterView,
    logout_view,
    DashboardView,
    ProfileView,
    UpdateProfileView,
    UpdateProfileInformationView,
    CompanyUpdateView,
)

app_name = "accounts"

urlpatterns = [

    # Auth
    path("login/", CustomLoginView.as_view(), name="login"),
    path("register/", RegisterView.as_view(), name="register"),
    path("logout/", logout_view, name="logout"),

    # Dashboard
    path("dashboard/", DashboardView.as_view(), name="dashboard"),

    # Profile
    path("profile/", ProfileView.as_view(), name="profile"),
    path("profile/edit/", UpdateProfileView.as_view(), name="profile_edit"),
    path("profile/info/edit/", UpdateProfileInformationView.as_view(), name="profile_info_edit"),

    # Company
    path("company/edit/", CompanyUpdateView.as_view(), name="company_edit"),
]