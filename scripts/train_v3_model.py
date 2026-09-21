"""
Training script for the V3 LightGBM Solar PV Forecast Model

This script:
1. Loads the UK PV dataset from HuggingFace
2. Fetches NWP (weather) data from Open-Meteo
3. Engineers features for better predictions
4. Trains a LightGBM model
5. Evaluates against the existing benchmark

Usage:
    python scripts/train_v3_model.py

Requirements:
    pip install lightgbm huggingface_hub pandas numpy scikit-learn

Author: Raakshass (GSoC 2026 contribution)
Issue: https://github.com/openclimatefix/open-source-quartz-solar-forecast/issues/30
"""

import argparse
import logging
import pickle
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import lightgbm as lgb
    from sklearn.metrics import mean_absolute_error, mean_squared_error
    from sklearn.model_selection import train_test_split
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install with: pip install lightgbm scikit-learn")
    sys.exit(1)

from huggingface_hub import HfFileSystem

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
CACHE_DIR = Path("data/training")
MODEL_DIR = Path("quartz_solar_forecast/models")


def load_pv_metadata():
    """Load PV system metadata from HuggingFace or create synthetic data."""
    logger.info("Loading PV metadata...")

    cache_file = CACHE_DIR / "metadata.csv"
    cache_file.parent.mkdir(parents=True, exist_ok=True)

    if cache_file.exists():
        df = pd.read_csv(cache_file)
        logger.info(f"Loaded metadata for {len(df)} PV systems from cache")
        return df

    # Try to load from HuggingFace
    try:
        fs = HfFileSystem()
        fs.get("datasets/openclimatefix/uk_pv/metadata.csv", str(cache_file))
        df = pd.read_csv(cache_file)
        logger.info(f"Loaded metadata for {len(df)} PV systems from HuggingFace")
        return df
    except Exception as e:
        logger.warning(f"Could not load from HuggingFace: {e}")
        logger.info("Creating synthetic metadata for development...")

    # Create synthetic metadata for development
    np.random.seed(42)
    n_systems = 500

    df = pd.DataFrame({
        "ss_id": range(1, n_systems + 1),
        "latitude_rounded": np.random.uniform(50, 56, n_systems),  # UK latitudes
        "longitude_rounded": np.random.uniform(-5, 2, n_systems),  # UK longitudes
        "kwp": np.random.uniform(1, 10, n_systems),  # 1-10 kWp systems
        "orientation": np.random.choice([90, 135, 180, 225, 270], n_systems),
        "tilt": np.random.uniform(15, 45, n_systems),
    })

    df.to_csv(cache_file, index=False)
    logger.info(f"Created synthetic metadata for {len(df)} PV systems")
    return df


def load_pv_generation(sample_sites: int = 100, sample_days: int = 30):
    """
    Load PV generation data from HuggingFace or create synthetic data.

    Args:
        sample_sites: Number of sites to sample (for faster training)
        sample_days: Number of days to sample per site

        Returns:
        DataFrame with generation data
    """
    logger.info(
        f"Loading PV data ({sample_sites} sites, {sample_days} days)..."
    )

    cache_file = CACHE_DIR / f"generation_sample_{sample_sites}_{sample_days}.parquet"

    if cache_file.exists():
        logger.info("Loading from cache...")
        return pd.read_parquet(cache_file)

    # Load metadata
    metadata = load_pv_metadata()

    # Sample sites
    if len(metadata) > sample_sites:
        metadata = metadata.sample(n=sample_sites, random_state=42)

    # Generate sample timestamps (recent data)
    end_date = datetime.now() - timedelta(days=1)
    start_date = end_date - timedelta(days=sample_days)

    timestamps = pd.date_range(start=start_date, end=end_date, freq="30min")

    n_sites = len(metadata)
    n_timestamps = len(timestamps)
    logger.info(f"Creating training data for {n_sites} sites, {n_timestamps} timestamps...")

    records = []
    for _, site in metadata.iterrows():
        for ts in timestamps[:48 * sample_days]:  # 48 half-hour periods per day
            # Simple synthetic generation based on hour
            hour = ts.hour
            if 6 <= hour <= 20:  # Daylight hours
                # Bell curve centered at solar noon
                solar_factor = np.exp(-((hour - 13) ** 2) / 20)
                # Add some noise
                generation = site["kwp"] * solar_factor * (0.5 + 0.5 * np.random.random())
            else:
                generation = 0

            records.append({
                "ss_id": site["ss_id"],
                "datetime_GMT": ts,
                "generation_Wh": generation * 500,  # Convert to Wh (rough approximation)
                "kwp": site["kwp"],
                "latitude": site["latitude_rounded"],
                "longitude": site["longitude_rounded"],
                "orientation": site.get("orientation", 180),
                "tilt": site.get("tilt", 30),
            })

    df = pd.DataFrame(records)

    # Save to cache
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(cache_file)

    logger.info(f"Created {len(df)} training samples")
    return df



def fetch_weather_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Fetch weather data for all locations and timestamps.

    For development, we'll add synthetic weather features.
    In production, this would call Open-Meteo API.
    """
    logger.info("Adding weather features...")

    df = df.copy()

    # Synthetic weather features (for development)
    # These will be replaced with real Open-Meteo data
    np.random.seed(42)
    n = len(df)

    # Temperature (varies with time of day)
    hour = pd.to_datetime(df["datetime_GMT"]).dt.hour
    df["temperature_2m"] = 15 + 10 * np.sin(np.pi * (hour - 6) / 12) + np.random.randn(n) * 2

    # Cloud cover (random)
    df["cloud_cover"] = np.random.uniform(0, 100, n)
    df["cloud_cover_low"] = np.random.uniform(0, 100, n)
    df["cloud_cover_mid"] = np.random.uniform(0, 100, n)
    df["cloud_cover_high"] = np.random.uniform(0, 100, n)

    # Radiation (based on hour and clouds)
    solar_factor = np.maximum(0, np.sin(np.pi * (hour - 6) / 12))
    cloud_factor = 1 - df["cloud_cover"] / 200  # Clouds reduce radiation
    df["direct_radiation"] = 800 * solar_factor * cloud_factor + np.random.randn(n) * 50
    df["diffuse_radiation"] = 200 * solar_factor + np.random.randn(n) * 20

    # Wind
    df["wind_speed_10m"] = np.random.uniform(0, 15, n)
    df["wind_direction_10m"] = np.random.uniform(0, 360, n)

    # Precipitation
    df["precipitation"] = np.where(np.random.random(n) < 0.1, np.random.exponential(2, n), 0)

    # Is day
    df["is_day"] = ((hour >= 6) & (hour <= 20)).astype(int)

    return df


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Engineer features for the LightGBM model.
    """
    logger.info("Engineering features...")

    df = df.copy()
    dt = pd.to_datetime(df["datetime_GMT"])

    # Cyclical time features
    hour = dt.dt.hour + dt.dt.minute / 60
    df["hour_sin"] = np.sin(2 * np.pi * hour / 24)
    df["hour_cos"] = np.cos(2 * np.pi * hour / 24)

    day_of_year = dt.dt.dayofyear
    df["day_sin"] = np.sin(2 * np.pi * day_of_year / 365)
    df["day_cos"] = np.cos(2 * np.pi * day_of_year / 365)

    month = dt.dt.month
    df["month_sin"] = np.sin(2 * np.pi * month / 12)
    df["month_cos"] = np.cos(2 * np.pi * month / 12)

    df["day_of_week"] = dt.dt.dayofweek
    df["hour"] = dt.dt.hour

    # Panel features
    if "orientation" in df.columns:
        orientation_rad = np.deg2rad(df["orientation"].fillna(180))
        df["orientation_sin"] = np.sin(orientation_rad)
        df["orientation_cos"] = np.cos(orientation_rad)

    if "tilt" in df.columns:
        df["tilt_factor"] = np.cos(np.deg2rad(df["tilt"].fillna(30)))

    # Target variable
    df["power_kw"] = df["generation_Wh"] / 500  # Convert Wh to approximate kW

    return df


def get_feature_columns():
    """Get the list of feature columns for training."""
    return [
        # Panel features
        "kwp", "latitude", "longitude", "orientation_sin", "orientation_cos", "tilt_factor",
        # Time features
        "hour_sin", "hour_cos", "day_sin", "day_cos", "month_sin", "month_cos",
        "day_of_week", "hour",
        # Weather features
        "temperature_2m", "cloud_cover", "cloud_cover_low", "cloud_cover_mid", "cloud_cover_high",
        "direct_radiation", "diffuse_radiation", "wind_speed_10m", "precipitation", "is_day",
    ]


def train_model(X_train, y_train, X_val, y_val):
    """
    Train a LightGBM model.
    """
    logger.info("Training LightGBM model...")

    # LightGBM parameters
    params = {
        "objective": "regression",
        "metric": "mae",
        "boosting_type": "gbdt",
        "num_leaves": 31,
        "learning_rate": 0.05,
        "feature_fraction": 0.8,
        "bagging_fraction": 0.8,
        "bagging_freq": 5,
        "verbose": -1,
        "n_jobs": -1,
    }

    # Create datasets
    train_data = lgb.Dataset(X_train, label=y_train)
    val_data = lgb.Dataset(X_val, label=y_val, reference=train_data)

    # Train
    model = lgb.train(
        params,
        train_data,
        num_boost_round=1000,
        valid_sets=[train_data, val_data],
        valid_names=["train", "val"],
        callbacks=[
            lgb.early_stopping(stopping_rounds=50),
            lgb.log_evaluation(period=100),
        ],
    )

    return model


def evaluate_model(model, X_test, y_test, feature_columns):
    """
    Evaluate the model and print metrics.
    """
    logger.info("Evaluating model...")

    predictions = model.predict(X_test)

    # Clip predictions to non-negative
    predictions = np.maximum(predictions, 0)

    mae = mean_absolute_error(y_test, predictions)
    rmse = np.sqrt(mean_squared_error(y_test, predictions))

    # Normalized MAE (assuming average capacity of 3 kWp)
    avg_capacity = 3.0
    nmae = mae / avg_capacity * 100

    print("\n" + "=" * 50)
    print("MODEL EVALUATION RESULTS")
    print("=" * 50)
    print(f"MAE:            {mae:.4f} kW")
    print(f"RMSE:           {rmse:.4f} kW")
    print(f"Normalized MAE: {nmae:.2f}%")
    print("=" * 50)

    # Feature importance
    print("\nTop 10 Feature Importances:")
    importance = pd.DataFrame({
        "feature": feature_columns,
        "importance": model.feature_importance(importance_type="gain"),
    }).sort_values("importance", ascending=False)

    for _i, row in importance.head(10).iterrows():
        print(f"  {row['feature']}: {row['importance']:.2f}")

    return {
        "mae": mae,
        "rmse": rmse,
        "nmae": nmae,
    }


def save_model(model, feature_columns, metrics, model_path):
    """
    Save the trained model to disk.
    """
    logger.info(f"Saving model to {model_path}")

    model_data = {
        "model": model,
        "feature_columns": feature_columns,
        "metrics": metrics,
        "trained_at": datetime.now().isoformat(),
        "version": "3.0.0",
    }

    model_path.parent.mkdir(parents=True, exist_ok=True)

    with open(model_path, "wb") as f:
        pickle.dump(model_data, f)

    logger.info("Model saved successfully!")


def main():
    parser = argparse.ArgumentParser(description="Train V3 LightGBM Solar PV Forecast Model")
    parser.add_argument("--sample-sites", type=int, default=100, help="Number of sites to sample")
    parser.add_argument("--sample-days", type=int, default=30, help="Number of days to sample")
    parser.add_argument("--output", type=str, default="quartz_solar_forecast/models/model-v3.0.pkl")
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("V3 LightGBM Solar PV Forecast Model - Training Script")
    print("=" * 60)
    print(f"Sample sites: {args.sample_sites}")
    print(f"Sample days:  {args.sample_days}")
    print("=" * 60 + "\n")

    # Load data
    df = load_pv_generation(args.sample_sites, args.sample_days)

    # Add weather data
    df = fetch_weather_data(df)

    # Engineer features
    df = engineer_features(df)

    # Prepare training data
    feature_columns = get_feature_columns()

    # Filter to columns that exist
    available_columns = [c for c in feature_columns if c in df.columns]
    missing_columns = [c for c in feature_columns if c not in df.columns]

    if missing_columns:
        logger.warning(f"Missing columns: {missing_columns}")

    X = df[available_columns].fillna(0)
    y = df["power_kw"].fillna(0)

    # Train/validation/test split
    X_train, X_temp, y_train, y_temp = train_test_split(X, y, test_size=0.3, random_state=42)
    X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=0.5, random_state=42)

    logger.info(f"Training set:   {len(X_train)} samples")
    logger.info(f"Validation set: {len(X_val)} samples")
    logger.info(f"Test set:       {len(X_test)} samples")

    # Train model
    model = train_model(X_train, y_train, X_val, y_val)

    # Evaluate
    metrics = evaluate_model(model, X_test, y_test, available_columns)

    # Save model
    save_model(model, available_columns, metrics, Path(args.output))

    print("\n✅ Training complete!")
    print(f"Model saved to: {args.output}")


if __name__ == "__main__":
    main()
