""" Example code to run the forecast"""
import pandas as pd

from quartz_solar_forecast.forecast import run_forecast
from quartz_solar_forecast.pydantic_models import PVSite

# set plotly backend to be plotly, you might have to install plotly
pd.options.plotting.backend = "plotly"


def main():

    ts = pd.Timestamp("2024-01-30 12:00")
    recent_pv_data = pd.DataFrame(
        {"timestamp": ["2024-01-30 11:30", "2024-01-30 11:45"], "power_kw": [0.7, 0.7]}
    )
    recent_pv_data["timestamp"] = pd.to_datetime(recent_pv_data["timestamp"])

    # make input data
    site = PVSite(latitude=51.75, longitude=-1.25, capacity_kwp=1.25)

    # run model, with and without recent pv data
    predictions_with_recent_pv_df = run_forecast(site=site, ts=ts, recent_pv_data=recent_pv_data)
    predictions_df = run_forecast(site=site, ts=ts)

    predictions_with_recent_pv_df["power_kw_no_live_pv"] = predictions_df["power_kw"]

    # plot
    fig = predictions_with_recent_pv_df.plot(
        title="PV Forecast",
        template="plotly_dark",
        y=["power_kw", "power_kw_no_live_pv"],
        labels={"value": "Power (kW)", "index": "Time"},
    )
    fig.show(renderer="browser")


if __name__ == "__main__":
    main()
