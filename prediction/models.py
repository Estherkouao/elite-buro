from django.db import models

class OccupancyPrediction(models.Model):
    room_id = models.IntegerField(default=1, help_text="Identifiant de la salle ou zone de coworking")
    prediction_timestamp = models.DateTimeField(auto_now_add=True)
    target_datetime = models.DateTimeField(help_text="Date/Heure cible de la prévision")
    predicted_occupants = models.IntegerField(help_text="Prévision Y : Nombre d'occupants")
    predicted_occupancy_rate = models.FloatField(help_text="Taux d'occupation calculé (%)")
    capacity = models.IntegerField(default=3, help_text="Capacité maximale de l'espace")
    actual_occupants = models.IntegerField(null=True, blank=True, help_text="Valeur réelle observée a posteriori")

    class Meta:
        ordering = ['-prediction_timestamp']

    def __str__(self):
        return f"Zone {self.room_id} | {self.target_datetime} | Prévu: {self.predicted_occupants}/{self.capacity}"