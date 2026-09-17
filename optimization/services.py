class SpaceOptimizationEngine:
    """
    Moteur de règles de Recherche Opérationnelle et d'Optimisation Décisionnelle.
    Transforme l'inférence ML (Ŷ) en décisions métiers d'allocation et de régulation énergétique.
    """

    @staticmethod
    def generate_recommendations(prediction_obj) -> dict:
        occupancy_rate = prediction_obj.predicted_occupancy_rate
        occupants = prediction_obj.predicted_occupants
        capacity = prediction_obj.capacity

        if occupancy_rate >= 80.0:
            return {
                'zone_status': 'Saturation Proche',
                'alert_level': 'DANGER',
                'allocation_action': 'Ouverture de Zone Secondaire',
                'hvac_status': 'Climatisation / Ventilation Maximum (100%)',
                'message': f"L'occupation prévue ({occupants}/{capacity} postes) dépasse le seuil critique (80%). Activer la zone de débordement et maximiser la ventilation CO2."
            }
        elif occupancy_rate <= 20.0:
            return {
                'zone_status': 'Sous-Occupation Sévere',
                'alert_level': 'SUCCESS',
                'allocation_action': 'Regroupement d\'Espace & Eco-Mode',
                'hvac_status': 'Mode Éco / Veille Thermique (30%)',
                'message': f"Occupation faible prévue ({occupants}/{capacity} postes). Rediriger les réservations vers la Zone A et passer cette zone en veille énergétique."
            }
        else:
            return {
                'zone_status': 'Nominal / Optimal',
                'alert_level': 'INFO',
                'allocation_action': 'Maintien de la Configuration',
                'hvac_status': 'Régulation Énergétique Standard (60%)',
                'message': f"Taux d'occupation équilibré ({occupants}/{capacity} postes, {occupancy_rate}%). Aucune réallocation requise."
            }