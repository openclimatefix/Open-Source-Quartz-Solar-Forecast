from pydantic import BaseModel, Field

class PVSite(BaseModel):
    latitude: float = Field(..., description="the latitude of the site", ge=-90, le=90)
    longitude: float = Field(
        ..., description="the longitude of the site", ge=-180, le=180
    )
    capacity_kwp: float = Field(..., description="the capacity [kwp] of the site", ge=0)
    tilt: float = Field(
        default=35,
        description="the tilt of the site [degrees], the panels' angle relative to horizontal ground",
        ge=0,
        le=90,
    )
    orientation: float = Field(
        default=180,
        description="the orientation of the site [degrees], the angle between north and the direction the panels face, measured on the horizontal plane.",
        ge=0,
        le=360,
    )
    inverter_type: str = Field(
        default=None,
        description="The type of inverter used",
        json_schema_extra=["enphase", "solis", "givenergy", "solarman", None],
    )
