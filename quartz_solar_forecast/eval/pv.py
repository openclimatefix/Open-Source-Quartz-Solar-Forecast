import glob
import os

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.dataset as ds
from huggingface_hub import HfFileSystem

fs = HfFileSystem()


def get_pv_metadata(testset: pd.DataFrame) -> pd.DataFrame:
    """Merge metadata (lat/lon/capacity) with testset of pv_id + timestamp."""
    cache_dir = "data/pv"
    metadata_file = f"{cache_dir}/metadata.csv"

    if not os.path.exists(metadata_file) or os.path.getsize(metadata_file) == 0:
        os.makedirs(cache_dir, exist_ok=True)
        fs.get("datasets/openclimatefix/uk_pv/metadata.csv", metadata_file)

    metadata_df = pd.read_csv(metadata_file)

    # align schema
    metadata_df = metadata_df.rename(columns={"ss_id": "pv_id"})

    combined_data = testset.merge(metadata_df, on="pv_id", how="left")

    # keep only useful columns
    combined_data = combined_data[
        ["pv_id", "timestamp", "latitude_rounded", "longitude_rounded", "kWp"]
    ].rename(
        columns={
            "latitude_rounded": "latitude",
            "longitude_rounded": "longitude",
            "kWp": "capacity",
        }
    )

    combined_data["timestamp"] = pd.to_datetime(combined_data["timestamp"])
    return combined_data


FOLDER_TO_TIME_RES = {
    "5_minutely": "5min",
    "30_minutely": "30min",
}


def get_pv_truth(
    testset: pd.DataFrame, horizon_hours: int = 48, folder_name: str = "30_minutely"
) -> pd.DataFrame:
    """
    Fetch PV generation truth values for given testset.
    Optimized for performance using Arrow predicate filtering.
    """

    cache_dir = "data/pv"
    parquet_dir = f"{cache_dir}/{folder_name}"

    if not os.path.exists(parquet_dir):
        print("Downloading PV parquet data from HuggingFace...")
        os.makedirs(cache_dir, exist_ok=True)
        fs.get(f"datasets/openclimatefix/uk_pv/{folder_name}", cache_dir, recursive=True)

    # Find all non-empty parquet files
    files = glob.glob(f"{parquet_dir}/**/*.parquet", recursive=True)
    non_empty_files = [f for f in files if os.path.getsize(f) > 0]

    if not non_empty_files:
        raise FileNotFoundError("No valid parquet files found (all are empty).")

    # Prepare filtering parameters
    unique_pv_ids = testset["pv_id"].unique().tolist()
    min_time = pd.to_datetime(testset["timestamp"]).min()
    max_time = min_time + pd.Timedelta(hours=horizon_hours)

    # Ensure timestamps are timezone-aware
    testset["timestamp"] = pd.to_datetime(testset["timestamp"], utc=True)

    # Define dataset with filtering
    dataset = ds.dataset(non_empty_files, format="parquet")

    arrow_min_time = pa.scalar(min_time, type=pa.timestamp("ns", tz="UTC"))
    arrow_max_time = pa.scalar(max_time, type=pa.timestamp("ns", tz="UTC"))

    filter_expr = (
        (ds.field("ss_id").isin(unique_pv_ids))
        & (ds.field("datetime_GMT") >= arrow_min_time)
        & (ds.field("datetime_GMT") <= arrow_max_time)
    )

    # Load filtered data only
    table = dataset.to_table(filter=filter_expr)
    pv_data = table.to_pandas()

    # Ensure datetime column is parsed and aligned
    pv_data["datetime_GMT"] = pd.to_datetime(pv_data["datetime_GMT"], utc=True)
    time_resolution = FOLDER_TO_TIME_RES.get(folder_name)
    if time_resolution is None:
        raise ValueError(
            f"Unknown folder_name '{folder_name}'. Please add it to FOLDER_TO_TIME_RES mapping."
        )

    pv_data["datetime_GMT"] = pv_data["datetime_GMT"].dt.floor(time_resolution)

    # Expand testset for all horizons
    horizons = np.arange(horizon_hours + 1)
    expanded = testset.loc[testset.index.repeat(len(horizons))].copy()
    expanded["horizon_hour"] = np.tile(horizons, len(testset))

    # Calculate actual timestamp for each horizon
    expanded["timestamp"] = expanded["timestamp"] + pd.to_timedelta(
        expanded["horizon_hour"], unit="h"
    )
    expanded["timestamp"] = expanded["timestamp"].dt.floor(time_resolution)
    # Merge
    merged = expanded.merge(
        pv_data,
        left_on=["pv_id", "timestamp"],
        right_on=["ss_id", "datetime_GMT"],
        how="left",
    )

    # Convert to kWh
    merged["value"] = merged["generation_Wh"] / 1000.0

    result = merged[["pv_id", "timestamp", "value", "horizon_hour"]].copy()

    return result
