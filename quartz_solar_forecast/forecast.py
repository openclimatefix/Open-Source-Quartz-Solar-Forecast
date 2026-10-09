import logging
from datetime import datetime, timedelta

import pandas as pd

from quartz_solar_forecast.data import get_nwp, make_pv_data
from quartz_solar_forecast.forecasts import (
    TryolabsSolarPowerPredictor,
    forecast_v1_tilt_orientation,
)
from quartz_solar_forecast.pydantic_models import PVSite

log = logging.getLogger(__name__)


def predict_ocf(
    site: PVSite,
    model=None,
    ts: datetime | str = None,
    nwp_source: str = "icon",
    live_generation: pd.DataFrame | None = None,
):
    """
    Run the forecast with the gb model, which can take tilt and orientation as inputs

    :param site: the PV site
    :param model: the model to use for prediction
    :param ts: the timestamp of the site. If None, defaults to the current
        timestamp rounded down to 15 minutes.
    :param nwp_source: the nwp data source. Either "gfs", "icon", "ukmo",
        or "ecmwf". Defaults to "icon"
    :param live_generation: a dataframe containing live generation data for the site
    :return: The PV forecast of the site for time (ts) for 48 hours
    """

    if ts is None:
        ts = pd.Timestamp.now().round("15min")

    if isinstance(ts, str):
        ts = datetime.fromisoformat(ts)

    if site.capacity_kwp > 4:
        # Keep the caller's site and live-generation objects unchanged. The
        # model is trained for sites up to 4 kWp, so the inputs are temporarily
        # normalised before inference and the forecast is scaled back below.
        site = site.model_copy(deep=True)
        if live_generation is not None:
            live_generation = live_generation.copy(deep=True)
        log.warning(
            "Your site capacity is greater than 4kWp, "
            "however the model is trained on sites with capacity <= 4kWp."
            "We therefore will run the model with a capacity of 4 kWp, "
            "and we'll scale the results afterwards."
        )
        capacity_kwp_original = site.capacity_kwp
        site.capacity_kwp = 4
        if live_generation is not None:
            live_generation["power_kw"] = live_generation["power_kw"] / capacity_kwp_original * 4
    else:
        capacity_kwp_original = site.capacity_kwp

    # make pv and nwp data from nwp_source
    nwp_xr = get_nwp(site=site, ts=ts, nwp_source=nwp_source)
    pv_xr = make_pv_data(site=site, ts=ts, live_generation=live_generation)

    # load and run models
    pred_df = forecast_v1_tilt_orientation(nwp_source, nwp_xr, pv_xr, ts, model=model)

    # scale the results if the capacity is different
    if capacity_kwp_original != site.capacity_kwp:
        pred_df["power_kw"] = pred_df["power_kw"] * capacity_kwp_original / site.capacity_kwp

    return pred_df


def predict_tryolabs(site: PVSite, ts: datetime | str = None):
    """
    Run the forecast with the xgb model

    :param site: the PV site
    :param ts: the timestamp of the site. If None, defaults to the current
        timestamp rounded down to 15 minutes.
    :return: The PV forecast of the site for time (ts) for 48 hours
    """

    # instantiate class to make predictions
    solar_power_predictor = TryolabsSolarPowerPredictor()

    # set start and end time, if no time is given use current time
    if ts is None:
        now = pd.Timestamp.now()
        start_date = now.strftime("%Y-%m-%d")
        start_time = now.round(freq="h")
    else:
        ts_pd = pd.Timestamp(ts)
        start_date = ts_pd.strftime("%Y-%m-%d")
        start_time = ts_pd.round(freq="h")

    end_time = start_time + pd.Timedelta(hours=48)
    start_date_datetime = datetime.strptime(start_date, "%Y-%m-%d")

    # Check if the start date is more than 3 months ago
    three_months_ago = datetime.today() - timedelta(days=3 * 30)

    if start_date_datetime < three_months_ago:
        raise ValueError(
            f"Start date ({start_date}) is more than 3 months ago. "
            "Historical forecast data is not available beyond this range. "
            "Please use a more recent date."
        )

    # download the model from google drive and decompress if necessary
    solar_power_predictor.load_model()
    # make predictions
    predictions = solar_power_predictor.predict_power_output(
        latitude=site.latitude,
        longitude=site.longitude,
        start_date=start_date,
        kwp=site.capacity_kwp,
        orientation=site.orientation,
        tilt=site.tilt,
    )

    # postprocessing of the dataframe
    predictions = predictions[
        (predictions["date"] >= start_time) & (predictions["date"] < end_time)
    ]
    predictions = predictions.reset_index(drop=True)
    predictions.set_index("date", inplace=True)
    log.info("Predictions finished.")
    return predictions


def run_forecast(
    site: PVSite,
    model: str = "gb",
    ts: datetime | str = None,
    nwp_source: str = "icon",
    live_generation: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    Predict solar power output for a given site using a specified model.

    :param site: the PV site
    :param model: the model to use for prediction, choose between "ocf" and "tryolabs",
                    by default "ocf" is used
    :param ts: the timestamp of the site. If None, defaults to the current
        timestamp rounded down to 15 minutes.
    :param nwp_source: the nwp data source. Either "gfs", "icon", "ukmo",
        or "ecmwf". Defaults to "icon" (only relevant if model=="gb")
    :param live_generation: a dataframe containing live generation data for the site.
        This should have the columns "power_kw" and "timestamp"
    :return: The PV forecast of the site for time (ts) for 48 hours
    """

    log.info(
        f"Running forecast for site at lat {site.latitude}, lon {site.longitude} "
        f"at time {ts} with model {model} and nwp source {nwp_source}"
    )

    if model == "gb":
        return predict_ocf(site, None, ts, nwp_source, live_generation)

    elif model == "xgb":
        if live_generation is not None:
            log.warning(
                "Live generation data is currently not supported with the xgb model. "
                "Ignoring live_generation input."
            )
        return predict_tryolabs(site, ts)

    else:
        raise ValueError(f"Unsupported model: {model}. Choose between 'xgb' and 'gb'")
