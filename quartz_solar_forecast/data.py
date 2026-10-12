"""Function to get NWP data and create fake PV dataset"""

import ssl
from datetime import datetime

import numpy as np
import openmeteo_requests
import pandas as pd
import requests_cache
import xarray as xr
from retry_requests import retry

from quartz_solar_forecast.pydantic_models import PVSite, PVSiteWithInverter

ssl._create_default_https_context = ssl._create_unverified_context


# Open-Meteo hourly variables requested by get_nwp
OPEN_METEO_VARIABLES = [
    "temperature_2m",
    "precipitation",
    "cloud_cover_low",
    "cloud_cover_mid",
    "cloud_cover_high",
    "cloud_cover",
    "wind_speed_10m",
    "shortwave_radiation",
    "dew_point_2m",
]

STEFAN_BOLTZMANN = 5.670374e-8  # W m-2 K-4


def downward_longwave_radiation(
    temperature_c: np.ndarray, dew_point_c: np.ndarray, cloud_cover_pct: np.ndarray
) -> np.ndarray:
    """
    Estimate downward longwave radiation at the surface, as Open-Meteo does not provide it

    Uses the Brutsaert (1975) clear-sky emissivity with a cloud correction of (1 + 0.22 c^2).

    :param temperature_c: 2 m air temperature in °C
    :param dew_point_c: 2 m dew point in °C
    :param cloud_cover_pct: total cloud cover in %
    :return: downward longwave radiation in W/m²
    """
    temperature_k = temperature_c + 273.15
    # vapour pressure in hPa (Magnus formula)
    vapour_pressure = 6.112 * np.exp(17.67 * dew_point_c / (dew_point_c + 243.5))
    clear_sky_emissivity = 1.24 * (vapour_pressure / temperature_k) ** (1 / 7)
    cloud_fraction = np.clip(cloud_cover_pct / 100.0, 0, 1)
    return (
        STEFAN_BOLTZMANN * temperature_k**4 * clear_sky_emissivity * (1 + 0.22 * cloud_fraction**2)
    )


def open_meteo_to_model_features(open_meteo_data: dict) -> dict:
    """
    Convert Open-Meteo hourly variables into the NWP features and units the gb model was trained on

    The model was trained on UKV data, which uses SI units, so:
    - t: temperature in K (Open-Meteo gives °C)
    - prate: precipitation rate in kg m-2 s-1 (Open-Meteo gives mm in the preceding hour)
    - si10: 10 m wind speed in m/s (Open-Meteo gives km/h)
    - dlwrf: downward longwave radiation in W/m², estimated as Open-Meteo does not provide it
    Cloud covers (%) and shortwave radiation (W/m²) already match.

    :param open_meteo_data: dict of Open-Meteo variable name to values
    :return: dict of model feature name to values
    """
    return {
        "t": open_meteo_data["temperature_2m"] + 273.15,
        "prate": open_meteo_data["precipitation"] / 3600.0,
        "lcc": open_meteo_data["cloud_cover_low"],
        "mcc": open_meteo_data["cloud_cover_mid"],
        "hcc": open_meteo_data["cloud_cover_high"],
        "si10": open_meteo_data["wind_speed_10m"] / 3.6,
        "dswrf": open_meteo_data["shortwave_radiation"],
        "dlwrf": downward_longwave_radiation(
            open_meteo_data["temperature_2m"],
            open_meteo_data["dew_point_2m"],
            open_meteo_data["cloud_cover"],
        ),
    }


def get_nwp(site: PVSite, ts: datetime, nwp_source: str = "icon") -> xr.Dataset:
    """
    Get GFS NWP data for a point time space and time

    :param site: the PV site
    :param ts: the timestamp for when you want the forecast for
    :param nwp_source: the nwp data source. Either "gfs", "icon" or "ukmo". Defaults to "icon"
    :return: nwp forecast in xarray
    """
    now = datetime.now()

    # Setup the Open-Meteo API client with cache and retry on error
    cache_session = requests_cache.CachedSession(".cache", expire_after=-1)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    openmeteo = openmeteo_requests.Client(session=retry_session)

    # Define the variables we want. Visibility is handled separately after the main request
    variables = OPEN_METEO_VARIABLES

    start = ts.date()
    end = start + pd.Timedelta(days=7)

    url = ""

    # check whether the time stamp is more than 3 months in the past
    if (now - ts).days > 90:
        print(
            "Warning: The requested timestamp is more than 3 months in the past. "
            "The weather data are provided by a reanalyse model and not ICON or GFS."
        )

        # load data from open-meteo Historical Weather API
        url = "https://archive-api.open-meteo.com/v1/archive"

    else:
        # Getting NWP from open meteo weather forecast API by ICON, GFS, or UKMO
        # within the last 3 months
        url_nwp_source = {
            "icon": "dwd-icon",
            "gfs": "gfs",
            "ukmo": "ukmo_seamless",
            "ecmwf": "ecmwf",
        }.get(nwp_source)
        if not url_nwp_source:
            raise Exception(
                f'Source ({nwp_source}) must be either "icon", "gfs", "ukmo", or "ecmwf"'
            )
        url = (
            f"https://api.open-meteo.com/v1/"
            f"{url_nwp_source if nwp_source != 'ukmo' else 'forecast'}"
        )

    params = {
        "latitude": site.latitude,
        "longitude": site.longitude,
        "start_date": f"{start}",
        "end_date": f"{end}",
        "hourly": variables,
    }

    # Add the "models" parameter if using "ukmo"
    if nwp_source == "ukmo":
        params["models"] = "ukmo_seamless"

    # Make API call to URL
    response = openmeteo.weather_api(url, params=params)
    hourly = response[0].Hourly()

    hourly_data = {
        "time": pd.date_range(
            start=pd.to_datetime(hourly.Time(), unit="s", utc=False),
            end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=False),
            freq=pd.Timedelta(seconds=hourly.Interval()),
            inclusive="left",
        )
    }

    # responses come back in the order they were requested, so key them by Open-Meteo name
    open_meteo_data = {
        var: hourly.Variables(idx).ValuesAsNumpy() for idx, var in enumerate(variables)
    }
    hourly_data.update(open_meteo_to_model_features(open_meteo_data))

    # handle visibility
    if (now - ts).days <= 90:
        # load data from open-meteo gfs model
        params = {
            "latitude": site.latitude,
            "longitude": site.longitude,
            "start_date": f"{start}",
            "end_date": f"{end}",
            "hourly": "visibility",
        }
        data_vis_gfs = (
            openmeteo.weather_api("https://api.open-meteo.com/v1/gfs", params=params)[0]
            .Hourly()
            .Variables(0)
            .ValuesAsNumpy()
        )
        hourly_data["vis"] = data_vis_gfs
    else:
        # set to maximum visibility possible
        hourly_data["vis"] = 24000.0

    df = pd.DataFrame(data=hourly_data).set_index("time").astype("float64")

    # convert data into xarray
    data_xr = format_nwp_data(df, nwp_source, site)

    return data_xr


def format_nwp_data(df: pd.DataFrame, nwp_source: str, site: PVSite):
    data_xr = xr.DataArray(
        data=df.values,
        dims=["step", "variable"],
        coords={
            "step": ("step", df.index - df.index[0]),
            "variable": df.columns,
        },
    )
    data_xr = data_xr.to_dataset(name=nwp_source)
    data_xr = data_xr.assign_coords(
        {"x": [site.longitude], "y": [site.latitude], "time": [df.index[0]]}
    )
    return data_xr


def process_pv_data(
    live_generation_kw: pd.DataFrame | None, ts: pd.Timestamp, site: "PVSite"
) -> xr.Dataset:
    """
    Process PV data and create an xarray Dataset.

    :param live_generation_kw: DataFrame containing live generation data, or None
    :param ts: Current timestamp
    :param site: PV site information
    :return: xarray Dataset containing processed PV data
    """
    if live_generation_kw is not None and not live_generation_kw.empty:
        # Get the most recent data
        recent_pv_data = live_generation_kw[live_generation_kw["timestamp"] <= ts]
        power_kw = np.array([recent_pv_data["power_kw"].values], dtype=np.float64)
        timestamp = recent_pv_data["timestamp"].values
    else:
        # Make fake PV data; this is where we could add the history of a PV system
        power_kw = np.array([[np.nan]])
        timestamp = [ts]

    da = xr.DataArray(
        data=power_kw,
        dims=["pv_id", "timestamp"],
        coords={
            "longitude": (["pv_id"], [site.longitude]),
            "latitude": (["pv_id"], [site.latitude]),
            "timestamp": timestamp,
            "pv_id": [1],
            "kwp": (["pv_id"], [site.capacity_kwp]),
            "tilt": (["pv_id"], [site.tilt]),
            "orientation": (["pv_id"], [site.orientation]),
        },
    )
    da = da.to_dataset(name="generation_kw")

    return da


def make_pv_data(
    site: PVSite | PVSiteWithInverter, ts: pd.Timestamp, live_generation: pd.DataFrame | None = None
) -> xr.Dataset:
    """
    Make PV data by combining live data from various inverters.

    :param site: the PV site
    :param ts: the timestamp of the site
    :param live_generation: a dataframe containing live generation data for the site
    :return: The combined PV dataset in xarray form
    """
    if isinstance(site, PVSiteWithInverter):
        live_generation_kw = site.get_inverter().get_data(ts)
    else:
        live_generation_kw = live_generation

    # Process the PV data
    da = process_pv_data(live_generation_kw, ts, site)

    return da
