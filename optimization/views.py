from datetime import datetime, timedelta

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
from django.conf import settings

from coworking.models import Workspace
from forecasting.services import get_forecast
from prediction.models import OccupancyPrediction


def _optimization_decision(workspace: Workspace, rate: float) -> dict:
    capacity = workspace.capacite
    if rate >= 0.85:
        return {
            "status": "SATURATION",
            "action": "Ouvrir espace tampon",
            "recommendation": (
                f"Risque de saturation sur {workspace.nom} ({rate*100:.1f}%). "
                "Basculer un espace adjacent en zone d'accueil de débordement."
            ),
            "energy": "Climatisation à puissance maximale (100%).",
            "pricing": "Arrêter les tarifs horaires, privilégier le forfait journée.",
            "maintenance": "Aucune intervention prévue.",
        }
    if rate <= 0.30:
        return {
            "status": "SOUS_UTILISATION",
            "action": "Optimisation énergétique & Marketing",
            "recommendation": (
                f"Sous-utilisation détectée ({rate*100:.1f}%). "
                "Proposer un Pass Journée à tarif réduit et regrouper les résidents."
            ),
            "energy": "Activer le mode éco sur les climatiseurs des zones inoccupées.",
            "pricing": "Lancer une promotion flash -30% sur les prochaines 2h.",
            "maintenance": "Planifier une intervention préventive dans les 48h.",
        }
    return {
        "status": "OPTIMAL",
        "action": "Rien à signaler",
        "recommendation": f"L'occupation prévisionnelle de {workspace.nom} est équilibrée ({rate*100:.1f}%).",
        "energy": "Régulation standard de la climatisation.",
        "pricing": "Maintenir les tarifs en vigueur.",
        "maintenance": "Aucune intervention prévue.",
    }


def optimize_workspace(request, workspace_id):
    workspace = get_object_or_404(Workspace, pk=workspace_id)
    now = timezone.localtime()

    forecasts = []
    for h in range(8, 18):
        target = now.replace(hour=h, minute=0, second=0, microsecond=0)
        if target < now:
            target += timedelta(days=1)
        result = get_forecast(workspace=workspace, target_dt=target, log=True)
        decision = _optimization_decision(workspace, result["occupancy_rate"])
        forecasts.append({
            "hour": f"{h:02d}:00",
            "target_datetime": target.isoformat(),
            "occupancy_rate": result["occupancy_rate"],
            "occupancy_count_est": result["occupancy_count_est"],
            "category": result["category"],
            "decision": decision,
        })

    latest_predictions = OccupancyPrediction.objects.filter(
        room_id=workspace.id
    ).order_by("-prediction_timestamp")[:10]

    return render(request, "optimization/optimize.html", {
        "workspace": workspace,
        "forecasts": forecasts,
        "latest_predictions": latest_predictions,
    })


def optimization_dashboard(request):
    workspaces = Workspace.objects.filter(disponible=True)
    rows = []
    for ws in workspaces:
        target = timezone.localtime().replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        result = get_forecast(workspace=ws, target_dt=target, log=False)
        decision = _optimization_decision(ws, result["occupancy_rate"])
        rows.append({
            "workspace": ws,
            "target_datetime": target.isoformat(),
            "occupancy_rate": result["occupancy_rate"],
            "occupancy_count_est": result["occupancy_count_est"],
            "category": result["category"],
            "decision": decision,
        })
    rows.sort(key=lambda r: r["occupancy_rate"], reverse=True)
    return render(request, "optimization/dashboard.html", {"rows": rows})
