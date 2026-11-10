"""
Experiments: replications, 95% confidence intervals, parameter sweeps and the
final policy comparison.

Method
------
1. Tune: for each policy, sweep its decision parameter (PM interval, health
   threshold or risk threshold) on TUNING seeds and pick the value with the
   lowest total cost per good part.
2. Evaluate: run all four policies at their tuned settings on a separate set of
   EVALUATION seeds. The same seeds are used for every policy (common random
   numbers), so differences come from the policy, not from luck.

Run:  python experiments.py            (writes results/*.csv, ~3-5 min)
      python experiments.py --quick    (fewer replications, for a smoke test)
"""
from __future__ import annotations

import argparse
import math
import os
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from typing import Iterable, List, Optional

import numpy as np
import pandas as pd

from line import MaintenanceConfig, StationConfig, default_line, run
from policies import POLICY_NAMES, POLICY_ORDER, Policy

KPIS = ["throughput_per_h", "cost_per_part", "maint_cost_per_part", "failures", "hard_failures",
        "pm_count", "cm_down_h", "pm_down_h", "avg_flow_time_h"]

# two-sided 95% Student-t quantiles for df = 1..30
_T95 = [12.706, 4.303, 3.182, 2.776, 2.571, 2.447, 2.365, 2.306, 2.262, 2.228,
        2.201, 2.179, 2.160, 2.145, 2.131, 2.120, 2.110, 2.101, 2.093, 2.086,
        2.080, 2.074, 2.069, 2.064, 2.060, 2.056, 2.052, 2.048, 2.045, 2.042]

SWEEPS = {
    "TBM": ("pm_interval_h", [20, 30, 40, 50, 60, 80, 100, 130, 160]),
    "CBM": ("threshold", [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]),
    "RBM": ("risk_threshold", [0.01, 0.02, 0.04, 0.06, 0.08, 0.10, 0.15, 0.20, 0.30]),
}
TUNE_SEEDS = list(range(101, 111))
EVAL_SEEDS = list(range(1, 21))


def t95(n: int) -> float:
    if n < 2:
        return float("nan")
    return _T95[n - 2] if n - 1 <= len(_T95) else 1.96


def mean_ci(values: Iterable[float]) -> tuple[float, float]:
    """Mean and half-width of the 95% confidence interval."""
    x = np.asarray(list(values), dtype=float)
    if len(x) < 2:
        return float(x.mean()) if len(x) else float("nan"), float("nan")
    return float(x.mean()), t95(len(x)) * float(x.std(ddof=1)) / math.sqrt(len(x))


def _one(args) -> dict:
    policy, seed, kw = args
    r = run(policy, seed=seed, **kw)
    r.pop("machines", None)
    return r


def replicate(policy: Policy, seeds: List[int], workers: int = 1, **kw) -> pd.DataFrame:
    """Run one replication per seed; returns one row per replication."""
    jobs = [(policy, s, kw) for s in seeds]
    if workers > 1:
        with ProcessPoolExecutor(workers) as ex:
            rows = list(ex.map(_one, jobs))
    else:
        rows = [_one(j) for j in jobs]
    return pd.DataFrame(rows)


def summarize(df: pd.DataFrame, by: List[str]) -> pd.DataFrame:
    """Mean and 95% CI half-width of every KPI, grouped by `by`."""
    out = []
    for keys, g in df.groupby(by, sort=False):
        keys = keys if isinstance(keys, tuple) else (keys,)
        row = dict(zip(by, keys))
        row["n"] = len(g)
        for k in KPIS:
            row[k], row[f"{k}_ci"] = mean_ci(g[k])
        out.append(row)
    return pd.DataFrame(out)


def sweep(kind: str, values: Optional[List[float]] = None, seeds: List[int] = TUNE_SEEDS,
          base: Policy = Policy(), workers: int = 1, **kw) -> pd.DataFrame:
    """Sweep the decision parameter of one policy. Returns per-value summary."""
    param, default_values = SWEEPS[kind]
    frames = []
    for v in values or default_values:
        df = replicate(base.with_(kind=kind, **{param: v}), seeds, workers, **kw)
        df["param"], df["value"] = param, v
        frames.append(df)
    return summarize(pd.concat(frames), ["policy", "param", "value"])


def best_value(sweep_summary: pd.DataFrame) -> float:
    return float(sweep_summary.loc[sweep_summary["cost_per_part"].idxmin(), "value"])


def tuned_policies(sweeps: dict[str, pd.DataFrame], base: Policy = Policy()) -> List[Policy]:
    pols = [base.with_(kind="RTF")]
    for kind in ("TBM", "CBM", "RBM"):
        param = SWEEPS[kind][0]
        pols.append(base.with_(kind=kind, **{param: best_value(sweeps[kind])}))
    return pols


def compare(policies: List[Policy], seeds: List[int] = EVAL_SEEDS, workers: int = 1, **kw):
    """Evaluate policies on common seeds. Returns (per-replication, summary)."""
    reps = pd.concat([replicate(p, seeds, workers, **kw) for p in policies], ignore_index=True)
    summ = summarize(reps, ["policy"])
    summ.insert(1, "policy_name", summ["policy"].map(POLICY_NAMES))
    return reps, summ


def paired_diff(reps: pd.DataFrame, a: str, b: str, kpi: str) -> tuple[float, float]:
    """Mean and 95% CI of (b - a) for one KPI using paired replications (CRN)."""
    pa = reps[reps.policy == a].set_index("seed")[kpi]
    pb = reps[reps.policy == b].set_index("seed")[kpi]
    return mean_ci((pb - pa).dropna())


def noise_sensitivity(policy: Policy, sigmas: List[float], seeds: List[int] = EVAL_SEEDS,
                      workers: int = 1, configs: Optional[List[StationConfig]] = None, **kw) -> pd.DataFrame:
    """How much does inspection accuracy matter? Re-run a policy with noisier inspections."""
    configs = configs or default_line()
    frames = []
    for s in sigmas:
        cfgs = [replace(c, health=replace(c.health, insp_sigma=s)) for c in configs]
        df = replicate(policy, seeds, workers, configs=cfgs, **kw)
        df["insp_sigma"] = s
        frames.append(df)
    return summarize(pd.concat(frames), ["policy", "insp_sigma"])


def machine_table(policies: List[Policy], seeds: List[int], **kw) -> pd.DataFrame:
    """Per-machine availability and maintenance counts, averaged over seeds."""
    rows = []
    for p in policies:
        for s in seeds:
            r = run(p, seed=s, **kw)
            for name, m in r["machines"].items():
                rows.append({"policy": p.kind, "machine": name, **m})
    df = pd.DataFrame(rows)
    return df.groupby(["policy", "machine", "station"], sort=False).mean(numeric_only=True).reset_index()


def main(quick: bool = False, out_dir: str = "results") -> None:
    os.makedirs(out_dir, exist_ok=True)
    workers = max(1, (os.cpu_count() or 2) - 1)
    tune_seeds = TUNE_SEEDS[:3] if quick else TUNE_SEEDS
    eval_seeds = EVAL_SEEDS[:4] if quick else EVAL_SEEDS
    kw = dict(days=20.0) if quick else {}

    sweeps = {}
    for kind in ("TBM", "CBM", "RBM"):
        sweeps[kind] = sweep(kind, seeds=tune_seeds, workers=workers, **kw)
        print(f"{kind} tuned {SWEEPS[kind][0]} = {best_value(sweeps[kind])}")
    pd.concat(sweeps.values()).to_csv(f"{out_dir}/sweeps.csv", index=False)

    pols = tuned_policies(sweeps)
    reps, summ = compare(pols, eval_seeds, workers, **kw)
    settings = {p.kind: ("-" if p.kind == "RTF" else f"{SWEEPS[p.kind][0]}={getattr(p, SWEEPS[p.kind][0])}") for p in pols}
    summ.insert(2, "setting", summ["policy"].map(settings))
    reps.to_csv(f"{out_dir}/policy_replications.csv", index=False)
    summ.to_csv(f"{out_dir}/policy_comparison.csv", index=False)

    rows = []
    for k in ("TBM", "CBM", "RBM"):
        for kpi in ("throughput_per_h", "cost_per_part", "failures"):
            m, h = paired_diff(reps, "RTF", k, kpi)
            rows.append({"vs": "RTF", "policy": k, "kpi": kpi, "diff": m, "ci": h})
    for kpi in ("throughput_per_h", "cost_per_part", "failures"):
        m, h = paired_diff(reps, "CBM", "RBM", kpi)
        rows.append({"vs": "CBM", "policy": "RBM", "kpi": kpi, "diff": m, "ci": h})
    pd.DataFrame(rows).to_csv(f"{out_dir}/paired_differences.csv", index=False)

    cbm = next(p for p in pols if p.kind == "CBM")
    noise_sensitivity(cbm, [0.0, 0.05, 0.10, 0.20], eval_seeds, workers, **kw).to_csv(
        f"{out_dir}/inspection_noise.csv", index=False)
    machine_table(pols, eval_seeds[:5], **kw).to_csv(f"{out_dir}/machine_availability.csv", index=False)

    cols = ["policy", "setting", "throughput_per_h", "throughput_per_h_ci", "cost_per_part",
            "cost_per_part_ci", "failures", "pm_count"]
    print(summ[cols].round(3).to_string(index=False))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()
    main(quick=a.quick)
