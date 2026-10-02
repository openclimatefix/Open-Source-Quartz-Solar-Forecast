from datetime import datetime

import pandas as pd
import pytest


@pytest.fixture
def mock_run_forecast():
    """Return a deterministic forecast without calling weather APIs."""

    def _mock_run_forecast(*args, **kwargs):
        index = pd.date_range(datetime(2021, 1, 26, 1, 15), periods=192, freq="15min")
        return pd.DataFrame({"power_kw": [0.0] * 192}, index=index)

    return _mock_run_forecast
