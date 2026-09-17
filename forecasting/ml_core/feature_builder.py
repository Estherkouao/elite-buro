"""
Construction des features pour une prédiction future (forecasting).
Aucune dépendance Django ici : facile à tester isolément.

Entrée attendue pour `history` : liste de tuples (timestamp: datetime, occupancy_rate: float)
triés par timestamp croissant, pour UN espace donné, la plus longue possible
(idéalement >= 4 semaines avant la date cible).
"""
from __future__ import annotations
from datetime import datetime, timedelta
from math import sin, cos, pi
from statistics import mean

SPACE_TYPES = ["HotDesk", "MeetingRoom", "TrainingRoom", "PrivateOffice"]


def _closest_rate(history: list[tuple[datetime, float]], target: datetime, tolerance_minutes: int = 20) -> float | None:
    """Retourne le taux d'occupation connu le plus proche de `target` (dans une tolérance)."""
    best = None
    best_diff = None
    for ts, rate in history:
        diff = abs((ts - target).total_seconds())
        if diff <= tolerance_minutes * 60 and (best_diff is None or diff < best_diff):
            best, best_diff = rate, diff
    return best


def build_features(
    target_dt: datetime,
    capacity: int,
    space_type: str,
    history: list[tuple[datetime, float]],
    is_holiday: bool = False,
    is_raining: bool = False,
    temperature_c: float = 27.0,
) -> dict:
    """
    Construit le vecteur de features EXACTEMENT dans l'ordre/nommage utilisé
    à l'entraînement (voir 01_explore_and_prepare.py / 02_train_models.py).
    """
    hour = target_dt.hour + target_dt.minute / 60
    dow = target_dt.weekday()  # 0=lundi ... 6=dimanche (aligner avec day_of_week du dataset si besoin)
    month = target_dt.month
    is_weekend = 1 if dow >= 5 else 0

    # --- Lags : occupation passée (mêmes règles que l'entraînement) ---
    lag_1d = _closest_rate(history, target_dt - timedelta(days=1))
    lag_1w = _closest_rate(history, target_dt - timedelta(weeks=1))

    # Moyenne des 4 dernières occurrences du même créneau (jour de semaine + heure)
    same_slot_rates = [
        rate for ts, rate in history
        if ts.weekday() == dow and abs((ts.hour * 60 + ts.minute) - (target_dt.hour * 60 + target_dt.minute)) <= 10
        and ts < target_dt
    ]
    rolling_mean = mean(same_slot_rates[-4:]) if same_slot_rates else (lag_1w if lag_1w is not None else 0.3)

    # Fallback si pas assez d'historique (nouveau site, cold start)
    if lag_1d is None:
        lag_1d = rolling_mean
    if lag_1w is None:
        lag_1w = rolling_mean

    features = {
        "capacity": capacity,
        "is_weekend": is_weekend,
        "is_holiday": int(is_holiday),
        "is_raining": int(is_raining),
        "temperature_c": temperature_c,
        "hour_sin": sin(2 * pi * hour / 24),
        "hour_cos": cos(2 * pi * hour / 24),
        "dow_sin": sin(2 * pi * dow / 7),
        "dow_cos": cos(2 * pi * dow / 7),
        "month_sin": sin(2 * pi * month / 12),
        "month_cos": cos(2 * pi * month / 12),
        "occ_lag_1d": lag_1d,
        "occ_lag_1w": lag_1w,
        "occ_rolling_mean_4w_same_slot": rolling_mean,
    }
    for t in SPACE_TYPES:
        features[f"type_{t}"] = 1 if space_type == t else 0

    return features
