""" Get nwp data from HF"""
import os
import sys
import pandas as pd
import numpy as np

import ocf_blosc2  # noqa
import xarray as xr

import multiprocessing

from quartz_solar_forecast.eval.utils import make_hf_filename

multiprocessing.set_start_method("spawn", force=True)


def get_nwp(time_locations: pd.DataFrame):
    """
    Get all the nwp data fpr the time locations

    time_locations should have the following columns:
    - timestamp
    - latitude
    - longitude
    - pv_id
    """

    all_nwp_dfs = []

    tasks_args = []
    with multiprocessing.Pool() as pool:
        for i, row in time_locations.iterrows():
            print(f"Making task {i} of {len(time_locations)}")

            kwargs = {
                "timestamp": row["timestamp"],
                "latitude": row["latitude"],
                "longitude": row["longitude"],
                "pv_id": row["pv_id"],
                "progress": np.round(i / len(time_locations), 3),
            }

            # collect together args for pool.starmap
            task_arg = list(kwargs.values())
            tasks_args.append(task_arg)

        print("Made all NWP tasks, now getting the data")
        results = pool.starmap(get_nwp_for_one_timestamp_one_location, tasks_args)

    print("Got all NWP data")

    for result in results:
        one_nwp_df = result

        all_nwp_dfs.append(one_nwp_df)

    all_nwp_df = pd.concat(all_nwp_dfs)

    return all_nwp_df


def get_nwp_for_one_timestamp_one_location(
    timestamp: pd.Timestamp, latitude, longitude, pv_id: int = None, progress: float = True
):
    """
    Get NWP data from Hugging Face for one timestamp and one location

    :param timestamp: the timestamp for when you want the forecast for
    :param latitude: the latitude of the location
    :param longitude: the longitude of the location
    :param pv_id: the pv_id of the location, if known
    :param progress: Float of how far through the process we are. This is becasue we use multiprocessing
        to pull lots of NWP data. This should be a float between 0 and 1


    :return: nwp forecast in xarray
    """

    # List which files are available. Not all dates, and model run times are available
    # fs = HfFileSystem()
    # print(fs.ls("datasets/openclimatefix/dwd-icon-eu/data/2022/4/11/", detail=False))

    # Ensure timestamp is a pd.Timestamp object
    if not isinstance(timestamp, pd.Timestamp):
        timestamp = pd.to_datetime(timestamp)

    # round timestamp to 6 hours floor
    timestamp_floor = timestamp.floor("6h")
    date_and_hour, huggingface_file = make_hf_filename(timestamp_floor)

    # dataset variables, note these are unique for ICON
    variables = ["t_2m", "tot_prec", "clch", "clcm", "clcl", "u", "v", "aswdir_s", "aswdifd_s"]

    cache_dir = "data/nwp"
    cache_file = f"{cache_dir}/{date_and_hour}_lat={latitude}_lon={longitude}.zarr"
    if not os.path.exists(cache_file):
        # use fsspec to copy file
        print(f"Copying file {huggingface_file} from HF to local")
        sys.stdout.flush()

        data = xr.open_zarr(
            f"{huggingface_file}",
            chunks="auto",
        )

        # take nearest location and only select the variables we want
        data_at_location = data.sel(latitude=latitude, longitude=longitude, method="nearest")
        data_at_location = data_at_location[variables]

        # choice the first isobaricInhPa
        data_at_location = data_at_location.isel(isobaricInhPa=-1)

        #  reduce to 54 hours timestamps, this means there is at least a 48 hours forecast
        data_at_location = data_at_location.isel(step=slice(0, 54))

        # load all the data, this can take about ~1 minute seconds
        print(f"Loading dataset for {timestamp=} {longitude=} {latitude=}")
        data_at_location.load()

        # save to cache
        print(f"Saving to cache {cache_file}")
        data_at_location.to_zarr(cache_file)
    else:
        # load from cache
        print("loading from cache")
        data_at_location = xr.open_zarr(cache_file)

    # make times from the init time + steps
    times = pd.to_datetime(data_at_location.time.values) + pd.to_timedelta(
        data_at_location.step.values, unit="h"
    )

    # convert to pandas dataframe
    df = pd.DataFrame(times, columns=["time"])
    for variable in variables:
        df[variable] = data_at_location[variable].values

    # make wind speed out of u and v
    df["si10"] = (df["u"] ** 2 + df["v"] ** 2) ** 0.5

    # rename variables
    df = df.rename(
        columns={
            "t_2m": "t",
            "tot_prec": "prate",
            "aswdifd_s": "dswrf",
            "aswdir_s": "dlwrf",
            "clcl": "lcc",
            "clcm": "mcc",
            "clch": "hcc",
        }
    )

    # change dswrf and dlwrf to hourly mean, rather than forecast mean
    df = change_from_forecast_mean_to_hourly_mean(df, variable="dswrf")
    df = change_from_forecast_mean_to_hourly_mean(df, variable="dlwrf")

    # add visbility for the moment
    # TODO
    df["vis"] = 10000

    # drop u and v
    df = df.drop(columns=["u", "v"])

    # rename id to pv_id
    df = df.rename(columns={"id": "pv_id"})

    # add columns for timestamp, latitude and longitude
    df["timestamp"] = timestamp
    df["latitude"] = latitude
    df["longitude"] = longitude

    # add pv_id columns if it is given
    if pv_id is not None:
        df["pv_id"] = pv_id

    if progress:
        print(f"Getting NWP for {timestamp} {pv_id}. Progress: {100*progress}%")

    return df


def change_from_forecast_mean_to_hourly_mean(df: pd.DataFrame, variable: str = "dswrf"):
    """Change the forecast mean to hourly mean for a variable

    The irradience variables are in forecast mean, so we need to change them to hourly mean.
    We do this by change the forecast mena to cumsum, and then taking the difference
    """

    # change the forecast mean to cumsum
    variable_cumsum = f"{variable}_cumsum"
    df[variable_cumsum] = df[variable] * range(0, len(df))

    # take the difference
    df.loc[1:, variable] = df[variable_cumsum].diff()[1:].astype(np.float32)

    # drop the cumsum column
    df = df.drop(columns=[variable_cumsum])

    # clip zero
    df[variable] = df[variable].clip(lower=0)

    return df
