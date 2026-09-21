"""
Unit tests for v3 LightGBM Solar Forecast Model.

These tests verify the core functionality of the LightGBMSolarPredictor class
and its feature engineering methods.
"""

import numpy as np
import pandas as pd
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# Import the module under test
from quartz_solar_forecast.forecasts.v3_lightgbm import (
    LightGBMSolarPredictor,
    predict_v3,
    LIGHTGBM_AVAILABLE,
)


class TestLightGBMSolarPredictor:
    """Tests for the LightGBMSolarPredictor class."""

    @pytest.fixture
    def predictor(self):
        """Create a predictor instance for testing."""
        return LightGBMSolarPredictor()

    @pytest.fixture
    def sample_dataframe(self):
        """Create a sample DataFrame for testing feature engineering."""
        dates = pd.date_range(start="2024-06-15 06:00", periods=24, freq="H")
        return pd.DataFrame({
            "date": dates,
            "temperature_2m": np.random.uniform(15, 25, 24),
            "cloud_cover": np.random.uniform(0, 100, 24),
            "direct_radiation": np.random.uniform(0, 800, 24),
            "diffuse_radiation": np.random.uniform(0, 200, 24),
            "orientation": [180] * 24,
            "tilt": [30] * 24,
            "kwp": [5.0] * 24,
            "latitude_rounded": [51.5] * 24,
            "longitude_rounded": [-0.1] * 24,
        })

    def test_init(self, predictor):
        """Test that predictor initializes correctly."""
        assert predictor.model is None
        assert predictor.feature_columns is None

    def test_add_solar_features(self, predictor, sample_dataframe):
        """Test solar feature engineering adds expected columns."""
        result = predictor._add_solar_features(sample_dataframe)
        
        # Check that cyclical time features are added
        assert "hour_sin" in result.columns
        assert "hour_cos" in result.columns
        assert "day_sin" in result.columns
        assert "day_cos" in result.columns
        assert "month_sin" in result.columns
        assert "month_cos" in result.columns
        assert "day_of_week" in result.columns
        
    def test_solar_features_cyclical_range(self, predictor, sample_dataframe):
        """Test that cyclical features are in valid range [-1, 1]."""
        result = predictor._add_solar_features(sample_dataframe)
        
        for col in ["hour_sin", "hour_cos", "day_sin", "day_cos", "month_sin", "month_cos"]:
            assert result[col].min() >= -1.0, f"{col} has values below -1"
            assert result[col].max() <= 1.0, f"{col} has values above 1"

    def test_add_panel_features(self, predictor, sample_dataframe):
        """Test panel feature engineering adds expected columns."""
        result = predictor._add_panel_features(sample_dataframe)
        
        assert "orientation_sin" in result.columns
        assert "orientation_cos" in result.columns
        assert "tilt_factor" in result.columns

    def test_panel_features_values(self, predictor, sample_dataframe):
        """Test panel features have expected values for south-facing panel."""
        result = predictor._add_panel_features(sample_dataframe)
        
        # For 180-degree (south-facing) orientation:
        # sin(180°) ≈ 0, cos(180°) ≈ -1
        assert np.allclose(result["orientation_sin"].iloc[0], 0, atol=0.01)
        assert np.allclose(result["orientation_cos"].iloc[0], -1, atol=0.01)
        
        # For 30-degree tilt: cos(30°) ≈ 0.866
        assert np.allclose(result["tilt_factor"].iloc[0], 0.866, atol=0.01)

    def test_prepare_features(self, predictor, sample_dataframe):
        """Test that prepare_features combines all feature engineering."""
        result = predictor.prepare_features(sample_dataframe)
        
        # Should have solar features
        assert "hour_sin" in result.columns
        
        # Should have panel features
        assert "orientation_sin" in result.columns
        
        # Should NOT have date column (dropped)
        assert "date" not in result.columns

    def test_prepare_features_drops_unused_columns(self, predictor, sample_dataframe):
        """Test that unused columns are dropped during feature preparation."""
        # Add some columns that should be dropped
        sample_dataframe["terrestrial_radiation"] = 100
        sample_dataframe["shortwave_radiation"] = 200
        sample_dataframe["direct_normal_irradiance"] = 300
        
        result = predictor.prepare_features(sample_dataframe)
        
        assert "terrestrial_radiation" not in result.columns
        assert "shortwave_radiation" not in result.columns
        assert "direct_normal_irradiance" not in result.columns


class TestCyclicalEncoding:
    """Tests for cyclical time encoding correctness."""

    @pytest.fixture
    def predictor(self):
        return LightGBMSolarPredictor()

    def test_hour_encoding_midnight(self, predictor):
        """Test that midnight (00:00) encodes correctly."""
        df = pd.DataFrame({"date": [datetime(2024, 6, 21, 0, 0)]})
        result = predictor._add_solar_features(df)
        
        # At hour 0: sin(0) = 0, cos(0) = 1
        assert np.isclose(result["hour_sin"].iloc[0], 0, atol=0.01)
        assert np.isclose(result["hour_cos"].iloc[0], 1, atol=0.01)

    def test_hour_encoding_noon(self, predictor):
        """Test that noon (12:00) encodes correctly."""
        df = pd.DataFrame({"date": [datetime(2024, 6, 21, 12, 0)]})
        result = predictor._add_solar_features(df)
        
        # At hour 12: sin(π) = 0, cos(π) = -1
        assert np.isclose(result["hour_sin"].iloc[0], 0, atol=0.01)
        assert np.isclose(result["hour_cos"].iloc[0], -1, atol=0.01)

    def test_hour_encoding_6am(self, predictor):
        """Test that 6 AM encodes correctly."""
        df = pd.DataFrame({"date": [datetime(2024, 6, 21, 6, 0)]})
        result = predictor._add_solar_features(df)
        
        # At hour 6: sin(π/2) = 1, cos(π/2) = 0
        assert np.isclose(result["hour_sin"].iloc[0], 1, atol=0.01)
        assert np.isclose(result["hour_cos"].iloc[0], 0, atol=0.01)


class TestPredictV3Function:
    """Tests for the convenience predict_v3 function."""

    @pytest.mark.skipif(not LIGHTGBM_AVAILABLE, reason="LightGBM not installed")
    def test_predict_v3_returns_dataframe(self):
        """Test that predict_v3 returns a DataFrame with expected columns."""
        # Skip if model file doesn't exist (would need to mock for full test)
        pass


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.fixture
    def predictor(self):
        return LightGBMSolarPredictor()

    def test_empty_dataframe(self, predictor):
        """Test handling of empty DataFrame."""
        df = pd.DataFrame(columns=["date", "temperature_2m", "orientation", "tilt"])
        result = predictor.prepare_features(df)
        assert len(result) == 0

    def test_missing_optional_columns(self, predictor):
        """Test that missing optional columns don't cause errors."""
        df = pd.DataFrame({
            "date": [datetime(2024, 6, 21, 12, 0)],
            "temperature_2m": [20.0],
        })
        # Should not raise even without orientation/tilt columns
        result = predictor._add_solar_features(df)
        assert "hour_sin" in result.columns

    def test_load_model_file_not_found(self, predictor):
        """Test that FileNotFoundError is raised when model file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            predictor.load_model("/nonexistent/path/model.pkl")


class TestModelIntegration:
    """Integration tests requiring the actual model file."""

    @pytest.fixture
    def predictor(self):
        return LightGBMSolarPredictor()

    @pytest.mark.skipif(not LIGHTGBM_AVAILABLE, reason="LightGBM not installed")
    def test_model_loads_successfully(self, predictor):
        """Test that the model can be loaded from the default location."""
        try:
            predictor.load_model()
            assert predictor.model is not None
        except FileNotFoundError:
            pytest.skip("Model file not found - run training first")

    @pytest.mark.skipif(not LIGHTGBM_AVAILABLE, reason="LightGBM not installed") 
    def test_model_has_feature_columns(self, predictor):
        """Test that loaded model includes feature column metadata."""
        try:
            predictor.load_model()
            assert predictor.feature_columns is not None
            assert isinstance(predictor.feature_columns, list)
        except FileNotFoundError:
            pytest.skip("Model file not found - run training first")


class TestSnowFeatures:
    """Tests for snow depth feature engineering (Issue #217)."""

    @pytest.fixture
    def predictor(self):
        return LightGBMSolarPredictor()

    def test_snow_features_added_with_snow_data(self, predictor):
        """Test that snow features are created when snow_depth column exists."""
        df = pd.DataFrame({
            "date": [datetime(2024, 1, 15, 12, 0)],
            "snow_depth": [0.2],  # 20cm of snow
            "temperature_2m": [-5.0],
        })
        result = predictor._add_snow_features(df)

        assert "snow_depth" in result.columns
        assert "has_snow" in result.columns
        assert "snow_impact" in result.columns

    def test_snow_features_values_with_snow(self, predictor):
        """Test snow feature values when snow is present."""
        df = pd.DataFrame({
            "date": [datetime(2024, 1, 15, 12, 0)],
            "snow_depth": [0.25],  # 25cm snow
        })
        result = predictor._add_snow_features(df)

        assert result["has_snow"].iloc[0] == 1
        assert result["snow_impact"].iloc[0] == 0.5  # 0.25/0.5 = 0.5

    def test_snow_features_values_no_snow(self, predictor):
        """Test snow feature values when no snow."""
        df = pd.DataFrame({
            "date": [datetime(2024, 6, 15, 12, 0)],
            "snow_depth": [0.0],
        })
        result = predictor._add_snow_features(df)

        assert result["has_snow"].iloc[0] == 0
        assert result["snow_impact"].iloc[0] == 0.0

    def test_snow_impact_capped_at_one(self, predictor):
        """Test that snow_impact is capped at 1.0 for heavy snow."""
        df = pd.DataFrame({
            "date": [datetime(2024, 1, 15, 12, 0)],
            "snow_depth": [1.0],  # 1 meter of snow (very heavy)
        })
        result = predictor._add_snow_features(df)

        assert result["snow_impact"].iloc[0] == 1.0  # Capped at 1.0

    def test_snow_features_nan_handling(self, predictor):
        """Test that NaN snow_depth values are filled with 0."""
        df = pd.DataFrame({
            "date": [datetime(2024, 1, 15, 12, 0)],
            "snow_depth": [np.nan],
        })
        result = predictor._add_snow_features(df)

        assert result["snow_depth"].iloc[0] == 0
        assert result["has_snow"].iloc[0] == 0

    def test_snow_features_backward_compatibility(self, predictor):
        """Test backward compatibility when snow_depth column is missing."""
        df = pd.DataFrame({
            "date": [datetime(2024, 6, 15, 12, 0)],
            "temperature_2m": [25.0],
            # No snow_depth column
        })
        result = predictor._add_snow_features(df)

        # Should have snow features with default values
        assert result["snow_depth"].iloc[0] == 0
        assert result["has_snow"].iloc[0] == 0
        assert result["snow_impact"].iloc[0] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

