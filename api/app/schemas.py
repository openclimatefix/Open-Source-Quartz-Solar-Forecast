from typing import Optional
from pydantic import BaseModel
from quartz_solar_forecast.pydantic_models import PVSite

class ForecastRequest(BaseModel):
    site: PVSite
    timestamp: Optional[str] = None
    nwp_source: Optional[str] = "icon"
    access_token: Optional[str] = None
    enphase_system_id: Optional[str] = None

class TokenRequest(BaseModel):
    redirect_url: str