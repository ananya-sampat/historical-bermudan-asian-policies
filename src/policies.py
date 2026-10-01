"""Backward Longstaff--Schwartz exercise policies with transparent sklearn models."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict
import numpy as np
from sklearn.base import clone
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler

from .simulation import exercise_indices


def running_average(paths: np.ndarray) -> np.ndarray:
    return np.cumsum(paths, axis=1) / np.arange(1, paths.shape[1] + 1)


def asian_put_payoff(averages: np.ndarray, strike: float = 100.0) -> np.ndarray:
    return np.maximum(strike - averages, 0.0)


def state_features(spot: np.ndarray, average: np.ndarray, strike: float = 100.0) -> np.ndarray:
    return np.column_stack((spot / strike, average / strike))


def model_factory(name: str, seed: int = 42):
    if name == "quadratic":
        return Pipeline([("poly", PolynomialFeatures(degree=2, include_bias=True)), ("reg", LinearRegression())])
    if name == "ridge":
        return Pipeline([("poly", PolynomialFeatures(degree=3, include_bias=True)), ("scale", StandardScaler()), ("reg", Ridge(alpha=1e-3))])
    if name == "neural":
        return Pipeline([("scale", StandardScaler()), ("reg", MLPRegressor(hidden_layer_sizes=(24, 16),
            activation="relu", solver="adam", learning_rate_init=1e-3, max_iter=250,
            early_stopping=True, validation_fraction=0.15, random_state=seed))])
    raise ValueError(f"unknown policy model: {name}")


@dataclass
class LSMPolicy:
    name: str
    models: Dict[int, object]
    strike: float
    rate: float
    n_steps: int
    exercise_every: int

    def continuation(self, t: int, spot: np.ndarray, average: np.ndarray) -> np.ndarray:
        model = self.models.get(t)
        if model is None:
            return np.full_like(np.asarray(spot, dtype=float), np.inf)
        return model.predict(state_features(np.asarray(spot), np.asarray(average), self.strike))


def train_lsm_policy(paths: np.ndarray, name: str, strike: float = 100.0, rate: float = 0.05,
                     exercise_every: int = 5, seed: int = 42) -> LSMPolicy:
    """Train one continuation model at each nonterminal Bermudan exercise date."""
    n_paths, width = paths.shape
    n_steps = width - 1
    schedule = exercise_indices(n_steps, exercise_every)
    averages = running_average(paths)
    payoffs = asian_put_payoff(averages, strike)
    dt = 1.0 / n_steps
    discount = np.exp(-rate * exercise_every * dt)
    values = payoffs[:, schedule[-1]].copy()
    models: Dict[int, object] = {}
    prototype = model_factory(name, seed)
    for t in schedule[-2::-1]:
        values *= discount
        immediate = payoffs[:, t]
        itm = immediate > 0
        if itm.sum() >= 12:
            model = clone(prototype)
            model.fit(state_features(paths[itm, t], averages[itm, t], strike), values[itm])
            continuation = model.predict(state_features(paths[:, t], averages[:, t], strike))
            exercise = itm & (immediate >= continuation)
            values[exercise] = immediate[exercise]
            models[int(t)] = model
    return LSMPolicy(name, models, strike, rate, n_steps, exercise_every)
