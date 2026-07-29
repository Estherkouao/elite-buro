from django.urls import path

from . import views

app_name = "domiciliation"

urlpatterns = [
    path("", views.index, name="index"),
    path("souscrire/", views.domiciliation_from, name="domiciliation_from"),
    path("individuelle/", views.domiciliation_individuelle, name="domiciliation_individuelle"),
    path("plans/", views.plans, name="plans"),
    path("plans/<slug:slug>/", views.plan_detail, name="plan_detail"),

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


