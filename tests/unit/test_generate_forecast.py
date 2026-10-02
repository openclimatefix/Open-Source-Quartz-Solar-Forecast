import os
from datetime import datetime, timedelta

import pandas as pd

import quartz_solar_forecast.utils.forecast_csv as forecast_csv
from quartz_solar_forecast.pydantic_models import PVSite


def test_generate_forecast(monkeypatch):
    site_name = "TestCase"
    latitude = 51.75
    longitude = -1.25
    capacity_kwp = 1.25
    start_datetime = "2024-03-10 00:00:00"
    end_datetime = "2024-03-11 00:00:00"
    init_time_freq = 6
    output_dir = os.path.join(os.getcwd(), "csv_forecasts")
    output_file_name = (
        f"forecast_{site_name}_{start_datetime[:10]}_{end_datetime[:10]}.csv"
    )
    output_file_path = os.path.join(output_dir, output_file_name)

    def mock_forecast(
        site: PVSite,
        model: str = "gb",
        ts: datetime | str = None,
        nwp_source: str = "icon",
    ):
        return pd.DataFrame(
            {
                "datetime": [
                    datetime(2024, 3, 10, 0, 0) + timedelta(hours=6 * i)
                    for i in range(4)
                ],
                "power_kw": [0.1, 0.5, 0.8, 0.6],
                "forecast_init_time": [datetime(2024, 3, 10, 0, 0)] * 4,
            }
        )

    monkeypatch.setattr(forecast_csv, "run_forecast", mock_forecast)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    forecast_csv.write_out_forecasts(
        init_time_freq,
        start_datetime,
        end_datetime,
        site_name,
        latitude,
        longitude,
        capacity_kwp,
    )

    assert os.path.exists(output_file_path)
    os.remove(output_file_path)
