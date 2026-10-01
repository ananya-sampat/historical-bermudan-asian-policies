"""Local, auditable CRSP CSV loading. Raw WRDS data is never bundled with this project."""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

REQUIRED = {"permno", "date", "prc", "ret"}

# The current CRSP Stock (CIZ) daily file uses these names.  The aliases also
# keep the loader compatible with a conventional/legacy CRSP CSV.
COLUMN_ALIASES = {
    "permno": "permno",
    "dlycaldt": "date",
    "date": "date",
    "dlyprc": "prc",
    "prc": "prc",
    "dlyret": "ret",
    "ret": "ret",
    "dlydelflg": "delisting_flag",
    "dlydelistflg": "delisting_flag",
    "dlret": "dlret",
    "cfacpr": "cfacpr",
    "shrcd": "shrcd",
    "exchcd": "exchcd",
    "ticker": "ticker",
}


def _standardize_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Translate CRSP CIZ or legacy column names to the project's schema."""
    rename = {
        column: COLUMN_ALIASES[column.lower()]
        for column in frame.columns
        if column.lower() in COLUMN_ALIASES
    }
    return frame.rename(columns=rename)


def load_crsp_daily(path: str | Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load a local CRSP export and return cleaned rows plus an exclusion log."""
    frame = _standardize_columns(pd.read_csv(path))
    missing = REQUIRED - set(frame.columns)
    if missing:
        raise ValueError(f"CRSP CSV is missing required columns: {sorted(missing)}")
    log: list[dict] = []
    frame = frame.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    for col in ["prc", "ret", "dlret", "cfacpr", "shrcd", "exchcd"]:
        if col in frame:
            frame[col] = pd.to_numeric(frame[col], errors="coerce")
    bad_date = frame["date"].isna()
    if bad_date.any():
        log.append({"reason": "invalid_date", "count": int(bad_date.sum())})
        frame = frame.loc[~bad_date]
    if "shrcd" in frame:
        non_common = ~frame["shrcd"].isin([10, 11])
        if non_common.any():
            log.append({"reason": "non_common_share_code", "count": int(non_common.sum())})
            frame = frame.loc[~non_common]
    bad_price = frame["prc"].isna() | (frame["prc"] == 0)
    if bad_price.any():
        log.append({"reason": "missing_or_zero_price", "count": int(bad_price.sum())})
        frame = frame.loc[~bad_price]
    frame["price_abs"] = frame["prc"].abs()
    if "cfacpr" in frame:
        factor = frame["cfacpr"].replace(0, np.nan).fillna(1.0)
        frame["price_split_adjusted"] = frame["price_abs"] / factor
    else:
        frame["price_split_adjusted"] = frame["price_abs"]
    frame["ret_clean"] = frame["ret"].fillna(0.0)
    if "dlret" in frame:
        # Preserve delisting information rather than silently ignoring it.
        frame["total_return_with_delisting"] = (1 + frame["ret_clean"]) * (1 + frame["dlret"].fillna(0.0)) - 1
    else:
        frame["total_return_with_delisting"] = frame["ret_clean"]
    frame = frame.sort_values(["permno", "date"]).drop_duplicates(["permno", "date"])
    # DlyRet is robust to stock splits.  We use its cumulative index to build
    # normalized contract paths, rather than treating an unadjusted DlyPrc
    # series as continuous through a split.  It is a realized-return proxy,
    # not a claim that these are traded option-underlying prices.
    frame["return_index"] = frame.groupby("permno", sort=False)["total_return_with_delisting"].transform(
        lambda returns: (1.0 + returns).cumprod()
    )
    if "delisting_flag" in frame:
        flagged = frame["delisting_flag"].astype(str).str.upper().ne("N")
        if flagged.any():
            log.append({"reason": "delisting_flagged_observations_retained", "count": int(flagged.sum())})
    return frame.reset_index(drop=True), pd.DataFrame(log, columns=["reason", "count"])
