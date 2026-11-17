"""
Export README figures (docs/) from the same Plotly charts used in the app.
Reads results/*.csv (run `python experiments.py` first).
Optional helper: needs `kaleido` (plotly 6+ also needs Chrome installed;
plotly==5.24.1 + kaleido==0.2.1 works without Chrome).
"""
import os

import pandas as pd

import charts
from line import run
from policies import Policy

os.makedirs("docs", exist_ok=True)
R = {n: pd.read_csv(f"results/{n}.csv") for n in
     ("policy_comparison", "sweeps", "inspection_noise", "machine_availability")}
pc = R["policy_comparison"].set_index("policy")
thr = float(pc.loc["CBM", "setting"].split("=")[1])
twin = run(Policy("CBM", threshold=thr), days=30, warmup_days=5, seed=1, trace_dt=2.0, record_events=True)

figs = {
    "policy_comparison.png": (charts.policy_overview(R["policy_comparison"]), 1200),
    "downtime_split.png": (charts.downtime_split(R["policy_comparison"]), 1200),
    "cbm_threshold_sweep.png": (charts.sweep_curve(R["sweeps"], "CBM"), 1100),
    "tbm_interval_sweep.png": (charts.sweep_curve(R["sweeps"], "TBM"), 1100),
    "rbm_risk_sweep.png": (charts.sweep_curve(R["sweeps"], "RBM"), 1100),
    "health_trajectories.png": (charts.health_traces(twin["trace"], twin["events"], thr, warmup_h=5 * 24), 1200),
    "availability_heatmap.png": (charts.availability_heatmap(R["machine_availability"]), 1100),
    "pm_allocation.png": (charts.pm_allocation(R["machine_availability"]), 1100),
    "inspection_noise.png": (charts.noise_curve(R["inspection_noise"]), 1000),
}
for name, (fig, width) in figs.items():
    fig.update_layout(paper_bgcolor="#0d1424")
    fig.write_image(f"docs/{name}", width=width, scale=2)
print(f"{len(figs)} docs figures written")
