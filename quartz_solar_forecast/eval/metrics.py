import numpy as np
import pandas as pd


def metrics(results_df: pd.DataFrame, pv_metadata: pd.DataFrame, include_night: bool = False):
    """
    Calculate and print metrics: MAE

    There is an option to include nighttime in the calculation of the MAE.

    results_df dataframe with the following columns
    - timestamp
    - pv_id
    - horizon_hours
    - forecast_power
    - generation_power

    pv_metadata is a dataframe with the following columns
    - pv_id
    - capacity

    """

    print(f'Making MAE results with {include_night=}')

    # remove night time
    if not include_night:
        results_df = results_df[results_df["generation_power"] > 0.1]

    # merge pv_metadata with results_df
    results_df = pd.merge(results_df, pv_metadata, on="pv_id")

    mae = np.round((results_df["forecast_power"] - results_df["generation_power"]).abs().mean(), 4)
    mae_normalized = np.round(
        ((results_df["forecast_power"] - results_df["generation_power"]) / results_df["capacity"])
        .abs()
        .mean(),
        4,
    )
    print(f"MAE: {mae} kw, normalized {mae_normalized} %")

    # calculate metrics over the different horizons hours
    # find all unique horizon_hours
    horizon_hours = results_df["horizon_hour"].unique()
    horizon_groups = [[x, x] for x in horizon_hours]
    horizon_groups += [[3, 4], [5, 8], [9, 16], [17, 24], [24, 48], [0, 36]]

    for horizon_group in horizon_groups:
        horizon_group_df = results_df[
            results_df["horizon_hour"].between(horizon_group[0], horizon_group[1])
        ]
        mae = np.round(
            (horizon_group_df["forecast_power"] - horizon_group_df["generation_power"])
            .abs()
            .mean(),
            3,
        )
        sem = np.round(
            (
                (horizon_group_df["forecast_power"] - horizon_group_df["generation_power"])
                .abs()
                .std()
                / 50 ** 0.5
            ),
            3,
        )

        mae_normalized = np.round(
            (
                (horizon_group_df["forecast_power"] - horizon_group_df["generation_power"])
                / horizon_group_df["capacity"]
            )
            .abs()
            .mean(),
            3,
        )

        print(
            f"MAE for horizon {horizon_group}: {mae} +- {1.96*sem}. mae_normalized: {100*mae_normalized} %"
        )

        # TODO add more metrics using ocf_ml_metrics
