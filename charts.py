"""Plotly figure builders. Pure functions: data in, styled figure out."""
from __future__ import annotations

import math

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from policies import POLICY_NAMES, POLICY_ORDER
from theme import (BG, CYAN, FONT, GRID, MINT, MONO, MUTED, POLICY_COLORS,
                   RED, SLATE, SURFACE, TEXT, TEXT_SOFT, VIOLET)

CONFIG = {"displaylogo": False, "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d"]}

PARAM_LABELS = {
    "pm_interval_h": "PM interval (operating hours)",
    "threshold": "Health threshold for PM (estimated H)",
    "risk_threshold": "Risk threshold for PM (P(fail) × consequence)",
}


def merge(base: dict, over: dict) -> dict:
    """Merge layout dicts one level deep, so no kwarg is passed twice."""
    out = dict(base)
    for k, v in over.items():
        out[k] = {**out[k], **v} if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def base_layout(height: int, title: str | None = None, **over) -> dict:
    lay = dict(
        height=height,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, color=TEXT_SOFT, size=12),
        margin=dict(l=64, r=28, t=58 if title else 24, b=52),
        hoverlabel=dict(bgcolor=SURFACE, bordercolor=MINT, font=dict(family=MONO, size=12, color=TEXT)),
        title=dict(text=f"<b>{title}</b>" if title else "", x=0.01, xanchor="left",
                   font=dict(size=15, color=TEXT, family=FONT)),
        xaxis=dict(gridcolor=GRID, zeroline=False, linecolor=GRID, tickfont=dict(size=11, family=MONO),
                   title=dict(font=dict(size=12, color=MUTED))),
        yaxis=dict(gridcolor=GRID, zeroline=False, linecolor=GRID, tickfont=dict(size=11, family=MONO),
                   title=dict(font=dict(size=12, color=MUTED))),
        showlegend=False,
    )
    return merge(lay, over)


def _order(df: pd.DataFrame) -> pd.DataFrame:
    return df.set_index("policy").loc[[p for p in POLICY_ORDER if p in set(df["policy"])]].reset_index()


# ─── Policy comparison ──────────────────────────────────────────────────────
def policy_bars(summary: pd.DataFrame, kpi: str, title: str, unit: str = "", fmt: str = ".2f",
                height: int = 360) -> go.Figure:
    """One bar per policy with 95% CI whiskers and a direct value label."""
    d = _order(summary)
    names = [POLICY_NAMES[p] for p in d["policy"]]
    ci = d.get(f"{kpi}_ci", pd.Series([0] * len(d))).fillna(0)
    fig = go.Figure(go.Bar(
        x=names, y=d[kpi], marker=dict(color=[POLICY_COLORS[p] for p in d["policy"]], line=dict(color=BG, width=2)),
        error_y=dict(type="data", array=ci, color=TEXT_SOFT, thickness=1.4, width=6),
        text=[f"{v:{fmt}}" for v in d[kpi]], textposition="inside", insidetextanchor="end",
        textfont=dict(family=MONO, size=13, color=BG), textangle=0,
        customdata=ci, hovertemplate="%{x}<br>%{y:" + fmt + "} ± %{customdata:" + fmt + "} " + unit + "<extra></extra>"))
    top = float((d[kpi] + ci).max())
    fig.update_layout(**base_layout(height, title, bargap=0.42,
                                    yaxis=dict(title=dict(text=unit), range=[0, top * 1.18])))
    return fig


def policy_overview(summary: pd.DataFrame, height: int = 420) -> go.Figure:
    """Two panels side by side (separate y-axes, no dual axis): throughput and cost per part."""
    d = _order(summary)
    names = [POLICY_NAMES[p].replace(" ", "<br>", 1) for p in d["policy"]]
    fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.12,
                        subplot_titles=("Throughput · good parts per hour", "Total cost per good part"))
    for col, kpi, fmt in ((1, "throughput_per_h", ".2f"), (2, "cost_per_part", ".2f")):
        ci = d[f"{kpi}_ci"].fillna(0)
        fig.add_trace(go.Bar(
            x=names, y=d[kpi], marker=dict(color=[POLICY_COLORS[p] for p in d["policy"]], line=dict(color=BG, width=2)),
            error_y=dict(type="data", array=ci, color=TEXT_SOFT, thickness=1.4, width=6),
            text=[f"{v:{fmt}}" for v in d[kpi]], textposition="inside", insidetextanchor="end",
            textfont=dict(family=MONO, size=13, color=BG), textangle=0,
            hovertemplate="%{x}<br>%{y:" + fmt + "}<extra></extra>"), row=1, col=col)
        fig.update_yaxes(range=[0, float((d[kpi] + ci).max()) * 1.2], row=1, col=col)
    fig.update_layout(**base_layout(height, None, bargap=0.38, margin=dict(t=48)))
    fig.update_xaxes(gridcolor=GRID, linecolor=GRID, tickfont=dict(size=11, family=FONT, color=TEXT_SOFT))
    fig.update_yaxes(gridcolor=GRID, zeroline=False, tickfont=dict(size=11, family=MONO))
    fig.update_annotations(font=dict(size=13, color=TEXT, family=FONT))
    return fig


def downtime_split(summary: pd.DataFrame, height: int = 340) -> go.Figure:
    """Stacked horizontal bars: corrective vs preventive downtime (machine-hours)."""
    d = _order(summary).iloc[::-1]
    names = [POLICY_NAMES[p] for p in d["policy"]]
    fig = go.Figure()
    for col, label, color in (("cm_down_h", "Corrective (failures + waiting for crew)", RED),
                              ("pm_down_h", "Preventive (planned PM)", CYAN)):
        fig.add_trace(go.Bar(y=names, x=d[col], name=label, orientation="h",
                             marker=dict(color=color, line=dict(color=BG, width=2)),
                             hovertemplate="%{y}<br>" + label + ": %{x:.0f} machine-h<extra></extra>"))
    for name, cm, pm in zip(names, d["cm_down_h"], d["pm_down_h"]):
        fig.add_annotation(x=cm + pm, y=name, text=f"{cm + pm:.0f} h", showarrow=False, xanchor="left", xshift=8,
                           font=dict(family=MONO, size=12, color=TEXT))
    fig.update_layout(**base_layout(height, "Where the downtime goes · machine-hours per run", barmode="stack",
                                    bargap=0.38, showlegend=True, margin=dict(l=150, r=60, b=84),
                                    legend=dict(orientation="h", y=-0.14, yanchor="top", x=0, traceorder="normal",
                                                font=dict(size=12, color=TEXT_SOFT))))
    return fig


# ─── Parameter sweep ────────────────────────────────────────────────────────
def sweep_curve(sw: pd.DataFrame, kind: str, height: int = 380) -> go.Figure:
    """Cost per good part vs the policy's decision parameter, with 95% CI band and the optimum."""
    d = sw[sw["policy"] == kind].sort_values("value")
    param = d["param"].iloc[0]
    color = POLICY_COLORS[kind]
    log_x = kind == "RBM"                                  # risk thresholds span 0.01 to 0.3
    ax_x = (lambda v: math.log10(v)) if log_x else (lambda v: v)  # annotations on log axes use log10
    cap = float(d["cost_per_part"].min()) * 1.35          # keep the sweet spot readable
    off = d[d["cost_per_part"] > cap]
    d = d[d["cost_per_part"] <= cap]
    x, y, ci = d["value"], d["cost_per_part"], d["cost_per_part_ci"].fillna(0)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=list(x) + list(x[::-1]), y=list(y + ci) + list((y - ci)[::-1]), fill="toself",
                             fillcolor=color, opacity=0.14, line=dict(width=0), hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=x, y=y, mode="lines+markers", line=dict(color=color, width=2),
                             marker=dict(size=8, color=color, line=dict(color=BG, width=2)),
                             customdata=list(zip(ci, d["throughput_per_h"])),
                             hovertemplate=PARAM_LABELS[param] + ": %{x}<br>cost/part %{y:.2f} ± %{customdata[0]:.2f}"
                                           "<br>throughput %{customdata[1]:.2f}/h<extra></extra>"))
    best = d.loc[d["cost_per_part"].idxmin()]
    fig.add_trace(go.Scatter(x=[best["value"]], y=[best["cost_per_part"]], mode="markers",
                             marker=dict(size=15, color=color, symbol="star", line=dict(color="white", width=1.4)),
                             hoverinfo="skip"))
    fig.add_annotation(x=ax_x(best["value"]), y=best["cost_per_part"], text=f"<b>best {best['value']:g}</b> · {best['cost_per_part']:.2f}",
                       showarrow=True, arrowhead=0, arrowcolor=MUTED, ax=0, ay=-38,
                       font=dict(family=MONO, size=12, color=TEXT), bgcolor=SURFACE, bordercolor=color, borderpad=4)
    for _, o in off.iterrows():
        fig.add_annotation(x=ax_x(o["value"]), y=cap, text=f"{o['value']:g} → {o['cost_per_part']:.0f}<br>(off scale)", showarrow=True,
                           arrowhead=2, arrowcolor=RED, ax=0, ay=26, yanchor="top", font=dict(family=MONO, size=10, color=TEXT_SOFT))
    fig.update_layout(**base_layout(height, f"{POLICY_NAMES[kind]} · cost per good part vs setting",
                                    xaxis=dict(title=dict(text=PARAM_LABELS[param])),
                                    yaxis=dict(title=dict(text="cost per good part"),
                                               range=[float(y.min() - ci.max()) * 0.97, cap * 1.02])))
    if log_x:
        fig.update_xaxes(type="log", tickvals=list(sw[sw.policy == kind]["value"]))
    return fig


def noise_curve(nz: pd.DataFrame, height: int = 340) -> go.Figure:
    d = nz.sort_values("insp_sigma")
    fig = go.Figure(go.Scatter(
        x=d["insp_sigma"], y=d["cost_per_part"], mode="lines+markers+text",
        line=dict(color=VIOLET, width=2), marker=dict(size=9, color=VIOLET, line=dict(color=BG, width=2)),
        error_y=dict(type="data", array=d["cost_per_part_ci"].fillna(0), color=TEXT_SOFT, thickness=1.2, width=5),
        text=[f"{v:.2f}" for v in d["cost_per_part"]], textposition="bottom right",
        textfont=dict(family=MONO, size=11, color=TEXT),
        hovertemplate="σ %{x}<br>cost/part %{y:.2f}<extra></extra>"))
    fig.update_layout(**base_layout(height, "Condition-based PM · value of accurate inspections",
                                    xaxis=dict(title=dict(text="inspection error σ (health units)"), range=[-0.01, 0.235]),
                                    yaxis=dict(title=dict(text="cost per good part"))))
    return fig


# ─── Health twin ────────────────────────────────────────────────────────────
def health_traces(trace: list, events: list, threshold: float | None = None, warmup_h: float = 0.0,
                  height: int | None = None) -> go.Figure:
    """Small multiples: one panel per machine, health over time with failures and PM marked."""
    tr = pd.DataFrame(trace, columns=["time_h", "machine", "health"])
    ev = pd.DataFrame(events) if events else pd.DataFrame(columns=["time_h", "machine", "event", "health"])
    machines = list(dict.fromkeys(tr["machine"]))
    n = len(machines)
    fig = make_subplots(rows=n, cols=1, shared_xaxes=True, vertical_spacing=0.035, subplot_titles=machines)
    for i, m in enumerate(machines, start=1):
        t = tr[tr.machine == m]
        fig.add_trace(go.Scatter(x=t.time_h / 24, y=t.health, mode="lines", line=dict(color=CYAN, width=1.8),
                                 fill="tozeroy", fillcolor="rgba(76,201,240,0.07)", name=m,
                                 hovertemplate=m + "<br>day %{x:.1f}<br>H = %{y:.2f}<extra></extra>"), row=i, col=1)
        e = ev[ev.machine == m] if len(ev) else ev
        for kind, sym, color, label in (("failure", "x", RED, "Failure"), ("pm_done", "triangle-up", MINT, "PM done")):
            k = e[e.event == kind] if len(e) else e
            if len(k):
                fig.add_trace(go.Scatter(x=k.time_h / 24, y=k.health, mode="markers", name=label,
                                         marker=dict(symbol=sym, size=9, color=color, line=dict(color=BG, width=1)),
                                         hovertemplate=label + "<br>day %{x:.1f} · H %{y:.2f}<extra></extra>"),
                              row=i, col=1)
        if threshold is not None:
            fig.add_hline(y=threshold, line=dict(color=VIOLET, width=1.2, dash="dash"), row=i, col=1)
        fig.update_yaxes(range=[-0.05, 1.08], tickvals=[0, 0.5, 1], row=i, col=1)
    if warmup_h:
        fig.add_vrect(x0=0, x1=warmup_h / 24, fillcolor=SLATE, opacity=0.18, line_width=0, layer="below")
    fig.update_layout(**base_layout(height or 120 + 118 * n, None, margin=dict(t=30, l=56, r=24, b=44)))
    fig.update_xaxes(gridcolor=GRID, linecolor=GRID, zeroline=False, tickfont=dict(size=11, family=MONO))
    fig.update_yaxes(gridcolor=GRID, zeroline=False, tickfont=dict(size=10, family=MONO))
    fig.update_xaxes(title=dict(text="day", font=dict(size=12, color=MUTED)), row=n, col=1)
    fig.update_annotations(font=dict(size=12, color=TEXT, family=FONT), x=0, xanchor="left")
    return fig


def availability_heatmap(mt: pd.DataFrame, height: int = 330) -> go.Figure:
    """Policies x machines availability (%), single-hue sequential scale, values printed."""
    pols = [p for p in POLICY_ORDER if p in set(mt["policy"])]
    machines = list(dict.fromkeys(mt["machine"]))
    z = [[float(mt[(mt.policy == p) & (mt.machine == m)]["availability"].iloc[0]) * 100 for m in machines] for p in pols]
    fig = go.Figure(go.Heatmap(
        z=z, x=machines, y=[POLICY_NAMES[p] for p in pols], zmin=min(min(r) for r in z), zmax=100,
        colorscale=[[0, "#0f2a3a"], [1, MINT]], xgap=3, ygap=3, showscale=False,
        text=[[f"{v:.1f}%" for v in r] for r in z], texttemplate="%{text}",
        textfont=dict(family=MONO, size=12, color=TEXT),
        hovertemplate="%{y} · %{x}<br>availability %{z:.1f}%<extra></extra>"))
    fig.update_layout(**base_layout(height, "Availability per machine (%)", margin=dict(l=150),
                                    yaxis=dict(autorange="reversed", gridcolor="rgba(0,0,0,0)"),
                                    xaxis=dict(gridcolor="rgba(0,0,0,0)", tickfont=dict(family=FONT))))
    return fig


def pm_allocation(mt: pd.DataFrame, height: int = 330) -> go.Figure:
    """Grouped bars: PM count per machine for each policy that does PM."""
    fig = go.Figure()
    for p in [p for p in POLICY_ORDER if p != "RTF" and p in set(mt["policy"])]:
        d = mt[mt.policy == p]
        fig.add_trace(go.Bar(x=d.machine, y=d.pm_count, name=POLICY_NAMES[p],
                             marker=dict(color=POLICY_COLORS[p], line=dict(color=BG, width=2)),
                             hovertemplate=POLICY_NAMES[p] + " · %{x}<br>%{y:.1f} PMs per run<extra></extra>"))
    fig.update_layout(**base_layout(height, "Where the PM effort goes · PMs per machine", barmode="group",
                                    bargap=0.3, bargroupgap=0.08, showlegend=True,
                                    legend=dict(orientation="h", y=1.0, yanchor="bottom", x=0, xanchor="left",
                                                font=dict(size=12, color=TEXT_SOFT)),
                                    margin=dict(t=92), yaxis=dict(title=dict(text="PMs per 60-day run"))))
    return fig

