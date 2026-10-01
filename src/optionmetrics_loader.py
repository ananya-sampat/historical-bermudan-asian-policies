"""Local loader for a small, user-exported OptionMetrics implied-volatility panel."""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd


ALIASES = {
    "date": "date", "permno": "permno", "ticker": "ticker", "cp_flag": "cp_flag", "call_put": "cp_flag",
    "impl_volatility": "implied_volatility", "implied_volatility": "implied_volatility",
    "implied_vol": "implied_volatility", "iv": "implied_volatility",
    "strike_price": "strike_price", "strike": "strike_price",
    "exdate": "expiration", "expiration": "expiration", "expiry": "expiration",
    "delta": "delta", "secid": "secid", "effect_date": "effect_date",
    "days": "days", "days_to_expiration": "days", "days_to_expiry": "days",
}


def load_optionmetrics_quotes(path: str | Path) -> pd.DataFrame:
    """Load a local OptionMetrics export using flexible, documented aliases."""
    raw = pd.read_csv(path)
    rename = {c: ALIASES[c.lower()] for c in raw.columns if c.lower() in ALIASES}
    data = raw.rename(columns=rename).copy()
    required = {"date", "implied_volatility"}
    missing = required - set(data.columns)
    if missing or not ({"permno", "ticker", "secid"} & set(data.columns)):
        raise ValueError("OptionMetrics CSV needs date, implied_volatility, and a permno, ticker, or secid identifier.")
    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    for column in ("implied_volatility", "strike_price", "delta", "days"):
        if column in data:
            data[column] = pd.to_numeric(data[column], errors="coerce")
    if "expiration" in data:
        data["expiration"] = pd.to_datetime(data["expiration"], errors="coerce")
    data = data.dropna(subset=["date", "implied_volatility"])
    data = data[(data["implied_volatility"] > 0) & (data["implied_volatility"] < 5)]
    if "cp_flag" in data:
        data = data[data["cp_flag"].astype(str).str.upper().str.startswith("P")]
    return data.reset_index(drop=True)


def load_optionmetrics_security_map(path: str | Path) -> pd.DataFrame:
    """Load the small IvyDB US security-name export used to map SECID to ticker."""
    raw = pd.read_csv(path)
    rename = {c: ALIASES[c.lower()] for c in raw.columns if c.lower() in ALIASES}
    data = raw.rename(columns=rename).copy()
    required = {"secid", "effect_date", "ticker"}
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"OptionMetrics security map is missing: {sorted(missing)}")
    data["effect_date"] = pd.to_datetime(data["effect_date"], errors="coerce")
    return data.dropna(subset=["secid", "effect_date", "ticker"]).sort_values(["effect_date", "secid"]).reset_index(drop=True)


def attach_point_in_time_ticker(quotes: pd.DataFrame, security_map: pd.DataFrame) -> pd.DataFrame:
    """Map SECID to its most recently effective ticker without looking ahead."""
    if "ticker" in quotes:
        return quotes
    if "secid" not in quotes:
        raise ValueError("OptionMetrics quotes need ticker or secid.")
    left = quotes.sort_values(["date", "secid"])
    right = security_map.sort_values(["effect_date", "secid"])
    return pd.merge_asof(left, right[["secid", "effect_date", "ticker"]], by="secid",
                         left_on="date", right_on="effect_date", direction="backward").drop(columns="effect_date")


def select_near_atm_one_year_put(quotes: pd.DataFrame, crsp: pd.DataFrame,
                                 target_days: int = 365, min_days: int = 180,
                                 max_days: int = 550) -> pd.DataFrame:
    """Select one same-day listed put quote per CRSP security-date.

    Selection uses only quote fields available on the contract start date:
    nearest maturity to one year, then closest-to-ATM strike (or delta).
    """
    underlier = crsp[[c for c in ("permno", "ticker", "date", "price_abs") if c in crsp]].copy()
    if "permno" in quotes:
        merged = quotes.merge(underlier[["permno", "date", "price_abs"]], on=["permno", "date"], how="inner")
    else:
        merged = quotes.merge(underlier[["ticker", "date", "permno", "price_abs"]], on=["ticker", "date"], how="inner")
    # The standardized OptionMetrics volatility surface already supplies fixed
    # maturity and delta buckets.  Select the 365-day put nearest -0.50 delta.
    if "days" in merged:
        surface = merged[merged["days"].between(360, 370)].copy()
        if "cp_flag" in surface:
            surface = surface[surface["cp_flag"].astype(str).str.upper().str.startswith("P")]
        delta = surface["delta"].astype(float)
        delta = np.where(np.abs(delta) > 1, delta / 100.0, delta)
        surface["maturity_distance"] = (surface["days"] - target_days).abs()
        surface["atm_distance"] = np.abs(delta + .5)
        selected = surface.sort_values(["permno", "date", "maturity_distance", "atm_distance"]).drop_duplicates(["permno", "date"])
        return selected[["permno", "date", "implied_volatility", "maturity_distance", "atm_distance"]].reset_index(drop=True)
    if "expiration" in merged:
        merged["days_to_expiry"] = (merged["expiration"] - merged["date"]).dt.days
        merged = merged[merged["days_to_expiry"].between(min_days, max_days)]
        merged["maturity_distance"] = (merged["days_to_expiry"] - target_days).abs()
    else:
        merged["maturity_distance"] = 0.0
    if "strike_price" in merged:
        usable = (merged["strike_price"] > 0) & (merged["price_abs"] > 0)
        merged = merged.loc[usable].copy()
        merged["atm_distance"] = np.abs(np.log(merged["strike_price"] / merged["price_abs"]))
    elif "delta" in merged:
        merged["atm_distance"] = (merged["delta"].abs() - .5).abs()
    else:
        raise ValueError("OptionMetrics CSV needs strike_price or delta to select a near-ATM contract.")
    selected = merged.sort_values(["permno", "date", "maturity_distance", "atm_distance"]).drop_duplicates(["permno", "date"])
    return selected[["permno", "date", "implied_volatility", "maturity_distance", "atm_distance"]].reset_index(drop=True)
