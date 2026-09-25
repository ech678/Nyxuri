"""
Orbit Launcher Palette Engine
Extracts dynamic colors from Noctalia Starship palette cache or defaults to Material You tokens.
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


NYXNIRI_PALETTE_PATH = "~/.cache/nyxniri/palette.toml"
STARSHIP_PALETTE_PATH = "~/.cache/noctalia/starship-palette.toml"


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
    """Load dynamic palette prioritizing native M3 cache (~/.cache/nyxniri/palette.toml) with graceful fallback."""
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

    # 1. Primary: Native NyxNiri M3 palette (clean semantic keys, zero reverse inference)
    nyx_path = os.path.expanduser(path or NYXNIRI_PALETTE_PATH)
    m3_colors = _parse_toml_colors(nyx_path)
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

    # 2. Fallback: Noctalia starship palette cache (legacy compatibility)
    starship_path = os.path.expanduser(STARSHIP_PALETTE_PATH)
    raw = _parse_toml_colors(starship_path)
    if raw:
        for k, rgb in raw.items():
            palette[k] = rgb
            if k in ("blue", "sapphire", "primary"):
                palette["primary"] = rgb
            elif k in ("teal", "green", "secondary"):
                palette["secondary"] = rgb
            elif k in ("peach", "pink", "mauve", "yellow", "tertiary"):
                palette["tertiary"] = rgb
            elif k in ("surface0", "surface1", "base"):
                palette["surface"] = rgb
            elif k in ("crust", "mantle"):
                palette["surface_dim"] = rgb
            elif k in ("text", "white"):
                palette["on_surface"] = rgb
            elif k in ("subtext0", "subtext1", "overlay2"):
                palette["on_surface_var"] = rgb
            elif k in ("overlay0", "overlay1"):
                palette["outline"] = rgb

    sr, sg, sb = palette["surface"]
    palette["is_dark"] = (0.299 * sr + 0.587 * sg + 0.114 * sb < 0.5)
    return palette
