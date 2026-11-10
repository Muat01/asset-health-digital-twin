import math
import random

import pytest

from experiments import mean_ci, paired_diff, replicate, summarize, t95
from health import (HealthParams, corrective_restore, degrade, failure_prob,
                    hazard, inspect)
from line import MaintenanceConfig, run
from policies import Policy, consequence_weights, pm_priority

P = HealthParams()


# ─── health.py ──────────────────────────────────────────────────────────────
def test_degradation_mean_rate_matches_life():
    rng = random.Random(0)
    losses = [1.0 - degrade(1.0, 10.0, P, rng) for _ in range(20000)]
    assert sum(losses) / len(losses) == pytest.approx(10.0 / P.life_h, rel=0.05)


def test_degradation_never_negative_and_monotone():
    rng = random.Random(1)
    h = 1.0
    for _ in range(2000):
        new = degrade(h, 1.0, P, rng)
        assert 0.0 <= new <= h
        h = new
    assert h == 0.0
    assert degrade(0.7, 0.0, P, rng) == 0.7


def test_hazard_rises_as_health_falls():
    assert hazard(1.0, P) == pytest.approx(1 / P.mtbf_new_h)
    assert hazard(0.0, P) == pytest.approx(math.exp(P.gamma) / P.mtbf_new_h)
    assert hazard(0.3, P) > hazard(0.6, P) > hazard(0.9, P)


def test_failure_prob_bounds_and_order():
    assert failure_prob(0.9, 0, P) == 0.0
    assert 0 < failure_prob(0.9, 8, P) < failure_prob(0.4, 8, P) < 1
    assert failure_prob(0.01, 8, P) == 1.0          # mean path reaches H = 0


def test_inspection_noise_and_clipping():
    rng = random.Random(2)
    xs = [inspect(0.5, P, rng) for _ in range(20000)]
    assert sum(xs) / len(xs) == pytest.approx(0.5, abs=0.003)
    assert all(0 <= inspect(0.99, HealthParams(insp_sigma=0.5), rng) <= 1 for _ in range(500))
    assert inspect(0.42, HealthParams(insp_sigma=0.0), rng) == 0.42


def test_corrective_restore_is_partial():
    assert corrective_restore(0.2, 0.3) == pytest.approx(0.44)
    assert corrective_restore(1.0, 0.3) == 1.0


# ─── policies.py ────────────────────────────────────────────────────────────
def test_policy_validation_and_priority():
    with pytest.raises(ValueError):
        Policy("XYZ")
    assert pm_priority(Policy("RBM"), 0.3) < pm_priority(Policy("RBM"), 0.1)   # riskier first
    assert pm_priority(Policy("CBM"), 0.3) == pm_priority(Policy("CBM"), 0.1)  # FIFO


def test_consequence_weights_bottleneck_is_one():
    w = consequence_weights({"A": 2.0, "B": 6.0, "C": 2.6}, {"A": 1, "B": 2, "C": 1})
    assert w["B"] == 1.0 and w["A"] == pytest.approx(2 / 3) and max(w.values()) == 1.0


# ─── line.py ────────────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def runs():
    return {k: run(Policy(k), days=20, warmup_days=3, seed=7) for k in ("RTF", "TBM", "CBM", "RBM")}


def test_run_is_reproducible():
    a = run(Policy("CBM"), days=5, warmup_days=1, seed=3)
    b = run(Policy("CBM"), days=5, warmup_days=1, seed=3)
    assert a["good_parts"] == b["good_parts"] and a["failures"] == b["failures"]


def test_state_shares_sum_to_100(runs):
    for r in runs.values():
        for m in r["machines"].values():
            tot = sum(m[f"{s}_pct"] for s in ("busy", "blocked", "starved", "down_cm", "down_pm"))
            assert tot == pytest.approx(100.0, abs=1e-6)
            assert 0 < m["availability"] <= 1


def test_run_to_failure_never_does_pm(runs):
    assert runs["RTF"]["pm_count"] == 0 and runs["RTF"]["pm_down_h"] == 0


def test_preventive_policies_reduce_failures_and_raise_output(runs):
    for k in ("TBM", "CBM", "RBM"):
        assert runs[k]["pm_count"] > 0
        assert runs[k]["failures"] < runs["RTF"]["failures"]
        assert runs[k]["throughput_per_h"] > runs["RTF"]["throughput_per_h"]


def test_throughput_below_bottleneck_capacity(runs):
    for r in runs.values():
        assert 0 < r["throughput_per_h"] < 20.0     # 2 machining machines x 10 parts/h


def test_cost_accounting(runs):
    m = MaintenanceConfig()
    r = runs["CBM"]
    assert r["maint_cost"] == r["failures"] * m.cost_cm + r["pm_count"] * m.cost_pm
    assert r["cost_per_part"] == pytest.approx(r["total_cost"] / r["good_parts"])


def test_more_crews_do_not_hurt():
    one = run(Policy("RTF"), days=20, warmup_days=3, seed=4)
    two = run(Policy("RTF"), mcfg=MaintenanceConfig(crew_size=2), days=20, warmup_days=3, seed=4)
    assert two["cm_down_h"] <= one["cm_down_h"] * 1.05


def test_trace_and_events_recorded():
    r = run(Policy("CBM"), days=3, warmup_days=1, seed=1, trace_dt=2.0, record_events=True)
    assert len(r["trace"]) >= 5 * (4 * 24 / 2)
    assert all(0 <= h <= 1 for _, _, h in r["trace"])
    assert {"time_h", "machine", "event", "health"} <= set(r["events"][0])


def test_no_crew_leak_with_one_crew():
    """If a PM request were ever lost, the single crew would stay busy forever
    and failures would stop being repaired; downtime would explode."""
    r = run(Policy("RBM", risk_threshold=0.02), days=30, warmup_days=3, seed=11)
    assert r["throughput_per_h"] > 5
    for m in r["machines"].values():
        assert m["down_cm_pct"] < 50


# ─── experiments.py ─────────────────────────────────────────────────────────
def test_t_quantiles_and_ci():
    assert t95(2) == 12.706 and t95(20) == 2.093 and t95(100) == 1.96
    m, h = mean_ci([1, 2, 3, 4, 5])
    assert m == 3 and h == pytest.approx(2.776 * math.sqrt(2.5) / math.sqrt(5))
    assert math.isnan(mean_ci([4.0])[1])


def test_replicate_summarize_and_paired_diff():
    a = replicate(Policy("RTF"), [1, 2], days=3, warmup_days=1)
    b = replicate(Policy("CBM"), [1, 2], days=3, warmup_days=1)
    import pandas as pd
    reps = pd.concat([a, b])
    s = summarize(reps, ["policy"])
    assert list(s["policy"]) == ["RTF", "CBM"] and (s["n"] == 2).all()
    d, _ = paired_diff(reps, "RTF", "CBM", "good_parts")
    assert d == pytest.approx(b["good_parts"].mean() - a["good_parts"].mean())
