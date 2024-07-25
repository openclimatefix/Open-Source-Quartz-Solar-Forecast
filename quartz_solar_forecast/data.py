""" Function to get NWP data and create fake PV dataset"""
import ssl
from datetime import datetime
import os  
import numpy as np
import pandas as pd
import xarray as xr
import openmeteo_requests
import requests_cache
import asyncio

from retry_requests import retry
from typing import Optional

from quartz_solar_forecast.pydantic_models import PVSite
from quartz_solar_forecast.inverters.enphase import get_enphase_data
from quartz_solar_forecast.inverters.solis import get_solis_data

ssl._create_default_https_context = ssl._create_unverified_context

from dotenv import load_dotenv

load_dotenv()  

def get_nwp(site: PVSite, ts: datetime, nwp_source: str = "icon") -> xr.Dataset:
    """
    Get GFS NWP data for a point time space and time

    :param site: the PV site
    :param ts: the timestamp for when you want the forecast for
    :param nwp_source: the nwp data source. Either "gfs" or "icon". Defaults to "icon"
    :return: nwp forecast in xarray
    """

    # Setup the Open-Meteo API client with cache and retry on error
    cache_session = requests_cache.CachedSession('.cache', expire_after = -1)
    retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
    openmeteo = openmeteo_requests.Client(session = retry_session)

    # Define the variables we want. Visibility is handled separately after the main request
    variables = [
        "temperature_2m", 
        "precipitation", 
        "cloud_cover_low", 
        "cloud_cover_mid", 
        "cloud_cover_high", 
        "wind_speed_10m", 
        "shortwave_radiation", 
        "direct_radiation"
    ]

    start = ts.date()
    end = start + pd.Timedelta(days=7)

    url = ""

    # check whether the time stamp is more than 3 months in the past
    if (datetime.now() - ts).days > 90:
        print("Warning: The requested timestamp is more than 3 months in the past. The weather data are provided by a reanalyse model and not ICON or GFS.")
        
        # load data from open-meteo Historical Weather API
        url = "https://archive-api.open-meteo.com/v1/archive"

    else:

        # Getting NWP from open meteo weather forecast API by ICON or GFS model within the last 3 months
        url_nwp_source = None
        if nwp_source == "icon":
            url_nwp_source = "dwd-icon"
        elif nwp_source == "gfs":
            url_nwp_source = "gfs"
        else:
            raise Exception(f'Source ({nwp_source}) must be either "icon" or "gfs"')

        url = f"https://api.open-meteo.com/v1/{url_nwp_source}"

    params = {
    	"latitude": site.latitude,
    	"longitude": site.longitude,
    	"start_date": f"{start}",
    	"end_date": f"{end}",
    	"hourly": variables
    }
    response = openmeteo.weather_api(url, params=params)
    hourly = response[0].Hourly()

    hourly_data = {"time": pd.date_range(
    	start = pd.to_datetime(hourly.Time(), unit = "s", utc = False),
    	end = pd.to_datetime(hourly.TimeEnd(), unit = "s", utc = False),
    	freq = pd.Timedelta(seconds = hourly.Interval()),
    	inclusive = "left"
    )}


    # variables index as in the variables array of the request
    hourly_data["t"] = hourly.Variables(0).ValuesAsNumpy()
    hourly_data["prate"] = hourly.Variables(1).ValuesAsNumpy()
    hourly_data["lcc"] = hourly.Variables(2).ValuesAsNumpy()
    hourly_data["mcc"] = hourly.Variables(3).ValuesAsNumpy()
    hourly_data["hcc"] = hourly.Variables(4).ValuesAsNumpy()
    hourly_data["si10"] = hourly.Variables(5).ValuesAsNumpy()
    hourly_data["dswrf"] = hourly.Variables(6).ValuesAsNumpy()
    hourly_data["dlwrf"] = hourly.Variables(7).ValuesAsNumpy()

    # handle visibility 
    if (datetime.now() - ts).days <= 90:
        # load data from open-meteo gfs model
        params = {
        	"latitude": site.latitude,
        	"longitude": site.longitude,
        	"start_date": f"{start}",
        	"end_date": f"{end}",
        	"hourly": "visibility"
        }
        data_vis_gfs = openmeteo.weather_api("https://api.open-meteo.com/v1/gfs", params=params)[0].Hourly().Variables(0).ValuesAsNumpy()
        hourly_data["vis"] = data_vis_gfs
    else:
        # set to maximum visibility possible
        hourly_data["vis"] = 24000.0

    df = pd.DataFrame(data = hourly_data)
    df = df.set_index("time")
    df = df.astype('float64')

    # convert data into xarray
    data_xr = format_nwp_data(df, nwp_source, site)

    return data_xr

def format_nwp_data(df: pd.DataFrame, nwp_source:str, site: PVSite):
    data_xr = xr.DataArray(
        data=df.values,
        dims=["step", "variable"],
        coords=dict(
            step=("step", df.index - df.index[0]),
            variable=df.columns,
        ),
    )
    data_xr = data_xr.to_dataset(name=nwp_source)
    data_xr = data_xr.assign_coords(
        {"x": [site.longitude], "y": [site.latitude], "time": [df.index[0]]}
    )
    return data_xr

def process_pv_data(live_generation_kw: Optional[pd.DataFrame], ts: pd.Timestamp, site: PVSite) -> xr.Dataset:
    """
    Process PV data and create an xarray Dataset.
    
    :param live_generation_kw: DataFrame containing live generation data, or None
    :param ts: Current timestamp
    :param site: PV site information
    :return: xarray Dataset containing processed PV data
    """
    if live_generation_kw is not None and not live_generation_kw.empty:
        # get the most recent data
        recent_pv_data = live_generation_kw[live_generation_kw['timestamp'] <= ts]
        power_kw = np.array([np.array(recent_pv_data["power_kw"].values, dtype=np.float64)])
        timestamp = recent_pv_data['timestamp'].values
    else:
        # make fake pv data, this is where we could add history of a pv system
        power_kw = [[np.nan]]
        timestamp = [ts]

    da = xr.DataArray(
        data=power_kw,
        dims=["pv_id", "timestamp"],
        coords=dict(
            longitude=(["pv_id"], [site.longitude]),
            latitude=(["pv_id"], [site.latitude]),
            timestamp=timestamp,
            pv_id=[1],
            kwp=(["pv_id"], [site.capacity_kwp]),
            tilt=(["pv_id"], [site.tilt]),
            orientation=(["pv_id"], [site.orientation]),
        ),
    )
    da = da.to_dataset(name="generation_kw")

    return da

def make_pv_data(site: PVSite, ts: pd.Timestamp) -> xr.Dataset:
    """
    Make PV data by combining live data from Enphase or Solis and fake PV data.
    Later we could add PV history here.
    :param site: the PV site
    :param ts: the timestamp of the site
    :return: The combined PV dataset in xarray form
    """
    # Initialize live_generation_kw to None
    live_generation_kw = None  

    # Check if the site has an inverter type specified
    if site.inverter_type == 'enphase':
        system_id = os.getenv('ENPHASE_SYSTEM_ID')
        if system_id:
            live_generation_kw = get_enphase_data(system_id)
        else:
            print("Error: Enphase inverter ID is not provided in the environment variables.")
    elif site.inverter_type == 'solis':
        live_generation_kw = asyncio.run(get_solis_data())
        if live_generation_kw is None:
            print("Error: Failed to retrieve Solis inverter data.")
    else:
        # If no inverter type is specified or not recognized, set live_generation_kw to None
        live_generation_kw = None

    print(live_generation_kw)

    # Process the PV data
    da = process_pv_data(live_generation_kw, ts, site)

    return da