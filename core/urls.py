from django.urls import path
from django.views.generic import TemplateView

from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),

    # Contact
    path("contact/", views.contact, name="contact"),

    # Devis formation
    path("demande-devis-formation/", views.devis_formation, name="devis_formation"),

    # Pages institutionnelles
    path("a-propos/", TemplateView.as_view(template_name="core/a_propos.html"), name="a_propos"),
    path("faq/", TemplateView.as_view(template_name="core/faq.html"), name="faq"),
    path(
        "mentions-legales/",
        TemplateView.as_view(template_name="core/mentions_legales.html"),
        name="mentions_legales",
    ),
    path(
        "politique-confidentialite/",
        TemplateView.as_view(template_name="core/politique_confidentialite.html"),
        name="politique_confidentialite",
    ),
    path(
        "conditions-utilisation/",
        TemplateView.as_view(template_name="core/conditions_utilisation.html"),
        name="conditions_utilisation",
    ),
]
