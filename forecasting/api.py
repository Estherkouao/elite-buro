from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response

from coworking.models import Workspace
from .services import get_forecast, get_week_forecast

ALERT_THRESHOLD = 0.85  # au-dela de 85% d'occupation prevue -> alerte


@api_view(["GET"])
def forecast_view(request, workspace_id: int):
    """
    GET /api/forecast/<workspace_id>/?datetime=2026-08-20T14:00:00
    Utilise cote PUBLIC pour afficher le badge previsionnel sur la carte espace.
    """
    workspace = get_object_or_404(Workspace, pk=workspace_id)

    dt_param = request.GET.get("datetime")
    target_dt = parse_datetime(dt_param) if dt_param else timezone.now()
    if target_dt is None:
        return Response({"error": "Format datetime invalide (ISO 8601 attendu)"}, status=400)
    if timezone.is_naive(target_dt):
        target_dt = timezone.make_aware(target_dt)

    result = get_forecast(workspace=workspace, target_dt=target_dt)
    return Response(result)


@api_view(["GET"])
def forecast_week_view(request, workspace_id: int):
    """
    GET /api/forecast/<workspace_id>/week/
    Utilise cote STAFF (dashboard interne) pour la courbe 7 jours.
    """
    workspace = get_object_or_404(Workspace, pk=workspace_id)
    results = get_week_forecast(workspace=workspace)
    return Response({"workspace_id": workspace.id, "workspace_name": workspace.nom, "forecast": results})


@api_view(["GET"])
def forecast_alerts_view(request):
    """
    GET /api/forecast/alerts/
    Scanne tous les espaces disponibles sur les 3 prochains jours et
    remonte les creneaux a forte affluence prevue (> 85%). Utilise par
    le panneau d'alertes du dashboard staff.
    """
    alerts = []
    for workspace in Workspace.objects.filter(disponible=True):
        slots = get_week_forecast(workspace=workspace, days=3)
        for slot in slots:
            if slot["occupancy_rate"] >= ALERT_THRESHOLD:
                alerts.append({
                    "workspace_id": workspace.id,
                    "workspace_name": workspace.nom,
                    "target_datetime": slot["target_datetime"],
                    "occupancy_rate": slot["occupancy_rate"],
                    "category": slot["category"],
                })
    alerts.sort(key=lambda a: a["target_datetime"])
    return Response({"threshold": ALERT_THRESHOLD, "count": len(alerts), "alerts": alerts})