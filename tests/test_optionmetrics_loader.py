import pandas as pd
from src.optionmetrics_loader import select_near_atm_one_year_put


def test_same_day_near_atm_one_year_put_is_selected():
    crsp = pd.DataFrame({"permno": [1], "date": pd.to_datetime(["2020-01-02"]), "price_abs": [100.0]})
    quotes = pd.DataFrame({
        "permno": [1, 1, 1],
        "date": pd.to_datetime(["2020-01-02"] * 3),
        "implied_volatility": [.20, .30, .40],
        "strike_price": [100.0, 110.0, 100.0],
        "expiration": pd.to_datetime(["2021-01-01", "2021-01-01", "2020-08-01"]),
    })
    chosen = select_near_atm_one_year_put(quotes, crsp)
    assert len(chosen) == 1
    assert chosen.loc[0, "implied_volatility"] == .20
