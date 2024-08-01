import os
import pandas as pd
import xarray as xr
from psp.data_sources.nwp import NwpDataSource
from psp.data_sources.pv import NetcdfPvDataSource
from psp.serialization import load_model
from psp.typings import X

from quartz_solar_forecast.data import get_nwp, make_pv_data
from quartz_solar_forecast.pydantic_models import PVSite
from quartz_solar_forecast.forecasts.v1 import forecast_v1
from quartz_solar_forecast.data import format_nwp_data

from datetime import datetime

dir_path = os.path.dirname(os.path.realpath(__file__))


def run_forecast(pv_df: pd.DataFrame, nwp_df: pd.DataFrame, nwp_source="ICON") -> pd.DataFrame:
    """
    Run the forecast from NWP data

    :param pv_df: the PV site data. This should have columns timestamp, id, latitude, longitude, and capacity
    :param nwp_df: all the nwp data for the site and location. This shoulw have the following rows
        - timestamp: the timestamp of the site
        - temperature_2m
        - precipitation
        - shortwave_radiation
        - direct_radiation",
        - cloudcover_low",
        - cloudcover_mid",
        - cloudcover_high",
        maybe more
    """

    # load model only once
    model = load_model(f"{dir_path}/../models/model-0.3.0.pkl")

    all_predictions = []
    for i in range(len(pv_df)):

        print(f"Running forecast for {i} of {len(pv_df)}")

        pv_row = pv_df.iloc[i]

        site = PVSite(
            latitude=pv_row["latitude"],
            longitude=pv_row["longitude"],
            capacity_kwp=pv_row["capacity"],
        )

        nwp_site_df = nwp_df[
            (nwp_df["pv_id"] == pv_row.pv_id) & (nwp_df["timestamp"] == pv_row.timestamp)
        ]

        pv_id = pv_df["pv_id"][i]
        ts = pv_df["timestamp"][i]

        # format
        for c in ["timestamp", "latitude", "longitude", "pv_id"]:
            if c in nwp_site_df.columns:
                nwp_site_df = nwp_site_df.drop(columns=c)

        nwp_site_df.set_index("time", inplace=True, drop=True)

        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)

        # make pv and nwp data from GFS
        # TODO move this to model
        print("Making pv and nwp data")
        nwp_xr = format_nwp_data(df=nwp_site_df, nwp_source=nwp_source, site=site)
        pv_xr = make_pv_data(site=site, ts=ts)

        # run model
        print('Running model')
        pred_df = forecast_v1(nwp_source, nwp_xr, pv_xr, ts, model=model)

        # only select hourly predictions
        pred_df = pred_df.resample("1h").mean()
        pred_df["horizon_hour"] = range(0, len(pred_df))
        pred_df["pv_id"] = pv_id

        all_predictions.append(pred_df)

    all_predictions = pd.concat(all_predictions)
    all_predictions['timestamp'] = all_predictions.index

    return all_predictions
