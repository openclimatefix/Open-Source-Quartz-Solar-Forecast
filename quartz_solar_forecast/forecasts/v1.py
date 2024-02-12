import pandas as pd
import xarray as xr
import os
from psp.data_sources.nwp import NwpDataSource
from psp.data_sources.pv import NetcdfPvDataSource
from psp.serialization import load_model
from psp.typings import X

dir_path = os.path.dirname(os.path.realpath(__file__))


def forecast_v1(nwp_source:str, nwp_xr:xr.Dataset, pv_xr:xr.Dataset, ts:pd.Timestamp, model=None):
    """
    Run the forecast

    This runs the pv-site-prediction model from the psp library.
    """

    if model is None:
        model = load_model(f"{dir_path}/../models/model-0.3.0.pkl")

    # format pv and nwp data
    pv_data_source = NetcdfPvDataSource(
        pv_xr,
        id_dim_name="pv_id",
        timestamp_dim_name="timestamp",
        rename={"generation_wh": "power", "kwp": "capacity"},
        ignore_pv_ids=[],
    )
    # make NwpDataSource
    nwp = NwpDataSource(nwp_xr, value_name=nwp_source)
    model.set_data_sources(pv_data_source=pv_data_source, nwp_data_sources={nwp_source: nwp})

    # make prediction.
    # Note pv_id=1 is arbitrary, but the pv_xr must have this in it.
    x = X(pv_id="1", ts=ts)
    pred = model.predict(x)

    # format into timerange and put into pd dataframe
    times = pd.date_range(start=x.ts, periods=len(pred.powers), freq="15min")
    pred_df = pd.DataFrame({"power_kw": pred.powers}, index=times)

    return pred_df
