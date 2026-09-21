import os

import numpy as np
import pandas as pd
from huggingface_hub import HfFileSystem

fs = HfFileSystem()


def get_pv_metadata(testset: pd.DataFrame):
    # download from huggingface or load from cache
    cache_dir = "data/pv"
    metadata_file = f"{cache_dir}/metadata.csv"

    if not os.path.exists(metadata_file):
        os.makedirs(cache_dir, exist_ok=True)
        fs.get("datasets/openclimatefix/uk_pv/metadata.csv", metadata_file)

    # Load in the dataset
    metadata_df = pd.read_csv(metadata_file)
    metadata_df = metadata_df.rename(columns={"ss_id": "pv_id"})

    # join metadata with testset
    combined_data = testset.merge(metadata_df, on="pv_id", how="left")

    # Select and rename columns
    combined_data = combined_data[
        ["pv_id", "timestamp", "latitude_rounded", "longitude_rounded", "kWp"]
    ]
    combined_data = combined_data.rename(
        columns={
            "latitude_rounded": "latitude",
            "longitude_rounded": "longitude",
            "kWp": "capacity",
        }
    )

    # format datetime
    combined_data["timestamp"] = pd.to_datetime(combined_data["timestamp"])

    return combined_data


def get_pv_truth(testset: pd.DataFrame):
    """
    Load PV ground truth data from Hugging Face dataset.
    Dataset uses parquet format: 5_minutely/year=YYYY/month=MM/data.parquet
    """
    print("Loading PV data")

    cache_dir = "data/pv/parquet_cache"
    os.makedirs(cache_dir, exist_ok=True)

    # Get unique year-month combinations from testset
    testset["timestamp_dt"] = pd.to_datetime(testset["timestamp"])
    testset["year"] = testset["timestamp_dt"].dt.year
    testset["month"] = testset["timestamp_dt"].dt.month
    year_months = testset[["year", "month"]].drop_duplicates()

    # downloads and load parquet files for each year-month
    all_pv_data = []
    for _, row in year_months.iterrows():
        year = int(row["year"])
        month = int(row["month"])
        cache_file = f"{cache_dir}/pv_{year}_{month:02d}.parquet"

        if not os.path.exists(cache_file):
            print(f"Downloading {year}-{month:02d}")
            hf_path = (
                f"datasets/openclimatefix/uk_pv/5_minutely"
                f"/year={year}/month={month:02d}/data.parquet"
            )
            fs.get(hf_path, cache_file)

        df = pd.read_parquet(cache_file)
        all_pv_data.append(df)
        print(f"Loaded {len(df)} records from {year}-{month:02d}")

    # Combine and prepare data
    pv_data = pd.concat(all_pv_data, ignore_index=True)
    pv_data = pv_data.rename(
        columns={
            "ss_id": "pv_id",
            "datetime_GMT": "timestamp",
            "generation_Wh": "generation_wh",
        }
    )
    pv_data["timestamp"] = pd.to_datetime(pv_data["timestamp"])
    pv_data["value"] = pv_data["generation_wh"] / 1000  # Convert Wh to kW

    # Generate forecast horizons for each testset entry
    combined_data = []
    for index, row in testset.iterrows():
        print(f"Processing {index + 1} of {len(testset)}")
        pv_id = row["pv_id"]
        base_datetime = pd.to_datetime(row["timestamp"])

        # Match timezone with PV data
        if base_datetime.tz is None and pv_data["timestamp"].dt.tz is not None:
            base_datetime = base_datetime.tz_localize("UTC")

        # Generate 48-hour forecast horizon (0-48 hours)
        for i in range(49):
            future_datetime = base_datetime + pd.Timedelta(hours=i)
            time_window = pd.Timedelta(minutes=5)

            # finds closest matching timestamp within 5-minute window
            mask = (
                (pv_data["pv_id"] == pv_id)
                & (pv_data["timestamp"] >= future_datetime - time_window)
                & (pv_data["timestamp"] <= future_datetime + time_window)
            )
            matching_data = pv_data[mask]

            if len(matching_data) > 0:
                # find closest match by time difference
                matching_data = matching_data.copy()
                matching_data["time_diff"] = abs(matching_data["timestamp"] - future_datetime)
                value = matching_data.loc[matching_data["time_diff"].idxmin(), "value"]
            else:
                value = np.nan

            combined_data.append(
                {
                    "pv_id": pv_id,
                    "timestamp": future_datetime,
                    "value": value,
                    "horizon_hour": i,
                }
            )

    return pd.DataFrame(combined_data)
