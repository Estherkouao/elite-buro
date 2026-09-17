from datetime import datetime, timedelta
from pathlib import Path
from django.conf import settings
from django.utils import timezone

from coworking.models import Workspace
from .models import OccupancySnapshot, ForecastLog
from .ml_core.predictor import predict_occupancy
from .type_mapping import get_space_type_for_workspace

MODEL_PATH = str(Path(settings.BASE_DIR) / "ml_models" / "forecasting_bundle.joblib")


def get_forecast(workspace: Workspace, target_dt: datetime,
                  is_holiday: bool = False, is_raining: bool = False,
                  temperature_c: float = 27.0, log: bool = True) -> dict:
    """
    Point d'entree unique utilise par les vues API et les templates.
    """
    since = target_dt - timedelta(weeks=5)
    snapshots = (
        OccupancySnapshot.objects
        .filter(workspace=workspace, timestamp__gte=since, timestamp__lt=timezone.now())
        .values_list("timestamp", "occupancy_rate")
    )
    history = list(snapshots)
    space_type = get_space_type_for_workspace(workspace)

    result = predict_occupancy(
        model_path=MODEL_PATH,
        target_dt=target_dt,
        capacity=workspace.capacite,
        space_type=space_type,
        history=history,
        is_holiday=is_holiday,
        is_raining=is_raining,
        temperature_c=temperature_c,
    )
    result["workspace_id"] = workspace.id
    result["workspace_name"] = workspace.nom

    if log:
        ForecastLog.objects.create(
            workspace=workspace,
            target_datetime=target_dt,
            occupancy_rate_predicted=result["occupancy_rate"],
            category_predicted=result["category"],
        )

    return result


def get_week_forecast(workspace: Workspace, days: int = 7) -> list[dict]:
    """Prevision heure par heure (creneaux ouvres 8h-18h) sur N jours - dashboard staff."""
    now = timezone.localtime()
    results = []
    for d in range(days):
        day = now + timedelta(days=d)
        for hour in range(8, 18):
            target = day.replace(hour=hour, minute=0, second=0, microsecond=0)
            results.append(get_forecast(workspace, target, log=False))
    return results
