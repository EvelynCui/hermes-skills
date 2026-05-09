"""Generate simple matplotlib charts for FRED macroeconomic time series."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
MATPLOTLIB_CACHE_DIR = PROJECT_ROOT / "logs" / "matplotlib-cache"
MATPLOTLIB_CACHE_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(MATPLOTLIB_CACHE_DIR))
os.environ.setdefault("XDG_CACHE_HOME", str(MATPLOTLIB_CACHE_DIR))

import matplotlib.pyplot as plt


def generate_macro_charts(macro_data: list[dict[str, Any]], output_dir: Path) -> list[Path]:
    """Save one PNG line chart per FRED series.

    The input is already cleaned once after fetching. We still use pandas here
    because grouping by series and sorting by date is clearer than manual loops.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    if not macro_data:
        logging.info("No FRED macro data available for charts")
        return []

    frame = pd.DataFrame(macro_data)
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
    frame = frame.dropna(subset=["date", "value"])
    if frame.empty:
        logging.info("FRED macro data had no numeric observations for charts")
        return []

    chart_paths: list[Path] = []
    for series_id, series_frame in frame.groupby("series_id"):
        series_frame = series_frame.sort_values("date")
        series_name = str(series_frame["series_name"].iloc[0])

        plt.figure(figsize=(9, 4.8))
        plt.plot(series_frame["date"], series_frame["value"], marker="o", linewidth=1.8)
        plt.title(f"{series_id}: {series_name}")
        plt.xlabel("Date")
        plt.ylabel("Value")
        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        output_path = output_dir / f"{series_id.lower()}_line.png"
        plt.savefig(output_path, dpi=140)
        plt.close()
        chart_paths.append(output_path)
        logging.info("Saved macro chart: %s", output_path)

    return chart_paths
