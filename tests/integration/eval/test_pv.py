from quartz_solar_forecast.eval.pv import get_pv_truth, get_pv_metadata
import pandas as pd
import pytest

# @pytest.mark.skip(reason="HF files have been changes"
# " - https://github.com/openclimatefix/open-source-quartz-solar-forecast/issues/292")
@pytest.mark.integration
def test_get_pv_metadata():
    test_set_df = pd.DataFrame(
        [
            {
                "timestamp": pd.Timestamp("2021-01-26 01:15:00"),
                "pv_id": 8215,
            }
        ]
    )

    metadata_df = get_pv_metadata(test_set_df)
    assert "latitude" in metadata_df.columns


# @pytest.mark.skip(reason="HF files have been changes"
# " - https://github.com/openclimatefix/open-source-quartz-solar-forecast/issues/292")
# @pytest.mark.parametrize("folder_name", ["30_minutely", "5_minutely"])
@pytest.mark.integration
def test_get_pv(folder_name):
    # make test dataset file
    test_set_df = pd.DataFrame(
        [
            {
                "timestamp": pd.Timestamp("2021-01-26 01:15:00"),
                "pv_id": 8215,
            }
        ]
    )

    # Collect NWP data from Hugging Face, ICON. (Peter)
    _ = get_pv_truth(test_set_df,folder_name=folder_name)
