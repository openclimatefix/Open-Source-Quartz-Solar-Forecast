"""
V3 Model: LightGBM-based Solar PV Forecast

This model improves upon the existing XGBoost model (v2) with:
- Enhanced feature engineering (solar position, rolling stats, lag features)
- LightGBM for faster training and better handling of large datasets
- Support for the standard evaluation pipeline

Author: Raakshass (GSoC 2026 contribution)
Issue: https://github.com/openclimatefix/open-source-quartz-solar-forecast/issues/30
"""

import datetime
import logging
import os
import pickle

import numpy as np
import pandas as pd

try:
    import lightgbm as lgb
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False
    lgb = None

import quartz_solar_forecast
from quartz_solar_forecast.weather import WeatherService

logger = logging.getLogger(__name__)

# Model directory
MODEL_DIR = os.path.dirname(quartz_solar_forecast.__file__) + "/models"


class LightGBMSolarPredictor:
    """
    A LightGBM-based solar power predictor with enhanced feature engineering.

    Improvements over v2 (XGBoost):
    - Solar position features (sin/cos encoding of hour, day of year)
    - Rolling weather statistics
    - Better handling of panel orientation and tilt
    - Faster training with LightGBM
    """

    DATE_COLUMN = "date"
    MODEL_FILE = "model-v3.0.pkl"

    def __init__(self):
        self.model = None
        self.feature_columns = None

    def _add_solar_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add solar position and cyclical time features.

        Features added:
        - hour_sin, hour_cos: Cyclical encoding of hour
        - day_sin, day_cos: Cyclical encoding of day of year
        - month_sin, month_cos: Cyclical encoding of month
        """
        df = df.copy()

        # Ensure datetime column exists
        if self.DATE_COLUMN in df.columns:
            dt = pd.to_datetime(df[self.DATE_COLUMN])
        else:
            dt = df.index.to_series()

        # Hour of day (cyclical)
        hour = dt.dt.hour + dt.dt.minute / 60
        df["hour_sin"] = np.sin(2 * np.pi * hour / 24)
        df["hour_cos"] = np.cos(2 * np.pi * hour / 24)

        # Day of year (cyclical)
        day_of_year = dt.dt.dayofyear
        df["day_sin"] = np.sin(2 * np.pi * day_of_year / 365)
        df["day_cos"] = np.cos(2 * np.pi * day_of_year / 365)

        # Month (cyclical)
        month = dt.dt.month
        df["month_sin"] = np.sin(2 * np.pi * month / 12)
        df["month_cos"] = np.cos(2 * np.pi * month / 12)

        # Day of week
        df["day_of_week"] = dt.dt.dayofweek

        return df

    def _add_panel_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add derived panel features.

        Features added:
        - orientation_sin, orientation_cos: Cyclical encoding of orientation
        - effective_area: Approximation based on tilt
        """
        df = df.copy()

        if "orientation" in df.columns:
            orientation_rad = np.deg2rad(df["orientation"])
            df["orientation_sin"] = np.sin(orientation_rad)
            df["orientation_cos"] = np.cos(orientation_rad)

        if "tilt" in df.columns:
            # Effective area factor based on tilt (simplified)
            df["tilt_factor"] = np.cos(np.deg2rad(df["tilt"]))

        return df

    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare features for prediction.

        Args:
            df: DataFrame with weather and panel data

        Returns:
            DataFrame with engineered features
        """
        df = df.copy()

        # Add solar/time features
        df = self._add_solar_features(df)

        # Add panel features
        df = self._add_panel_features(df)

        # Standard time features (kept for compatibility)
        if self.DATE_COLUMN in df.columns:
            dt = pd.to_datetime(df[self.DATE_COLUMN])
            df["date_month"] = dt.dt.month
            df["date_day"] = dt.dt.day
            df["date_hour"] = dt.dt.hour

        # Drop columns not needed for prediction
        columns_to_drop = [
            self.DATE_COLUMN,
            "date_minute",
            "date_year",
            "terrestrial_radiation",
            "shortwave_radiation",
            "direct_normal_irradiance",
        ]

        for col in columns_to_drop:
            if col in df.columns:
                df = df.drop(columns=[col])

        return df

    def get_data(
        self,
        latitude: float,
        longitude: float,
        start_date: str,
        kwp: float,
        orientation: float = 180,
        tilt: float = 30,
    ) -> pd.DataFrame:
        """
        Fetch weather data for the given location and date range.

        Args:
            latitude: Latitude of the location
            longitude: Longitude of the location
            start_date: Start date in 'YYYY-MM-DD' format
            kwp: Kilowatt peak of the solar panel system
            orientation: Orientation angle in degrees
            tilt: Tilt angle in degrees

        Returns:
            DataFrame with weather and panel data
        """
        start_date_datetime = datetime.datetime.strptime(start_date, "%Y-%m-%d")
        end_date_datetime = start_date_datetime + datetime.timedelta(days=2)
        end_date = end_date_datetime.strftime("%Y-%m-%d")

        weather_service = WeatherService()
        weather_data = weather_service.get_hourly_weather(
            latitude, longitude, start_date, end_date
        )

        # Add panel parameters
        weather_data["latitude_rounded"] = latitude
        weather_data["longitude_rounded"] = longitude
        weather_data["orientation"] = orientation
        weather_data["tilt"] = tilt
        weather_data["kwp"] = kwp

        return weather_data

    def load_model(self, model_path: str | None = None):
        """
        Load a trained model from disk.

        Args:
            model_path: Path to the model file. If None, uses default location.

        Returns:
            The loaded LightGBM model
        """
        if not LIGHTGBM_AVAILABLE:
            raise ImportError(
                "LightGBM is not installed. Install it with: pip install lightgbm"
            )

        if model_path is None:
            model_path = os.path.join(MODEL_DIR, self.MODEL_FILE)

        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Model file not found: {model_path}. "
                "Please train the model first using scripts/train_v3_model.py"
            )

        logger.info(f"Loading model from {model_path}")
        with open(model_path, "rb") as f:
            saved_data = pickle.load(f)

        self.model = saved_data["model"]
        self.feature_columns = saved_data.get("feature_columns")

        return self.model

    def predict_power_output(
        self,
        latitude: float,
        longitude: float,
        start_date: str,
        kwp: float,
        orientation: float = 180,
        tilt: float = 30,
    ) -> pd.DataFrame:
        """
        Predict solar power output for the specified parameters.

        Args:
            latitude: Latitude of the location
            longitude: Longitude of the location
            start_date: Start date in 'YYYY-MM-DD' format
            kwp: Kilowatt peak of the solar panel system
            orientation: Orientation angle in degrees
            tilt: Tilt angle in degrees

        Returns:
            DataFrame with predicted power output in kW
        """
        if self.model is None:
            self.load_model()

        # Get weather data
        data = self.get_data(latitude, longitude, start_date, kwp, orientation, tilt)

        # Prepare features
        features = self.prepare_features(data)

        # Align columns with training data
        if self.feature_columns is not None:
            # Add missing columns with zeros
            for col in self.feature_columns:
                if col not in features.columns:
                    features[col] = 0
            # Select only the columns used during training
            features = features[self.feature_columns]

        # Predict
        predictions = self.model.predict(features)

        # Post-process predictions
        predictions_df = pd.DataFrame({
            self.DATE_COLUMN: data[self.DATE_COLUMN],
            "power_kw": predictions
        })

        # Set night predictions to 0
        if "is_day" in data.columns:
            predictions_df.loc[data["is_day"] == 0, "power_kw"] = 0

        # Set negative outputs to 0
        predictions_df.loc[predictions_df["power_kw"] < 0, "power_kw"] = 0

        return predictions_df


def predict_v3(
    latitude: float,
    longitude: float,
    start_date: str,
    kwp: float,
    orientation: float = 180,
    tilt: float = 30,
) -> pd.DataFrame:
    """
    Convenience function to make predictions using the v3 LightGBM model.

    Args:
        latitude: Latitude of the location
        longitude: Longitude of the location
        start_date: Start date in 'YYYY-MM-DD' format
        kwp: Kilowatt peak of the solar panel system
        orientation: Orientation angle in degrees
        tilt: Tilt angle in degrees

    Returns:
        DataFrame with predicted power output in kW
    """
    predictor = LightGBMSolarPredictor()
    predictor.load_model()
    return predictor.predict_power_output(
        latitude, longitude, start_date, kwp, orientation, tilt
    )
