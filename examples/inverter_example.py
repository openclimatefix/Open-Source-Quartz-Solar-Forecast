import pandas as pd
from datetime import datetime, timezone
from quartz_solar_forecast.forecast import run_forecast
from quartz_solar_forecast.pydantic_models import PVSite
import os
import typer

# Set plotly backend to be plotly, you might have to install plotly
pd.options.plotting.backend = "plotly"

def main(save_outputs: bool = False):
    timestamp = datetime.now().timestamp()
    timestamp_str = datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    ts = pd.to_datetime(timestamp_str)

    # make input data with live enphase, solis, givenergy, or solarman data
    site_live = PVSite(latitude=51.75, longitude=-1.25, capacity_kwp=1.25, inverter_type="enphase") # inverter_type="enphase", "solis", "givenergy", "solarman" or "victron"

    # make input data with nan data
    site_no_live = PVSite(latitude=51.75, longitude=-1.25, capacity_kwp=1.25)

    # run model, with and without recent pv data
    predictions_with_recent_pv_df = run_forecast(site=site_live, ts=ts)
    predictions_df = run_forecast(site=site_no_live, ts=ts) 

    predictions_with_recent_pv_df["power_kw_no_live_pv"] = predictions_df["power_kw"]

    if save_outputs:
        # Get the directory of the current script
        script_dir = os.path.dirname(os.path.abspath(__file__))

        # Create a 'results' directory if it doesn't exist
        results_dir = os.path.join(script_dir, 'results')
        os.makedirs(results_dir, exist_ok=True)

        # Save dataframe to CSV file in the 'results' directory
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_filename = f"predictions_with_recent_pv_{current_time}.csv"
        csv_path = os.path.join(results_dir, csv_filename)
        predictions_with_recent_pv_df.to_csv(csv_path, index=True)
        
        print(f"CSV file saved at: {csv_path}")
    else:
        print("Outputs not saved to CSV. Use --save-outputs to save.")

    # plot
    fig = predictions_with_recent_pv_df.plot(
        title="PV Forecast",
        template="plotly_dark",
        y=["power_kw", "power_kw_no_live_pv"],
        labels={"value": "Power (kW)", "index": "Time"},
    )
    fig.show(renderer="browser")

if __name__ == "__main__":
    typer.run(main)