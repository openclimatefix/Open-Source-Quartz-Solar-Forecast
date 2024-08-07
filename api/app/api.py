from http.client import HTTPException
import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from dotenv import load_dotenv

# Add the project root to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(project_root)

from .schemas import ForecastRequest, EnphaseTokenRequest
from quartz_solar_forecast.forecast import run_forecast
from quartz_solar_forecast.pydantic_models import PVSite
from .utils.enphase_utils import (
    get_enphase_auth_url_wrapper,
    get_enphase_access_token_wrapper
)
from quartz_solar_forecast.inverters.enphase import (
    get_enphase_auth_url
)

# Load environment variables
load_dotenv()

app = FastAPI()

# CORS middleware setup
origins = [
    "http://localhost:5173",
    "localhost:5173",
    "http://localhost:8501",
    "localhost:8501"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.post("/forecast/")
def forecast(request: ForecastRequest):
    site = request.site
    ts = request.timestamp if request.timestamp else pd.Timestamp.now(tz='UTC').isoformat()
    nwp_source = request.nwp_source
    access_token = request.access_token
    enphase_system_id = request.enphase_system_id

    timestamp = pd.Timestamp(ts).tz_localize(None)
    formatted_timestamp = timestamp.strftime('%Y-%m-%d %H:%M:%S')

    # Run forecast without live data
    site_no_live = PVSite(latitude=site.latitude, longitude=site.longitude, capacity_kwp=site.capacity_kwp)
    predictions_no_live = run_forecast(site=site_no_live, ts=timestamp, nwp_source=nwp_source)

    if site.inverter_type:  # Run forecast with live data only if inverter is specified
        predictions_with_live = run_forecast(site=site, ts=timestamp, nwp_source=nwp_source)
        predictions_with_live['power_kw_no_live_pv'] = predictions_no_live['power_kw']
        predictions = predictions_with_live
    else:
        predictions = predictions_no_live.rename(columns={'power_kw': 'power_kw_no_live_pv'})

    response = {
        "timestamp": formatted_timestamp,
        "predictions": predictions.to_dict()
    }
    
    return response

@app.get("/solar_inverters/enphase/auth_url")
def get_enphase_authorization_url():
    auth_url = get_enphase_auth_url_wrapper()
    return {"auth_url": auth_url}

@app.post("/solar_inverters/enphase/token")
def get_enphase_token(request: EnphaseTokenRequest):
    try:
        access_token = get_enphase_access_token_wrapper(request.redirect_url)
        return {"access_token": access_token}
    except Exception as e:
        print(e)