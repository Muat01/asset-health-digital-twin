"""UI layer: global CSS and small HTML components for the Streamlit app.

Note: HTML snippets are built on a single line on purpose. Markdown treats lines
indented by 4+ spaces as code blocks, which would break the layout.
"""
from __future__ import annotations

import streamlit as st

from theme import BG, MINT, TEXT, TONES

GITHUB = "https://github.com/Muat01/asset-health-digital-twin"
LINKEDIN = "https://www.linkedin.com/in/muatasem-hadi"

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap');

:root {
  --bg: #070b14; --surface: #0d1424; --surface2: #121a2e;
  --border: rgba(255,255,255,0.08); --text: #e8edf7; --soft: #aab3c8; --muted: #7b86a0;
  --mint: #19e3b1; --cyan: #4cc9f0; --violet: #8b7bff; --amber: #ffb020; --red: #ff5470;
  --mono: 'JetBrains Mono', Consolas, monospace;
}

html, body, [class*="css"], .stApp, button, input, textarea, select {
  font-family: 'Inter', 'Segoe UI', system-ui, sans-serif !important;
}
.stApp {
  background:
    radial-gradient(1100px 560px at 88% -8%, rgba(25,227,177,0.11), transparent 62%),
    radial-gradient(900px 520px at -8% 6%, rgba(139,123,255,0.11), transparent 58%),
    radial-gradient(800px 500px at 50% 112%, rgba(76,201,240,0.07), transparent 60%),
    var(--bg);
  color: var(--text);
}
header[data-testid="stHeader"] { background: transparent; }
footer, #MainMenu { visibility: hidden; }
.block-container { padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1380px; }

/* ── Sidebar ─────────────────────────────────────────── */
section[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #0a1122 0%, #080d1a 100%);
  border-right: 1px solid var(--border);
}
section[data-testid="stSidebar"] .block-container { padding-top: 1.4rem; }
section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] p { color: var(--soft); }

/* ── Hero ────────────────────────────────────────────── */
.hero { margin: 0 0 1.4rem 0; }
.hero-eyebrow {
  font-family: var(--mono); font-size: 11.5px; letter-spacing: 0.22em; color: var(--mint);
  text-transform: uppercase; margin-bottom: 10px; display: flex; align-items: center; gap: 10px;
}
.hero-eyebrow::before { content: ""; width: 26px; height: 2px; background: var(--mint); border-radius: 2px; }
.hero-title {
  font-size: 2.6rem; line-height: 1.08; font-weight: 800; letter-spacing: -0.03em; margin: 0 0 10px 0;
  background: linear-gradient(92deg, #ffffff 0%, #b9fbe8 45%, #4cc9f0 100%);
  -webkit-background-clip: text; background-clip: text; color: transparent;
}
.hero-sub { color: var(--soft); font-size: 1.02rem; max-width: 760px; margin: 0 0 14px 0; line-height: 1.55; }
.hero-badges { display: flex; flex-wrap: wrap; gap: 8px; }

/* ── Pills & callouts ────────────────────────────────── */
.pill {
  --c: var(--mint);
  display: inline-flex; align-items: center; gap: 7px; padding: 5px 12px; border-radius: 999px;
  font-size: 11.5px; font-weight: 600; letter-spacing: 0.04em; color: var(--c);
  background: color-mix(in srgb, var(--c) 12%, transparent);
  border: 1px solid color-mix(in srgb, var(--c) 32%, transparent);
}
.pill .dot { width: 7px; height: 7px; border-radius: 50%; background: var(--c); box-shadow: 0 0 10px var(--c); }
.callout {
  --c: var(--cyan);
  display: flex; gap: 12px; align-items: flex-start; padding: 13px 16px; border-radius: 14px; margin: 6px 0;
  background: color-mix(in srgb, var(--c) 8%, transparent);
  border: 1px solid color-mix(in srgb, var(--c) 26%, transparent);
  border-left: 4px solid var(--c); color: var(--text); font-size: 0.93rem; line-height: 1.5;
}
.callout .ic { font-size: 1.1rem; line-height: 1.4; }
.callout b { color: #fff; }

/* ── KPI cards ───────────────────────────────────────── */
.kpi {
  --c: var(--mint);
  position: relative; overflow: hidden; border-radius: 16px; padding: 16px 18px 15px; height: 100%;
  background: linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0.016));
  border: 1px solid var(--border); transition: transform .18s ease, border-color .18s ease, box-shadow .18s ease;
}
.kpi::before { content: ""; position: absolute; left: 0; top: 0; right: 0; height: 3px; background: var(--c); opacity: 0.95; }
.kpi::after {
  content: ""; position: absolute; right: -40px; top: -40px; width: 120px; height: 120px; border-radius: 50%;
  background: radial-gradient(circle, color-mix(in srgb, var(--c) 22%, transparent), transparent 70%);
}
.kpi:hover { transform: translateY(-2px); border-color: color-mix(in srgb, var(--c) 45%, transparent);
  box-shadow: 0 10px 30px -12px color-mix(in srgb, var(--c) 55%, transparent); }
.kpi-label { font-size: 11px; font-weight: 600; letter-spacing: 0.14em; text-transform: uppercase; color: var(--muted); }
.kpi-value { font-family: var(--mono); font-variant-numeric: tabular-nums; font-size: 1.95rem; font-weight: 700;
  color: var(--text); margin: 7px 0 3px; letter-spacing: -0.02em; line-height: 1.1; }
.kpi-value.num { white-space: nowrap; font-size: clamp(1.25rem, 2.1vw, 1.95rem); }
.kpi-value.txt { font-family: 'Inter', sans-serif; font-size: clamp(1.05rem, 1.6vw, 1.5rem); letter-spacing: -0.01em;
  word-break: normal; overflow-wrap: normal; hyphens: none; }
.kpi-value small { font-size: 0.95rem; color: var(--soft); font-weight: 500; margin-left: 3px; }
.kpi-sub { font-size: 12.5px; color: var(--soft); }

/* ── Section headings ────────────────────────────────── */
.sec { margin: 26px 0 8px; }
.sec-label { font-family: var(--mono); font-size: 11px; letter-spacing: 0.2em; color: var(--mint); text-transform: uppercase; }
.sec-title { font-size: 1.35rem; font-weight: 700; letter-spacing: -0.015em; color: var(--text); margin-top: 3px; }
.sec-sub { color: var(--muted); font-size: 0.9rem; margin-top: 2px; }

/* ── Progress bars ───────────────────────── */
.bar-card { --c: var(--cyan); padding: 14px 18px; border-radius: 16px; border: 1px solid var(--border);
  background: linear-gradient(180deg, rgba(255,255,255,0.045), rgba(255,255,255,0.015)); }
.bar-top { display: flex; justify-content: space-between; align-items: baseline; }
.bar-name { font-size: 11px; font-weight: 600; letter-spacing: 0.14em; text-transform: uppercase; color: var(--muted); }
.bar-val { font-family: var(--mono); font-weight: 700; font-size: 1.5rem; color: var(--text); }
.bar-track { height: 8px; border-radius: 99px; background: rgba(255,255,255,0.07); margin: 10px 0 7px; position: relative; }
.bar-fill { height: 100%; border-radius: 99px; background: linear-gradient(90deg, color-mix(in srgb, var(--c) 55%, transparent), var(--c));
  box-shadow: 0 0 14px color-mix(in srgb, var(--c) 55%, transparent); }
.bar-mark { position: absolute; top: -4px; width: 2px; height: 16px; background: #fff; opacity: 0.85; border-radius: 2px; }
.bar-note { font-size: 12px; color: var(--soft); }

/* ── Insight cards ───────────────────────────────────── */
.insight { --c: var(--mint); height: 100%; padding: 16px 18px; border-radius: 16px; border: 1px solid var(--border);
  background: linear-gradient(180deg, rgba(255,255,255,0.045), rgba(255,255,255,0.015)); }
.insight-tag { font-family: var(--mono); font-size: 10.5px; letter-spacing: 0.18em; color: var(--c); text-transform: uppercase; }
.insight-text { color: var(--text); font-size: 0.95rem; line-height: 1.55; margin-top: 6px; }
.insight-text b { color: #fff; }

/* ── Tabs (pill style) ───────────────────────────────── */
.stTabs [data-baseweb="tab-list"] { gap: 8px; background: transparent; border-bottom: none; padding-bottom: 6px; }
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display: none !important; }
.stTabs [data-baseweb="tab"] {
  height: 42px; padding: 0 18px; border-radius: 12px; color: var(--soft); font-weight: 600; font-size: 0.92rem;
  background: rgba(255,255,255,0.035); border: 1px solid var(--border);
}
.stTabs [data-baseweb="tab"]:hover { color: #fff; border-color: rgba(25,227,177,0.4); }
.stTabs [aria-selected="true"] {
  color: #04120e !important; background: linear-gradient(92deg, #19e3b1, #4cc9f0) !important;
  border-color: transparent !important; box-shadow: 0 6px 22px -8px rgba(25,227,177,0.7);
}

/* ── Bordered containers (chart cards) ───────────────── */
div[data-testid="stVerticalBlockBorderWrapper"] {
  background: linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.012));
  border: 1px solid var(--border) !important; border-radius: 18px;
}

/* ── Inputs ──────────────────────────────────────────── */
div[data-baseweb="select"] > div, div[data-baseweb="input"] > div, div[data-baseweb="base-input"] {
  background: var(--surface2) !important; border-color: var(--border) !important; border-radius: 10px !important;
}
label[data-testid="stWidgetLabel"] p { font-size: 12px; font-weight: 600; letter-spacing: 0.06em; color: var(--soft); text-transform: uppercase; }
span[data-baseweb="tag"] { background: rgba(25,227,177,0.14) !important; color: #b9fbe8 !important; border-radius: 8px !important; }
div[data-testid="stDataFrame"] { border-radius: 14px; overflow: hidden; border: 1px solid var(--border); }
div[data-testid="stRadio"] label p { text-transform: none; letter-spacing: 0; font-size: 14px; font-weight: 500; }
hr { border-color: var(--border); }

/* ── Sidebar brand & footer ──────────────────────────── */
.brand { display: flex; align-items: center; gap: 12px; margin-bottom: 18px; }
.brand-logo { width: 42px; height: 42px; border-radius: 12px; display: grid; place-items: center; font-size: 21px;
  background: linear-gradient(135deg, #19e3b1, #4cc9f0 60%, #8b7bff); box-shadow: 0 8px 24px -8px rgba(25,227,177,0.6); }
.brand-name { font-weight: 800; font-size: 1.05rem; letter-spacing: -0.01em; color: #fff; line-height: 1.1; }
.brand-sub { font-family: var(--mono); font-size: 10px; letter-spacing: 0.16em; color: var(--muted); text-transform: uppercase; }
.side-note { font-size: 12px; color: var(--muted); line-height: 1.5; }
.footer { margin-top: 36px; padding-top: 18px; border-top: 1px solid var(--border); color: var(--muted); font-size: 12.5px;
  display: flex; justify-content: space-between; flex-wrap: wrap; gap: 10px; }
.footer a { color: var(--mint); text-decoration: none; }
.footer a:hover { text-decoration: underline; }
"""


def inject() -> None:
    st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)


def _c(tone: str) -> str:
    return TONES.get(tone, tone)


def hero(eyebrow: str, title: str, subtitle: str, pills: list[tuple[str, str]]) -> None:
    badges = "".join(pill(t, tone) for t, tone in pills)
    st.markdown(
        f'<div class="hero"><div class="hero-eyebrow">{eyebrow}</div>'
        f'<div class="hero-title">{title}</div><p class="hero-sub">{subtitle}</p>'
        f'<div class="hero-badges">{badges}</div></div>', unsafe_allow_html=True)


def pill(text: str, tone: str = "mint", dot: bool = True) -> str:
    d = '<span class="dot"></span>' if dot else ""
    return f'<span class="pill" style="--c:{_c(tone)}">{d}{text}</span>'


def callout(text: str, tone: str = "cyan", icon: str = "💡") -> None:
    st.markdown(f'<div class="callout" style="--c:{_c(tone)}"><span class="ic">{icon}</span><div>{text}</div></div>',
                unsafe_allow_html=True)


def section(label: str, title: str, sub: str = "") -> None:
    sub_html = f'<div class="sec-sub">{sub}</div>' if sub else ""
    st.markdown(f'<div class="sec"><div class="sec-label">{label}</div><div class="sec-title">{title}</div>{sub_html}</div>',
                unsafe_allow_html=True)


def kpi(label: str, value: str, sub: str = "", tone: str = "mint", unit: str = "", text: bool = False) -> str:
    """KPI card. text=True for a word value (e.g. a policy name): sans font, wraps between words only."""
    u = f"<small>{unit}</small>" if unit else ""
    cls = "txt" if text else "num"
    return (f'<div class="kpi" style="--c:{_c(tone)}"><div class="kpi-label">{label}</div>'
            f'<div class="kpi-value {cls}">{value}{u}</div><div class="kpi-sub">{sub or "&nbsp;"}</div></div>')


def show(html: str) -> None:
    st.markdown(html, unsafe_allow_html=True)


def bar_card(name: str, value: float, tone: str, note: str, mark: float | None = None) -> str:
    pct = max(0.0, min(100.0, value * 100))
    m = f'<div class="bar-mark" style="left:{mark * 100:.1f}%"></div>' if mark else ""
    return (f'<div class="bar-card" style="--c:{_c(tone)}"><div class="bar-top"><span class="bar-name">{name}</span>'
            f'<span class="bar-val">{pct:.1f}%</span></div><div class="bar-track"><div class="bar-fill" style="width:{pct:.1f}%"></div>{m}</div>'
            f'<div class="bar-note">{note}</div></div>')


def insight(tag: str, text: str, tone: str = "mint") -> str:
    return f'<div class="insight" style="--c:{_c(tone)}"><div class="insight-tag">{tag}</div><div class="insight-text">{text}</div></div>'


def sidebar_brand() -> None:
    st.markdown('<div class="brand"><div class="brand-logo">🩺</div><div><div class="brand-name">Asset Health Twin</div>'
                '<div class="brand-sub">Maintenance policy lab</div></div></div>', unsafe_allow_html=True)


def footer() -> None:
    st.markdown(
        f'<div class="footer"><span>Built by <b style="color:#fff">Muatasem Hadi</b> · MEng Industrial Engineering, Telkom University · '
        f'simulated data · illustrative parameters</span><span><a href="{GITHUB}" target="_blank">Source code</a> · '
        f'<a href="{LINKEDIN}" target="_blank">LinkedIn</a></span></div>', unsafe_allow_html=True)
