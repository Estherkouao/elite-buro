from django.db import models
from coworking.models import Workspace


class OccupancySnapshot(models.Model):
    """
    Une ligne = l'occupation constatée d'un espace à un instant T.
    Alimentée toutes les 15 min par la commande log_occupancy_snapshot.
    C'est CET historique qui sert à calculer les features de lag
    (occ_lag_1d, occ_lag_1w, occ_rolling_mean_4w_same_slot).

    On garde space_type et capacity dupliqués ici (plutôt que de tout
    recalculer via des jointures) pour que l'historique reste correct
    même si la catégorie ou la capacité du Workspace change plus tard.
    """
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="occupancy_snapshots")
    space_type = models.CharField(max_length=30)  # HotDesk / MeetingRoom / TrainingRoom / PrivateOffice
    capacity = models.PositiveIntegerField()
    timestamp = models.DateTimeField(db_index=True)
    occupancy_count = models.PositiveIntegerField()
    occupancy_rate = models.FloatField()

    class Meta:
        indexes = [models.Index(fields=["workspace", "timestamp"])]
        ordering = ["timestamp"]

    def __str__(self):
        return f"{self.workspace.nom} @ {self.timestamp:%Y-%m-%d %H:%M} = {self.occupancy_rate:.0%}"


class ForecastLog(models.Model):
    """
    Trace chaque prédiction servie : utile pour mesurer la dérive du modèle
    (comparer plus tard occupancy_rate_predicted vs occupancy_rate réel observé).
    """
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="forecast_logs")
    target_datetime = models.DateTimeField(db_index=True)
    occupancy_rate_predicted = models.FloatField()
    category_predicted = models.CharField(max_length=20)
    model_version = models.CharField(max_length=50, default="random_forest_v1")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Prévision {self.workspace.nom} @ {self.target_datetime:%Y-%m-%d %H:%M} = {self.occupancy_rate_predicted:.0%}"
