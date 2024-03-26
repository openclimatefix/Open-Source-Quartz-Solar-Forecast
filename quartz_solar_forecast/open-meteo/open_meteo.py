import requests
import pandas as pd
from datetime import datetime, timedelta
import xarray as xr

from quartz_solar_forecast.pydantic_models import PVSite

def fetch_open_meteo_temperature(site: PVSite, ts: datetime):
    """
    Fetch hourly temperature data from the local Open-Meteo API for a specific site.

    :param site: The PV site object containing latitude and longitude.
    :param ts: Timestamp for when the forecast is desired.
    :return: A Dataset with the requested weather data.
    """

    variables = ['temperature_2m', 'precipitation', 'cloud_cover']

    # Format the timestamp to a suitable string format for the API
    start_date = ts.strftime('%Y-%m-%d')
    end_date = (ts + timedelta(days=2)).strftime('%Y-%m-%d')

    # Construct the API URL
    api_url = (
        f"http://127.0.0.1:8080/v1/forecast?latitude={site.latitude}&longitude={site.longitude}"
        f"&hourly={','.join(variables)}"
        f"&start_date={start_date}&end_date={end_date}"
    )

    try:
        response = requests.get(api_url)
        response.raise_for_status()
        data = response.json()

        df = pd.DataFrame({
            'time': pd.to_datetime(data['hourly']['time']),
            'temperature_2m': data['hourly'].get('temperature_2m', [None] * len(data['hourly']['time'])),
            'precipitation': data['hourly'].get('precipitation', [None] * len(data['hourly']['time'])),
            'cloud_cover': data['hourly'].get('cloud_cover', [None] * len(data['hourly']['time']))
        }).set_index('time')

        # Convert the DataFrame to an xarray Dataset
        data_xr = xr.Dataset.from_dataframe(df)

        return df

    except requests.RequestException as e:
        print(f"Request failed: {e}")
        return None


# Example usage
site = PVSite(latitude=47.1, longitude=8.4, capacity_kwp=1)
ts = datetime.now()
data = fetch_open_meteo_temperature(site, ts)
print(data)
