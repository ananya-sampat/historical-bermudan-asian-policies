"""Run rolling, no-look-ahead calibration after adding a licensed local CRSP CSV."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from src.study import local_contracts, fixed_transfer, rolling_calibration, save_study

if __name__ == "__main__":
    csv = ROOT / "data/raw/crsp_daily.csv"
    if not csv.exists(): raise SystemExit("Missing data/raw/crsp_daily.csv. See docs/wrds_download_instructions.md.")
    rate_csv = ROOT / "data/raw/dgs1.csv"
    if not rate_csv.exists(): raise SystemExit("Missing data/raw/dgs1.csv. Download FRED DGS1 as described in docs/wrds_download_instructions.md.")
    contracts, load_log, contract_log = local_contracts(csv, rate_path=rate_csv, require_rate=True)
    fixed = fixed_transfer(contracts)
    rolling = rolling_calibration(contracts)
    results = __import__("pandas").concat([fixed, rolling], ignore_index=True)
    save_study(results, contracts, ROOT / "outputs", ROOT / "figures", "Local CRSP study",
        {"data": "local user-provided CRSP export", "risk_free_rate": "FRED DGS1, last available observation at contract start", "seed": 42, "experiments": ["fixed policy transfer", "rolling calibration"]},
        exclusions=load_log.assign(stage="loader")._append(contract_log.assign(stage="contract_builder"), ignore_index=True))
