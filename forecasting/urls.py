from django.urls import path
from . import api

app_name = "forecasting"

urlpatterns = [
    path("forecast/<int:workspace_id>/", api.forecast_view, name="forecast"),
    path("forecast/<int:workspace_id>/week/", api.forecast_week_view, name="forecast_week"),
]

# Dans ton urls.py principal :
#   path("api/", include("forecasting.urls")),
