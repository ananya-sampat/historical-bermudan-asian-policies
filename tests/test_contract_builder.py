import numpy as np
import pandas as pd
from src.contract_builder import normalize_path, build_historical_contracts
from src.synthetic_data import make_synthetic_crsp
from src.crsp_loader import load_crsp_daily
from src.policies import running_average, asian_put_payoff


def test_normalization_and_average():
    p = normalize_path(np.array([50., 75., 100.]))
    assert np.allclose(p, [100., 150., 200.])
    assert np.allclose(running_average(p[None, :])[0], [100., 125., 150.])
    assert np.allclose(asian_put_payoff(np.array([90., 100., 110.])), [10., 0., 0.])


def test_historical_contract_has_fifty_exercise_dates(tmp_path):
    data = make_synthetic_crsp(n_stocks=2, n_days=800)
    p = tmp_path / "x.csv"; data.to_csv(p, index=False)
    clean, _ = load_crsp_daily(p)
    contracts, _ = build_historical_contracts(clean, start_step=250)
    assert contracts
    assert len(contracts[0].exercise_dates) == 50
    assert contracts[0].path[0] == 100.
