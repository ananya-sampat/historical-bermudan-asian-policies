"""Risk-neutral GBM simulation used only to train hypothetical exercise policies."""
from __future__ import annotations

import numpy as np


def simulate_gbm_paths(n_paths: int, n_steps: int = 250, spot: float = 100.0,
                       rate: float = 0.05, volatility: float = 0.20,
                       seed: int | None = None) -> np.ndarray:
    """Return paths with shape (n_paths, n_steps + 1), including time zero."""
    rng = np.random.default_rng(seed)
    dt = 1.0 / n_steps
    shocks = rng.standard_normal((n_paths, n_steps))
    increments = (rate - 0.5 * volatility**2) * dt + volatility * np.sqrt(dt) * shocks
    paths = np.empty((n_paths, n_steps + 1), dtype=float)
    paths[:, 0] = spot
    paths[:, 1:] = spot * np.exp(np.cumsum(increments, axis=1))
    return paths


def exercise_indices(n_steps: int = 250, every: int = 5) -> np.ndarray:
    """Fifty Bermudan exercise dates for the default 250-step contract."""
    idx = np.arange(every, n_steps + 1, every, dtype=int)
    if len(idx) != n_steps // every:
        raise ValueError("exercise schedule is inconsistent with n_steps/every")
    return idx
