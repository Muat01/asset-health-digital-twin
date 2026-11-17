"""Design tokens (colors and fonts) shared by the UI layer and the charts."""

# Surfaces
BG = "#070b14"
SURFACE = "#0d1424"
SURFACE_2 = "#121a2e"
BORDER = "rgba(255,255,255,0.08)"
GRID = "rgba(255,255,255,0.055)"

# Text
TEXT = "#e8edf7"
TEXT_SOFT = "#aab3c8"
MUTED = "#7b86a0"

# Accents
MINT = "#19e3b1"
CYAN = "#4cc9f0"
VIOLET = "#8b7bff"
AMBER = "#ffb020"
RED = "#ff5470"
GREEN = "#2ee59d"
SLATE = "#3b4a6b"

# Fonts (loaded from Google Fonts in ui.py)
FONT = "Inter, 'Segoe UI', system-ui, sans-serif"
MONO = "'JetBrains Mono', 'SF Mono', Consolas, monospace"

# validated for colour-vision deficiency on the dark surface (adjacent pairs dE >= 15)
POLICY_COLORS = {"RTF": RED, "TBM": AMBER, "CBM": VIOLET, "RBM": MINT}

TONES = {
    "mint": MINT, "cyan": CYAN, "violet": VIOLET, "amber": AMBER,
    "red": RED, "green": GREEN, "neutral": MUTED,
}
