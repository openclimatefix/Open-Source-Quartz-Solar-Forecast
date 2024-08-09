from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from dotenv import load_dotenv
from .schemas import ForecastRequest, TokenRequest
from quartz_solar_forecast.forecast import run_forecast
from quartz_solar_forecast.pydantic_models import PVSite
from .utils.enphase_utils import get_enphase_auth_url, get_enphase_access_token, get_enphase_data, run_forecast_for_enphase

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
    ts = request.timestamp if request.timestamp else datetime.now(timezone.utc).isoformat()
    nwp_source = request.nwp_source
    access_token = request.access_token
    enphase_system_id = request.enphase_system_id

    timestamp = pd.Timestamp(ts).tz_localize(None)
    formatted_timestamp = timestamp.strftime('%Y-%m-%d %H:%M:%S')

    # Run forecast without live data
    site_no_live = PVSite(latitude=site.latitude, longitude=site.longitude, capacity_kwp=site.capacity_kwp)
    predictions_no_live = run_forecast(site=site_no_live, ts=timestamp, nwp_source=nwp_source)

    if site.inverter_type == 'enphase' and access_token and enphase_system_id:
        try:
            live_data = get_enphase_data(enphase_system_id, access_token)
            predictions_with_live = run_forecast_for_enphase(
                site=site, 
                ts=timestamp, 
                nwp_source=nwp_source, 
                access_token=access_token, 
                enphase_system_id=enphase_system_id
            )
            predictions_with_live['power_kw_no_live_pv'] = predictions_no_live['power_kw']
            predictions = predictions_with_live
        except Exception as e:
            print(f"Error fetching Enphase data: {str(e)}")
            predictions = predictions_no_live.rename(columns={'power_kw': 'power_kw_no_live_pv'})
    else:
        # For all other inverter types, use the standard run_forecast function
        predictions_with_live = run_forecast(site=site, ts=timestamp, nwp_source=nwp_source)
        predictions_with_live['power_kw_no_live_pv'] = predictions_no_live['power_kw']
        predictions = predictions_with_live

    response = {
        "timestamp": formatted_timestamp,
        "predictions": predictions.to_dict()
    }
    
    return response

@app.get("/solar_inverters/enphase/auth_url")
def get_enphase_authorization_url():
    auth_url = get_enphase_auth_url()
    return {"auth_url": auth_url}

@app.post("/solar_inverters/enphase/token")
def get_enphase_token(request: TokenRequest):
    if "?code=" not in request.redirect_url:
        raise HTTPException(status_code=400, detail="Invalid redirect URL")
    
    auth_code = request.redirect_url.split("?code=")[1]
    try:
        access_token = get_enphase_access_token(auth_code)
        return {"access_token": access_token}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error getting access token: {str(e)}")