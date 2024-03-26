# Quartz Solar Forecast
<!-- ALL-CONTRIBUTORS-BADGE:START - Do not remove or modify this section -->
[![All Contributors](https://img.shields.io/badge/all_contributors-13-orange.svg?style=flat-square)](#contributors-)
<!-- ALL-CONTRIBUTORS-BADGE:END -->

The aim of the project is to build an open source PV forecast that is free and easy to use.
The forecast provides the expected generation in `kw` for 0 to 48 hours for a single PV site.

Open Climate Fix also provides a commercial PV forecast, please get in touch at quartz.support@openclimatefix.org

The current model uses GFS or ICON NWPs to predict the solar generation at a site

```python
from quartz_solar_forecast.forecast import run_forecast
from quartz_solar_forecast.pydantic_models import PVSite

# make a pv site object
site = PVSite(latitude=51.75, longitude=-1.25, capacity_kwp=1.25)

# run model, uses ICON NWP data by default
predictions_df = run_forecast(site=site, ts='2023-11-01')
```

Which gives the following prediction

![https://github.com/openclimatefix/Open-Source-Quartz-Solar-Forecast/blob/main/predictions.png?raw=true](https://github.com/openclimatefix/Open-Source-Quartz-Solar-Forecast/blob/main/predictions.png?raw=true)

## Generating Forecasts
To generate solar forecasts and save them into a CSV file, follow these steps:
1. Navigate to the scripts directory
```bash
cd scripts
```
2. Run the forecast_csv.py script with desired inputs
```bash
python forecast_csv.py
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
````
This can solve the [bug: ___kmpc_for_static_fini](https://github.com/openclimatefix/Open-Source-Quartz-Solar-Forecast/issues/32).

## Model

The model is a gradient boosted tree model and uses 9 NWP variables.
It is trained on 25,000 PV sites with over 5 years of PV history, which is available [here](https://huggingface.co/datasets/openclimatefix/uk_pv).
The training of this model is handled in [pv-site-prediction](https://github.com/openclimatefix/pv-site-prediction)
TODO - we need to benchmark this forecast. 

The 9 NWP variables, from Open-Meteo documentation, are mentioned above with their appropariate units. 

1. **Visibility (km)**, or vis: Distance at which objects can be clearly seen. Can affect the amount of sunlight reaching solar panels.
2. **Wind Speed at 10 meters (km/h)**, or si10 : Wind speed measured at a height of 10 meters above ground level. Important for understanding weather conditions and potential impacts on solar panels.
3. **Temperature at 2 meters (°C)**, or t : Air temperature measure at 2 meters above the ground. Can affect the efficiency of PV systems. 
4. **Precipiration (mm)**, or prate : Precipitation (rain, snow, sleet, etc.). Helps to predict cloud cover and potentiel reductions in solar irradiance. 
5. **Shortwave Radiation (W/m²)**, or dswrf: Solar radiation in the shortwave spectrum reaching the Earth's surface. Measure of the potential solar energy available for PV systems. 
6. **Direct Radiation (W/m²)** or dlwrf: Longwave (infrared) radiation emitted by the Earth back into the atmosphere. **confirm it is correct**
7. **Cloud Cover low (%)**, or lcc: Percentage of the sky covered by clouds at low altitudes. Impacts the amount of solar radiation reachign the ground, and similarly the PV system.
8. **Cloud Cover mid (%)**, or mcc : Percentage of the sky covered by clouds at mid altitudes. 
9. **Cloud Cover high (%)**, or lcc : Percentage of the sky covered by clouds at high altitude

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

## Running Multiple Forecasts
To run multiple forecasts and save the results, 
1. Navigate to the scripts directory
```bash
cd scripts
```
2. Add new sites to the "sites" dictionary on line 60. 

3. Run 
```bash
python generate_multiple_forecasts.py
```

4. For each site, a new csv will be saved to the "dataset" folder. The csv will be titled forecast_[pv_id].csv.

## Known restrictions

- The model is trained on [UK MetOffice](https://www.metoffice.gov.uk/services/data/met-office-weather-datahub) NWPs, but when running inference we use [GFS](https://www.ncei.noaa.gov/products/weather-climate-models/global-forecast) data from [Open-meteo](https://open-meteo.com/). The differences between GFS and UK MetOffice could led to some odd behaviours.
- It looks like the GFS data on Open-Meteo is only available for free for the last 3 months. 

## Evaluation

To evaluate the model we use the [UK PV](https://huggingface.co/datasets/openclimatefix/uk_pv) dataset and the [ICON NWP](https://huggingface.co/datasets/openclimatefix/dwd-icon-eu) dataset.
All the data is publicly available and the evaluation script can be run with the following command

```bash
python scripts/run_evaluation.py
```

The test dataset we used is defined in `quartz_solar_forecast/dataset/testset.csv`. 
This contains 50 PV sites, which 50 unique timestamps. The data is from 2021. 

The results of the evaluation are as follows
The MAE is 0.1906 kw across all horizons. 

| Horizons | MAE [kw]      | MAE [%] |
|----------|---------------| ------- |
| 0        | 0.202 +- 0.03 | 6.2 |
| 1        | 0.211 +- 0.03 | 6.4 |
| 2        | 0.216 +- 0.03 | 6.5 |
| 3 - 4    | 0.211 +- 0.02 |6.3 |
| 5 - 8    | 0.191 +- 0.01 | 6 |
| 9 - 16   | 0.161 +- 0.01 | 5 |
| 17 - 24  | 0.173 +- 0.01 | 5.3 |
| 24 - 48  | 0.201 +- 0.01 | 6.1 |

If we exclude nighttime, then the average MAE [%] from 0 to 36 forecast hours is 13.0%. 

Notes: 
- The MAE in % is the MAE divided by the capacity of the PV site. We acknowledge there are a number of different ways to do this. 
- It is slightly surprising that the 0-hour forecast horizon and the 24-48 hour horizon have a similar MAE.
This may be because the model is trained expecting live PV data, but currently in this project we provide no live PV data. 

## Abbreviations

- NWP: Numerical Weather Predictions
- GFS: Global Forecast System
- PV: Photovoltaic
- MAE: Mean Absolute Error
- [ICON](https://www.dwd.de/EN/ourservices/nwp_forecast_data/nwp_forecast_data.html): ICOsahedral Nonhydrostatic
- KW: Kilowatt

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
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/peterdudfield"><img src="https://avatars.githubusercontent.com/u/34686298?v=4?s=100" width="100px;" alt="Peter Dudfield"/><br /><sub><b>Peter Dudfield</b></sub></a><br /><a href="https://github.com/openclimatefix/Open-Source-Quartz-Solar-Forecast/commits?author=peterdudfield" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/zakwatts"><img src="https://avatars.githubusercontent.com/u/47150349?v=4?s=100" width="100px;" alt="Megawattz"/><br /><sub><b>Megawattz</b></sub></a><br /><a href="#ideas-zakwatts" title="Ideas, Planning, & Feedback">🤔</a> <a href="#talk-zakwatts" title="Talks">📢</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/EdFage"><img src="https://avatars.githubusercontent.com/u/87755165?v=4?s=100" width="100px;" alt="EdFage"/><br /><sub><b>EdFage</b></sub></a><br /><a href="https://github.com/openclimatefix/Open-Source-Quartz-Solar-Forecast/commits?author=EdFage" title="Documentation">📖</a> <a href="https://github.com/openclimatefix/Open-Source-Quartz-Solar-Forecast/commits?author=EdFage" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/chloepilonv"><img src="https://avatars.githubusercontent.com/u/136987461?v=4?s=100" width="100px;" alt="Chloe Pilon Vaillancourt"/><br /><sub><b>Chloe Pilon Vaillancourt</b></sub></a><br /><a href="https://github.com/openclimatefix/Open-Source-Quartz-Solar-Forecast/commits?author=chloepilonv" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="http://racheltipton.dev"><img src="https://avatars.githubusercontent.com/u/86949265?v=4?s=100" width="100px;" alt="rachel tipton"/><br /><sub><b>rachel tipton</b></sub></a><br /><a href="#talk-rachel-labri-tipton" title="Talks">📢</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/armenbod"><img src="https://avatars.githubusercontent.com/u/84937223?v=4?s=100" width="100px;" alt="armenbod"/><br /><sub><b>armenbod</b></sub></a><br /><a href="#content-armenbod" title="Content">🖋</a> <a href="https://github.com/openclimatefix/Open-Source-Quartz-Solar-Forecast/commits?author=armenbod" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/shreyasudaya"><img src="https://avatars.githubusercontent.com/u/94735680?v=4?s=100" width="100px;" alt="Shreyas Udaya"/><br /><sub><b>Shreyas Udaya</b></sub></a><br /><a href="https://github.com/openclimatefix/Open-Source-Quartz-Solar-Forecast/commits?author=shreyasudaya" title="Documentation">📖</a></td>
    </tr>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="http://github.com/aryanbhosale"><img src="https://avatars.githubusercontent.com/u/36108149?v=4?s=100" width="100px;" alt="Aryan Bhosale"/><br /><sub><b>Aryan Bhosale</b></sub></a><br /><a href="https://github.com/openclimatefix/Open-Source-Quartz-Solar-Forecast/commits?author=aryanbhosale" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/0xFrama"><img src="https://avatars.githubusercontent.com/u/30957828?v=4?s=100" width="100px;" alt="Francesco"/><br /><sub><b>Francesco</b></sub></a><br /><a href="https://github.com/openclimatefix/Open-Source-Quartz-Solar-Forecast/commits?author=0xFrama" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/roshnaeem"><img src="https://avatars.githubusercontent.com/u/47316899?v=4?s=100" width="100px;" alt="Rosheen Naeem"/><br /><sub><b>Rosheen Naeem</b></sub></a><br /><a href="https://github.com/openclimatefix/Open-Source-Quartz-Solar-Forecast/commits?author=roshnaeem" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/bikramb98"><img src="https://avatars.githubusercontent.com/u/24806286?v=4?s=100" width="100px;" alt="Bikram Baruah"/><br /><sub><b>Bikram Baruah</b></sub></a><br /><a href="https://github.com/openclimatefix/Open-Source-Quartz-Solar-Forecast/commits?author=bikramb98" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/Hapyr"><img src="https://avatars.githubusercontent.com/u/23398802?v=4?s=100" width="100px;" alt="Jakob Gebler"/><br /><sub><b>Jakob Gebler</b></sub></a><br /><a href="https://github.com/openclimatefix/Open-Source-Quartz-Solar-Forecast/issues?q=author%3AHapyr" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/ombhojane"><img src="https://avatars.githubusercontent.com/u/82753658?v=4?s=100" width="100px;" alt="Om Bhojane"/><br /><sub><b>Om Bhojane</b></sub></a><br /><a href="https://github.com/openclimatefix/Open-Source-Quartz-Solar-Forecast/commits?author=ombhojane" title="Code">💻</a></td>
    </tr>
  </tbody>
</table>

<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->

<!-- ALL-CONTRIBUTORS-LIST:END -->

This project follows the [all-contributors](https://github.com/all-contributors/all-contributors) specification. Contributions of any kind welcome!

