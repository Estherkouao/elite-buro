from django.urls import path
from django.views.generic import TemplateView

app_name = "notification"

urlpatterns = [
    path("", TemplateView.as_view(template_name="notification/index.html"), name="index"),
]

