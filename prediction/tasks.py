# apps/prediction/tasks.py
import logging
from apps.prediction.services import OccupancyPredictorService
from apps.iot.services import TelemetryService

logger = logging.getLogger(__name__)

def run_occupancy_prediction_pipeline(room_id: int = 1, capacity: int = 3):
    """
    Pipeline asynchrone : Métriques IoT -> Features Vector -> Inférence ML -> Persistence DB
    """
    try:
        # 1. Extraire les métriques réelles des capteurs depuis la BDD IoT / TimescaleDB
        current_features = TelemetryService.get_latest_room_features(room_id=room_id)
        
        # 2. Exécuter l'inférence ML et enregistrer la prédiction
        predictor = OccupancyPredictorService()
        prediction_obj = predictor.predict_from_features(
            features_dict=current_features, 
            room_id=room_id, 
            capacity=capacity
        )
        
        logger.info(f"Pipeline ML exécuté avec succès : {prediction_obj.predicted_occupants} occupants prévus (ID: {prediction_obj.id}).")
        return prediction_obj

    except Exception as e:
        logger.error(f"Échec de l'exécution du pipeline de prédiction asynchrone : {e}", exc_info=True)
        return None