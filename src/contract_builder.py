"""Construct hypothetical Asian-option contracts from realized price histories."""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import pandas as pd
from .simulation import exercise_indices


@dataclass
class HistoricalContract:
    permno: int
    start_date: pd.Timestamp
    path: np.ndarray
    exercise_dates: np.ndarray
    trailing_volatility: float
    trailing_return: float
    rate: float
    calibration_volatility: float | None = None


def normalize_path(prices: np.ndarray, spot: float = 100.0) -> np.ndarray:
    prices = np.asarray(prices, dtype=float)
    if len(prices) == 0 or prices[0] <= 0:
        raise ValueError("path must have a positive initial price")
    return spot * prices / prices[0]


def build_historical_contracts(frame: pd.DataFrame, n_steps: int = 250, exercise_every: int = 5,
                               trailing_days: int = 252, start_step: int = 250,
                               default_rate: float = 0.05,
                               calibration_vol_column: str | None = None) -> tuple[list[HistoricalContract], pd.DataFrame]:
    contracts: list[HistoricalContract] = []
    log: list[dict] = []
    schedule = exercise_indices(n_steps, exercise_every)
    for permno, group in frame.groupby("permno", sort=False):
        g = group.sort_values("date").reset_index(drop=True)
        candidates = range(trailing_days, len(g) - n_steps, start_step)
        made = 0
        for start in candidates:
            prior = g.iloc[start - trailing_days:start]
            future = g.iloc[start:start + n_steps + 1]
            # return_index is preferred because DlyRet carries split changes
            # through as returns.  The fallback keeps the builder usable with
            # a manually prepared price-only file.
            path_column = "return_index" if "return_index" in future else "price_split_adjusted"
            if len(future) != n_steps + 1 or future[path_column].isna().any():
                continue
            rets = prior["total_return_with_delisting"].to_numpy(float)
            if len(rets) < trailing_days or not np.isfinite(rets).all():
                continue
            realized_vol = float(np.std(rets, ddof=1) * np.sqrt(252))
            calibration_vol = None
            if calibration_vol_column is not None:
                quoted_vol = future[calibration_vol_column].iloc[0] if calibration_vol_column in future else np.nan
                if not np.isfinite(quoted_vol) or quoted_vol <= 0:
                    continue
                calibration_vol = float(quoted_vol)
            trailing_return = float(np.prod(1 + rets) - 1)
            rate = float(future["rf"].iloc[0]) if "rf" in future and pd.notna(future["rf"].iloc[0]) else default_rate
            contracts.append(HistoricalContract(int(permno), pd.Timestamp(future["date"].iloc[0]),
                normalize_path(future[path_column].to_numpy()), schedule, realized_vol, trailing_return, rate,
                calibration_vol))
            made += 1
        if made == 0:
            log.append({"permno": int(permno), "reason": "no_complete_calibration_and_contract_window"})
    return contracts, pd.DataFrame(log, columns=["permno", "reason"])
