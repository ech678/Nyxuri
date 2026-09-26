"""
Orbit Launcher Palette Engine
Loads the shared NyxNiri Material 3 palette or static defaults.
"""

import os


def hex_to_rgb(hex_str: str, default=(0.5, 0.5, 0.5)):
    """Convert hex color string (#RRGGBB) to normalized float RGB tuple (0.0 - 1.0)."""
    try:
        hex_str = hex_str.strip().lstrip("#")
        if len(hex_str) == 6:
            return tuple(int(hex_str[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    except Exception:
        pass
    return default


PALETTE_PATH = "~/.cache/nyxuri/palette.toml"
LEGACY_PALETTE_PATH = "~/.cache/nyxniri/palette.toml"
NYXURI_PALETTE_PATH = PALETTE_PATH
NYXNIRI_PALETTE_PATH = PALETTE_PATH


def _parse_toml_colors(path: str) -> dict:
    """Parse a simple key = "value" TOML file into a key -> normalized RGB dict."""
    colors = {}
    if not os.path.isfile(path):
        return colors
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith(("#", "[")):
                    k, v = [x.strip() for x in line.split("=", 1)]
                    rgb = hex_to_rgb(v.strip("\"'"))
                    if rgb:
                        colors[k] = rgb
    except Exception:
        pass
    return colors


def load_material_palette(path: str = None) -> dict:
    """Load dynamic palette prioritizing native M3 cache (~/.cache/nyxuri/palette.toml) with graceful fallback."""
    palette = {
        "primary": (0.42, 0.70, 1.00),
        "secondary": (0.38, 0.85, 0.65),
        "tertiary": (1.00, 0.75, 0.35),
        "surface": (0.12, 0.13, 0.18),
        "surface_dim": (0.05, 0.06, 0.09),
        "on_surface": (0.95, 0.96, 0.99),
        "on_surface_var": (0.68, 0.72, 0.78),
        "outline": (0.80, 0.84, 0.90),
        "is_dark": True,
    }

    # 1. Primary: Native Nyxuri M3 palette
    target_path = path or (
        NYXURI_PALETTE_PATH
        if NYXURI_PALETTE_PATH != PALETTE_PATH
        else (NYXNIRI_PALETTE_PATH if NYXNIRI_PALETTE_PATH != PALETTE_PATH else PALETTE_PATH)
    )
    expanded = os.path.expanduser(target_path)
    if not path and target_path == PALETTE_PATH and not os.path.isfile(expanded):
        legacy = os.path.expanduser(LEGACY_PALETTE_PATH)
        if os.path.isfile(legacy):
            expanded = legacy
    m3_colors = _parse_toml_colors(expanded)
    if m3_colors and "primary" in m3_colors and "surface" in m3_colors:
        for k in ("primary", "secondary", "tertiary", "surface", "surface_dim", "on_surface", "outline"):
            if k in m3_colors:
                palette[k] = m3_colors[k]
        if "on_surface_variant" in m3_colors:
            palette["on_surface_var"] = m3_colors["on_surface_variant"]
        elif "on_surface_var" in m3_colors:
            palette["on_surface_var"] = m3_colors["on_surface_var"]
        sr, sg, sb = palette["surface"]
        palette["is_dark"] = (0.299 * sr + 0.587 * sg + 0.114 * sb < 0.5)
        return palette

    sr, sg, sb = palette["surface"]
    palette["is_dark"] = (0.299 * sr + 0.587 * sg + 0.114 * sb < 0.5)
    return palette
