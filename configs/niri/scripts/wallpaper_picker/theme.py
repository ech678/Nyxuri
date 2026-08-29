"""
NyxNiri Wallpaper Picker — Material 3 Expressive (M3E) Design System.

From M3 (published values, transcribed verbatim): the 10-step shape scale,
30-style type scale, 6 elevation levels, state-layer opacities, and the
spring→bezier conversion curves.

Design decisions (not in M3, or adapted for GTK3):
- Color roles are RGB-mix approximations of the Noctalia starship palette;
  HCT tone ladders become linear blends toward the on-color. The pairing
  contract (4.5:1 on-colors, 3:1 containers) is enforced by tests instead
  of the tone ladder.
- The dialog exceeds M3's 560dp max (1080px nominal, runtime-clamped to the
  screen minus a 56dp placement margin) — a wallpaper grid needs the
  breadth (cf. docked search view, 720dp+).
- The search bar sits on a surface-container-high dialog, so it drops to
  surface-container-low: M3 publishes no search-inside-dialog combination,
  and the anti-blending rule demands roles more than one step apart. The
  bar also spans the full content width (exceeds the 720dp search max).
- Chip unselected corners are 8dp per the chips guidelines text and the
  v7_0_1 chip tokens; the newer Compose Chips set (v37.2.1) publishes 12dp
  — the reference layers conflict, 8dp is kept. Pressing morphs to the
  published CornerSmall pressed shape; selection morphs to full.
- Chip label weight snaps on selection (GTK3 cannot animate font-weight);
  the checkmark slide-reveal and corner morph carry the expressive motion.
- 48dp hit targets wrap 32/40dp visuals in a transparent button (GTK3 hit
  area = widget allocation; M3 lets the target exceed the visual).
- The result count is neutral text: M3 reserves error for alerts and the
  badge component for notifications.
- Scrim opacity 0.32 follows the Compose dialog scrim constant.
- Enabled/selected tiles recolor a resident 3px primary border (M3 photo
  picker's 3dp outline, shared by .card.current and .card:selected); the
  footprint is always reserved, so selection never shifts content. Focus
  takes the M3 state layer, not a second ring — M3 publishes no
  tile-selection treatment.
- Thumbnails fade in via widget opacity (GTK3 cannot transition
  background-image); M3's new-content fade-through at the 150ms effects pace.
- Focus ring is a 2px primary outline — no focus-indicator thickness is
  published in the references consulted.
- GtkRevealer animates on its built-in ease (GTK3 cannot take the token
  bezier); durations still come from the motion tokens.
- Overscroll: M3 publishes no over/underscroll treatment, so the toolkit's
  Adwaita edge glow is suppressed — scrolling stops at content bounds.
- Scroll glide (window.py) rides a critically-damped exponential approach
  (no overshoot, effects-spring semantics); scroll motion has no published
  M3 tokens, so the time constant is a design decision.
"""

import os

# ── M3 Shape Scale (10 steps: dp → px 1:1) ───────────────────────────────────
SHAPE = {
    "none": 0,
    "xs": 4,
    "s": 8,
    "m": 12,
    "l": 16,
    "l_inc": 20,
    "xl": 28,
    "xl_inc": 32,
    "xxl": 48,
    "full": 9999,
}


# ── M3 Type Scale (30 styles: 15 baseline + 15 emphasized) ───────────────────
TYPE = {
    # Baseline
    "display-large": (57, 400),
    "display-medium": (45, 400),
    "display-small": (36, 400),
    "headline-large": (32, 400),
    "headline-medium": (28, 400),
    "headline-small": (24, 400),
    "title-large": (22, 400),
    "title-medium": (16, 500),
    "title-small": (14, 500),
    "body-large": (16, 400),
    "body-medium": (14, 400),
    "body-small": (12, 400),
    "label-large": (14, 500),
    "label-medium": (12, 500),
    "label-small": (11, 500),
    # Emphasized (M3 Expressive)
    "display-large-emph": (57, 500),
    "display-medium-emph": (45, 500),
    "display-small-emph": (36, 500),
    "headline-large-emph": (32, 500),
    "headline-medium-emph": (28, 500),
    "headline-small-emph": (24, 500),
    "title-large-emph": (22, 500),
    "title-medium-emph": (16, 700),
    "title-small-emph": (14, 700),
    "body-large-emph": (16, 500),
    "body-medium-emph": (14, 500),
    "body-small-emph": (12, 500),
    "label-large-emph": (14, 700),
    "label-medium-emph": (12, 700),
    "label-small-emph": (11, 700),
}

# ── M3 Elevation Levels (0 to 5) ──────────────────────────────────────────────
ELEVATION = {
    0: "none",
    1: "0 1px 2px rgba(0,0,0,0.30), 0 1px 3px 1px rgba(0,0,0,0.15)",
    2: "0 1px 2px rgba(0,0,0,0.30), 0 2px 6px 2px rgba(0,0,0,0.15)",
    3: "0 1px 3px rgba(0,0,0,0.30), 0 4px 8px 3px rgba(0,0,0,0.15)",
    4: "0 2px 3px rgba(0,0,0,0.30), 0 6px 10px 4px rgba(0,0,0,0.15)",
    5: "0 4px 4px rgba(0,0,0,0.30), 0 8px 12px 6px rgba(0,0,0,0.15)",
}

# ── M3 State Layer Opacities ──────────────────────────────────────────────────
STATE_HOVER = 0.08
STATE_PRESSED = 0.10
STATE_FOCUSED = 0.10

# ── M3 Expressive Motion Physics System ───────────────────────────────────────
# Spatial springs (overshoot / bounce for geometry, position, size, shape morph)
EASE_EXPRESSIVE_FAST_SPATIAL = "cubic-bezier(0.42, 1.67, 0.21, 0.90)"
EASE_EXPRESSIVE_DEFAULT_SPATIAL = "cubic-bezier(0.38, 1.21, 0.22, 1.00)"
EASE_EXPRESSIVE_SLOW_SPATIAL = "cubic-bezier(0.39, 1.29, 0.35, 0.98)"

# Effects springs (damping 1.0, strictly NO overshoot for color and opacity)
EASE_EXPRESSIVE_FAST_EFFECTS = "cubic-bezier(0.31, 0.94, 0.34, 1.00)"
EASE_EXPRESSIVE_DEFAULT_EFFECTS = "cubic-bezier(0.34, 0.80, 0.34, 1.00)"
EASE_EXPRESSIVE_SLOW_EFFECTS = "cubic-bezier(0.34, 0.88, 0.34, 1.00)"

# Sanctioned spring durations (web conversion table in tokens.md)
DUR_FAST_MS = 150
DUR_DEFAULT_MS = 200
DUR_STATE_MS = 150
DUR_FAST_SPATIAL_MS = 350
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
    "error": ("red", "maroon", "error"),
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
    "error": (0.85, 0.31, 0.32),
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
    error = pick("error")
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
        "tertiary_container": _mix(tertiary, surface, container_t),
        "on_tertiary_container": _mix(on_surface, tertiary, 0.14),
        "surface": surface,
        "on_surface": on_surface,
        "on_surface_variant": pick("on_surface_variant"),
        "surface_container_lowest": tiers[0],
        "surface_container_low": tiers[1],
        "surface_container": tiers[2],
        "surface_container_high": tiers[3],
        "surface_container_highest": tiers[4],
        "outline": pick("outline"),
        "outline_variant": pick("outline_variant"),
        "error": error,
        "on_error": _on_color(error),
    }


# ── Stylesheet compiler ────────────────────────────────────────────────────

def build_css(t, geometry):
    """Compile the M3 Expressive picker stylesheet from tokens and geometry (px)."""
    card_w = int(geometry.get("card_w", 334))
    thumb_w = int(geometry.get("thumb_w", card_w - 6))
    thumb_h = int(geometry.get("thumb_h", thumb_w * 9 // 16))
    search_h = int(geometry["search_h"])
    chip_h = int(geometry["chip_h"])

    surface = t["surface"]
    on_surface = t["on_surface"]
    scl = t["surface_container_low"]
    sch = t["surface_container_high"]
    sc = t["secondary_container"]
    osc = t["on_secondary_container"]
    pc = t["primary_container"]
    opc = t["on_primary_container"]
    tc = t.get("tertiary_container", _mix(t["tertiary"], surface, 0.62 if t["is_dark"] else 0.80))
    otc = t.get("on_tertiary_container", _mix(on_surface, t["tertiary"], 0.14))

    full = SHAPE["full"]
    xl = SHAPE["xl"]
    m = SHAPE["m"]
    s = SHAPE["s"]

    tl_e = TYPE["title-large-emph"]
    bm = TYPE["body-medium"]
    bl = TYPE["body-large"]
    ll = TYPE["label-large"]
    ll_e = TYPE["label-large-emph"]
    lm = TYPE["label-medium"]

    return f"""
window.background {{ background-color: transparent; }}

/* M3E basic dialog: ExtraLarge shape (28dp), surface-container-high, Level 3 */
.picker-dialog {{
    font-family: "Inter", "Noto Sans CJK SC", sans-serif;
    background-color: {_rgb(sch)};
    border-radius: {xl}px;
    box-shadow: {ELEVATION[3]};
    padding: 24px;
    opacity: 0;
    transition: opacity {DUR_DEFAULT_MS}ms {EASE_EXPRESSIVE_DEFAULT_EFFECTS};
}}
.picker-dialog.revealed {{ opacity: 1; }}

/* Scrim: modal dim layer behind the dialog; click bubbles to the window */
.scrim {{
    background-color: rgba(0,0,0,0.32);
    opacity: 0;
    transition: opacity {DUR_DEFAULT_MS}ms {EASE_EXPRESSIVE_DEFAULT_EFFECTS};
}}
.scrim.revealed {{ opacity: 1; }}

/* Top app bar (64dp, title-large emphasized typography) */
.appbar-title {{
    color: {_rgb(on_surface)};
    font-size: {tl_e[0]}px;
    font-weight: {tl_e[1]};
}}

/* Result count: neutral text. Error stays reserved for alerts; M3 badges
   carry notifications, not information counts. */
.count-label {{
    color: {_rgb(t['on_surface_variant'])};
    font-size: {lm[0]}px;
    font-weight: {lm[1]};
    margin-left: 8px;
}}

/* Standard icon button: 40dp visual face inside a 48dp hit target, full shape */
.icon-btn {{
    min-width: 48px; min-height: 48px; padding: 0;
    background-color: transparent;
    border: none;
}}
.icon-btn > .icon-btn-face {{
    min-width: 40px; min-height: 40px;
    border-radius: {full}px;
    background-color: transparent;
    color: {_rgb(t['on_surface_variant'])};
    transition: background-color {DUR_STATE_MS}ms {EASE_EXPRESSIVE_FAST_EFFECTS};
}}
.icon-btn:hover > .icon-btn-face {{ background-color: {_sl(sch, on_surface, STATE_HOVER)}; }}
.icon-btn:active > .icon-btn-face {{ background-color: {_sl(sch, on_surface, STATE_PRESSED)}; }}

/* M3 contained search bar (56dp, full pill, resting Level 3). Sits on a
   surface-container-high dialog, so it drops to container-low to keep the
   >1 step separation the anti-blending rule demands. */
.search {{
    min-height: {search_h}px;
    border-radius: {full}px;
    background-color: {_rgb(scl)};
    padding: 0 24px;
    color: {_rgb(on_surface)};
    font-size: {bl[0]}px;
    caret-color: {_rgb(t['primary'])};
    border: none;
    box-shadow: {ELEVATION[3]};
    transition: background-color {DUR_STATE_MS}ms {EASE_EXPRESSIVE_FAST_EFFECTS};
}}
.search:hover {{ background-color: {_sl(scl, on_surface, STATE_HOVER)}; }}
.search image {{ color: {_rgb(t['on_surface_variant'])}; }}
.search selection {{ background-color: {_rgb(pc)}; color: {_rgb(opc)}; }}

/* M3 Expressive filter chips: 32dp visual face inside a 48dp hit target.
   8dp corner unselected, morphing to full when selected — spatial spring,
   the signature move. Pressing morphs to the published CornerSmall shape. */
.chip {{
    min-height: {chip_h}px; padding: 0 8px;
    background-color: transparent;
    border: none;
}}
.chip > .chip-face {{
    min-height: 32px; padding: 0 16px;
    border-radius: {s}px;
    background-color: transparent;
    border: 1px solid {_rgb(t['outline_variant'])};
    color: {_rgb(t['on_surface_variant'])};
    font-size: {ll[0]}px; font-weight: {ll[1]};
    transition: border-radius {DUR_FAST_SPATIAL_MS}ms {EASE_EXPRESSIVE_FAST_SPATIAL},
                background-color {DUR_STATE_MS}ms {EASE_EXPRESSIVE_FAST_EFFECTS},
                border-color {DUR_STATE_MS}ms {EASE_EXPRESSIVE_FAST_EFFECTS},
                color {DUR_STATE_MS}ms {EASE_EXPRESSIVE_FAST_EFFECTS};
}}
.chip:hover > .chip-face {{ background-color: {_sl(sch, on_surface, STATE_HOVER)}; }}
.chip:active > .chip-face {{
    border-radius: {s}px;
    background-color: {_sl(sch, on_surface, STATE_PRESSED)};
}}
.chip:checked > .chip-face {{
    border-radius: {full}px;
    background-color: {_rgb(sc)};
    border-color: {_rgb(sc)};
    color: {_rgb(osc)};
    font-weight: {ll_e[1]};
}}
.chip:checked:hover > .chip-face {{ background-color: {_sl(sc, osc, STATE_HOVER)}; }}
.chip > .chip-face image {{ color: {_rgb(t['on_surface_variant'])}; }}
.chip:checked > .chip-face image {{ color: {_rgb(osc)}; }}

/* GtkFlowBoxChild reset: eliminate Adwaita default padding and focus outline */
flowboxchild {{
    padding: 0;
    margin: 0;
    outline: none;
}}

/* M3 elevated image cards (CornerMedium 12dp, surface-container-low, Elevation 1).
   A 3px transparent border is resident on every card — it is the selection
   indicator's footprint (M3 photo picker's 3dp outline), so toggling
   selection only recolors it: content never shifts, and nothing extends
   past the card edge to get clipped. */
.card {{
    border-radius: {m}px;
    background-color: {_rgb(scl)};
    border: 3px solid transparent;
    padding: 0;
    margin: 0;
    outline: none;
    box-shadow: {ELEVATION[1]};
    transition: background-color {DUR_STATE_MS}ms {EASE_EXPRESSIVE_FAST_EFFECTS},
                border-color {DUR_STATE_MS}ms {EASE_EXPRESSIVE_FAST_EFFECTS},
                box-shadow {DUR_FAST_MS}ms {EASE_EXPRESSIVE_FAST_EFFECTS};
}}
.card:hover {{
    background-color: {_sl(scl, on_surface, STATE_HOVER)};
    box-shadow: {ELEVATION[2]};
}}
.card:active {{ background-color: {_sl(scl, on_surface, STATE_PRESSED)}; }}

/* Enabled (current), keyboard-selected and focused cards recolor the resident
   border. Design decision — M3 photo picker's 3dp primary outline. */
.card.current, .card:selected, .card:focus {{
    border-color: {_rgb(t['primary'])};
}}

/* M3 nested radii rule: inner = outer - padding/border (12 - 3 = 9dp) */
.thumb {{
    border-radius: {m - 3}px {m - 3}px 0 0;
    background-color: {_rgb(t['surface_container_highest'])};
    min-width: {thumb_w}px;
    min-height: {thumb_h}px;
}}
.card-inner {{ background-color: transparent; }}
.card-info {{ padding: 10px 16px; }}
.card-title {{
    color: {_rgb(on_surface)};
    font-size: {bm[0]}px;
    font-weight: {bm[1]};
}}

/* Live tag (16dp, full pill), tertiary container */
.live {{
    background-color: {_rgb(tc)};
    color: {_rgb(otc)};
    font-size: {lm[0]}px;
    font-weight: {lm[1]};
    border-radius: {full}px;
    min-height: 16px;
    padding: 0 4px;
}}

.grid {{ background-color: transparent; }}
.grid-scroll {{ background-color: transparent; border: none; }}
/* Overscroll: M3 has no over/underscroll treatment — the toolkit's edge
   glow is foreign chrome here; scrolling stops hard at content bounds. */
.grid-scroll undershoot, .grid-scroll overshoot {{ background: none; }}
.grid-scroll scrollbar {{ background-color: transparent; }}
.grid-scroll trough {{ background-color: transparent; }}
.grid-scroll slider {{
    background-color: {_rgb(_mix(t['on_surface_variant'], surface, 0.25))};
    border-radius: {full}px;
    min-width: 6px;
    min-height: 32px;
}}

/* Empty state */
.empty-title {{
    color: {_rgb(on_surface)};
    font-size: {bl[0]}px;
    font-weight: 400;
}}
.empty-hint {{
    color: {_rgb(t['on_surface_variant'])};
    font-size: {bm[0]}px;
}}
.empty image {{ color: {_rgb(t['on_surface_variant'])}; }}

/* Focus indicators (2px primary ring, outside — thickness is a design
   decision, M3 publishes no focus-indicator width). Cards take the M3
   focus state layer instead of a ring: keyboard navigation rides the
   selection border, and a second outline would only fight it. */
.chip:focus, .icon-btn:focus, .search:focus {{
    outline-width: 2px;
    outline-style: solid;
    outline-color: {_rgb(t['primary'])};
    outline-offset: 2px;
}}
.card:focus {{ background-color: {_sl(scl, on_surface, STATE_FOCUSED)}; }}
"""
