from quartz_solar_forecast.forecast import run_forecast
from quartz_solar_forecast.pydantic_models import PVSite


def test_run_forecast():
    # make input data
    site = PVSite(latitude=51.75, longitude=-1.25, capacity_kwp=1.25)

    # run model
    predications_df = run_forecast(site=site, ts='2023-10-30')

    print(predications_df)
    print(f"Max: {predications_df['power_kw'].max()}")

