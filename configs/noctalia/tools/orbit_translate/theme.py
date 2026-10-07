"""Orbit-compatible palette loading and GTK CSS generation."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import tomllib


@dataclass(frozen=True)
class Palette:
    primary: str = "#6fa4ff"
    surface: str = "#1f2430"
    surface_dim: str = "#11151e"
    on_surface: str = "#f1f4fb"
    muted: str = "#b0b8c8"
    outline: str = "#53617a"
    # Material 3 tonal roles; older palettes derive them from the six above.
    secondary: str = "#9fc2e8"
    tertiary: str = "#d6b8f0"
    on_primary: str = "#0b1d3d"
    primary_container: str = "#2c4a7c"
    on_primary_container: str = "#d8e2ff"
    secondary_container: str = "#3a4459"
    on_secondary_container: str = "#d9e2f9"
    surface_container: str = "#1f2430"
    surface_container_high: str = "#2a303c"
    surface_container_highest: str = "#353b48"
    outline_variant: str = "#3d4658"
    error: str = "#ffb4ab"


def load_palette(path: str | Path | None = None) -> Palette:
    candidates = (Path(path),) if path is not None else _default_palette_paths()
    for palette_path in candidates:
        values: dict[str, str] = {}
        try:
            with palette_path.open("rb") as handle:
                _collect_strings(tomllib.load(handle), values)
        except (OSError, tomllib.TOMLDecodeError):
            continue

        primary = _pick(values, "primary", "blue", fallback=Palette.primary)
        surface = _pick(values, "surface", "surface0", "base", fallback=Palette.surface)
        surface_dim = _pick(values, "surface_dim", "crust", "mantle", fallback=Palette.surface_dim)
        on_surface = _pick(values, "on_surface", "text", "white", fallback=Palette.on_surface)
        outline = _pick(values, "outline", "overlay0", "overlay1", fallback=Palette.outline)
        container = _pick(values, "surface_container", "base", fallback=surface)
        container_high = _pick(
            values, "surface_container_high", "surface0", fallback=mix(container, on_surface, 0.06)
        )
        return Palette(
            primary=primary,
            surface=surface,
            surface_dim=surface_dim,
            on_surface=on_surface,
            muted=_pick(values, "on_surface_variant", "on_surface_var", "subtext0", "subtext1", "overlay2", fallback=Palette.muted),
            outline=outline,
            secondary=_pick(values, "secondary", "teal", "green", fallback=mix(primary, on_surface, 0.35)),
            tertiary=_pick(values, "tertiary", "mauve", "peach", fallback=Palette.tertiary),
            on_primary=_pick(values, "on_primary", "crust", fallback=surface_dim),
            primary_container=_pick(values, "primary_container", fallback=mix(surface, primary, 0.34)),
            on_primary_container=_pick(values, "on_primary_container", fallback=mix(primary, on_surface, 0.55)),
            secondary_container=_pick(values, "secondary_container", fallback=mix(container_high, primary, 0.16)),
            on_secondary_container=_pick(values, "on_secondary_container", fallback=on_surface),
            surface_container=container,
            surface_container_high=container_high,
            surface_container_highest=_pick(
                values, "surface_container_highest", "surface1", fallback=mix(container, on_surface, 0.11)
            ),
            outline_variant=_pick(values, "outline_variant", "surface2", fallback=mix(surface, outline, 0.45)),
            error=_pick(values, "error", "red", fallback=Palette.error),
        )
    return Palette()


# Warm amber-gold accent for the title sparkle; fixed so it stays warm on any
# dynamic Material You palette.
TITLE_ICON_COLOR = "#ffb74d"


def gtk_css(palette: Palette) -> str:
    p = palette
    # Material 3 dark, tonal elevation: the panel is a surface-container sheet,
    # sections step up one container tone, accents use primary/secondary
    # containers. State layers are translucent tints of the content color.
    return f"""
    .translate-overlay {{ background-color: {rgba(p.surface_dim, 0.12)}; }}
    .translate-panel {{
        background-color: {rgba(p.surface_container, 0.97)};
        border: 1px solid {rgba(p.outline_variant, 0.70)};
        border-radius: 24px;
        padding: 6px 8px 8px;
        box-shadow: 0 12px 32px rgba(0, 0, 0, 0.36), 0 2px 6px rgba(0, 0, 0, 0.22);
    }}
    .translate-topbar {{ padding: 0 0 0 10px; min-height: 32px; }}
    .translate-title {{
        color: {p.muted};
        font-size: 12px;
        font-weight: 600;
        letter-spacing: 0.4px;
    }}
    .translate-title-icon {{
        color: {TITLE_ICON_COLOR};
        font-family: "Symbols Nerd Font", "JetBrainsMono Nerd Font Propo", "JetBrainsMono Nerd Font";
        font-size: 15px;
        text-shadow: 0 0 6px {rgba(TITLE_ICON_COLOR, 0.45)};
    }}
    .translate-section-label {{
        color: {p.muted};
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 0.5px;
    }}
    .translate-source-surface {{
        background-color: {p.surface_container_high};
        border-radius: 16px;
        padding: 4px 4px 10px 12px;
    }}
    .translate-source {{ color: {p.on_surface}; font-size: 14px; padding-right: 8px; }}
    .translate-source-scroll, .translate-results-scroll {{
        background-color: transparent;
        border: none;
    }}
    .translate-language-bar {{ padding: 0; }}
    .translate-language-chip {{
        color: {p.on_surface};
        font-size: 13px;
        font-weight: 500;
        background-image: none;
        background-color: transparent;
        border: 1px solid {p.outline_variant};
        border-radius: 999px;
        box-shadow: none;
        min-height: 30px;
        padding: 0 8px 0 14px;
    }}
    .translate-language-chip image {{ color: {p.muted}; }}
    .translate-language-chip:hover {{ background-color: {rgba(p.on_surface, 0.08)}; }}
    .translate-language-chip:active {{ background-color: {rgba(p.on_surface, 0.12)}; }}
    .translate-language-chip.translate-language-chip-open {{
        color: {p.on_secondary_container};
        background-color: {p.secondary_container};
        border-color: transparent;
    }}
    .translate-language-chip.translate-language-chip-open image {{ color: {p.on_secondary_container}; }}
    .translate-language-swap {{
        color: {p.on_secondary_container};
        background-image: none;
        background-color: {p.secondary_container};
        border: none;
        box-shadow: none;
        border-radius: 999px;
        font-size: 15px;
        font-weight: 700;
        min-width: 32px;
        min-height: 32px;
        padding: 0;
    }}
    .translate-language-swap:hover {{
        background-image: linear-gradient({rgba(p.on_secondary_container, 0.08)}, {rgba(p.on_secondary_container, 0.08)});
    }}
    .translate-language-swap:active {{
        background-image: linear-gradient({rgba(p.on_secondary_container, 0.16)}, {rgba(p.on_secondary_container, 0.16)});
    }}
    .translate-language-menu {{
        background-color: {p.surface_container_high};
        border: 1px solid {rgba(p.outline_variant, 0.60)};
        border-radius: 12px;
        margin: 8px;
        padding: 6px 0;
        box-shadow: 0 6px 16px rgba(0, 0, 0, 0.34), 0 1px 3px rgba(0, 0, 0, 0.24);
    }}
    .translate-language-menu list {{ background-color: transparent; }}
    .translate-language-option {{
        color: {p.on_surface};
        font-size: 13px;
        min-height: 32px;
        padding: 0 14px 0 10px;
        outline: none;
    }}
    .translate-language-option image {{ color: {p.on_secondary_container}; }}
    .translate-language-option:hover {{ background-color: {rgba(p.on_surface, 0.08)}; }}
    .translate-language-option:focus {{ background-color: {rgba(p.on_surface, 0.12)}; }}
    .translate-language-option.translate-language-option-active {{
        color: {p.on_secondary_container};
        background-color: {p.secondary_container};
        font-weight: 600;
    }}
    .translate-card {{
        background-color: {p.surface_container_high};
        border-radius: 16px;
    }}
    .translate-card-header {{
        padding: 6px 4px 4px 10px;
        min-height: 28px;
    }}
    .translate-provider-badge {{
        background-color: {p.primary_container};
        color: {p.on_primary_container};
        border-radius: 7px;
        min-width: 23px;
        min-height: 23px;
        padding: 0 2px;
        font-size: 12px;
        font-weight: 700;
    }}
    .translate-provider {{ color: {p.on_surface}; font-size: 13px; font-weight: 600; }}
    .translate-status {{
        color: {p.muted};
        font-size: 10px;
        font-weight: 600;
        border-radius: 999px;
        padding: 1px 8px;
    }}
    .translate-status-success {{
        color: {p.on_primary_container};
        background-color: {rgba(p.primary_container, 0.85)};
    }}
    .translate-status-error {{ color: {p.error}; }}
    .translate-card-body {{
        background-color: transparent;
        padding: 0 12px 10px 12px;
    }}
    .translate-result {{ color: {p.on_surface}; font-size: 15px; }}
    .translate-error {{ color: {p.error}; }}
    .translate-message {{ color: {p.muted}; font-size: 12px; padding: 6px 12px; }}
    .translate-copy-feedback {{
        color: {p.on_primary_container};
        background-color: {p.primary_container};
        border-radius: 999px;
        font-size: 11px;
        font-weight: 600;
        padding: 2px 10px;
    }}
    .translate-copied {{ color: {p.primary}; }}
    .translate-action, .translate-close, .translate-expand {{
        color: {p.muted};
        background-image: none;
        background-color: transparent;
        border: none;
        box-shadow: none;
        border-radius: 999px;
        padding: 0;
        min-width: 28px;
        min-height: 28px;
    }}
    .translate-action:hover, .translate-close:hover, .translate-expand:hover {{
        color: {p.on_surface};
        background-color: {rgba(p.on_surface, 0.08)};
    }}
    .translate-action:active, .translate-close:active, .translate-expand:active {{
        background-color: {rgba(p.on_surface, 0.14)};
    }}
    .translate-action.translate-copied {{ color: {p.primary}; }}
    .translate-action:disabled {{ opacity: 0.38; }}
    .translate-source-scroll > scrollbar.vertical,
    .translate-results-scroll > scrollbar.vertical {{
        background-color: transparent;
        border: none;
    }}
    .translate-source-scroll > scrollbar.vertical trough,
    .translate-results-scroll > scrollbar.vertical trough {{
        background-image: none;
        background-color: transparent;
        border: none;
        border-radius: 999px;
        box-shadow: none;
    }}
    .translate-source-scroll > scrollbar.vertical slider,
    .translate-results-scroll > scrollbar.vertical slider {{
        background-image: none;
        background-color: {rgba(p.outline, 0.55)};
        border: none;
        border-radius: 999px;
        box-shadow: none;
        min-width: 4px;
    }}
    .translate-source-scroll > scrollbar.vertical slider:hover,
    .translate-results-scroll > scrollbar.vertical slider:hover {{
        background-color: {rgba(p.primary, 0.76)};
        box-shadow: none;
        min-width: 6px;
    }}
    .translate-source-scroll > scrollbar.vertical slider:active,
    .translate-results-scroll > scrollbar.vertical slider:active {{
        background-color: {rgba(p.primary, 0.92)};
        box-shadow: none;
    }}
    """


def mix(base: str, other: str, amount: float) -> str:
    """Blend two ``#rrggbb`` colors; ``amount`` is the share of ``other``."""
    first, second = _rgb(base), _rgb(other)
    return "#" + "".join(
        f"{round(a + (b - a) * amount):02x}" for a, b in zip(first, second)
    )


def rgba(value: str, alpha: float) -> str:
    red, green, blue = _rgb(value)
    return f"rgba({red}, {green}, {blue}, {alpha:.2f})"


def _rgb(value: str) -> tuple[int, int, int]:
    color = value.lstrip("#")
    if len(color) != 6:
        color = "808898"
    try:
        red, green, blue = (int(color[index : index + 2], 16) for index in (0, 2, 4))
    except ValueError:
        return 128, 136, 152
    return red, green, blue


def _default_palette_paths() -> tuple[Path, ...]:
    cache_home = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return (
        Path(cache_home) / "nyxuri" / "palette.toml",
        Path(cache_home) / "nyxniri" / "palette.toml",
        Path(cache_home) / "noctalia" / "starship-palette.toml",
    )


def _collect_strings(value: object, target: dict[str, str]) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(item, str):
                target[str(key)] = item
            else:
                _collect_strings(item, target)


def _pick(values: dict[str, str], *keys: str, fallback: str) -> str:
    for key in keys:
        value = values.get(key, "").strip()
        if len(value) == 7 and value.startswith("#"):
            try:
                int(value[1:], 16)
            except ValueError:
                continue
            return value
    return fallback
