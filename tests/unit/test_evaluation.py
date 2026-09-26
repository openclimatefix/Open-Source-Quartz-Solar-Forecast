"""Unit tests for the evaluation entry point testset path resolution.

These tests never touch the network or any external dataset:
``get_pv_metadata`` is patched to raise a sentinel so that ``run_eval`` stops
immediately after the testset has been read.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

import quartz_solar_forecast
from quartz_solar_forecast import evaluation

# The testset is stored next to the package modules, and is referenced by
# dataset/make_test_set.py relative to that same location.
TESTSET = Path(quartz_solar_forecast.__file__).parent / "dataset" / "testset.csv"


class _StopBeforeDownload(Exception):
    """Sentinel raised in place of hitting Hugging Face."""


@pytest.fixture
def stop_before_download(monkeypatch):
    def _raise_sentinel(testset):
        raise _StopBeforeDownload

    monkeypatch.setattr(evaluation, "get_pv_metadata", _raise_sentinel)


def test_default_testset_path_points_at_the_real_testset():
    """The default resolves to the testset that actually ships with the sources."""
    assert TESTSET.is_file()
    assert Path(evaluation.DEFAULT_TESTSET_PATH) == TESTSET


def test_run_eval_default_works_from_any_cwd(tmp_path, monkeypatch, stop_before_download):
    """Regression test: the default must not depend on the working directory.

    The default used to be the cwd-relative string "dataset/testset.csv", so
    running scripts/run_evaluation.py from the repository root raised
    FileNotFoundError.
    """
    monkeypatch.chdir(tmp_path)
    assert not Path("dataset/testset.csv").exists(), "precondition: no dataset/ in cwd"

    with pytest.raises(_StopBeforeDownload):
        evaluation.run_eval()


def test_run_eval_accepts_an_explicit_relative_path(tmp_path, monkeypatch, stop_before_download):
    """An explicitly passed path keeps its original cwd-relative meaning."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "dataset").mkdir()
    pd.DataFrame([{"pv_id": 1, "timestamp": "2021-01-26 01:15:00"}]).to_csv(
        tmp_path / "dataset" / "testset.csv", index=False
    )

    with pytest.raises(_StopBeforeDownload):
        evaluation.run_eval("dataset/testset.csv")
