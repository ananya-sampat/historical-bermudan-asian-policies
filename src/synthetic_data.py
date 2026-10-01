"""Clearly labeled synthetic CRSP-like data for tests and demonstrations only."""
from __future__ import annotations
import numpy as np
import pandas as pd


def make_synthetic_crsp(n_stocks: int = 12, n_days: int = 900, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2016-01-04", periods=n_days)
    frames = []
    for i in range(n_stocks):
        vol = rng.uniform(0.12, 0.42)
        drift = rng.uniform(-0.04, 0.10)
        shocks = rng.standard_normal(n_days)
        returns = drift / 252 + vol / np.sqrt(252) * shocks
        price = 20 + 10 * i
        prices = price * np.exp(np.cumsum(returns))
        frames.append(pd.DataFrame({"permno": 10000 + i, "date": dates, "prc": prices,
            "ret": np.r_[0.0, prices[1:] / prices[:-1] - 1], "dlret": np.nan,
            "cfacpr": 1.0, "shrcd": 10, "exchcd": 1}))
    return pd.concat(frames, ignore_index=True)
