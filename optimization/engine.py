# optimization/engine.py
from dataclasses import dataclass
from typing import Dict, Any
from prediction.models import OccupancyPrediction


@dataclass
class OptimizationDecision:
    """
    Structure de données représentant la décision calculée par le moteur d'optimisation.
    """
    prediction: OccupancyPrediction
    hvac_status: str           # ex: "ÉCONOMIE", "CONFORT_STANDARD", "VENTILATION_MAX"
    target_temperature: float   # Consigne thermostat en °C
    space_recommendation: str   # Action recommandée sur l'espace
    alert_level: str            # "NORMAL", "ATTENTION", "CRITIQUE"
    kpi_impact: Dict[str, Any]  # Estimation de l'impact sur les KPI métiers
    zone_status: str = "Nominal / Optimal"
    allocation_action: str = ""


class SpaceOptimizationEngine:
    """
    Moteur de décision opérationnelle.
    Transforme les prévisions ML (ex: taux d'occupation à t+15min)
    en actions concrètes d'optimisation des espaces et de la consommation énergétique.
    """

    @staticmethod
    def evaluate(prediction: OccupancyPrediction) -> OptimizationDecision:
        """
        Évalue la prédiction courante et retourne la décision d'optimisation.
        
        Args:
            prediction (OccupancyPrediction): Instance contenant le taux d'occupation prédit.
            
        Returns:
            OptimizationDecision: Décisions opérationnelles et consignes d'équipements.
        """
        rate = prediction.predicted_occupancy_rate

        # Stratégie 1 : Sous-utilisation (< 20%) -> Réduction des coûts énergétiques
        if rate < 20.0:
            hvac = "ÉCONOMIE"
            temp = 25.0  # Consigne d'économie en zone tropicale (Abidjan)
            reco = "Sous-utilisation détectée. Regrouper les utilisateurs en zone principale et fermer les annexes."
            alert = "NORMAL"
            kpi_impact = {"energy_saving_est": "15-20%", "space_efficiency": "Faible"}

        # Stratégie 2 : Occupation Nominale (20% à 80%) -> Confort et stabilité
        elif 20.0 <= rate <= 80.0:
            hvac = "CONFORT_STANDARD"
            temp = 22.0
            reco = "Taux d'occupation optimal. Maintenir la configuration actuelle des espaces."
            alert = "NORMAL"
            kpi_impact = {"energy_saving_est": "0%", "space_efficiency": "Optimale"}

        # Stratégie 3 : Forte Occupation / Risque de Saturation (> 80%) -> Prévention des conflits
        else:
            hvac = "VENTILATION_MAX"
            temp = 20.0
            reco = "Risque de saturation imminente. Ouvrir la salle de débordement B2 et réguler la ventilation."
            alert = "ATTENTION" if rate <= 95.0 else "CRITIQUE"
            kpi_impact = {"energy_saving_est": "-10%", "space_efficiency": "Saturée"}

        return OptimizationDecision(
            prediction=prediction,
            hvac_status=hvac,
            target_temperature=temp,
            space_recommendation=reco,
            alert_level=alert,
            kpi_impact=kpi_impact,
            zone_status=("Saturation Proche" if rate > 80 else "Sous-Occupation Sévere" if rate < 20 else "Nominal / Optimal"),
            allocation_action=reco,
        )