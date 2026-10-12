# Quartz Solar Forecast

<!-- ALL-CONTRIBUTORS-BADGE:START - Do not remove or modify this section -->
[![All Contributors](https://img.shields.io/badge/all_contributors-36-orange.svg?style=flat-square)](#contributors-)
<!-- ALL-CONTRIBUTORS-BADGE:END -->

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.15322532.svg)](https://doi.org/10.5281/zenodo.15322532)
[![tags badge](https://img.shields.io/github/v/tag/openclimatefix/open-source-quartz-solar-forecast?include_prereleases&sort=semver&color=FFAC5F)](https://github.com/openclimatefix/open-source-quartz-solar-forecast/tags)
[![pypi badge](https://img.shields.io/pypi/v/quartz-solar-forecast?&color=07BCDF)](https://pypi.org/project/quartz-solar-forecast/)
[![ease of contribution: easy](https://img.shields.io/badge/ease%20of%20contribution:%20easy-32bd50)](https://github.com/openclimatefix/ocf-meta-repo?tab=readme-ov-file#overview-of-ocfs-nowcasting-repositories) 
[![Python package tests](https://github.com/openclimatefix/open-source-quartz-solar-forecast/actions/workflows/pytest.yaml/badge.svg)](https://github.com/openclimatefix/open-source-quartz-solar-forecast/actions/workflows/pytest.yaml)


The aim of the project is to build an open source PV forecast that is free and easy to use.
The forecast provides the expected generation in `kw` for 0 to 48 hours for a single PV site.

Open Climate Fix also provides a commercial PV forecast, please get in touch at quartz.support@openclimatefix.org

Want to learn more about the project? We've presented Quartz Solar Forecast at two open source conferences:

- **FOSDEM 2024** (Free and Open source Software Developers' European Meeting): How we built Open Quartz, our motivation behind it and its impact on aiding organizations in resource optimization [Watch the talk](https://www.youtube.com/watch?v=NAZ2VeiN1N8)

- **LF Energy 2024**: Exploring Open Quartz's developments - new models, inverter APIs, and our Open Source journey at Open Climate Fix [Watch the talk](https://www.youtube.com/watch?v=YTaq41ztEDg)


The current model uses GFS, ICON, or ECMWF NWPs to predict the solar generation at a site

```python
from quartz_solar_forecast.forecast import run_forecast
from quartz_solar_forecast.pydantic_models import PVSite
from datetime import datetime

# make a pv site object
site = PVSite(latitude=51.75, longitude=-1.25, capacity_kwp=1.25)

# run model for today, using ICON NWP data
predictions_df = run_forecast(site=site, ts=datetime.today(), nwp_source="icon")
```

which should result in a time series similar to this one:

![https://github.com/openclimatefix/Open-Source-Quartz-Solar-Forecast/blob/main/predictions.png?raw=true](https://github.com/openclimatefix/Open-Source-Quartz-Solar-Forecast/blob/main/predictions.png?raw=true)

A colab notebook providing some examples can be found [here](https://colab.research.google.com/drive/1qKDFRpq4Hk-LHgWuDsz_Najc3Zq-GVNY?usp=sharing).

## Generating Forecasts

There is an API to generate forecasts at [https://open.quartz.solar](https://open.quartz.solar/docs). For more detailed information on all available endpoints and parameters, please refer to the [Official API Documentation](https://open.quartz.solar/docs) and the project's `api/` directory.

### Using the Python Script

To generate solar forecasts and save them into a CSV file, follow these steps:

- Run the forecast_csv.py script with desired inputs


```bash
python scripts/forecast_csv.py
```

Replace the --init_time_freq, --start_datetime, --end_datetime, and --site_name with your desired forecast initialization frequency (in hours), start datetime, end datetime, and the name of the forecast or site, respectively.

Output

The script will generate solar forecasts at the specified intervals between the start and end datetimes. The results will be combined into a CSV file named using the site name, start and end datetimes, and the frequency of forecasts. This file will be saved in the scripts/csv_forecasts directory.

## Installation

The source code is currently hosted on GitHub at: https://github.com/openclimatefix/Open-Source-Quartz-Solar-Forecast

Binary installers for the latest released version are available at the Python Package Index (PyPI)

```bash
pip install quartz-solar-forecast
```

You might need to install the following packages first

```bash
conda install -c conda-forge pyresample
```

This can solve the [bug: \_\_\_kmpc_for_static_fini](https://github.com/openclimatefix/Open-Source-Quartz-Solar-Forecast/issues/32).

### Logging

The package logs when `run_forecast` is used. This is useful for OCF to determine how the package is being used 
and how we can make improvements in the future.
Note that any latitudes and longitudes are rounded to 2 decimals places in order to anonymize the data.
If you would like to disable this logging, you can do so by setting the environment variable `QUARTZ_SOLAR_FORECAST_LOGGING` to `False`.

### API Monitoring (APITally)

The FastAPI application supports optional monitoring via APITally.

To enable API request monitoring, set the following environment variables before starting the API:

```bash
export APITALLY_CLIENT_ID=your_client_id
export APITALLY_ENVIRONMENT=open_quartz_local
```

## Model

Two models are currently available to make predictions.

**Gradient Boosting Model** (default)

The model uses GFS, ICON, or ECMWF NWPs to predict the solar generation at a site.
It is a gradient boosted tree model and uses 9 NWP variables.
It is trained on 25,000 PV sites with over 5 years of PV history, which is available [here](https://huggingface.co/datasets/openclimatefix/uk_pv).
The training of this model is handled in [pv-site-prediction](https://github.com/openclimatefix/pv-site-prediction)
TODO - we need to benchmark this forecast.

The 9 NWP variables are listed below, with the units the model was trained on (UKV NWP).
They are fetched from Open-Meteo and converted to these units in `quartz_solar_forecast/data.py`.

1. **Visibility (m)**, or vis: Distance at which objects can be clearly seen. Can affect the amount of sunlight reaching solar panels.
2. **Wind Speed at 10 meters (m/s)**, or si10 : Wind speed measured at a height of 10 meters above ground level. Important for understanding weather conditions and potential impacts on solar panels.
3. **Temperature at 2 meters (K)**, or t : Air temperature measure at 2 meters above the ground. Can affect the efficiency of PV systems.
4. **Precipitation rate (kg m⁻² s⁻¹)**, or prate : Precipitation (rain, snow, sleet, etc.). Helps to predict cloud cover and potentiel reductions in solar irradiance.
5. **Shortwave Radiation (W/m²)**, or dswrf: Solar radiation in the shortwave spectrum reaching the Earth's surface. Measure of the potential solar energy available for PV systems.
6. **Downward Longwave Radiation (W/m²)** or dlwrf: Longwave (infrared) radiation emitted by the atmosphere down to the surface. Open-Meteo does not provide this, so it is estimated from temperature, dew point and cloud cover.
7. **Cloud Cover low (%)**, or lcc: Percentage of the sky covered by clouds at low altitudes. Impacts the amount of solar radiation reachign the ground, and similarly the PV system.
8. **Cloud Cover mid (%)**, or mcc : Percentage of the sky covered by clouds at mid altitudes.
9. **Cloud Cover high (%)**, or hcc : Percentage of the sky covered by clouds at high altitude
   We also use the following features

- poa_global: The plane of array irradiance, which is the amount of solar radiation that strikes a solar panel.
- poa_global_now_is_zero: A boolean variable that is true if the poa_global is zero at the current time. This is used to help the model learn that the PV generation is zero at night.
- capacity (kw): The capacity of the PV system in kw.
- The model also has a feature to check if these variables are NaNs or not.
  The model also uses the following variables, which are currently all set to nan
- recent_power: The mean power over the last 30 minutes
- h_mean: The mean of the recent pv data over the last 7 days
- h_median: The median of the recent pv data over the last 7 days
- h_max: The max of the recent pv data over the last 7 days

**XGBoost**

The second option is an XGBoost model and uses the following Numerical Weather Predictions (NWP) input features achieved from [open-meteo](https://open-meteo.com/) variables. Different types of data is provided by open-meteo. To train this model hourly forecast data of [the historical weather API](https://open-meteo.com/en/docs/historical-weather-api) was used. The time period is restricted by the availabilty of the target solar enegery data of the panels and covers the time between 2018 and 2021. Additional information about the time, location and specifics about the panel are used. The weather features used are listed below, with the description given by open-meteo.

- Temperature at 2m (ºC): Air temperature at 2 meters above ground
- Relative Humidity at 2m (%): Relative humidity at 2 meters above ground
- Dewpoint at 2m (ºC): Dew point temperature at 2 meters above ground
- Precipitation (rain + snow) (mm): Total precipitation (rain, showers, snow) sum of the preceding hour
- Surface Pressure (hPa): Atmospheric air pressure reduced to mean sea level (msl) or pressure at surface. Typically pressure on mean sea level is used in meteorology. Surface pressure gets lower with increasing elevation.
- Cloud Cover Total (%): Total cloud cover as an area fraction
- Cloud Cover Low (%): Low level clouds and fog up to 3 km altitude
- Cloud Cover Mid (%): Mid level clouds from 3 to 8 km altitude
- Cloud Cover High (%): High level clouds from 8 km altitude
- Wind Speed at 10m (km/h): Wind speed at 10, 80, 120 or 180 meters above ground. Wind speed on 10 meters is the standard level.
- Wind Direction (10m): Wind direction at 10 meters above ground
- Is day or Night: 1 if the current time step has daylight, 0 at night
- Direct Solar Radiation (W/m2): Direct solar radiation as average of the preceding hour on the horizontal plane and the normal plane (perpendicular to the sun)
- Diffusive Solar Radiation DHI (W/m2): Diffuse solar radiation as average of the preceding hour

To use this model specify `model="xgb"` in `run_forecast(site=site, model="xgb", ts=datetime.today())`.

## Model Comparisons

The following plot shows example predictions of both models for the same time period. Additionally for the Gradient Boosting model (default) the results from the two different data sources are shown.

![model comparison](images/model_data_comparison_hr.png)
_Predictions using the two different models and different data sources._

## Known restrictions

- The model is trained on [UK MetOffice](https://www.metoffice.gov.uk/services/data/met-office-weather-datahub) NWPs, but when running inference we use [GFS](https://www.ncei.noaa.gov/products/weather-climate-models/global-forecast) data from [Open-meteo](https://open-meteo.com/). The differences between GFS and UK MetOffice could led to some odd behaviours.
- Depending, whether the timestamp for the prediction lays more than 90 days in the past or not, different data sources for the NWP are used. If we predict within the last 90 days, we can use ICON, GFS, or ECMWF from the open-meteo Weather Forecast API. Since ICON doesn't provide visibility, this parameter is queried from GFS in any case. If the date for the prediction is further back in time, a reanalysis model of historical data is used (open-meteo | Historical Weather API). The historical weather API doesn't provide visibility at all, that's why it's set to a maximum of 24000 meter in this case. This can lead to some loss of precision.
- The model was trained and tested only over the UK, applying it to other geographical regions should be done with caution.
- When using the XGBoost model, only hourly predictions within the last 90 days are available for data consistency.

## Evaluation

**Gradient Boosting Model** (default)

To evaluate the model we use the [UK PV](https://huggingface.co/datasets/openclimatefix/uk_pv) dataset and the [ICON NWP](https://huggingface.co/datasets/openclimatefix/dwd-icon-eu) dataset.
All the data is publicly available and the evaluation script can be run with the following command

```bash
python scripts/run_evaluation.py
```

The test dataset we used is defined in `quartz_solar_forecast/dataset/testset.csv`.
This contains 50 PV sites, which 50 unique timestamps. The data is from 2021.

The results of the evaluation are as follows The MAE is 0.1906 kw across all horizons.

| Horizons | MAE [kw]      | MAE [%] |
| -------- | ------------- | ------- |
| 0        | 0.202 +- 0.03 | 6.2     |
| 1        | 0.211 +- 0.03 | 6.4     |
| 2        | 0.216 +- 0.03 | 6.5     |
| 3 - 4    | 0.211 +- 0.02 | 6.3     |
| 5 - 8    | 0.191 +- 0.01 | 6       |
| 9 - 16   | 0.161 +- 0.01 | 5       |
| 17 - 24  | 0.173 +- 0.01 | 5.3     |
| 24 - 48  | 0.201 +- 0.01 | 6.1     |

If we exclude nighttime, then the average MAE [%] from 0 to 36 forecast hours is 13.0%.

Notes:

- The MAE in % is the MAE divided by the capacity of the PV site. We acknowledge there are a number of different ways to do this.
- It is slightly surprising that the 0-hour forecast horizon and the 24-48 hour horizon have a similar MAE.
  This may be because the model is trained expecting live PV data, but currently in this project we provide no live PV data.

**XGBoost**

The model was trained and evaluated on 1147 solar panels and tested on 37 independent locations. An intensive hyperparameter tuning was performed. The model provides a feature importance list. Different metrics were calculated and analyzed. Finally the model was evaluated using the Mean Absolute Error (MAE). The MAE over the entire test data is $0.12$ kW, when the night times are excluded the MAE is $0.21$ kW. A plot with the MAE for each panel in the test set is shown in the figure below.

![MAE](images/mae_test.png)
_Mean absolute error for the panels in the test set._

Notes:

- The evaluation per horizon is not available for this model, as it is not provided by the open-meteo data.

## Development Environment Setup

To set up the development environment for this project, follow these steps:

1. **Clone the repository:**
  ```bash
  git clone https://github.com/openclimatefix/open-source-quartz-solar-forecast.git
  cd open-source-quartz-solar-forecast
  ```

2. **Create a virtual environment:**
  ```bash
  python3 -m venv venv
  source venv/bin/activate  # On Windows use `venv\Scripts\activate`
  ```

3. **Install the package in editable mode (uses `pyproject.toml`):**
  ```bash
  pip install -e .
  ```

4. **Run the Jupyter Notebook server:**
  ```bash
  jupyter notebook
  ```

5. **Open your browser and navigate to:**
  ```bash
  http://localhost:8888
  ```

## Abbreviations

- NWP: Numerical Weather Predictions
- GFS: Global Forecast System
- PV: Photovoltaic
- MAE: Mean Absolute Error
- [ICON](https://www.dwd.de/EN/ourservices/nwp_forecast_data/nwp_forecast_data.html): ICOsahedral Nonhydrostatic
- [ECMWF IFS](https://www.ecmwf.int/en/forecasts/datasets/open-data): European Centre for Medium-Range Weather Forecasts Integrated Forecasting System
- KW: Kilowatt

## FOSDEM

FOSDEM is a free event for software developers to meet, share ideas and collaborate. Every year, thousands of developers of free and open source software from all over the world gather at the event in Brussels.
OCF presented Quartz Solar Forecast project at FOSDEM 2024. The link to the original FOSDEM video is availble at [Quartz Solar OS: Building an open source AI solar forecast for everyone](https://fosdem.org/2024/schedule/event/fosdem-2024-2960-quartz-solar-os-building-an-open-source-ai-solar-forecast-for-everyone/).
It is also available on [YouTube](https://www.youtube.com/watch?v=NAZ2VeiN1N8)

## Running the dashboard locally

Start the API first (port 8000):
`cd api`
`python main.py`

Start the frontend (port 5137):
`cd dashboards/dashboard_1`
`npm install`
`npm run dev`

There is also a steamlit dashboard in `dashboards/dashboard_2` that can be used. 

## Global Model

Although this model is trained on UK data, this tool has been used in the following countries, (please let us know if you want your country to be added)

🇬🇧🇺🇸🇦🇺🇧🇦🇪🇸🇯🇵🇨🇳🇧🇪🇩🇪🇫🇷🇵🇹🇳🇱🇮🇳🇰🇷

## Contribution

We welcome other models.

## Contributors ✨

Thanks goes to these wonderful people ([emoji key](https://allcontributors.org/docs/en/emoji-key)):

<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<table>
  <tbody>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/peterdudfield"><img src="https://avatars.githubusercontent.com/u/34686298?v=4?s=100" width="100px;" alt="Peter Dudfield"/><br /><sub><b>Peter Dudfield</b></sub></a><br /><a href="https://github.com/openclimatefix/open-source-quartz-solar-forecast/commits?author=peterdudfield" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/zakwatts"><img src="https://avatars.githubusercontent.com/u/47150349?v=4?s=100" width="100px;" alt="Megawattz"/><br /><sub><b>Megawattz</b></sub></a><br /><a href="#ideas-zakwatts" title="Ideas, Planning, & Feedback">🤔</a> <a href="#talk-zakwatts" title="Talks">📢</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/EdFage"><img src="https://avatars.githubusercontent.com/u/87755165?v=4?s=100" width="100px;" alt="EdFage"/><br /><sub><b>EdFage</b></sub></a><br /><a href="https://github.com/openclimatefix/open-source-quartz-solar-forecast/commits?author=EdFage" title="Documentation">📖</a> <a href="https://github.com/openclimatefix/open-source-quartz-solar-forecast/commits?author=EdFage" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/chloepilonv"><img src="https://avatars.githubusercontent.com/u/136987461?v=4?s=100" width="100px;" alt="Chloe Pilon Vaillancourt"/><br /><sub><b>Chloe Pilon Vaillancourt</b></sub></a><br /><a href="https://github.com/openclimatefix/open-source-quartz-solar-forecast/commits?author=chloepilonv" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="http://racheltipton.dev"><img src="https://avatars.githubusercontent.com/u/86949265?v=4?s=100" width="100px;" alt="rachel tipton"/><br /><sub><b>rachel tipton</b></sub></a><br /><a href="#talk-rachel-labri-tipton" title="Talks">📢</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/armenbod"><img src="https://avatars.githubusercontent.com/u/84937223?v=4?s=100" width="100px;" alt="armenbod"/><br /><sub><b>armenbod</b></sub></a><br /><a href="#content-armenbod" title="Content">🖋</a> <a href="https://github.com/openclimatefix/open-source-quartz-solar-forecast/commits?author=armenbod" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/shreyasudaya"><img src="https://avatars.githubusercontent.com/u/94735680?v=4?s=100" width="100px;" alt="Shreyas Udaya"/><br /><sub><b>Shreyas Udaya</b></sub></a><br /><a href="https://github.com/openclimatefix/open-source-quartz-solar-forecast/commits?author=shreyasudaya" title="Documentation">📖</a></td>
    </tr>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="http://github.com/aryanbhosale"><img src="https://avatars.githubusercontent.com/u/36108149?v=4?s=100" width="100px;" alt="Aryan Bhosale"/><br /><sub><b>Aryan Bhosale</b></sub></a><br /><a href="https://github.com/openclimatefix/open-source-quartz-solar-forecast/commits?author=aryanbhosale" title="Documentation">📖</a> <a href="https://github.com/openclimatefix/open-source-quartz-solar-forecast/commits?author=aryanbhosale" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/0xFrama"><img src="https://avatars.githubusercontent.com/u/30957828?v=4?s=100" width="100px;" alt="Francesco"/><br /><sub><b>Francesco</b></sub></a><br /><a href="https://github.com/openclimatefix/open-source-quartz-solar-forecast/commits?author=0xFrama" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/roshnaeem"><img src="https://avatars.githubusercontent.com/u/47316899?v=4?s=100" width="100px;" alt="Rosheen Naeem"/><br /><sub><b>Rosheen Naeem</b></sub></a><br /><a href="https://github.com/openclimatefix/open-source-quartz-solar-forecast/commits?author=roshnaeem" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/bikramb98"><img src="https://avatars.githubusercontent.com/u/24806286?v=4?s=100" width="100px;" alt="Bikram Baruah"/><br /><sub><b>Bikram Baruah</b></sub></a><br /><a href="https://github.com/openclimatefix/open-source-quartz-solar-forecast/commits?author=bikramb98" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/Hapyr"><img src="https://avatars.githubusercontent.com/u/23398802?v=4?s=100" width="100px;" alt="Jakob Gebler"/><br /><sub><b>Jakob Gebler</b></sub></a><br /><a href="https://github.com/openclimatefix/open-source-quartz-solar-forecast/issues?q=author%3AHapyr" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/ombhojane"><img src="https://avatars.githubusercontent.com/u/82753658?v=4?s=100" width="100px;" alt="Om Bhojane"/><br /><sub><b>Om Bhojane</b></sub></a><br /><a href="https://github.com/openclimatefix/open-source-quartz-solar-forecast/commits?author=ombhojane" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="http://chrisadams.me.uk"><img src="https://avatars.githubusercontent.com/u/17906?v=4?s=100" width="100px;" alt="Chris Adams"/><br /><sub><b>Chris Adams</b></sub></a><br /><a href="#ideas-mrchrisadams" title="Ideas, Planning, & Feedback">🤔</a></td>
    </tr>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/mudrap17"><img src="https://avatars.githubusercontent.com/u/76879120?v=4?s=100" width="100px;" alt="Mudra Patel"/><br /><sub><b>Mudra Patel</b></sub></a><br /><a href="https://github.com/openclimatefix/open-source-quartz-solar-forecast/commits?author=mudrap17" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/diegomarvid"><img src="https://avatars.githubusercontent.com/u/33181424?v=4?s=100" width="100px;" alt="Diego Marvid"/><br /><sub><b>Diego Marvid</b></sub></a><br /><a href="https://github.com/openclimatefix/open-source-quartz-solar-forecast/commits?author=diegomarvid" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/froukje"><img src="https://avatars.githubusercontent.com/u/10419258?v=4?s=100" width="100px;" alt="Frauke Albrecht"/><br /><sub><b>Frauke Albrecht</b></sub></a><br /><a href="https://github.com/openclimatefix/open-source-quartz-solar-forecast/commits?author=froukje" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/Ludecan"><img src="https://avatars.githubusercontent.com/u/17169248?v=4?s=100" width="100px;" alt="Pablo Alfaro"/><br /><sub><b>Pablo Alfaro</b></sub></a><br /><a href="https://github.com/openclimatefix/open-source-quartz-solar-forecast/pulls?q=is%3Apr+reviewed-by%3ALudecan" title="Reviewed Pull Requests">👀</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/KelRem"><img src="https://avatars.githubusercontent.com/u/175075550?v=4?s=100" width="100px;" alt="KelRem"/><br /><sub><b>KelRem</b></sub></a><br /><a href="#question-KelRem" title="Answering Questions">💬</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/sicunchen"><img src="https://avatars.githubusercontent.com/u/14258987?v=4?s=100" width="100px;" alt="Lia Chen"/><br /><sub><b>Lia Chen</b></sub></a><br /><a href="https://github.com/openclimatefix/open-source-quartz-solar-forecast/commits?author=sicunchen" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://clementlumumba.netlify.app/"><img src="https://avatars.githubusercontent.com/u/43673340?v=4?s=100" width="100px;" alt="Clement Lumumba"/><br /><sub><b>Clement Lumumba</b></sub></a><br /><a href="https://github.com/openclimatefix/open-source-quartz-solar-forecast/commits?author=Clemo97" title="Code">💻</a></td>
    </tr>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/aayushyatiwari"><img src="https://avatars.githubusercontent.com/u/169576527?v=4?s=100" width="100px;" alt="aayush"/><br /><sub><b>aayush</b></sub></a><br /><a href="https://github.com/openclimatefix/open-source-quartz-solar-forecast/commits?author=aayushyatiwari" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/Brohan7524"><img src="https://avatars.githubusercontent.com/u/85754035?v=4?s=100" width="100px;" alt="Rohan Singh"/><br /><sub><b>Rohan Singh</b></sub></a><br /><a href="https://github.com/openclimatefix/open-source-quartz-solar-forecast/commits?author=Brohan7524" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/sumana-2705"><img src="https://avatars.githubusercontent.com/u/110307215?v=4?s=100" width="100px;" alt="Sumana Sree Angajala"/><br /><sub><b>Sumana Sree Angajala</b></sub></a><br /><a href="https://github.com/openclimatefix/open-source-quartz-solar-forecast/commits?author=sumana-2705" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/EmilyIsCoding"><img src="https://avatars.githubusercontent.com/u/98443131?v=4?s=100" width="100px;" alt="Emily"/><br /><sub><b>Emily</b></sub></a><br /><a href="https://github.com/openclimatefix/open-source-quartz-solar-forecast/commits?author=EmilyIsCoding" title="Tests">⚠️</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/sergejlazuk"><img src="https://avatars.githubusercontent.com/u/33606741?v=4?s=100" width="100px;" alt="sergejla"/><br /><sub><b>sergejla</b></sub></a><br /><a href="#question-sergejlazuk" title="Answering Questions">💬</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/JadeVexo"><img src="https://avatars.githubusercontent.com/u/66781710?v=4?s=100" width="100px;" alt="Jaay"/><br /><sub><b>Jaay</b></sub></a><br /><a href="https://github.com/openclimatefix/open-source-quartz-solar-forecast/commits?author=JadeVexo" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="http://rachitex.me"><img src="https://avatars.githubusercontent.com/u/18143615?v=4?s=100" width="100px;" alt="Rachit Mishra"/><br /><sub><b>Rachit Mishra</b></sub></a><br /><a href="https://github.com/openclimatefix/open-source-quartz-solar-forecast/commits?author=rachitex" title="Documentation">📖</a></td>
    </tr>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/vashisthrahul13"><img src="https://avatars.githubusercontent.com/u/182660137?v=4?s=100" width="100px;" alt="Rahul Vashisth"/><br /><sub><b>Rahul Vashisth</b></sub></a><br /><a href="https://github.com/openclimatefix/open-source-quartz-solar-forecast/commits?author=vashisthrahul13" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/LynnLawren"><img src="https://avatars.githubusercontent.com/u/107563516?v=4?s=100" width="100px;" alt="Lynn Mary Lawrence"/><br /><sub><b>Lynn Mary Lawrence</b></sub></a><br /><a href="https://github.com/openclimatefix/open-source-quartz-solar-forecast/commits?author=LynnLawren" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/j4ckieee"><img src="https://avatars.githubusercontent.com/u/146953876?v=4?s=100" width="100px;" alt="Jackie Truong"/><br /><sub><b>Jackie Truong</b></sub></a><br /><a href="https://github.com/openclimatefix/open-source-quartz-solar-forecast/commits?author=j4ckieee" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/binaryecheos"><img src="https://avatars.githubusercontent.com/u/130131792?v=4?s=100" width="100px;" alt="Gourav Sahu "/><br /><sub><b>Gourav Sahu </b></sub></a><br /><a href="https://github.com/openclimatefix/open-source-quartz-solar-forecast/commits?author=binaryecheos" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="http://hrsvrn.com"><img src="https://avatars.githubusercontent.com/u/76729417?v=4?s=100" width="100px;" alt="Harshvardhan Vatsa"/><br /><sub><b>Harshvardhan Vatsa</b></sub></a><br /><a href="#infra-hrsvrn" title="Infrastructure (Hosting, Build-Tools, etc)">🚇</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/Krishnadubey1008"><img src="https://avatars.githubusercontent.com/u/121748506?v=4?s=100" width="100px;" alt="Krishna Dubey"/><br /><sub><b>Krishna Dubey</b></sub></a><br /><a href="https://github.com/openclimatefix/open-source-quartz-solar-forecast/commits?author=Krishnadubey1008" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/akshay-juneja"><img src="https://avatars.githubusercontent.com/u/226966641?v=4?s=100" width="100px;" alt="Akshay Juneja"/><br /><sub><b>Akshay Juneja</b></sub></a><br /><a href="https://github.com/openclimatefix/open-source-quartz-solar-forecast/commits?author=akshay-juneja" title="Documentation">📖</a></td>
    </tr>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/yuvraajnarula"><img src="https://avatars.githubusercontent.com/u/49155095?v=4?s=100" width="100px;" alt="Yuvraaj Narula"/><br /><sub><b>Yuvraaj Narula</b></sub></a><br /><a href="https://github.com/openclimatefix/open-source-quartz-solar-forecast/commits?author=yuvraajnarula" title="Documentation">📖</a></td>
    </tr>
  </tbody>
</table>

<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->

<!-- ALL-CONTRIBUTORS-LIST:END -->

This project follows the [all-contributors](https://github.com/all-contributors/all-contributors) specification. Contributions of any kind welcome!
