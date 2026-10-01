"""Point-in-time risk-free-rate helpers for the rolling experiment."""
from __future__ import annotations

from pathlib import Path
import pandas as pd


def load_dgs1(path: str | Path) -> pd.DataFrame:
    """Load a locally downloaded FRED DGS1 CSV as annual decimal rates.

    DGS1 is quoted in percent. Missing observations (weekends/holidays are
    common) are removed; merge_asof below carries only the last published
    value forward to a contract start date.
    """
    data = pd.read_csv(path)
    columns = {column.lower(): column for column in data.columns}
    # FRED's direct CSV download calls the date column ``observation_date``;
    # older exports commonly call it ``DATE``.  Accept both formats.
    date_column = columns.get("date", columns.get("observation_date"))
    if date_column is None or "dgs1" not in columns:
        raise ValueError("DGS1 CSV must contain DATE and DGS1 columns.")
    out = data.rename(columns={date_column: "date", columns["dgs1"]: "rf_percent"})[["date", "rf_percent"]].copy()
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out["rf_percent"] = pd.to_numeric(out["rf_percent"], errors="coerce")
    out = out.dropna().sort_values("date").drop_duplicates("date", keep="last")
    out["rf"] = out.pop("rf_percent") / 100.0
    if out.empty:
        raise ValueError("DGS1 CSV has no usable observations.")
    return out.reset_index(drop=True)


def attach_point_in_time_rates(frame: pd.DataFrame, rates: pd.DataFrame) -> pd.DataFrame:
    """Attach the most recently published rate; never use a later date."""
    left = frame.sort_values("date").reset_index().rename(columns={"index": "_row_order"})
    merged = pd.merge_asof(left, rates.sort_values("date"), on="date", direction="backward")
    return merged.sort_values("_row_order").drop(columns="_row_order").reset_index(drop=True)
