import numpy as np
import pandas as pd
from src.contract_builder import HistoricalContract
from src.evaluation import evaluate_policy_on_contract
from src.policies import LSMPolicy


def test_early_payoff_is_carried_to_maturity():
    class AlwaysContinueLow:
        def predict(self, x): return np.zeros(len(x))
    path = np.r_[100., np.full(250, 80.)]
    c = HistoricalContract(1, pd.Timestamp("2020-01-01"), path, np.arange(5,251,5), .2, -.1, .05)
    p = LSMPolicy("test", {5: AlwaysContinueLow()}, 100., .05, 250, 5)
    out = evaluate_policy_on_contract(p,c)
    assert out["exercise_step"] == 5
    assert out["maturity_equivalent_policy_payoff"] > out["policy_payoff"]
