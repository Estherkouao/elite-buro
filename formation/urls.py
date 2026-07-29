from django.urls import path

from . import views

app_name = "formation"

urlpatterns = [
    path("", views.FormationHomeView.as_view(), name="home"),
    path("catalogue/", views.CatalogueView.as_view(), name="catalogue"),
    path("catalogue-page/", views.CatalogueView.as_view(), name="catalogue_page"),
    path("recherche/", views.SearchView.as_view(), name="search"),
    path("filtres/", views.FiltersView.as_view(), name="filters"),
    path("sessions/", views.SessionsView.as_view(), name="sessions"),
    path("session/<int:session_id>/inscription/", views.SessionRegisterView.as_view(), name="register"),
    path("my-courses/", views.MyCoursesView.as_view(), name="my_courses"),
    path("certificates/", views.MyCertificatesView.as_view(), name="my_certificates"),
    path("quotes/", views.MyQuotesView.as_view(), name="my_quotes"),
    path("contracts/", views.MyContractsView.as_view(), name="my_contracts"),
    path("payments/", views.PaymentView.as_view(), name="payment"),
    path("reviews/", views.ReviewCreateView.as_view(), name="review"),
    path("formateurs/", views.TrainerListView.as_view(), name="trainers"),
    path("formateurs/<int:trainer_id>/", views.TrainerDetailView.as_view(), name="trainer_detail"),
    # ═══════════════════════════════════════════════
    #  INSCRIPTION FORMATION — Nouveau workflow
    #  (Doit être AVANT <slug:slug>/ pour éviter que
    #   "inscription" soit interprété comme un slug)
    # ═══════════════════════════════════════════════
    path("inscription/", views.InscriptionFormationView.as_view(), name="inscription"),
    path("inscription/load-sessions/", views.LoadSessionsView.as_view(), name="load_sessions"),
    path("paiement/<int:inscription_id>/", views.FormationPaymentView.as_view(), name="formation_payment"),
    path("paiement/<int:inscription_id>/process/", views.FormationPaymentProcessView.as_view(), name="formation_payment_process"),

    path("<slug:slug>/", views.FormationDetailView.as_view(), name="detail"),
    # Endpoints backoffice (admin-like) utilisés par actions Django Admin
    path("backoffice/quotes/<int:quote_id>/preview/", views.QuotePreviewView.as_view(), name="quote_preview"),
    path(
        "devis/formation/create/",
        views.devis_formation_create,
        name="devis_formation_create",
    ),
    path(
        "devis/success/",
        views.devis_success,
        name="devis_success"
    ),
    path(
        "devis-formation/<int:pk>/",
        views.DevisFormationDetailView.as_view(),
        name="devis_formation_detail",
    ),
]


