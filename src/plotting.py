"""Figures are labeled synthetic unless the caller explicitly supplies real results."""
from __future__ import annotations
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


DISPLAY = {
    "quadratic": "Quadratic LSM",
    "ridge": "Cubic ridge",
    "neural": "Neural network",
    "fixed_policy_transfer": "Fixed 20% volatility",
    "implied_vol_calibration": "Implied-volatility calibration",
    "rolling_calibration": "Trailing-volatility calibration",
}


def _display(value):
    return DISPLAY.get(str(value), str(value).replace("_", " ").title())


def _title(label: str, suffix: str) -> str:
    return f"{label}\n{suffix}"


def _save(fig, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(); fig.savefig(path, dpi=160); plt.close(fig)


def plot_paths(path: np.ndarray, simulated: np.ndarray, output: Path, label: str):
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(path, lw=2, label="realized-like path")
    for p in simulated[:5]: ax.plot(p, alpha=.35, color="gray")
    ax.set(title=_title(label, "Normalized realized and simulated paths"), xlabel="Trading day", ylabel="Normalized price")
    ax.legend(); _save(fig, output)


def plot_model_advantage(summary: pd.DataFrame, output: Path, label: str):
    fig, ax = plt.subplots(figsize=(7, 4))
    yerr = np.vstack((summary["mean_policy_minus_hold"] - summary["ci95_low"], summary["ci95_high"] - summary["mean_policy_minus_hold"]))
    ax.bar([_display(x) for x in summary["model"]], summary["mean_policy_minus_hold"], yerr=yerr, capsize=4)
    ax.axhline(0, color="black", lw=1); ax.set(title=_title(label, "Policy payoff minus hold payoff (95% CI)"), ylabel="Maturity-equivalent payoff difference")
    _save(fig, output)


def plot_exercise_timing(results: pd.DataFrame, output: Path, label: str):
    fig, ax = plt.subplots(figsize=(7, 4))
    for model, g in results.groupby("model"):
        ax.hist(g.loc[g["early_exercise"], "exercise_step"], bins=20, alpha=.45, label=_display(model))
    ax.set(title=_title(label, "Early-exercise timing"), xlabel="Trading day of exercise", ylabel="Contracts"); ax.legend(); _save(fig, output)


def plot_rolling_volatility(results: pd.DataFrame, output: Path, label: str, column: str = "trailing_volatility"):
    data = results.drop_duplicates(["permno", "start_date"]).sort_values("start_date")
    fig, ax = plt.subplots(figsize=(7, 4))
    series_label = "Selected listed-put implied volatility" if column == "calibration_volatility" else "Trailing realized volatility"
    ax.plot(data["start_date"], data[column], marker="o", ms=3)
    ax.set(title=_title(label, series_label), xlabel="Contract start", ylabel="Annualized volatility")
    _save(fig, output)


def plot_regime_advantage(results: pd.DataFrame, output: Path, label: str):
    data = results.groupby(["model", "volatility_regime"], observed=True)["paired_difference"].mean().unstack()
    data = data.reindex(columns=[c for c in ("low", "medium", "high") if c in data.columns])
    fig, ax = plt.subplots(figsize=(8, 4.5)); data.plot.bar(ax=ax)
    ax.set_xticklabels([_display(x) for x in data.index], rotation=0)
    ax.legend(title="Trailing-volatility regime")
    ax.axhline(0, color="black", lw=1); ax.set(title=_title(label, "Policy advantage by trailing-volatility regime"), ylabel="Mean payoff minus hold payoff")
    _save(fig, output)


def plot_experiment_comparison(results: pd.DataFrame, output: Path, label: str):
    data = results.groupby(["experiment", "model"])["paired_difference"].mean().unstack(0)
    data.columns = [_display(x) for x in data.columns]
    fig, ax = plt.subplots(figsize=(8, 4.5)); data.plot.bar(ax=ax)
    ax.set_xticklabels([_display(x) for x in data.index], rotation=0)
    ax.axhline(0, color="black", lw=1); ax.set(title=_title(label, "Fixed versus implied-volatility calibration"), ylabel="Mean payoff minus hold payoff")
    _save(fig, output)


def plot_calibration_increment(results: pd.DataFrame, output: Path, label: str):
    """Show the paired incremental effect of IV calibration relative to fixed policies."""
    required = {"fixed_policy_transfer", "implied_vol_calibration"}
    if not required.issubset(set(results["experiment"])):
        return
    paired = results.pivot(index=["permno", "start_date", "model"], columns="experiment", values="paired_difference")
    paired["increment"] = paired["implied_vol_calibration"] - paired["fixed_policy_transfer"]
    summary = paired.groupby("model")["increment"].agg(["mean", "std", "count"])
    se = summary["std"] / np.sqrt(summary["count"])
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar([_display(x) for x in summary.index], summary["mean"], yerr=1.96 * se, capsize=4)
    ax.axhline(0, color="black", lw=1)
    ax.set(title=_title(label, "Implied-volatility calibration minus fixed policy (95% CI)"),
           ylabel="Paired payoff-difference change")
    _save(fig, output)


def plot_representative_path(contract, result: dict, output: Path, label: str):
    from .policies import running_average, asian_put_payoff
    avg = running_average(contract.path[None, :])[0]; payoff = asian_put_payoff(avg)
    fig, ax = plt.subplots(figsize=(8, 4)); ax.plot(contract.path, label="normalized price")
    ax.plot(avg, label="running average"); ax.plot(payoff, label="exercise payoff")
    ax.axvline(result["exercise_step"], color="crimson", ls="--", label="policy exercise")
    ax.set(title=_title(label, "Representative hypothetical contract"), xlabel="Trading day", ylabel="Normalized value"); ax.legend(ncol=2)
    _save(fig, output)
