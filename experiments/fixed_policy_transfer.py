"""Run fixed-policy transfer after placing a licensed CRSP CSV in data/raw/crsp_daily.csv."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from src.study import local_contracts, fixed_transfer, save_study

if __name__ == "__main__":
    csv = ROOT / "data/raw/crsp_daily.csv"
    if not csv.exists(): raise SystemExit("Missing data/raw/crsp_daily.csv. See docs/wrds_download_instructions.md.")
    contracts, load_log, contract_log = local_contracts(csv)
    results = fixed_transfer(contracts)
    save_study(results, contracts, ROOT / "outputs", ROOT / "figures", "Local CRSP study",
        {"data": "local user-provided CRSP export", "seed": 42, "experiment": "fixed policy transfer"},
        exclusions=load_log.assign(stage="loader")._append(contract_log.assign(stage="contract_builder"), ignore_index=True))
