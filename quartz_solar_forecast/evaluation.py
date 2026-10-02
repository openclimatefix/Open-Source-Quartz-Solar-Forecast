"""
To evaluate the performance of the solar forecast, a predefined testset is used.

A file has been added to this branch (make-testset) which defines a set of
random timestamps and sites ids.
This contains 50 sites each with 50 timestamps to make 2500 samples in total.

"""

import os

import pandas as pd
from dotenv import load_dotenv
from huggingface_hub.hf_api import HfFolder

from quartz_solar_forecast.eval.forecast import run_forecast
from quartz_solar_forecast.eval.metrics import metrics
from quartz_solar_forecast.eval.nwp import get_nwp
from quartz_solar_forecast.eval.pv import get_pv_metadata, get_pv_truth
from quartz_solar_forecast.eval.utils import combine_forecast_ground_truth

load_dotenv()

try:
    hf_token = os.environ["HF_TOKEN"]
    HfFolder.save_token(hf_token)
except Exception:
    print(
        "Warning, you wont be able to run evaluation if you dont set your "
        "Hugging Face Access Token to HF_TOKEN, or be logged in with Hugging Face"
    )


def run_eval(testset_path: str = "dataset/testset.csv"):
    # load testset from csv
    testset = pd.read_csv(testset_path)

    # Extract generation data and metadata for specific sites and timestamps
    # for the testset from Hugging Face. (Zak)
    pv_metadata = get_pv_metadata(testset)

    # Split data into PV inputs and ground truth. (Zak)
    ground_truth_df = get_pv_truth(testset)


    # Collect NWP data from Hugging Face, ICON. (Peter)
    nwp_df = get_nwp(pv_metadata)

    # Run forecast with PV and NWP inputs.
    predictions_df = run_forecast(pv_df=pv_metadata, nwp_df=nwp_df)

    # Combine the forecast results with the ground truth
    # (ts, id, horizon (in hours), pred, truth, diff)
    results_df = combine_forecast_ground_truth(predictions_df, ground_truth_df)

    # Drop rows where generation_power is missing
    results_df = results_df.dropna(subset=["generation_power"])

    # Save file
    results_df.to_csv("results.csv", index=False)

    # Calculate and print metrics: MAE
    metrics(results_df, pv_metadata, include_night=True)
    metrics(results_df, pv_metadata, include_night=False)

    # Visualizations
    # TODO


# run_eval()
