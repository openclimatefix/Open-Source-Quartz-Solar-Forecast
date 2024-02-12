""" Example code to run the forecast"""
from quartz_solar_forecast.forecast import run_forecast
from quartz_solar_forecast.pydantic_models import PVSite


def main():
    # make input data
    site = PVSite(latitude=51.75, longitude=-1.25, capacity_kwp=1.25)

    # run model
    predictions_df = run_forecast(site=site, ts="2023-10-30")

    print(predictions_df)
    print(f"Max: {predictions_df['power_kw'].max()}")


if __name__ == "__main__":
    main()
