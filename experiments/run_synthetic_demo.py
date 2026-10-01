"""End-to-end synthetic demonstration. It never represents CRSP or WRDS results."""
from __future__ import annotations
from pathlib import Path
import sys
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.synthetic_data import make_synthetic_crsp
from src.crsp_loader import load_crsp_daily
from src.contract_builder import build_historical_contracts
from src.simulation import simulate_gbm_paths
from src.policies import train_lsm_policy
from src.evaluation import evaluate_policies
from src.regimes import add_regimes
from src.study import save_study


def main() -> None:
    raw = make_synthetic_crsp()
    raw_path = ROOT / "data" / "processed" / "synthetic_crsp_daily.csv"
    raw.to_csv(raw_path, index=False)
    frame, load_log = load_crsp_daily(raw_path)
    contracts, contract_log = build_historical_contracts(frame)
    if not contracts: raise RuntimeError("synthetic construction produced no contracts")
    paths = simulate_gbm_paths(4000, seed=42)
    policies = [train_lsm_policy(paths, name, seed=42) for name in ("quadratic", "ridge", "neural")]
    results = add_regimes(evaluate_policies(policies, contracts))
    out = ROOT / "outputs" / "synthetic"
    figs = ROOT / "figures" / "synthetic"
    results["experiment"] = "fixed_policy_transfer"
    save_study(results, contracts, out, figs, "Synthetic demonstration", {"data": "synthetic demonstration only", "seed": 42, "n_contracts": len(contracts)}, pd.concat([load_log.assign(stage="loader"), contract_log.assign(stage="contract_builder")], ignore_index=True, sort=False))
    print(f"Synthetic demo complete: {len(contracts)} hypothetical paths; outputs saved under {out}")

if __name__ == "__main__": main()
