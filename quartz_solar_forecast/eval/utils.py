import pandas as pd


def combine_forecast_ground_truth(forecast_df: pd.DataFrame, ground_truth_df: pd.DataFrame) ->pd.DataFrame:
    """
    Combine the forecast results with the ground truth (ts, id, horizon (in hours), pred, truth, diff)


    forecast_df should have the following columns
    - timestamp
    - pv_id
    - horizon_hours
    - power

    ground_truth_df should have the following columns
    - timestamp
    - pv_id
    - horizon_hours
    - power

    returns a dataframe with the following columns
    - timestamp
    - pv_id
    - horizon_hours
    - forecast_power
    - generation_power

    """

    # rename power to forecast_power
    forecast_df = forecast_df.rename(columns={"power_kw": "forecast_power"})

    # rename power to ground_truth_power
    ground_truth_df = ground_truth_df.rename(columns={"value": "generation_power"})

    # make pv_ids are ints
    forecast_df["pv_id"] = forecast_df["pv_id"].astype(int)
    ground_truth_df["pv_id"] = ground_truth_df["pv_id"].astype(int)

    # merge the two dataframes
    combined_df = pd.merge(forecast_df, ground_truth_df, on=["timestamp", "pv_id", "horizon_hour"])

    return combined_df


def make_hf_filename(timestamp_floor):
    """
    Make ICON filename from timestamp_floor

    '2021-01-01 00:00:00' ->
    'zip:///::hf://datasets/openclimatefix/dwd-icon-eu/data/2021/1/1/20210101_00.zarr.zip'

    """
    year = timestamp_floor.year
    month = timestamp_floor.month
    day = timestamp_floor.day
    date_and_hour = timestamp_floor.strftime("%Y%m%d_%H")
    date = f"{year}/{month}/{day}"
    file_location = f"{date}/{date_and_hour}"
    huggingface_route = "zip:///::hf://datasets/openclimatefix/dwd-icon-eu/data"
    # huggingface_route = "datasets/openclimatefix/dwd-icon-eu/data"
    huggingface_file = f"{huggingface_route}/{file_location}.zarr.zip"
    return date_and_hour, huggingface_file
