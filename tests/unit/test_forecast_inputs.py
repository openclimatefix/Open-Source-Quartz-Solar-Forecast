from datetime import datetime

import pandas as pd

import quartz_solar_forecast.forecast as forecast
from quartz_solar_forecast.pydantic_models import PVSite


def test_predict_ocf_does_not_mutate_large_site_or_live_generation(monkeypatch):
    site = PVSite(latitude=51.75, longitude=-1.25, capacity_kwp=8)
    live_generation = pd.DataFrame(
        {
            "timestamp": [datetime(2026, 1, 1)],
            "power_kw": [2.0],
        }
    )

    monkeypatch.setattr(forecast, "get_nwp", lambda **kwargs: object())
    monkeypatch.setattr(forecast, "make_pv_data", lambda **kwargs: object())
    monkeypatch.setattr(
        forecast,
        "forecast_v1_tilt_orientation",
        lambda *args, **kwargs: pd.DataFrame({"power_kw": [1.0]}),
    )

    result = forecast.predict_ocf(
        site=site,
        ts=datetime(2026, 1, 1),
        live_generation=live_generation,
    )

    assert site.capacity_kwp == 8
    assert live_generation["power_kw"].tolist() == [2.0]
    assert result["power_kw"].tolist() == [2.0]
