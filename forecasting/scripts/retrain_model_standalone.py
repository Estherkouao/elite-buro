#!/usr/bin/env python3
"""
Réentraîne le modèle forecasting à partir du dataset brut + snapshots DB.
Peut être lancé manuellement ou par cron, sans dépendre de Celery.
"""
from __future__ import annotations

import os
import sys
import logging
from pathlib import Path

import pandas as pd
import joblib
import numpy as np
from sklearn.model_selection import TimeSeriesSplit
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_PATH = BASE_DIR / "data" / "raw" / "coworking_occupancy_dataset.csv"
MODEL_DIR = BASE_DIR / "ml_models"
MODEL_PATH = MODEL_DIR / "forecasting_bundle.joblib"


def retrain():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    sys.path.insert(0, str(BASE_DIR))
    import django
    django.setup()

    from forecasting.models import OccupancySnapshot
    from forecasting.ml_core.train_forecasting_model import build_forecasting_features

    if not DATA_PATH.exists():
        logger.error("Dataset introuvable : %s", DATA_PATH)
        return False

    logger.info("Chargement du dataset : %s", DATA_PATH)
    df = pd.read_csv(DATA_PATH)

    snapshots = OccupancySnapshot.objects.all().select_related("workspace").order_by("timestamp")
    if snapshots.exists():
        rows = []
        for snap in snapshots:
            ws = snap.workspace
            rows.append({
                "timestamp": snap.timestamp,
                "space_name": ws.nom,
                "space_type": snap.space_type,
                "capacity": snap.capacity,
                "occupancy_count": snap.occupancy_count,
                "occupancy_rate": snap.occupancy_rate,
                "is_weekend": 1 if snap.timestamp.weekday() >= 5 else 0,
                "is_holiday": 0,
                "is_raining": 0,
                "temperature_c": 27.0,
                "active_reservations": 0,
                "cancellations_last_24h": 0,
                "wifi_connected_devices": 0,
                "co2_ppm": 400,
                "power_consumption_kwh": 0,
            })
        df_snapshots = pd.DataFrame(rows)
        df = pd.concat([df, df_snapshots], ignore_index=True)
        logger.info("%d snapshots DB ajoutés au dataset", len(rows))

    try:
        df_model, feature_cols = build_forecasting_features(df)
    except Exception as e:
        logger.error("Erreur features : %s", e, exc_info=True)
        return False

    X = df_model[feature_cols]
    y = df_model["occupancy_rate"]

    tscv = TimeSeriesSplit(n_splits=3)
    model = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)

    mae_list, rmse_list, r2_list = [], [], []
    for train_idx, test_idx in tscv.split(X):
        X_tr, X_te = X.iloc[train_idx], X.iloc[test_idx]
        y_tr, y_te = y.iloc[train_idx], y.iloc[test_idx]
        model.fit(X_tr, y_tr)
        preds = model.predict(X_te)
        mae_list.append(mean_absolute_error(y_te, preds))
        rmse_list.append(np.sqrt(mean_squared_error(y_te, preds)))
        if np.var(y_te) > 0:
            r2_list.append(r2_score(y_te, preds))

    logger.info("MAE : %.4f", np.mean(mae_list))
    logger.info("RMSE : %.4f", np.mean(rmse_list))
    logger.info("R² : %.4f", np.mean(r2_list) if r2_list else 0.0)

    model.fit(X, y)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    bundle = {
        "model": model,
        "features": feature_cols,
        "metadata": {
            "model_name": "RandomForest",
            "trained_on": str(DATA_PATH.name),
            "n_rows": int(len(df_model)),
            "cv_results": {
                "mae": round(float(np.mean(mae_list)), 6),
                "rmse": round(float(np.mean(rmse_list)), 6),
                "r2": round(float(np.mean(r2_list)), 6) if r2_list else 0.0,
            },
        },
    }
    joblib.dump(bundle, MODEL_PATH)
    logger.info("[OK] Modèle réentraîné : %s", MODEL_PATH)
    return True


if __name__ == "__main__":
    success = retrain()
    sys.exit(0 if success else 1)
