"""Make a script to generate forecasts for multiple sites.

The idea is to generate forecasts for multiple sites and to combine them into a 
single csv. A list with several sites containing pv_id, latitude, longitude 
and capacity will be passed through the forecaster then each forecast will be saved 
to a csv.

"""

import pandas as pd
from quartz_solar_forecast.forecast import run_forecast
from quartz_solar_forecast.pydantic_models import PVSite
from datetime import datetime

def generate_forecasts(sites):
    """Generate forecasts for pv_sites."""

    # run forecast for each pv site
    for pv_id, site in sites.items():
        csv_data = []  # Initialize csv_data here

        predictions_df = run_forecast(site=site)

        # add to csv data
        for index, row in predictions_df.iterrows():
            csv_row = [
                pv_id,
                site.latitude,
                site.longitude,
                site.capacity_kwp,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                index.date(),
                index.time(),
                row["power_wh"],
            ]
            csv_data.append(csv_row)
    
        csv_df = pd.DataFrame(
            csv_data,
            columns=[
                "pv_id",
                "latitude",
                "longitude",
                "capacity_kwp",
                "forecast creation time",
                "forecast date",
                "forecast time",
                "power_wh",
            ],
        )
        

        # write to a new csv
        csv_df.to_csv(
            f"quartz_solar_forecast/dataset/forecast_{pv_id}.csv", index=False
        )

if __name__ == "__main__":
    # dummy sites for now
    sites = {
        # PV_ID: Site
        12323: PVSite(latitude=50, longitude=0, capacity_kwp=23),
        2324: PVSite(latitude=54, longitude=2, capacity_kwp=10),
        1023: PVSite(latitude=48, longitude=-1, capacity_kwp=5),
        3242: PVSite(latitude=46, longitude=10, capacity_kwp=10),
        1453: PVSite(latitude=54, longitude=-8, capacity_kwp=2.5)
    }

    generate_forecasts(sites)