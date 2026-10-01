import numpy as np
from src.contract_builder import build_historical_contracts
from src.crsp_loader import load_crsp_daily
from src.synthetic_data import make_synthetic_crsp


def test_trailing_volatility_is_unchanged_by_future_price_edit(tmp_path):
    raw = make_synthetic_crsp(n_stocks=1, n_days=800, seed=3)
    p = tmp_path / "a.csv"; raw.to_csv(p,index=False)
    clean, _ = load_crsp_daily(p); first, _ = build_historical_contracts(clean, start_step=250)
    start = first[0].start_date
    changed = raw.copy(); changed.loc[changed.date > str(start.date()), "prc"] *= 100
    q = tmp_path / "b.csv"; changed.to_csv(q,index=False)
    clean2, _ = load_crsp_daily(q); second, _ = build_historical_contracts(clean2, start_step=250)
    assert np.isclose(first[0].trailing_volatility, second[0].trailing_volatility)
