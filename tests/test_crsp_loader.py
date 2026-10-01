import pandas as pd
from src.crsp_loader import load_crsp_daily


def test_loader_handles_negative_prices_and_optional_delisting(tmp_path):
    p = tmp_path / "crsp.csv"
    pd.DataFrame({"permno":[1,1,2], "date":["2020-01-01","bad","2020-01-01"],
        "prc":[-10,12,0], "ret":[.01,.02,.0], "dlret":[None,None,-.5], "shrcd":[10,10,10], "cfacpr":[1,1,1]}).to_csv(p,index=False)
    clean, log = load_crsp_daily(p)
    assert len(clean) == 1
    assert clean.iloc[0].price_abs == 10
    assert set(log.reason) == {"invalid_date", "missing_or_zero_price"}
