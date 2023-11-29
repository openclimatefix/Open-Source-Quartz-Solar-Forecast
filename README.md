# Quartz Solar Forecast

The aim of the project is to build an open source PV forecast that is free and easy to use.
Open Climate Fix also provide a commercial PV forecast, please get in touch at quartz.support@openclimatefix.org

The current model uses GFS NWPs to predict the solar generation at a site


```python
from quartz_solar_forecast.forecast import run_forecast
from quartz_solar_forecast.pydantic_models import PVSite

# make input data
site = PVSite(latitude=51.75, longitude=-1.25, capacity_kwp=1.25)
ts = datetime(2023, 11, 1, 0, 0, 0)

# run model
predications_df = run_forecast(site=site, ts='2023-11-01')
```

Which gives the following prediction

![predictions.png](predictions.png)

## Model

The model is a gradient boosted tree model and uses 9 NWP variables.
It is trained on 25,000 PV sites with over 5 years of PV history, which is available [here](https://huggingface.co/datasets/openclimatefix/uk_pv).
The training of this model is handled in [pv-site-prediction](https://github.com/openclimatefix/pv-site-prediction)
TODO - we need to benchmark this forecast. 

The 9 NWP variables are mentioned above with their appropariate units. 

1. Visibility (vis), in km : Distance at which objects can be clearly seen. Can affect the amount of sunlight reaching solar panels.
2. Wind Speed at 10 meters (si10), in m/s or km/h : Wind speed measured at a height of 10 meters above ground level. Important for understanding weather conditions and potential impacts on solar panels.
3. Temperature at 2 meters (t), in Degrees Celsius (°C) or Fahrenheit (°F) : Air temperature measure at 2 meters above the ground. Can affect the efficiency of PV systems. 
4. Precipiration rate (prate), in mm/h or in/h : Rate of precipitation (rain, snow, sleet, etc.). Helps to predict cloud cover and potentiel reductions in solar irradiance. 
5. Shortwave Radiation (dswrf), in W/m² : Solar radiation in the shortwave spectrum reaching the Earth's surface. Measure of the potential solar energy available for PV systems. 
6. Direct Radiation (dlwrf), in W/m² : Longwave (infrared) radiation emitted by the Earth back into the atmosphere. **confirm it is correct**
7. Cloud Cover (low, mid or high such as lcc, mcc or hcc), in % or oktas (scale from 0 to 8) : Fraction of the sky covered by clouds at low, mid or high altitudes. Impacts the amount of solar radiation reachign the ground, and similarly the PV system.



## Known restrictions

- The model is trained on [UK MetOffice](https://www.metoffice.gov.uk/services/data/met-office-weather-datahub) NWPs, but when running inference we use [GFS](https://www.ncei.noaa.gov/products/weather-climate-models/global-forecast) data from [Open-meteo](https://open-meteo.com/). The differences between GFS and UK MetOffice, could led to some odd behaviours.
- It looks like the GFS data on Open-Meteo is only available for free for the last 3 months. 

## Abbreviations

- NWP: Numerical Weather Predictions
- GFS: Global Forecast System
- PV: Photovoltaic

## Contribution

We welcome other models