import streamlit as st
import http.client
import pandas as pd
from datetime import datetime, timezone, timedelta
import os
import xarray as xr
import base64
import json
import logging

from quartz_solar_forecast.forecasts import forecast_v1_tilt_orientation
from quartz_solar_forecast.pydantic_models import PVSite
from quartz_solar_forecast.forecast import predict_tryolabs
from quartz_solar_forecast.data import get_nwp, process_pv_data
from quartz_solar_forecast.inverters.enphase import get_enphase_auth_url, process_enphase_data

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_enphase_auth_url():
    client_id = os.getenv("ENPHASE_CLIENT_ID")
    redirect_uri = os.getenv("ENPHASE_REDIRECT_URI", "https://api.enphaseenergy.com/oauth/redirect_uri")
    return f"https://api.enphaseenergy.com/oauth/authorize?response_type=code&client_id={client_id}&redirect_uri={redirect_uri}"

def get_enphase_access_token(auth_code):
    client_id = os.getenv("ENPHASE_CLIENT_ID")
    client_secret = os.getenv("ENPHASE_CLIENT_SECRET")
    redirect_uri = os.getenv("ENPHASE_REDIRECT_URI", "https://api.enphaseenergy.com/oauth/redirect_uri")

    credentials = f"{client_id}:{client_secret}"
    encoded_credentials = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")

    conn = http.client.HTTPSConnection("api.enphaseenergy.com")
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {encoded_credentials}"
    }
    payload = f"grant_type=authorization_code&redirect_uri={redirect_uri}&code={auth_code}"

    conn.request("POST", "/oauth/token", payload, headers)
    res = conn.getresponse()
    data = res.read()
    conn.close()

    data_json = json.loads(data.decode("utf-8"))

    if "error" in data_json:
        raise ValueError(f"Error in getting access token: {data_json['error_description']}")

    if "access_token" not in data_json:
        raise KeyError(f"Access token not found in response. Response: {data_json}")

    return data_json["access_token"]

def get_enphase_data(enphase_system_id: str, access_token: str) -> pd.DataFrame:
    api_key = os.getenv("ENPHASE_API_KEY")
    start_at = int((datetime.now() - timedelta(weeks=1)).timestamp())
    granularity = "week"

    conn = http.client.HTTPSConnection("api.enphaseenergy.com")
    headers = {"Authorization": f"Bearer {access_token}", "key": api_key}

    url = f"/api/v4/systems/{enphase_system_id}/telemetry/production_micro?start_at={start_at}&granularity={granularity}"
    conn.request("GET", url, headers=headers)
    res = conn.getresponse()
    data = res.read()
    conn.close()

    data_json = json.loads(data.decode("utf-8"))
    return process_enphase_data(data_json, start_at)

def make_pv_data(
    site: PVSite,
    ts: pd.Timestamp,
    access_token: str = None,
    enphase_system_id: str = None,
    solis_data: pd.DataFrame = None,
    givenergy_data: pd.DataFrame = None,
    solarman_data: pd.DataFrame = None
) -> xr.Dataset:
    live_generation_kw = None

    if site.inverter_type == "enphase" and access_token and enphase_system_id:
        live_generation_kw = get_enphase_data(enphase_system_id, access_token)
    elif site.inverter_type == "solis" and solis_data is not None:
        live_generation_kw = solis_data
    elif site.inverter_type == "givenergy" and givenergy_data is not None:
        live_generation_kw = givenergy_data
    elif site.inverter_type == "solarman" and solarman_data is not None:
        live_generation_kw = solarman_data

    da = process_pv_data(live_generation_kw, ts, site)
    return da

def predict_ocf(
    site: PVSite,
    model=None,
    ts: datetime | str = None,
    nwp_source: str = "icon",
    access_token: str = None,
    enphase_system_id: str = None,
    solis_data: pd.DataFrame = None,
    givenergy_data: pd.DataFrame = None,
    solarman_data: pd.DataFrame = None
):
    if ts is None:
        ts = pd.Timestamp.now().round("15min")
    if isinstance(ts, str):
        ts = datetime.fromisoformat(ts)

    nwp_xr = get_nwp(site=site, ts=ts, nwp_source=nwp_source)
    pv_xr = make_pv_data(
        site=site, ts=ts, access_token=access_token, enphase_system_id=enphase_system_id, 
        solis_data=solis_data, givenergy_data=givenergy_data, solarman_data=solarman_data
    )

    pred_df = forecast_v1_tilt_orientation(nwp_source, nwp_xr, pv_xr, ts, model=model)
    return pred_df

def run_forecast_for_enphase(
    site: PVSite,
    model: str = "gb",
    ts: datetime | str = None,
    nwp_source: str = "icon",
    access_token: str = None,
    enphase_system_id: str = None,
    solis_data: pd.DataFrame = None,
    givenergy_data: pd.DataFrame = None,
    solarman_data: pd.DataFrame = None
) -> pd.DataFrame:
    if model == "gb":
        return predict_ocf(site, None, ts, nwp_source, access_token, enphase_system_id, solis_data, givenergy_data, solarman_data)
    elif model == "xgb":
        return predict_tryolabs(site, ts)
    else:
        raise ValueError(f"Unsupported model: {model}. Choose between 'xgb' and 'gb'")

def fetch_data_and_run_forecast(
    site: PVSite,
    access_token: str = None,
    enphase_system_id: str = None,
    solis_data: pd.DataFrame = None,
    givenergy_data: pd.DataFrame = None,
    solarman_data: pd.DataFrame = None
):
    with st.spinner("Running forecast..."):
        try:
            timestamp = datetime.now().timestamp()
            timestamp_str = datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            ts = pd.to_datetime(timestamp_str)

            # Run forecast with the given site
            predictions_with_inverter = run_forecast_for_enphase(
                site=site,
                ts=ts,
                access_token=access_token,
                enphase_system_id=enphase_system_id,
                solis_data=solis_data,
                givenergy_data=givenergy_data,
                solarman_data=solarman_data
            )

            # Create a site without inverter for comparison
            site_without_inverter = PVSite(
                latitude=site.latitude,
                longitude=site.longitude,
                capacity_kwp=site.capacity_kwp
            )
            predictions_without_inverter = run_forecast_for_enphase(site=site_without_inverter, ts=ts)

            # Combine the results
            predictions_df = predictions_with_inverter.copy()
            predictions_df["power_kw_no_live_pv"] = predictions_without_inverter["power_kw"]

            return predictions_df, ts

        except Exception as e:
            logger.error(f"An error occurred: {str(e)}")
            st.error(f"An error occurred: {str(e)}")
            return None, None