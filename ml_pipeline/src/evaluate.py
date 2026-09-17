import pandas as pd
import numpy as np
import os

def process_occupancy_data(raw_data_path: str, output_data_path: str) -> pd.DataFrame:
    """
    Nettoie et rééchantillonne le dataset Kaggle Room Occupancy Estimation.
    Génère les caractéristiques temporelles et les lags pour la prévision.
    """
    if not os.path.exists(raw_data_path):
        raise FileNotFoundError(f"Le fichier brut est introuvable : {raw_data_path}")

    # 1. Chargement et fusion des colonnes de date/heure
    df = pd.read_csv(raw_data_path)
    df['Datetime'] = pd.to_datetime(df['Date'] + ' ' + df['Time'])
    df = df.set_index('Datetime')
    df = df.drop(columns=['Date', 'Time'])

    # 2. Aggrégations temporelles (Pas de 15 minutes)
    # Capteurs IoT -> Moyenne | Cible Room_Occupancy_Count -> Valeur maximale
    resample_rules = {col: 'mean' for col in df.columns if col != 'Room_Occupancy_Count'}
    resample_rules['Room_Occupancy_Count'] = 'max'
    
    df_15m = df.resample('15min').agg(resample_rules).dropna()
    df_15m['Room_Occupancy_Count'] = df_15m['Room_Occupancy_Count'].round().astype(int)

    # 3. Feature Engineering Temporel
    df_15m['hour'] = df_15m.index.hour
    df_15m['dayofweek'] = df_15m.index.dayofweek
    df_15m['is_weekend'] = (df_15m['dayofweek'] >= 5).astype(int)

    # 4. Lags (Variables décalées pour séries temporelles)
    # 4 pas de 15 min = 1h | 8 pas = 2h | 96 pas = 24h
    df_15m['occupancy_lag_1h'] = df_15m['Room_Occupancy_Count'].shift(4)
    df_15m['occupancy_lag_2h'] = df_15m['Room_Occupancy_Count'].shift(8)
    df_15m['occupancy_lag_24h'] = df_15m['Room_Occupancy_Count'].shift(96)

    # Moyenne mobile de l'occupation sur 2h
    df_15m['occupancy_rolling_mean_2h'] = (
        df_15m['Room_Occupancy_Count'].shift(1).rolling(window=8).mean()
    )

    # Nettoyage des valeurs nuls générées par les lags
    df_processed = df_15m.dropna().copy()

    # Sauvegarde du fichier transformé
    os.makedirs(os.path.dirname(output_data_path), exist_ok=True)
    df_processed.to_csv(output_data_path)
    print(f"[SUCCÈS] Données prétraitées sauvegardées dans : {output_data_path}")
    
    return df_processed

if __name__ == "__main__":
    RAW_PATH = "ml_pipeline/data/raw/Occupancy_Estimation.csv"
    PROCESSED_PATH = "ml_pipeline/data/processed/occupancy_15min_features.csv"
    
    try:
        data = process_occupancy_data(RAW_PATH, PROCESSED_PATH)
        print(f"Dimensions de la matrice finale : {data.shape}")
    except Exception as e:
        print(f"[ERREUR] {e}")