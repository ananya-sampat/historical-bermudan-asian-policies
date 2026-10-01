"""Summary statistics for paired realized-payoff comparisons."""
from __future__ import annotations
import numpy as np
import pandas as pd


def paired_summary(results: pd.DataFrame) -> pd.DataFrame:
    rows = []
    # A combined fixed-versus-rolling run must report one row per experiment
    # and model, rather than accidentally pooling the two experiments.
    group_keys = ["experiment", "model"] if "experiment" in results.columns else ["model"]
    for key, g in results.groupby(group_keys):
        experiment, model = key if len(group_keys) == 2 else (None, key)
        d = g["paired_difference"].to_numpy(float)
        se = np.std(d, ddof=1) / np.sqrt(len(d)) if len(d) > 1 else np.nan
        row = {"model": model, "n_contracts": len(g), "mean_policy_minus_hold": d.mean(),
            "ci95_low": d.mean() - 1.96 * se, "ci95_high": d.mean() + 1.96 * se,
            "early_exercise_rate": g["early_exercise"].mean(),
            "mean_exercise_step_if_early": g.loc[g["early_exercise"], "exercise_step"].mean()}
        if experiment is not None:
            row = {"experiment": experiment, **row}
        rows.append(row)
    return pd.DataFrame(rows)
