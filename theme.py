"""Design tokens (colors and fonts) shared by the UI layer and the charts."""

# Surfaces
BG = "#0E1311"
SURFACE = "#171E1B"
SURFACE_2 = "#1F2824"
BORDER = "#2A3530"
GRID = "#232D29"

# Text
TEXT = "#EEF2EF"
TEXT_SOFT = "#B7C2BC"
MUTED = "#7E8C85"

# Accents
MINT = "#22C98A"
CYAN = "#6FA8FF"
VIOLET = "#9479E6"
AMBER = "#E6B94A"
RED = "#F0616D"
GREEN = "#16A673"
SLATE = "#2F3C36"

# Fonts (loaded from Google Fonts in ui.py)
FONT = "Inter, 'Segoe UI', system-ui, sans-serif"
MONO = "'JetBrains Mono', 'SF Mono', Consolas, monospace"

# validated for colour-vision deficiency on the dark surface (adjacent pairs dE >= 15)
POLICY_COLORS = {"RTF": RED, "TBM": AMBER, "CBM": VIOLET, "RBM": MINT}

TONES = {
    "mint": MINT, "cyan": CYAN, "violet": VIOLET, "amber": AMBER,
    "red": RED, "green": GREEN, "neutral": MUTED,
}
