from django.urls import path

from .views import (
    AdminReclamationCloseView,
    AdminReclamationDetailView,
    AdminReclamationEditView,
    AdminReclamationListView,
    AdminReclamationReopenView,
    MemberReclamationCreateView,
    MemberReclamationDetailView,
    MemberReclamationListView,
)

app_name = "reclamation_admin"

# URLs pour les membres (accessible via `reclamation:member_*`)
member_urlpatterns = [
    path("creer/", MemberReclamationCreateView.as_view(), name="member_create"),
    path("liste/", MemberReclamationListView.as_view(), name="member_list"),
    path("<uuid:pk>/", MemberReclamationDetailView.as_view(), name="member_detail"),
]

# URLs pour l'admin
urlpatterns = [
    path("", AdminReclamationListView.as_view(), name="list"),
    path("<uuid:reclamation_id>/", AdminReclamationDetailView.as_view(), name="detail"),
    path(
        "<uuid:reclamation_id>/edit/",
        AdminReclamationEditView.as_view(),
        name="edit",
    ),
    path(
        "<uuid:reclamation_id>/close/",
        AdminReclamationCloseView.as_view(),
        name="close",
    ),
    path(
        "<uuid:reclamation_id>/reopen/",
        AdminReclamationReopenView.as_view(),
        name="reopen",
    ),
]

