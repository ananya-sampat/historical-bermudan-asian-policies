"""Market-informed rolling calibration using local CRSP, DGS1, and OptionMetrics exports."""
from pathlib import Path
import pandas as pd
import sys
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from src.study import implied_vol_contracts, fixed_transfer, rolling_calibration, save_study

if __name__ == "__main__":
    crsp = ROOT / "data/raw/crsp_daily.csv"
    rates = ROOT / "data/raw/dgs1.csv"
    options = ROOT / "data/raw/optionmetrics_daily.csv"
    security_map = ROOT / "data/raw/optionmetrics_security_map.csv"
    missing = [str(p.relative_to(ROOT)) for p in (crsp, rates, options, security_map) if not p.exists()]
    if missing: raise SystemExit("Missing local input(s): " + ", ".join(missing) + ". See docs/optionmetrics_download_instructions.md.")
    contracts, load_log, contract_log = implied_vol_contracts(crsp, options, rates, security_map)
    fixed = fixed_transfer(contracts)
    implied = rolling_calibration(contracts, experiment_name="implied_vol_calibration")
    results = pd.concat([fixed, implied], ignore_index=True)
    exclusions = pd.concat([load_log.assign(stage="loader"), contract_log.assign(stage="contract_builder")], ignore_index=True)
    save_study(results, contracts, ROOT / "outputs", ROOT / "figures", "CRSP + OptionMetrics implied-volatility study",
        {"data": "local user-provided CRSP and OptionMetrics exports", "volatility_input": "same-day 365-day, -0.50 delta standardized listed-put implied volatility", "risk_free_rate": "FRED DGS1, last available start-date observation", "seed": 42}, exclusions)
