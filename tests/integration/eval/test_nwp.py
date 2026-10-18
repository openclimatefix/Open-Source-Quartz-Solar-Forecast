import os

import pandas as pd
import pytest
from huggingface_hub import HfFileSystem
from huggingface_hub.utils import HfHubHTTPError

from quartz_solar_forecast.eval.nwp import get_nwp

HF_DATASET = "openclimatefix/dwd-icon-eu"
HF_TEST_FILE = "datasets/openclimatefix/dwd-icon-eu/data/2021/1/26/20210126_00.zarr.zip"


def _require_hf_dataset_access() -> None:
    """Skip this external-data test when the gated dataset is unavailable."""
    try:
        # Metadata can be public even when the underlying LFS object is gated.
        # Read only the ZIP signature so this check never downloads the 3+ GB file.
        with HfFileSystem(token=os.environ.get("HF_TOKEN")).open(
            HF_TEST_FILE, "rb"
        ) as data_file:
            if data_file.read(4) != b"PK\x03\x04":
                raise RuntimeError(f"{HF_TEST_FILE} is not a valid ZIP archive")
    except HfHubHTTPError as exc:
        status_code = getattr(exc.response, "status_code", None)
        if status_code in {401, 403}:
            pytest.skip(
                f"Hugging Face access to {HF_DATASET} is unavailable "
                f"(HTTP {status_code}); configure an HF_TOKEN with dataset access to run it."
            )
        raise


# can take ~ 1 minute to run
@pytest.mark.integration
def test_get_nwp():
    _require_hf_dataset_access()

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
