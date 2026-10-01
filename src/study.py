"""Shared local-data runners. They expect a user-provided, ignored CRSP CSV."""
from __future__ import annotations
import json
from pathlib import Path
import pandas as pd
from .crsp_loader import load_crsp_daily
from .rates import load_dgs1, attach_point_in_time_rates
from .optionmetrics_loader import (load_optionmetrics_quotes, load_optionmetrics_security_map,
                                  attach_point_in_time_ticker, select_near_atm_one_year_put)
from .contract_builder import build_historical_contracts
from .simulation import simulate_gbm_paths
from .policies import train_lsm_policy
from .evaluation import evaluate_policies
from .metrics import paired_summary
from .regimes import add_regimes, regime_summary
from .plotting import (plot_paths, plot_model_advantage, plot_exercise_timing, plot_rolling_volatility,
                       plot_regime_advantage, plot_experiment_comparison, plot_calibration_increment,
                       plot_representative_path)

MODEL_NAMES = ("quadratic", "ridge", "neural")


def local_contracts(csv_path: str | Path, start_step: int = 250, default_rate: float = .05,
                    rate_path: str | Path | None = None, require_rate: bool = False):
    frame, loader_log = load_crsp_daily(csv_path)
    if rate_path is not None:
        frame = attach_point_in_time_rates(frame, load_dgs1(rate_path))
    elif require_rate:
        raise ValueError("Rolling calibration requires data/raw/dgs1.csv. See docs/wrds_download_instructions.md.")
    contracts, contract_log = build_historical_contracts(frame, start_step=start_step, default_rate=default_rate)
    if not contracts:
        raise ValueError("No eligible contracts were built; inspect outputs/exclusions_log.csv and your CRSP export.")
    return contracts, loader_log, contract_log


def implied_vol_contracts(csv_path: str | Path, optionmetrics_path: str | Path,
                          rate_path: str | Path, security_map_path: str | Path | None = None,
                          start_step: int = 250):
    """Build contracts whose simulation volatility is a same-day listed-put IV."""
    frame, loader_log = load_crsp_daily(csv_path)
    frame = attach_point_in_time_rates(frame, load_dgs1(rate_path))
    quotes = load_optionmetrics_quotes(optionmetrics_path)
    if "ticker" not in quotes and "permno" not in quotes:
        if security_map_path is None:
            raise ValueError("OptionMetrics SECID quotes require a local security-name mapping export.")
        quotes = attach_point_in_time_ticker(quotes, load_optionmetrics_security_map(security_map_path))
    iv = select_near_atm_one_year_put(quotes, frame)
    frame = frame.merge(iv[["permno", "date", "implied_volatility"]], on=["permno", "date"], how="left")
    contracts, contract_log = build_historical_contracts(
        frame, start_step=start_step, calibration_vol_column="implied_volatility"
    )
    if not contracts:
        raise ValueError("No contracts matched an OptionMetrics near-ATM one-year put quote.")
    return contracts, loader_log, contract_log


def train_fixed_policies(n_paths: int = 20000, seed: int = 42):
    paths = simulate_gbm_paths(n_paths, rate=.05, volatility=.20, seed=seed)
    return [train_lsm_policy(paths, name, rate=.05, seed=seed) for name in MODEL_NAMES]


def fixed_transfer(contracts, n_paths: int = 20000, seed: int = 42) -> pd.DataFrame:
    out = evaluate_policies(train_fixed_policies(n_paths, seed), contracts)
    out["experiment"] = "fixed_policy_transfer"
    return add_regimes(out)


def rolling_calibration(contracts, n_paths: int = 4000, seed: int = 42,
                        experiment_name: str = "rolling_calibration") -> pd.DataFrame:
    """Train using only the volatility/rate available at each contract start date."""
    total = len(contracts)
    rows = []
    for i, contract in enumerate(contracts):
        volatility = contract.calibration_volatility or contract.trailing_volatility
        paths = simulate_gbm_paths(n_paths, rate=contract.rate, volatility=max(volatility, .01), seed=seed+i)
        policies = [train_lsm_policy(paths, name, rate=contract.rate, seed=seed+i) for name in MODEL_NAMES]
        one = evaluate_policies(policies, [contract]); one["experiment"] = experiment_name; rows.append(one)
        if (i + 1) % 10 == 0 or i + 1 == total:
            print(f"Rolling calibration: {i + 1}/{total} contracts complete", flush=True)
    return add_regimes(pd.concat(rows, ignore_index=True))


def save_study(results: pd.DataFrame, contracts, output_dir: str | Path, figure_dir: str | Path,
               label: str, metadata: dict, exclusions: pd.DataFrame | None = None) -> None:
    output_dir, figure_dir = Path(output_dir), Path(figure_dir)
    output_dir.mkdir(exist_ok=True); figure_dir.mkdir(exist_ok=True)
    results.to_csv(output_dir / "path_level_results.csv", index=False)
    summary = paired_summary(results); summary.to_csv(output_dir / "model_summary.csv", index=False)
    regime_summary(results).to_csv(output_dir / "regime_summary.csv", index=False)
    if exclusions is None: exclusions = pd.DataFrame(columns=["reason", "count"])
    exclusions.to_csv(output_dir / "exclusions_log.csv", index=False)
    (output_dir / "run_metadata.json").write_text(json.dumps(metadata, indent=2, default=str))
    fixed = results[results["experiment"] == "fixed_policy_transfer"] if "experiment" in results else results
    plot_paths(contracts[0].path, simulate_gbm_paths(5, seed=metadata.get("seed",42)), figure_dir / "historical_like_vs_gbm.png", label)
    plot_rolling_volatility(
        fixed, figure_dir / "rolling_realized_volatility.png", label,
        column="calibration_volatility" if fixed["calibration_volatility"].notna().any() else "trailing_volatility",
    )
    plot_model_advantage(paired_summary(fixed), figure_dir / "model_advantage.png", label)
    plot_regime_advantage(fixed, figure_dir / "advantage_by_regime.png", label)
    plot_exercise_timing(fixed, figure_dir / "exercise_timing.png", label)
    if "experiment" in results and results["experiment"].nunique() > 1:
        plot_experiment_comparison(results, figure_dir / "fixed_vs_calibrated.png", label)
        plot_calibration_increment(results, figure_dir / "calibration_minus_fixed.png", label)
    else:
        # A transparent placeholder based on the available fixed experiment, not fabricated calibration data.
        plot_experiment_comparison(fixed.assign(experiment="fixed_policy_transfer"), figure_dir / "fixed_vs_calibrated.png", label + " (calibration not run)")
    representative = fixed.loc[fixed["early_exercise"]].iloc[0].to_dict() if fixed["early_exercise"].any() else fixed.iloc[0].to_dict()
    contract = next(c for c in contracts if c.permno == representative["permno"] and c.start_date == representative["start_date"])
    plot_representative_path(contract, representative, figure_dir / "representative_path.png", label)
