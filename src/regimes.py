"""Regimes use only trailing information available on each contract's start date."""
from __future__ import annotations
import pandas as pd


def add_regimes(results: pd.DataFrame, low_vol: float = 0.15, high_vol: float = 0.30) -> pd.DataFrame:
    out = results.copy()
    out["volatility_regime"] = pd.cut(out["trailing_volatility"], [-float("inf"), low_vol, high_vol, float("inf")], labels=["low", "medium", "high"])
    out["return_regime"] = out["trailing_return"].ge(0).map({True: "positive", False: "negative"})
    return out


def regime_summary(results: pd.DataFrame) -> pd.DataFrame:
    keys = (["experiment"] if "experiment" in results else []) + ["model", "volatility_regime", "return_regime"]
    return results.groupby(keys, observed=True).agg(
        n_contracts=("paired_difference", "size"), mean_policy_minus_hold=("paired_difference", "mean"),
        early_exercise_rate=("early_exercise", "mean")).reset_index()
