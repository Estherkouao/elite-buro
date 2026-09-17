"""
Entraîne le modèle de prévision d'occupation sur le dataset enrichi
du coworking Elite Buro et sauvegarde un bundle joblib compatible
avec forecasting/ml_core/predictor.py.

Usage :
    python forecasting/ml_core/train_forecasting_model.py
"""
from __future__ import annotations

import os
import sys
import joblib
import logging
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_PATH = BASE_DIR / "data" / "raw" / "coworking_occupancy_dataset.csv"
MODEL_DIR = BASE_DIR / "ml_models"
MODEL_PATH = MODEL_DIR / "forecasting_bundle.joblib"


def build_forecasting_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Construit les features identiques à forecasting/ml_core/feature_builder.py
    pour l'ensemble du dataset.
    """
    SPACE_TYPES = ["HotDesk", "MeetingRoom", "TrainingRoom", "PrivateOffice"]

    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    # Rééchantillonnage à 1h pour réduire la taille et accélérer l'entraînement
    df = (
        df.set_index("timestamp")
        .groupby("space_name")
        .resample("1h")
        .agg({
            "capacity": "last",
            "space_type": "last",
            "is_weekend": "last",
            "is_holiday": "last",
            "is_raining": "last",
            "temperature_c": "mean",
            "occupancy_count": "max",
            "active_reservations": "mean",
            "cancellations_last_24h": "sum",
            "wifi_connected_devices": "mean",
            "co2_ppm": "mean",
            "power_consumption_kwh": "sum",
        })
        .dropna(subset=["space_type"])
        .reset_index()
    )
    df["occupancy_rate"] = (df["occupancy_count"] / df["capacity"]).clip(0, 1)

    df["hour"] = df["timestamp"].dt.hour + df["timestamp"].dt.minute / 60.0
    df["dow"] = df["timestamp"].dt.weekday
    df["month"] = df["timestamp"].dt.month
    df["is_weekend"] = (df["dow"] >= 5).astype(int)

    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)
    df["dow_sin"] = np.sin(2 * np.pi * df["dow"] / 7)
    df["dow_cos"] = np.cos(2 * np.pi * df["dow"] / 7)
    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)

    # Lags par espace
    df["occ_lag_1d"] = np.nan
    df["occ_lag_1w"] = np.nan
    df["occ_rolling_mean_4w_same_slot"] = np.nan

    rows = []
    for space_name, gdf in df.groupby("space_name", sort=False):
        gdf = gdf.sort_values("timestamp").set_index("timestamp")
        gdf["occ_lag_1d"] = gdf["occupancy_rate"].shift(1, freq="D")
        gdf["occ_lag_1w"] = gdf["occupancy_rate"].shift(7, freq="D")
        gdf = gdf.reset_index()

        # Rolling mean sur 4 occurrences du même créneau (jour + heure)
        gdf["slot_key"] = gdf["timestamp"].dt.weekday * 24 + gdf["timestamp"].dt.hour
        slot_buf: dict[int, list[float]] = {}
        rolling_vals = []
        for _, row in gdf.iterrows():
            sk = int(row["slot_key"])
            slot_buf.setdefault(sk, [])
            buf = slot_buf[sk][-4:]
            val = float(np.mean(buf)) if buf else 0.3
            rolling_vals.append(val)
            slot_buf[sk].append(float(row["occupancy_rate"]))
        gdf["occ_rolling_mean_4w_same_slot"] = rolling_vals

        gdf["occ_lag_1d"] = gdf["occ_lag_1d"].fillna(gdf["occ_rolling_mean_4w_same_slot"])
        gdf["occ_lag_1w"] = gdf["occ_lag_1w"].fillna(gdf["occ_rolling_mean_4w_same_slot"])

        rows.append(gdf)

    df = pd.concat(rows, ignore_index=True)

    for t in SPACE_TYPES:
        df[f"type_{t}"] = (df["space_type"] == t).astype(int)

    feature_cols = [
        "capacity",
        "is_weekend",
        "is_holiday",
        "is_raining",
        "temperature_c",
        "hour_sin",
        "hour_cos",
        "dow_sin",
        "dow_cos",
        "month_sin",
        "month_cos",
        "occ_lag_1d",
        "occ_lag_1w",
        "occ_rolling_mean_4w_same_slot",
        "type_HotDesk",
        "type_MeetingRoom",
        "type_PrivateOffice",
        "type_TrainingRoom",
    ]
    target_col = "occupancy_rate"

    df_model = df[feature_cols + [target_col]].dropna().copy()
    logger.info("Dataset modèle prêt : %d lignes, %d features", len(df_model), len(feature_cols))
    return df_model, feature_cols


def train_and_save():
    if not DATA_PATH.exists():
        logger.error("Dataset introuvable : %s", DATA_PATH)
        sys.exit(1)

    logger.info("Chargement du dataset : %s", DATA_PATH)
    df = pd.read_csv(DATA_PATH)
    df_model, feature_cols = build_forecasting_features(df)

    X = df_model[feature_cols]
    y = df_model["occupancy_rate"]

    tscv = TimeSeriesSplit(n_splits=3)
    models = {
        "LinearRegression": LinearRegression(),
        "RandomForest": RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1),
        "GradientBoosting": GradientBoostingRegressor(n_estimators=100, max_depth=5, random_state=42),
        "XGBoost": XGBRegressor(n_estimators=100, learning_rate=0.1, max_depth=6, random_state=42, n_jobs=-1),
    }

    cv_results = []
    for name, model in models.items():
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
        cv_results.append({
            "model": name,
            "mae": round(float(np.mean(mae_list)), 6),
            "rmse": round(float(np.mean(rmse_list)), 6),
            "r2": round(float(np.mean(r2_list)), 6) if r2_list else 0.0,
        })

    results_df = pd.DataFrame(cv_results).sort_values("rmse")
    logger.info("=== Résultats Cross-Validation ===")
    logger.info("\n%s", results_df.to_string(index=False))

    best_name = results_df.iloc[0]["model"]
    best_model = models[best_name]
    best_model.fit(X, y)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    bundle = {
        "model": best_model,
        "features": feature_cols,
        "metadata": {
            "model_name": best_name,
            "trained_on": str(DATA_PATH.name),
            "n_rows": int(len(df_model)),
            "cv_results": cv_results,
        },
    }
    joblib.dump(bundle, MODEL_PATH)
    logger.info("[OK] Bundle sauvegardé : %s", MODEL_PATH)


if __name__ == "__main__":
    train_and_save()
