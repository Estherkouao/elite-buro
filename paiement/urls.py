from django.urls import path

from . import views

app_name = "paiement"

urlpatterns = [
    path("", views.indexpaiement, name="index"),
    path("process/", views.process_payment, name="process"),
    path("success/", views.payment_success, name="success"),
    path("cancel/", views.payment_cancel, name="cancel"),
    path("notify/", views.payment_notify, name="notify"),
    path(
        "config/<str:provider_code>/",
        views.provider_config,
        name="provider_config",
    ),
]

