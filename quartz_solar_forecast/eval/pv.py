import os

import numpy as np
import pandas as pd
import xarray as xr
from huggingface_hub import HfFileSystem

fs = HfFileSystem()


def get_pv_metadata(testset: pd.DataFrame):
    # download from hugginface or load from cache
    cache_dir = "data/pv"
    metadata_file = f"{cache_dir}/metadata.csv"
    if not os.path.exists(metadata_file):
        os.makedirs(cache_dir, exist_ok=True)
        fs.get("datasets/openclimatefix/uk_pv/metadata.csv", metadata_file)

    # Load in the dataset
    metadata_df = pd.read_csv(metadata_file)

    # join metadata with testset
    metadata_df = metadata_df.rename(columns={"ss_id": "pv_id"})
    combined_data = testset.merge(metadata_df, on="pv_id", how="left")

    # only keep the columns we need
    # normalize column names to lowercase for consistent access
    combined_data.columns = combined_data.columns.str.lower()

    combined_data = combined_data[
        ["pv_id", "timestamp", "latitude_rounded", "longitude_rounded", "kwp"]
    ]

    # rename latitude_rounded to latitude and longitude_rounded to longitude
    combined_data = combined_data.rename(
        columns={
            "latitude_rounded": "latitude",
            "longitude_rounded": "longitude",
            "kwp": "capacity",
        }
    )

    # format datetime
    combined_data["timestamp"] = pd.to_datetime(combined_data["timestamp"])

    return combined_data


def get_pv_truth(testset: pd.DataFrame):
    print("Loading PV data")

    # download from hugginface or load from cache
    cache_dir = "data/pv"
    metadata_file = f"{cache_dir}/pv.netcdf"
    if not os.path.exists(metadata_file):
        print("Loading from HF)")
        os.makedirs(cache_dir, exist_ok=True)
        fs.get("datasets/openclimatefix/uk_pv/pv.netcdf", metadata_file)

    # Load in the dataset
    pv_ds = xr.open_dataset(metadata_file, engine="h5netcdf")

    combined_data = []
    for index, row in testset.iterrows():
        print(f"Processing {index} of {len(testset)}")
        pv_id = str(row["pv_id"])
        base_datetime = pd.to_datetime(row["timestamp"])

        # Calculate future timestamps up to the max horizon
        for i in range(0, 49):  # 48 hours in steps of 1 hour
            future_datetime = base_datetime + pd.DateOffset(hours=i)
            horizon = i  # horizon in hours

            try:
                # Attempt to select data for the future datetime
                selected_data = pv_ds[pv_id].sel(datetime=future_datetime)
                value = selected_data.values.item()
                value = value / 1000  # to convert from w to kw
            except KeyError:
                # If data is not found for the future datetime, set value as NaN
                value = np.nan

            # Add the data to the DataFrame
            combined_data.append(
                pd.DataFrame(
                    {
                        "pv_id": pv_id,
                        "timestamp": future_datetime,
                        "value": value,
                        "horizon_hour": horizon,
                    },
                    index=[i],
                )
            )
    combined_data = pd.concat(combined_data)
    return combined_data
