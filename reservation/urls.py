from django.urls import path

from . import views

app_name = "reservation"

urlpatterns = [
    # Landing page publique - accessible sans authentification
    path("", views.ReservationLandingView.as_view(), name="landing"),
    path("reservations/", views.ReservationListView.as_view(), name="list"),
    path("reservations/create/", views.ReservationCreateView.as_view(), name="create"),
    path("reservations/<uuid:reservation_id>/", views.ReservationDetailView.as_view(), name="detail"),
    path("reservations/<uuid:reservation_id>/edit/", views.ReservationUpdateView.as_view(), name="edit"),
    path(
        "reservations/<uuid:reservation_id>/cancel/",
        views.ReservationCancelView.as_view(),
        name="cancel",
    ),
    path("reservations/<uuid:reservation_id>/invoice/", views.ReservationInvoiceView.as_view(), name="invoice"),
    path("reservations/calendar/", views.ReservationCalendarView.as_view(), name="calendar"),
    path("reservations/history/", views.ReservationHistoryView.as_view(), name="history"),
    path("reservations/search/", views.ReservationSearchView.as_view(), name="search"),
]

