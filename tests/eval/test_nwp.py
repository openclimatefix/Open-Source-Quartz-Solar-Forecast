from quartz_solar_forecast.eval.nwp import get_nwp, change_from_forecast_mean_to_hourly_mean
import pandas as pd


# can take ~ 1 minute to run
def test_get_nwp():
    # make test dataset file
    test_set_df = pd.DataFrame(
        [
            {
                "timestamp": pd.Timestamp("2021-01-26 01:15:00"),
                "latitude": 51.5,
                "longitude": 0.0,
                "pv_id": 0,
            }
        ]
    )

    # Collect NWP data from Hugging Face, ICON. (Peter)
    _ = get_nwp(test_set_df)


def test_change_from_forecast_mean_to_hourly_mean():
    test_set_df = pd.DataFrame(data=[0, 1, 1.5, 2, 6], columns=["data"])
    df_hourly = change_from_forecast_mean_to_hourly_mean(test_set_df, variable="data")

    assert df_hourly["data"].values[0] == 0
    assert df_hourly["data"].values[1] == 1
    assert df_hourly["data"].values[2] == 2
    assert df_hourly["data"].values[3] == 3
    assert df_hourly["data"].values[4] == 18
