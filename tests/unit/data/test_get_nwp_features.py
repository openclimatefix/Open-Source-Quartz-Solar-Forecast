from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from quartz_solar_forecast.data import (
    OPEN_METEO_VARIABLES,
    downward_longwave_radiation,
    get_nwp,
    open_meteo_to_model_features,
)
from quartz_solar_forecast.pydantic_models import PVSite

# distinct values per Open-Meteo variable, so a mix-up between features shows up
OPEN_METEO_VALUES = {
    "temperature_2m": 15.0,
    "precipitation": 1.8,
    "cloud_cover_low": 20.0,
    "cloud_cover_mid": 30.0,
    "cloud_cover_high": 40.0,
    "cloud_cover": 50.0,
    "wind_speed_10m": 36.0,
    "shortwave_radiation": 500.0,
    "dew_point_2m": 10.0,
}


def test_open_meteo_to_model_features_units():
    data = {k: np.array([v]) for k, v in OPEN_METEO_VALUES.items()}

    features = open_meteo_to_model_features(data)

    assert features["t"] == pytest.approx(288.15)  # K
    assert features["prate"] == pytest.approx(0.0005)  # kg m-2 s-1
    assert features["si10"] == pytest.approx(10.0)  # m/s
    assert features["lcc"] == pytest.approx(20.0)
    assert features["mcc"] == pytest.approx(30.0)
    assert features["hcc"] == pytest.approx(40.0)
    assert features["dswrf"] == pytest.approx(500.0)
    assert features["dlwrf"] == pytest.approx(downward_longwave_radiation(15.0, 10.0, 50.0))


def test_downward_longwave_radiation():
    # clear sky at 15 °C with 10 °C dew point is about 309 W/m²
    clear = downward_longwave_radiation(np.array([15.0]), np.array([10.0]), np.array([0.0]))
    assert clear[0] == pytest.approx(309, abs=1)

    # cloud increases longwave, by 22% at full cover
    overcast = downward_longwave_radiation(np.array([15.0]), np.array([10.0]), np.array([100.0]))
    assert overcast[0] == pytest.approx(clear[0] * 1.22)


def test_get_nwp_maps_variables_by_name():
    site = PVSite(latitude=51.75, longitude=-1.25, capacity_kwp=1.25)
    # more than 90 days ago, so visibility is not requested
    ts = datetime.now() - timedelta(days=200)
    n_hours = 3

    hourly = MagicMock()
    hourly.Time.return_value = 0
    hourly.TimeEnd.return_value = n_hours * 3600
    hourly.Interval.return_value = 3600
    hourly.Variables.side_effect = lambda idx: MagicMock(
        ValuesAsNumpy=MagicMock(
            return_value=np.full(n_hours, OPEN_METEO_VALUES[OPEN_METEO_VARIABLES[idx]])
        )
    )
    client = MagicMock()
    client.weather_api.return_value = [MagicMock(Hourly=MagicMock(return_value=hourly))]

    with patch("quartz_solar_forecast.data.openmeteo_requests.Client", return_value=client):
        nwp = get_nwp(site=site, ts=ts, nwp_source="icon")

    requested = client.weather_api.call_args.kwargs["params"]["hourly"]
    assert requested == OPEN_METEO_VARIABLES

    values = nwp["icon"].isel(step=0).to_series()
    expected = open_meteo_to_model_features({k: np.array([v]) for k, v in OPEN_METEO_VALUES.items()})
    for feature, value in expected.items():
        assert values[feature] == pytest.approx(value[0])
    assert values["vis"] == 24000.0
