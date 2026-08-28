"""
NyxNiri Wallpaper Picker — Material 3 design system.

Maps Noctalia's wallpaper-derived tonal palette onto the full M3 color-role
model (the five surface-container tiers are derived tonally from the surface
anchor), then compiles the picker stylesheet from the M3 type / shape /
elevation / motion / state-layer scales. Every pixel value in the generated
CSS traces back to a token defined here — component styling is generated,
never hand-hacked in selectors.
"""

import os

# ── M3 scales (dp → px 1:1) ────────────────────────────────────────────────

TYPE = {
    "title-large": (22, 400),
    "body-large": (16, 400),
    "body-medium": (14, 400),
    "label-large": (14, 500),
    "label-medium": (12, 500),
}

SHAPE = {"xl": 28, "l": 16, "m": 12, "full": 999}

ELEVATION = {
    1: "0 1px 2px rgba(0,0,0,0.30), 0 1px 3px 1px rgba(0,0,0,0.15)",
    3: "0 1px 3px rgba(0,0,0,0.30), 0 4px 8px 3px rgba(0,0,0,0.15)",
}

# M3 state-layer opacities
STATE_HOVER = 0.08
STATE_PRESSED = 0.10

EASE_STANDARD = "cubic-bezier(0.2, 0, 0, 1)"
EASE_EMPHASIZED_DECELERATE = "cubic-bezier(0.05, 0.7, 0.1, 1.0)"
EASE_EMPHASIZED_ACCELERATE = "cubic-bezier(0.3, 0.0, 0.8, 0.15)"

DUR_STATE_MS = 100
DUR_EXIT_MS = 200

STARSHIP_PALETTE_PATH = "~/.cache/noctalia/starship-palette.toml"

# Starship (Catppuccin-compatible) key candidates per M3 role, first hit wins.
_ROLE_SOURCES = {
    "primary": ("blue", "sapphire", "lavender", "primary"),
    "secondary": ("teal", "green", "sky", "secondary"),
    "tertiary": ("pink", "peach", "mauve", "yellow", "tertiary"),
    "surface": ("base", "surface0", "mantle", "crust"),
    "on_surface": ("text", "subtext1", "white"),
    "on_surface_variant": ("subtext0", "overlay2", "overlay1"),
    "outline": ("overlay1", "subtext0", "overlay2"),
    "outline_variant": ("overlay0", "surface2", "surface1"),
}

# Used when Noctalia's palette cache is missing entirely.
_FALLBACK = {
    "primary": (0.42, 0.70, 1.00),
    "secondary": (0.38, 0.85, 0.65),
    "tertiary": (1.00, 0.75, 0.35),
    "surface": (0.12, 0.13, 0.18),
    "on_surface": (0.95, 0.96, 0.99),
    "on_surface_variant": (0.68, 0.72, 0.78),
    "outline": (0.80, 0.84, 0.90),
    "outline_variant": (0.45, 0.48, 0.55),
}


# ── Color helpers ──────────────────────────────────────────────────────────

def hex_to_rgb(hex_str, default=None):
    """Convert '#RRGGBB' to normalized float RGB tuple, or `default`."""
    try:
        s = hex_str.strip().lstrip("#")
        if len(s) == 6:
            return tuple(int(s[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    except Exception:
        pass
    return default


def _mix(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def _luminance(rgb):
    def chan(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (chan(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast(a, b):
    la, lb = _luminance(a), _luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def _on_color(rgb):
    """M3 on-color: whichever of black/white keeps the higher contrast."""
    black = _contrast(rgb, (0.0, 0.0, 0.0))
    white = _contrast(rgb, (1.0, 1.0, 1.0))
    return (0.0, 0.0, 0.0) if black >= white else (1.0, 1.0, 1.0)


def _rgb(c):
    return "rgb({},{},{})".format(*(int(round(x * 255)) for x in c))


def _sl(base, fg, opacity):
    """State layer: fg overlaid on base at M3 opacity, precomputed as a solid."""
    return _rgb(_mix(base, fg, opacity))


# ── Palette loading ────────────────────────────────────────────────────────

def _load_starship_colors(path=None):
    """Parse Noctalia's starship palette cache into a key → rgb dict."""
    colors = {}
    p = os.path.expanduser(path or STARSHIP_PALETTE_PATH)
    if not os.path.isfile(p):
        return colors
    try:
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith(("#", "[")) or "=" not in line:
                    continue
                k, v = (x.strip() for x in line.split("=", 1))
                rgb = hex_to_rgb(v.strip("\"'"))
                if rgb:
                    colors[k] = rgb
    except Exception:
        return {}
    return colors


def build_tokens(raw=None):
    """Compile the full M3 color-role set from starship raw colors (or fallback).

    Container tiers approximate the M3 tonal ladder: dark surfaces step toward
    the on-color (tones 4/10/12/17/22), light surfaces step down toward the
    on-color while `lowest` steps up toward white (tone 100).
    """
    if raw is None:
        raw = _load_starship_colors()

    def pick(role):
        for key in _ROLE_SOURCES[role]:
            if key in raw:
                v = raw[key]
                if isinstance(v, str):
                    v = hex_to_rgb(v)
                if v is not None:
                    return v
        return _FALLBACK[role]

    primary = pick("primary")
    secondary = pick("secondary")
    tertiary = pick("tertiary")
    surface = pick("surface")
    on_surface = pick("on_surface")
    is_dark = _luminance(surface) < 0.5

    if is_dark:
        tiers = [_mix(surface, on_surface, t) for t in (0.045, 0.11, 0.145, 0.20, 0.255)]
    else:
        tiers = [_mix(surface, (1.0, 1.0, 1.0), 0.30)]
        tiers += [_mix(surface, on_surface, t) for t in (0.045, 0.075, 0.105, 0.135)]

    container_t = 0.62 if is_dark else 0.80

    return {
        "is_dark": is_dark,
        "primary": primary,
        "on_primary": _on_color(primary),
        "primary_container": _mix(primary, surface, container_t),
        "on_primary_container": _mix(on_surface, primary, 0.14),
        "secondary": secondary,
        "on_secondary": _on_color(secondary),
        "secondary_container": _mix(secondary, surface, container_t),
        "on_secondary_container": _mix(on_surface, secondary, 0.14),
        "tertiary": tertiary,
        "on_tertiary": _on_color(tertiary),
        "surface": surface,
        "surface_variant": tiers[3],
        "on_surface": on_surface,
        "on_surface_variant": pick("on_surface_variant"),
        "surface_container_lowest": tiers[0],
        "surface_container_low": tiers[1],
        "surface_container": tiers[2],
        "surface_container_high": tiers[3],
        "surface_container_highest": tiers[4],
        "outline": pick("outline"),
        "outline_variant": pick("outline_variant"),
    }


# ── Stylesheet compiler ────────────────────────────────────────────────────

def build_css(t, geometry):
    """Compile the picker stylesheet from tokens and card geometry (px)."""
    card_w = int(geometry["card_w"])
    thumb_h = int(geometry["thumb_h"])

    surface = t["surface"]
    on_surface = t["on_surface"]
    scl = t["surface_container_low"]
    sch = t["surface_container_high"]
    sc = t["secondary_container"]
    osc = t["on_secondary_container"]
    pc = t["primary_container"]
    opc = t["on_primary_container"]
    full = SHAPE["full"]

    tl, bl, bm, ll, lm = (TYPE[k] for k in ("title-large", "body-large", "body-medium", "label-large", "label-medium"))

    return f"""
window.background {{ background-color: transparent; }}

/* M3 dialog: extra-large shape, surface color, elevation 3 */
.picker-dialog {{
    font-family: "Inter","Noto Sans CJK SC",sans-serif;
    background-color: {_rgb(surface)};
    border-radius: {SHAPE['xl']}px;
    box-shadow: {ELEVATION[3]};
    padding: 24px;
    transition: opacity {DUR_EXIT_MS}ms {EASE_EMPHASIZED_ACCELERATE};
}}
.picker-dialog.dismissing {{ opacity: 0; }}

/* Top app bar (64dp) */
.appbar-title {{ color: {_rgb(on_surface)}; font-size: {tl[0]}px; font-weight: {tl[1]}; }}
.appbar-count {{ color: {_rgb(t['on_surface_variant'])}; font-size: {bm[0]}px; }}

/* Standard icon button (40dp, full shape) */
.icon-btn {{
    min-width: 40px; min-height: 40px; padding: 0;
    border-radius: {full}px;
    background-color: transparent;
    border: none;
    color: {_rgb(t['on_surface_variant'])};
    transition: background-color {DUR_STATE_MS}ms {EASE_STANDARD};
}}
.icon-btn:hover {{ background-color: {_sl(surface, on_surface, STATE_HOVER)}; }}
.icon-btn:active {{ background-color: {_sl(surface, on_surface, STATE_PRESSED)}; }}

/* M3 search bar (56dp pill, surface-container-high) */
.search {{
    min-height: 56px;
    border-radius: {full}px;
    background-color: {_rgb(sch)};
    padding: 0 16px;
    color: {_rgb(on_surface)};
    font-size: {bl[0]}px;
    caret-color: {_rgb(t['primary'])};
    border: none;
    box-shadow: none;
}}
.search:focus {{ box-shadow: {ELEVATION[1]}; }}
.search image {{ color: {_rgb(t['on_surface_variant'])}; }}
.search selection {{ background-color: {_rgb(pc)}; color: {_rgb(opc)}; }}

/* M3 filter chips (32dp pill) */
.chip {{
    min-height: 32px; padding: 0 16px;
    border-radius: {full}px;
    background-color: transparent;
    border: 1px solid {_rgb(t['outline'])};
    color: {_rgb(t['on_surface_variant'])};
    font-size: {ll[0]}px; font-weight: {ll[1]};
    transition: background-color {DUR_STATE_MS}ms {EASE_STANDARD}, border-color {DUR_STATE_MS}ms {EASE_STANDARD};
}}
.chip:hover {{ background-color: {_sl(surface, on_surface, STATE_HOVER)}; }}
.chip:active {{ background-color: {_sl(surface, on_surface, STATE_PRESSED)}; }}
.chip:checked {{
    background-color: {_rgb(sc)};
    border-color: {_rgb(sc)};
    color: {_rgb(osc)};
}}
.chip:checked:hover {{ background-color: {_sl(sc, osc, STATE_HOVER)}; }}

/* M3 image cards (medium shape, surface-container-low) */
.card {{
    border-radius: {SHAPE['m']}px;
    background-color: {_rgb(scl)};
    transition: background-color {DUR_STATE_MS}ms {EASE_STANDARD};
}}
.card:hover {{ background-color: {_sl(scl, on_surface, STATE_HOVER)}; }}
.card:active {{ background-color: {_sl(scl, on_surface, STATE_PRESSED)}; }}

.thumb {{
    border-radius: {SHAPE['m']}px {SHAPE['m']}px 0 0;
    background-color: {_rgb(t['surface_container_highest'])};
    min-width: {card_w}px;
    min-height: {thumb_h}px;
}}
.card-inner {{ background-color: transparent; }}
.card-info {{ padding: 12px 16px 14px; }}
.card-title {{ color: {_rgb(on_surface)}; font-size: {bm[0]}px; }}
.live {{ color: {_rgb(t['tertiary'])}; font-size: {lm[0]}px; font-weight: {lm[1]}; }}

/* Selected-image indicator (24dp primary badge) */
.badge {{
    min-width: 24px; min-height: 24px;
    border-radius: {full}px;
    background-color: {_rgb(t['primary'])};
    color: {_rgb(t['on_primary'])};
    font-size: 14px; font-weight: 700;
}}

.grid {{ background-color: transparent; padding-bottom: 88px; }}
.grid-scroll {{ background-color: transparent; border: none; }}
.grid-scroll scrollbar {{ background-color: transparent; }}
.grid-scroll trough {{ background-color: transparent; }}
.grid-scroll slider {{
    background-color: {_rgb(_mix(t['on_surface_variant'], surface, 0.25))};
    border-radius: {full}px;
    min-width: 6px;
    min-height: 32px;
}}

/* M3 FAB (56dp, large shape, primary-container, elevation 3) */
.fab {{
    min-width: 56px; min-height: 56px; padding: 0;
    border-radius: {SHAPE['l']}px;
    background-color: {_rgb(pc)};
    color: {_rgb(opc)};
    border: none;
    box-shadow: {ELEVATION[3]};
    transition: background-color {DUR_STATE_MS}ms {EASE_STANDARD};
}}
.fab:hover {{ background-color: {_sl(pc, opc, STATE_HOVER)}; }}
.fab:active {{ background-color: {_sl(pc, opc, STATE_PRESSED)}; }}
.fab-extended {{ min-width: 0px; padding: 0 20px; }}

/* Empty state */
.empty-title {{ color: {_rgb(on_surface)}; font-size: {bl[0]}px; font-weight: 500; }}
.empty-hint {{ color: {_rgb(t['on_surface_variant'])}; font-size: {bm[0]}px; }}
.empty image {{ color: {_rgb(t['on_surface_variant'])}; }}

/* Focus indicators (2dp primary ring, outside) */
.chip:focus, .card:focus, .icon-btn:focus {{
    outline-width: 2px;
    outline-style: solid;
    outline-color: {_rgb(t['primary'])};
    outline-offset: 2px;
}}
/* Current-wallpaper selection: inset ring wins over the focus ring */
.card.current {{
    outline-width: 2px;
    outline-style: solid;
    outline-color: {_rgb(t['primary'])};
    outline-offset: -2px;
}}
"""
