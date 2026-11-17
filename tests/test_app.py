"""Headless tests of the charts and the Streamlit app (streamlit.testing)."""
import os
from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

import charts
from line import run
from policies import Policy

ROOT = Path(__file__).resolve().parents[1]


def _res(name):
    return pd.read_csv(ROOT / "results" / f"{name}.csv")


def test_all_charts_build():
    pc, sw = _res("policy_comparison"), _res("sweeps")
    mt, nz = _res("machine_availability"), _res("inspection_noise")
    r = run(Policy("CBM"), days=3, warmup_days=1, trace_dt=2.0, record_events=True)
    figs = [charts.policy_overview(pc), charts.policy_bars(pc, "throughput_per_h", "T"), charts.downtime_split(pc),
            charts.sweep_curve(sw, "TBM"), charts.sweep_curve(sw, "CBM"), charts.sweep_curve(sw, "RBM"),
            charts.health_traces(r["trace"], r["events"], 0.6, 24), charts.availability_heatmap(mt),
            charts.pm_allocation(mt), charts.noise_curve(nz)]
    assert all(len(f.data) > 0 for f in figs)


def test_merge_does_not_duplicate_keys():
    lay = charts.base_layout(300, "x", xaxis=dict(title=dict(text="a")), margin=dict(l=10))
    assert lay["xaxis"]["title"] == {"text": "a"} and lay["margin"]["l"] == 10 and "gridcolor" in lay["xaxis"]


def test_saved_study_tells_a_consistent_story():
    pc = _res("policy_comparison").set_index("policy")
    assert pc["cost_per_part"].idxmin() != "RTF"
    assert (pc.drop("RTF")["throughput_per_h"] > pc.loc["RTF", "throughput_per_h"]).all()
    assert (pc.drop("RTF")["failures"] < pc.loc["RTF", "failures"]).all()


def _app():
    cwd = os.getcwd()
    os.chdir(ROOT)
    try:
        at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=180)
        at.run()
    finally:
        os.chdir(cwd)
    return at


def test_app_runs_without_errors():
    at = _app()
    assert not at.exception, at.exception
    assert len(at.tabs) == 4
    assert any("Asset Health Digital Twin" in m.value for m in at.markdown)


def test_app_reacts_to_widgets():
    at = _app()
    at.radio(key="crew").set_value(2)
    at.selectbox(key="twin_policy").set_value("TBM").run()
    assert not at.exception, at.exception
    assert any("2 crew" in m.value or "Throughput" in m.value for m in at.markdown)
    assert not at.exception, at.exception
    at.radio(key="sweep_pick").set_value("RBM").run()
    assert not at.exception, at.exception
