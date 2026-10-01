"""Forward policy application to realized paths; these are payoff comparisons, not prices."""
from __future__ import annotations
import numpy as np
import pandas as pd
from .policies import LSMPolicy, running_average, asian_put_payoff
from .contract_builder import HistoricalContract


def evaluate_policy_on_contract(policy: LSMPolicy, contract: HistoricalContract) -> dict:
    path = contract.path
    avgs = running_average(path[None, :])[0]
    payoff = asian_put_payoff(avgs, policy.strike)
    n_steps = len(path) - 1
    exercise_time = n_steps
    for t in contract.exercise_dates[:-1]:
        if payoff[t] <= 0 or t not in policy.models:
            continue
        continuation = policy.continuation(t, np.array([path[t]]), np.array([avgs[t]]))[0]
        if payoff[t] >= continuation:
            exercise_time = int(t)
            break
    raw = float(payoff[exercise_time])
    maturity_equivalent = raw * np.exp(contract.rate * (n_steps - exercise_time) / n_steps)
    hold = float(payoff[-1])
    return {"permno": contract.permno, "start_date": contract.start_date, "model": policy.name,
            "exercise_step": exercise_time, "early_exercise": exercise_time < n_steps,
            "policy_payoff": raw, "maturity_equivalent_policy_payoff": maturity_equivalent,
            "hold_payoff": hold, "paired_difference": maturity_equivalent - hold,
            "trailing_volatility": contract.trailing_volatility, "trailing_return": contract.trailing_return,
            "rate_at_start": contract.rate, "calibration_volatility": contract.calibration_volatility}


def evaluate_policies(policies: list[LSMPolicy], contracts: list[HistoricalContract]) -> pd.DataFrame:
    return pd.DataFrame([evaluate_policy_on_contract(p, c) for p in policies for c in contracts])
