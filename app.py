"""
Asset Health Digital Twin · maintenance policy lab

Run:  streamlit run app.py
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pandas as pd
import streamlit as st

import charts
import ui
from experiments import compare, summarize
from line import MaintenanceConfig, default_line, run
from policies import POLICY_NAMES, POLICY_ORDER, Policy

RESULTS = Path(__file__).parent / "results"

st.set_page_config(page_title="Asset Health Digital Twin", page_icon="🩺", layout="wide")
ui.inject()


def plot(fig) -> None:
    with st.container(border=True):
        st.plotly_chart(fig, width="stretch", config=charts.CONFIG)


def html(s: str, col=None) -> None:
    (col or st).markdown(s, unsafe_allow_html=True)


# ─── Cached model runs ──────────────────────────────────────────────────────
@st.cache_data(show_spinner=False, max_entries=32)
def live_compare(pm_interval, threshold, risk_threshold, inspection_h, crew, insp_sigma, days, reps):
    base = Policy(pm_interval_h=pm_interval, threshold=threshold, risk_threshold=risk_threshold, inspection_h=inspection_h)
    pols = [base.with_(kind=k) for k in POLICY_ORDER]
    cfgs = [replace(c, health=replace(c.health, insp_sigma=insp_sigma)) for c in default_line()]
    reps_df, summ = compare(pols, list(range(1, reps + 1)), configs=cfgs,
                            mcfg=MaintenanceConfig(crew_size=crew), days=days, warmup_days=5.0)
    return reps_df, summ


@st.cache_data(show_spinner=False, max_entries=16)
def twin_run(kind, pm_interval, threshold, risk_threshold, inspection_h, crew, insp_sigma, days, seed):
    pol = Policy(kind, pm_interval_h=pm_interval, threshold=threshold, risk_threshold=risk_threshold, inspection_h=inspection_h)
    cfgs = [replace(c, health=replace(c.health, insp_sigma=insp_sigma)) for c in default_line()]
    return run(pol, configs=cfgs, mcfg=MaintenanceConfig(crew_size=crew), days=days, warmup_days=5.0,
               seed=seed, trace_dt=2.0, record_events=True)


@st.cache_data(show_spinner=False)
def study():
    out = {}
    for name in ("policy_comparison", "sweeps", "paired_differences", "inspection_noise", "machine_availability"):
        f = RESULTS / f"{name}.csv"
        out[name] = pd.read_csv(f) if f.exists() else None
    return out


# ─── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    ui.sidebar_brand()
    st.markdown("**Policy settings**")
    pm_interval = st.slider("Time-based · PM interval (h)", 20, 160, 60, 10,
                            help="Overhaul after this many operating hours.")
    threshold = st.slider("Condition-based · health threshold", 0.10, 0.80, 0.60, 0.05,
                          help="Request PM when the inspected health index falls below this value.")
    risk_threshold = st.select_slider("Risk-based · risk threshold", [0.01, 0.02, 0.04, 0.06, 0.08, 0.10, 0.15, 0.20, 0.30], 0.10,
                                      help="Request PM when P(failure before next inspection) × consequence reaches this value.")
    st.markdown("**Plant settings**")
    inspection_h = st.select_slider("Inspection interval (h)", [4, 8, 12, 24, 48], 8)
    crew = st.radio("Maintenance crews", [1, 2], horizontal=True, key="crew")
    insp_sigma = st.select_slider("Inspection error σ", [0.0, 0.05, 0.10, 0.20], 0.05)
    st.markdown("**Simulation**")
    days = st.select_slider("Days simulated (after 5-day warm-up)", [10, 20, 30, 60], 20)
    reps = st.slider("Replications", 1, 10, 3, help="Each replication uses a different random seed, shared by all policies.")
    html('<div class="side-note">All data are simulated and every parameter is illustrative. '
         'The model is a digital-twin-style simulation, not connected to a real machine.</div>')

args = (pm_interval, threshold, risk_threshold, inspection_h, crew, insp_sigma, days)

# ─── Hero ───────────────────────────────────────────────────────────────────
ui.hero("Smart maintenance · discrete-event simulation", "Asset Health Digital Twin",
        "Each machine in a 4-station production line carries a health index that wears down while it runs; "
        "lower health means more failures. Compare four maintenance policies by what really matters: "
        "throughput, downtime and cost per good part.",
        [("Simulated data", "amber"), ("SimPy line model", "cyan"), ("Health-driven failures", "violet"),
         ("4 maintenance policies", "mint")])

tab_cmp, tab_twin, tab_study, tab_method = st.tabs(
    ["📊  Policy what-if", "🩺  Health twin", "🔬  Study results", "ℹ️  Method"])

# ═══════════════════════════════ WHAT-IF ════════════════════════════════════
with tab_cmp:
    ui.section("What-if", "Which maintenance policy pays off?",
               f"All four policies run on the same {reps} random seed(s) (common random numbers), "
               f"{days} days each. Change the settings in the sidebar.")
    with st.spinner("Simulating the line under four policies…"):
        reps_df, summ = live_compare(*args, reps)
    s = summ.set_index("policy")
    best = s["cost_per_part"].idxmin()
    rtf = s.loc["RTF"]
    b = s.loc[best]
    c1, c2, c3, c4 = st.columns(4)
    html(ui.kpi("Lowest cost per part", POLICY_NAMES[best], f"{b['cost_per_part']:.2f} vs {rtf['cost_per_part']:.2f} run-to-failure", "mint"), c1)
    html(ui.kpi("Throughput", f"{b['throughput_per_h']:.2f}", f"good parts/h · {(b['throughput_per_h'] / rtf['throughput_per_h'] - 1) * 100:+.1f}% vs RTF",
                "cyan", unit="/h"), c2)
    html(ui.kpi("Failures per run", f"{b['failures']:.0f}", f"vs {rtf['failures']:.0f} with run-to-failure", "violet"), c3)
    html(ui.kpi("PMs per run", f"{b['pm_count']:.0f}", f"planned overhauls · {b['pm_down_h']:.0f} machine-h", "amber"), c4)
    st.write("")
    plot(charts.policy_overview(summ))
    plot(charts.downtime_split(summ))

    worst = s["cost_per_part"].idxmax()
    i1, i2, i3 = st.columns(3)
    html(ui.insight("Best vs worst", f"<b>{POLICY_NAMES[best]}</b> costs {b['cost_per_part']:.2f} per good part; "
                    f"<b>{POLICY_NAMES[worst]}</b> costs {s.loc[worst, 'cost_per_part']:.2f} "
                    f"({(s.loc[worst, 'cost_per_part'] / b['cost_per_part'] - 1) * 100:.0f}% more).", "mint"), i1)
    ft = s["failures"].replace(0, float("nan"))
    html(ui.insight("Failures avoided", f"Preventive policies cut failures from <b>{rtf['failures']:.0f}</b> to "
                    f"<b>{ft.drop('RTF').min():.0f} to {ft.drop('RTF').max():.0f}</b> per run. Each failure also leaves the "
                    "machine worse than before, because a repair restores only part of its health.", "violet"), i2)
    overlap = (b["cost_per_part"] + b["cost_per_part_ci"]) > s.drop(best)["cost_per_part"].sub(s.drop(best)["cost_per_part_ci"]).min() \
        if reps > 1 else True
    html(ui.insight("Confidence", ("Confidence intervals of the top policies overlap: run more replications or longer horizons "
                                   "before calling a winner." if overlap else
                                   "The best policy's 95% confidence interval does not overlap with the others.")
                    if reps > 1 else "Only 1 replication: no confidence interval. Increase replications for a fair comparison.",
                    "amber"), i3)
    with st.expander("Results table"):
        cols = ["policy_name", "throughput_per_h", "throughput_per_h_ci", "cost_per_part", "cost_per_part_ci",
                "failures", "pm_count", "cm_down_h", "pm_down_h"]
        st.dataframe(summ[cols].round(2), hide_index=True, width="stretch")

# ═══════════════════════════════ HEALTH TWIN ════════════════════════════════
with tab_twin:
    ui.section("Health twin", "Watch every machine wear down and recover",
               "One replication with the sidebar settings. Health is recorded every 2 hours; the shaded band is the warm-up.")
    a, b_, _ = st.columns([1.2, 0.8, 2])
    kind = a.selectbox("Policy", POLICY_ORDER, index=2, format_func=lambda k: POLICY_NAMES[k], key="twin_policy")
    seed = b_.number_input("Seed", 1, 999, 1)
    with st.spinner("Running one replication…"):
        r = twin_run(kind, *args, int(seed))
    k1, k2, k3, k4 = st.columns(4)
    html(ui.kpi("Throughput", f"{r['throughput_per_h']:.2f}", "good parts per hour", "cyan", unit="/h"), k1)
    html(ui.kpi("Failures", f"{r['failures']}", f"{r['hard_failures']} at health 0 (worn out)", "red"), k2)
    html(ui.kpi("PMs", f"{r['pm_count']}", "planned overhauls", "mint"), k3)
    html(ui.kpi("Cost per part", f"{r['cost_per_part']:.2f}", "line + maintenance cost", "amber"), k4)
    st.write("")
    thr = threshold if kind == "CBM" else None
    plot(charts.health_traces(r["trace"], r["events"], thr, warmup_h=5 * 24))
    html('<div class="side-note">✕ failure · ▲ PM done' + (" · dashed line = health threshold" if thr else "") + "</div>")
    ev = pd.DataFrame(r["events"])
    if len(ev):
        ev = ev[ev.event.isin(["failure", "pm_done", "pm_request"])]
        with st.expander(f"Maintenance event log ({len(ev)} events)"):
            show = ev.assign(day=(ev.time_h / 24).round(2))[["day", "machine", "event", "health"]]
            st.dataframe(show, hide_index=True, width="stretch", height=300)

# ═══════════════════════════════ STUDY ══════════════════════════════════════
with tab_study:
    S = study()
    if S["policy_comparison"] is None:
        st.warning("No study results found. Run `python experiments.py` to create the results/ folder.")
    else:
        pc = S["policy_comparison"]
        n = int(pc["n"].iloc[0])
        ui.section("Full study", "Tuned policies, 60 days, many replications",
                   f"Each policy's setting was tuned on 10 separate seeds, then all four were evaluated on {n} common seeds.")
        ps = pc.set_index("policy")
        bst = ps["cost_per_part"].idxmin()
        cols = st.columns(4)
        for col, p in zip(cols, POLICY_ORDER):
            row = ps.loc[p]
            html(ui.kpi(POLICY_NAMES[p], f"{row['cost_per_part']:.2f}",
                        f"{row['throughput_per_h']:.2f} parts/h · {row['setting']}",
                        {"RTF": "red", "TBM": "amber", "CBM": "violet", "RBM": "mint"}[p], unit=" /part"), col)
        st.write("")
        plot(charts.policy_overview(pc))

        pdiff = S["paired_differences"]
        if pdiff is not None:
            g = lambda v, p, k: pdiff[(pdiff.vs == v) & (pdiff.policy == p) & (pdiff.kpi == k)].iloc[0]  # noqa: E731
            d1 = g("RTF", bst, "throughput_per_h")
            d2 = g("RTF", bst, "cost_per_part")
            d3 = g("CBM", "RBM", "cost_per_part")
            i1, i2, i3 = st.columns(3)
            html(ui.insight("Gain vs run-to-failure", f"<b>{POLICY_NAMES[bst]}</b>: {d1['diff']:+.2f} ± {d1['ci']:.2f} parts/h "
                            f"and {d2['diff']:+.2f} ± {d2['ci']:.2f} cost per part (paired 95% CI).", "mint"), i1)
            verdict = "no significant difference" if abs(d3["diff"]) <= d3["ci"] else ("risk-based is cheaper" if d3["diff"] < 0 else "condition-based is cheaper")
            html(ui.insight("Risk ranking vs plain CBM", f"Risk-based minus condition-based: {d3['diff']:+.2f} ± {d3['ci']:.2f} "
                            f"cost per part → <b>{verdict}</b>.", "violet"), i2)
            html(ui.insight("Tuned settings", " · ".join(f"<b>{p}</b> {ps.loc[p, 'setting']}" for p in ("TBM", "CBM", "RBM")), "amber"), i3)

        if S["sweeps"] is not None:
            ui.section("Tuning", "Every policy has a sweet spot", "Too little PM lets machines fail; too much PM wastes crew time and capacity.")
            pick = st.radio("Policy", ["TBM", "CBM", "RBM"], index=1, horizontal=True, format_func=lambda k: POLICY_NAMES[k],
                            label_visibility="collapsed", key="sweep_pick")
            plot(charts.sweep_curve(S["sweeps"], pick))
        m1, m2 = st.columns(2)
        if S["machine_availability"] is not None:
            with m1:
                plot(charts.availability_heatmap(S["machine_availability"]))
            with m2:
                plot(charts.pm_allocation(S["machine_availability"]))
        if S["inspection_noise"] is not None:
            plot(charts.noise_curve(S["inspection_noise"]))

# ═══════════════════════════════ METHOD ═════════════════════════════════════
with tab_method:
    ui.section("Method", "How the twin works", "Every component is plain Python, covered by unit tests.")
    m1, m2 = st.columns(2)
    with m1:
        with st.container(border=True):
            st.markdown("##### Health & failures")
            st.latex(r"H_{t+\Delta t} = H_t - \Delta H,\quad \Delta H \sim \text{Gamma}\left(\frac{\Delta t}{L\,c^2},\ c^2\right)")
            st.latex(r"\lambda(H) = \lambda_0\, e^{\gamma (1-H)}")
            st.markdown("Health falls only while a machine **operates** (mean life *L* hours, path variability *c*). "
                        "The failure rate follows a proportional-hazards form: a new machine still fails occasionally, "
                        "a worn one much more often, and **H = 0 is a certain failure**. Corrective repair restores 30% of "
                        "the lost health; PM restores H to 1.")
    with m2:
        with st.container(border=True):
            st.markdown("##### Policies")
            st.markdown("- **Run-to-failure**: repair only after a failure.\n"
                        "- **Time-based**: PM every *T* operating hours.\n"
                        "- **Condition-based**: inspect every shift (noisy health score), PM when Ĥ < threshold, crew works first-come-first-served.\n"
                        "- **Risk-based**: risk = P(fail before next inspection) × consequence, where consequence is the station's "
                        "share of the bottleneck load. PM when risk ≥ threshold; the crew serves the riskiest machine first.\n\n"
                        "Corrective work always comes before PM. One shared crew by default.")
    with st.container(border=True):
        st.markdown("##### Line and costs")
        st.markdown("Cutting → Machining (2 machines, bottleneck) → Assembly → Inspection, finite buffers of 5, gamma processing "
                    "times, scrap 0.5 to 3%. Cost per good part = (line cost 400/h × hours + 2000 per corrective repair + "
                    "600 per PM) ÷ good parts. **All values are illustrative**, chosen to be plausible, not measured.")

ui.footer()
