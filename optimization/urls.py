from django.urls import path
from . import views

app_name = "optimization"

urlpatterns = [
    path("workspace/<int:workspace_id>/", views.optimize_workspace, name="optimize_workspace"),
    path("dashboard/", views.optimization_dashboard, name="dashboard"),
]
