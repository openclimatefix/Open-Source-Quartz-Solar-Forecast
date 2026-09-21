"""
DuckDB vs Pandas Performance Benchmark
Generates small, medium, large datasets and benchmarks real ForecastAnalyzer.
"""

import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import psutil
import seaborn as sns

from scripts.duck_db_utils import ForecastAnalyzer


def get_memory_mb() -> float:
    """Return current process memory usage in MB."""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024


def time_and_memory(
    func: Callable[..., Any],
    *args,
    **kwargs,
) -> tuple[float, float, Any]:
    """Measure runtime + memory usage."""
    start_mem = get_memory_mb()
    start = time.time()
    result = func(*args, **kwargs)
    elapsed = time.time() - start
    used_mb = max(0.0, get_memory_mb() - start_mem)
    return elapsed, used_mb, result


def generate_synthetic_dataset(base_df: pd.DataFrame, factor: int) -> pd.DataFrame:
    """
    Expand dataset by repeating with noise.

    factor = 1    → small dataset
    factor = 100  → medium dataset
    factor = 5000 → large dataset
    """
    df = pd.concat([base_df] * factor, ignore_index=True)

    power_cols = [col for col in df.columns if "Power" in col]
    for col in power_cols:
        df[col] *= np.random.uniform(0.95, 1.05, size=len(df))

    df["timestamp"] = pd.date_range(
        start="2023-01-01",
        periods=len(df),
        freq="15min",
    )

    return df


def write_dataset(df: pd.DataFrame, folder: Path, name: str) -> tuple[Path, Path]:
    """Write both CSV and Parquet for ForecastAnalyzer to read."""
    folder.mkdir(exist_ok=True, parents=True)
    csv_path = folder / f"{name}.csv"
    parquet_path = folder / f"{name}.parquet"

    df.to_csv(csv_path, index=False)
    df.to_parquet(parquet_path, index=False)
    return csv_path, parquet_path


def pandas_daily(df: pd.DataFrame) -> pd.DataFrame:
    total_cols = [c for c in df.columns if "Power" in c]
    df2 = df.assign(
        date=df.timestamp.dt.date,
        total_power=df[total_cols].sum(axis=1),
    )
    return (
        df2.groupby("date")
        .agg(
            count_rows=("total_power", "count"),
            avg_power_kw=("total_power", "mean"),
            peak_power_kw=("total_power", "max"),
            total_energy_kwh=("total_power", "sum"),
            stddev_power_kw=("total_power", "std"),
        )
        .reset_index()
    )


def pandas_hourly(df: pd.DataFrame) -> pd.DataFrame:
    total_cols = [c for c in df.columns if "Power" in c]
    df2 = df.assign(
        hour=df.timestamp.dt.hour,
        total_power=df[total_cols].sum(axis=1),
    )

    result = (
        df2.groupby("hour")["total_power"]
        .agg(
            sample_count="count",
            avg_power_kw="mean",
            min_power_kw="min",
            max_power_kw="max",
            stddev_power_kw="std",
        )
        .reset_index()
    )

    percentiles = (
        df2.groupby("hour")["total_power"]
        .quantile([0.05, 0.25, 0.5, 0.75, 0.95])
        .unstack()
    )
    percentiles.columns = ["p05", "p25", "p50", "p75", "p95"]

    return result.merge(percentiles, on="hour")


def pandas_site_compare(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for col in [c for c in df.columns if "Power" in c]:
        s = df[col]
        rows.append(
            {
                "site_name": col.replace("_Power", "").replace(" Power", ""),
                "total_forecasts": len(s),
                "avg_power_kw": s.mean(),
                "peak_power_kw": s.max(),
                "total_energy_kwh": s.sum(),
                "capacity_factor": (s > 0).mean(),
            }
        )
    return pd.DataFrame(rows)


def pandas_peak(df: pd.DataFrame, limit: int = 20) -> pd.DataFrame:
    total_cols = [c for c in df.columns if "Power" in c]
    df2 = df.assign(total_power=df[total_cols].sum(axis=1))
    df2 = df2.sort_values("timestamp")
    df2["rolling"] = df2["total_power"].rolling(4, min_periods=1).mean()

    top = df2.nlargest(limit, "rolling")[["timestamp", "total_power", "rolling"]]
    top["rank"] = range(1, len(top) + 1)
    return top


def pandas_date_filter(
    df: pd.DataFrame,
    start: str,
    end: str,
) -> pd.DataFrame:
    df2 = df[(df.timestamp >= start) & (df.timestamp < end)]
    total_cols = [c for c in df.columns if "Power" in c]
    df2 = df2.assign(total_power=df2[total_cols].sum(axis=1))

    return pd.DataFrame(
        [
            {
                "rows": len(df2),
                "avg_power": df2.total_power.mean(),
                "total_energy": df2.total_power.sum(),
            }
        ]
    )


def pandas_complex(df: pd.DataFrame) -> pd.DataFrame:
    total_cols = [c for c in df.columns if "Power" in c]
    df2 = df.assign(
        date=df.timestamp.dt.date,
        hour=df.timestamp.dt.hour,
        is_day=df.timestamp.dt.hour.between(6, 18),
        total_power=df[total_cols].sum(axis=1),
    )
    return (
        df2.groupby(["date", "is_day"])
        .agg(
            count=("total_power", "count"),
            avg_power=("total_power", "mean"),
            peak_power=("total_power", "max"),
            total_energy=("total_power", "sum"),
        )
        .reset_index()
    )


class MultiSizeBenchmark:
    def __init__(self, base_csv: Path, work_dir: Path) -> None:
        self.base_csv = base_csv
        self.work_dir = work_dir
        self.results: list[dict[str, Any]] = []

    def run_single_size(
        self,
        name: str,
        df: pd.DataFrame,
        dataset_folder: Path,
    ) -> None:
        print("=" * 90)
        print(f"RUNNING {name.upper()} DATASET BENCHMARK ({len(df):,} rows)")
        print("=" * 90)

        write_dataset(df, dataset_folder, f"{name}_forecasts")

        analyzer = ForecastAnalyzer(
            data_dir=dataset_folder,
            persistent=True,
            enable_cache=True,
        )

        benchmarks = [
            (
                "Daily Aggregation",
                lambda: pandas_daily(df),
                analyzer.daily_summary,
            ),
            (
                "Hourly Profile",
                lambda: pandas_hourly(df),
                analyzer.hourly_profile,
            ),
            (
                "Site Comparison",
                lambda: pandas_site_compare(df),
                analyzer.site_comparison,
            ),
            (
                "Peak Periods",
                lambda: pandas_peak(df, 20),
                lambda: analyzer.peak_periods(20),
            ),
            (
                "Date Filtering",
                lambda: pandas_date_filter(df, "2023-01-01", "2023-06-01"),
                lambda: analyzer.daily_summary(
                    "2023-01-01",
                    "2023-06-01",
                ),
            ),
            (
                "Complex Aggregation",
                lambda: pandas_complex(df),
                analyzer.complex_aggregation
                if hasattr(analyzer, "complex_aggregation")
                else analyzer.daily_summary,
            ),
        ]

        for bench_name, p_func, d_func in benchmarks:
            print(f"\n{bench_name}")

            p_time, p_mem, _ = time_and_memory(p_func)
            print(f"Pandas: {p_time:.4f}s | {p_mem:.4f} MB")

            d_time, d_mem, _ = time_and_memory(d_func)
            print(f"DuckDB: {d_time:.4f}s | {d_mem:.4f} MB")

            self.results.append(
                {
                    "dataset": name,
                    "benchmark": bench_name,
                    "pandas_time": p_time,
                    "duckdb_time": d_time,
                    "speedup": p_time / d_time if d_time > 0 else 0.0,
                    "pandas_memory": p_mem,
                    "duckdb_memory": d_mem,
                }
            )

        analyzer.close()

    def run_all(self) -> pd.DataFrame:
        base_df = pd.read_csv(self.base_csv, parse_dates=[0])
        base_df.rename(columns={base_df.columns[0]: "timestamp"}, inplace=True)

        for name, factor in [("small", 1), ("medium", 100), ("large", 5000)]:
            df_expanded = generate_synthetic_dataset(base_df, factor)
            self.run_single_size(name, df_expanded, self.work_dir / name)

        results_df = pd.DataFrame(self.results)
        out_path = self.work_dir / "all_benchmarks.csv"
        results_df.to_csv(out_path, index=False)
        print("\nSaved all benchmark results to:", out_path)

        return results_df


def plot_benchmark_comparison(results_df: pd.DataFrame) -> None:
    """Pandas vs DuckDB performance (time and memory)."""
    sns.set(style="whitegrid")

    time_df = results_df.melt(
        id_vars=["dataset", "benchmark"],
        value_vars=["pandas_time", "duckdb_time"],
        var_name="engine",
        value_name="time_sec",
    )

    memory_df = results_df.melt(
        id_vars=["dataset", "benchmark"],
        value_vars=["pandas_memory", "duckdb_memory"],
        var_name="engine",
        value_name="memory_mb",
    )

    mapping = {
        "pandas_time": "Pandas",
        "duckdb_time": "DuckDB",
        "pandas_memory": "Pandas",
        "duckdb_memory": "DuckDB",
    }

    time_df["engine"] = time_df["engine"].map(mapping)
    memory_df["engine"] = memory_df["engine"].map(mapping)

    plt.figure(figsize=(14, 6))
    sns.barplot(
        data=time_df,
        x="benchmark",
        y="time_sec",
        hue="engine",
        errorbar=None,
    )
    plt.yscale("log")
    plt.title("Pandas vs DuckDB: Execution Time (log scale)")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.show()

    plt.figure(figsize=(14, 6))
    sns.barplot(
        data=memory_df,
        x="benchmark",
        y="memory_mb",
        hue="engine",
        errorbar=None,
    )
    plt.yscale("log")
    plt.title("Pandas vs DuckDB: Memory Usage (log scale)")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.show()


def main() -> None:
    data_path = Path("csv_forecasts/multi_site_pv_forecasts.csv")
    work_dir = Path("benchmarks_option_b")
    work_dir.mkdir(exist_ok=True)

    runner = MultiSizeBenchmark(data_path, work_dir)
    results_df = runner.run_all()
    plot_benchmark_comparison(results_df)

    print("\nDONE.\n")


if __name__ == "__main__":
    main()
