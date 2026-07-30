from django.urls import path

from . import views
from .views import CreationEntrepriseView

app_name = "domiciliation"

urlpatterns = [
    path("", views.index, name="index"),
    path("souscrire/", views.domiciliation_from, name="domiciliation_from"),
    path("individuelle/", views.domiciliation_individuelle, name="domiciliation_individuelle"),
    path("plans/", views.plans, name="plans"),
    path("plans/<slug:slug>/", views.plan_detail, name="plan_detail"),
    path(
        "creation-entreprise/",
        CreationEntrepriseView.as_view(),
        name="creation_entreprise"
    ),
    path(
        "creation-sarl/",
        views.creation_sarl,
        name="creation_sarl"
    ),
    path(
        "creation-sarlu/",
        views.creation_sarlu,
        name="creation_sarlu"
    ),
    path(
        "creation-sas/",
        views.creation_sas,
        name="creation_sas"
    ),
    path(
        "creation-sasu/",
        views.creation_sasu,
        name="creation_sasu"
    ),
    path(
        "creation-ong/",
        views.creation_ong,
        name="creation_ong"
    ),
    path(
        "creation-startup/",
        views.creation_startup,
        name="creation_startup"
    ),
    path(
        "creation-sci/",
        views.creation_sci,
        name="creation_sci"
    ),
    path(
        "creation-association/",
        views.creation_association,
        name="creation_association"
    ),
    path(
        "creation-fondation/",
        views.creation_fondation,
        name="creation_fondation"
    ),
    path(
        "creation-scoop/",
        views.creation_scoop,
        name="creation_scoop"
    ),


    path("request/", views.new_request, name="new_request"),
    path("history/", views.history_list, name="history_list"),
    path("<uuid:uuid>/", views.request_detail, name="request_detail"),
    path("<uuid:uuid>/edit/", views.request_edit, name="request_edit"),
    path("<uuid:uuid>/documents/", views.upload_documents, name="documents"),
    path("<uuid:uuid>/contract/", views.contract_view, name="contract"),
    path("<uuid:uuid>/contract/download/", views.contract_download, name="contract_download"),

    path("<uuid:uuid>/history/", views.history, name="history"),
    path("<uuid:uuid>/renew/", views.renew, name="renew"),

]


