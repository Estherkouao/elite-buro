"""
Chargement du modèle et prédiction. Singleton pour éviter de recharger
le .pkl à chaque appel (coûteux).
"""
from __future__ import annotations
import os
from datetime import datetime
from pathlib import Path
import joblib
import pandas as pd

from .feature_builder import build_features

_MODEL_CACHE = {}


def _load_bundle(model_path: str):
    if model_path in _MODEL_CACHE:
        return _MODEL_CACHE[model_path]

    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Modèle introuvable : {model_path}")

    obj = joblib.load(model_path)

    if isinstance(obj, dict) and "model" in obj and "features" in obj:
        _MODEL_CACHE[model_path] = obj
        return obj

    features_path = model_path.replace(".joblib", "_features.joblib")
    if not os.path.exists(features_path):
        raise FileNotFoundError(
            f"Fichier de features introuvable : {features_path}. "
            "Le modèle doit être sauvegardé en format bundle (model + features)."
        )
    features = joblib.load(features_path)
    bundle = {"model": obj, "features": features}
    _MODEL_CACHE[model_path] = bundle
    return bundle


def _category_from_rate(rate: float) -> str:
    if rate < 0.34:
        return "Faible"
    if rate < 0.67:
        return "Moyenne"
    return "Forte"


def predict_occupancy(
    model_path: str,
    target_dt: datetime,
    capacity: int,
    space_type: str,
    history: list[tuple[datetime, float]],
    is_holiday: bool = False,
    is_raining: bool = False,
    temperature_c: float = 27.0,
) -> dict:
    """
    Retourne : {"occupancy_rate": float, "category": str, "occupancy_count_est": int}
    """
    bundle = _load_bundle(model_path)
    model, feature_order = bundle["model"], bundle["features"]

    feats = build_features(
        target_dt=target_dt, capacity=capacity, space_type=space_type,
        history=history, is_holiday=is_holiday, is_raining=is_raining,
        temperature_c=temperature_c,
    )
    row = pd.DataFrame([[feats[f] for f in feature_order]], columns=feature_order)

    raw_pred = float(model.predict(row)[0])
    rate = min(max(raw_pred, 0.0), 1.0)  # clip [0, 1]

    return {
        "target_datetime": target_dt.isoformat(),
        "space_type": space_type,
        "occupancy_rate": round(rate, 4),
        "occupancy_count_est": round(rate * capacity),
        "category": _category_from_rate(rate),
    }
