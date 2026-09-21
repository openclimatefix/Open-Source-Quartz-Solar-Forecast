"""
DuckDB utilities for forecasting data analysis
- Stable timestamp detection
- Robust view creation
- Optimized column handling
- Fully benchmark-compatible
"""

import duckdb
import pandas as pd
from pathlib import Path
from typing import Optional, List, Dict, Union, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import time


# Performance Dataclass

@dataclass
class QueryStats:
    query_time: float = 0.0
    rows_returned: int = 0
    memory_used: float = 0.0
    cache_hit: bool = False


# ForecastAnalyzer

class ForecastAnalyzer:

    def __init__(
        self,
        data_dir: Union[str, Path],
        db_path: Optional[str] = None,
        persistent: bool = True,
        memory_limit: str = "4GB",
        threads: Optional[int] = None,
        enable_cache: bool = True
    ):
        """
        Initialize analyzer with automatic file detection
        """
        self.data_dir = Path(data_dir)
        self.enable_cache = enable_cache
        self.query_cache: Dict[str, Tuple[pd.DataFrame, float]] = {}
        self.column_cache: Dict[str, List[str]] = {}
        self.stats: List[QueryStats] = []

        if db_path is None and persistent:
            db_path = str(self.data_dir / "forecasts_optimized.db")

        self.db_path = db_path or ":memory:"
        self.con = duckdb.connect(self.db_path)

        self._configure_duckdb(memory_limit, threads)
        self._data_pattern, self._file_type, self._read_func = self._detect_files()

        if self._read_func:
            self._create_optimized_view()


    def _configure_duckdb(self, memory_limit: str, threads: Optional[int]):
        settings = [
            f"SET memory_limit='{memory_limit}'",
            "SET enable_progress_bar=false",
            "SET enable_object_cache=true",
            "SET preserve_insertion_order=false",
            "SET default_null_order='nulls_first'",
            "SET default_order='asc'",
            "SET enable_http_metadata_cache=true"
        ]
        if threads:
            settings.append(f"SET threads={threads}")

        for s in settings:
            try:
                self.con.execute(s)
            except:
                pass


    def _detect_files(self) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Returns:
            glob-pattern, filetype, DuckDB read function string
        """
        parquet_files = list(self.data_dir.glob("*.parquet"))
        csv_files = list(self.data_dir.glob("*.csv"))

        if parquet_files:
            pattern = str(self.data_dir / "*.parquet").replace("\\", "/")
            return pattern, "parquet", f"read_parquet('{pattern}', hive_partitioning=true)"

        if csv_files:
            pattern = str(self.data_dir / "*.csv").replace("\\", "/")
            return pattern, "csv", f"""
                read_csv_auto(
                    '{pattern}',
                    header=true,
                    normalize_names=true,
                    parallel=true,
                    sample_size=-1,
                    delim=',',
                    auto_detect=true,
                    union_by_name=true
                )
            """
        return None, None, None


    def _get_timestamp_column(self) -> str:
        """
        Detect the timestamp column robustly.
        """
        key = "timestamp_column"
        if key in self.column_cache:
            return self.column_cache[key]

        df = self.con.execute(f"SELECT * FROM {self._read_func} LIMIT 1").fetchdf()
        candidates = ["timestamp", "datetime", "date", "time"]

        for c in df.columns:
            if c.lower() in candidates:
                self.column_cache[key] = c
                return c

        # fallback
        self.column_cache[key] = df.columns[0]
        return df.columns[0]


    def _get_power_columns(self) -> List[str]:
        """
        Detect power columns (robust version)
        """
        key = "power_columns"
        if key in self.column_cache:
            return self.column_cache[key]

        df = self.con.execute(f"SELECT * FROM {self._read_func} LIMIT 1").fetchdf()
        cols = [
            c for c in df.columns
            if ("power" in c.lower() or "kw" in c.lower() or "pv" in c.lower())
            and c.lower() not in ("timestamp",)
        ]

        self.column_cache[key] = cols
        return cols


    def _create_optimized_view(self):
        ts = self._get_timestamp_column()
        try:
            self.con.execute("DROP VIEW IF EXISTS forecast_data")

            self.con.execute("DROP TABLE IF EXISTS forecast_data")

            self.con.execute(f"""
                CREATE TABLE forecast_data AS
                SELECT {ts}::TIMESTAMP AS timestamp, * EXCLUDE ({ts})
                FROM {self._read_func}
            """)
            self.con.execute("ANALYZE forecast_data")
        except Exception as e:
            print("WARNING: Optimized table creation failed:", e)
            try:
                self.con.execute(f"CREATE OR REPLACE VIEW forecast_data AS SELECT * FROM {self._read_func}")
            except:
                pass
      
    def _execute_with_stats(self, sql: str, params=None, cache_key=None) -> pd.DataFrame:
        """
        Execute SQL with stats + optional caching
        """
        t0 = time.time()

        # Cache hit
        if cache_key and cache_key in self.query_cache:
            df, ts = self.query_cache[cache_key]
            if time.time() - ts < 240:
                self.stats.append(QueryStats(0.001, len(df), cache_hit=True))
                return df

        df = (
            self.con.execute(sql, params).fetchdf()
            if params else self.con.execute(sql).fetchdf()
        )
        dt = time.time() - t0

        qstats = QueryStats(
            query_time=dt,
            rows_returned=len(df)
        )
        self.stats.append(qstats)

        if cache_key and dt > 0.05:
            self.query_cache[cache_key] = (df.copy(), time.time())

        return df

    # =======================================================================================
    # ANALYTICS
    # =======================================================================================

    def daily_summary(self, start_date=None, end_date=None):
        power_cols = self._get_power_columns()
        if not power_cols:
            return pd.DataFrame()

        where = []
        params = []

        if start_date:
            where.append("timestamp >= ?")
            params.append(start_date)
        if end_date:
            where.append("timestamp < ?")
            params.append(end_date)

        W = "WHERE " + " AND ".join(where) if where else ""
        total = " + ".join([f'COALESCE("{c}",0)' for c in power_cols])

        sql = f"""
            SELECT
                DATE_TRUNC('day', timestamp) AS date,
                COUNT(*) AS count_rows,
                AVG(total_power) AS avg_power_kw,
                MAX(total_power) AS peak_power_kw,
                SUM(total_power) AS total_energy_kwh,
                STDDEV(total_power) AS stddev_power_kw
            FROM (
                SELECT timestamp, ({total}) AS total_power
                FROM forecast_data
                {W}
            )
            GROUP BY date
            ORDER BY date
        """

        ck = f"daily_{start_date}_{end_date}"
        return self._execute_with_stats(sql, params, ck)


    def hourly_profile(self):
        power_cols = self._get_power_columns()
        if not power_cols:
            return pd.DataFrame()

        total = " + ".join([f'COALESCE("{c}",0)' for c in power_cols])

        sql = f"""
            SELECT
                EXTRACT(HOUR FROM timestamp) AS hour,
                COUNT(*) AS sample_count,
                AVG({total}) AS avg_power_kw,
                MIN({total}) AS min_power_kw,
                MAX({total}) AS max_power_kw,
                STDDEV({total}) AS stddev_power_kw
            FROM forecast_data
            GROUP BY 1
            ORDER BY 1
        """

        return self._execute_with_stats(sql, cache_key="hourly")


    def site_comparison(self):
        power_cols = self._get_power_columns()
        site_cols = [c for c in power_cols if "site" in c.lower()]

        if not site_cols:
            return pd.DataFrame()

        parts = []
        for col in site_cols:
            site = col.replace("_power", "").replace("site", "Site ")

            parts.append(f"""
                SELECT
                    '{site}' AS site_name,
                    COUNT("{col}") AS total_forecasts,
                    AVG("{col}") AS avg_power_kw,
                    MAX("{col}") AS peak_power_kw,
                    SUM("{col}") AS total_energy_kwh,
                    AVG(CASE WHEN "{col}" > 0 THEN 1 ELSE 0 END) AS capacity_factor
                FROM forecast_data
            """)

        return self._execute_with_stats(
            " UNION ALL ".join(parts),
            cache_key="site_compare"
        )


    def peak_periods(self, limit=20, window_minutes=15):
        power_cols = self._get_power_columns()
        if not power_cols:
            return pd.DataFrame()

        total = " + ".join([f'COALESCE("{c}",0)' for c in power_cols])

        sql = f"""
            WITH rolling AS (
                SELECT
                    timestamp,
                    ({total}) AS power,
                    AVG({total}) OVER (
                        ORDER BY timestamp
                        RANGE BETWEEN INTERVAL '{window_minutes} minutes' PRECEDING
                        AND CURRENT ROW
                    ) AS rolling_power
                FROM forecast_data
            )
            SELECT *
            FROM rolling
            ORDER BY rolling_power DESC
            LIMIT {limit}
        """

        return self._execute_with_stats(sql, cache_key=f"peak_{limit}")

    def get_performance_stats(self):
        if not self.stats:
            return pd.DataFrame()
        return pd.DataFrame([asdict(s) for s in self.stats])

    def clear_cache(self):
        self.query_cache.clear()
        self.column_cache.clear()
        print("Cache cleared")

    def close(self):
        if self.stats:
            stats = self.get_performance_stats()
            outfile = self.data_dir / "query_performance.json"
            stats.to_json(outfile, orient="records", indent=2)
        self.con.close()

    def __enter__(self): return self
    def __exit__(self, *args): self.close()