import math
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple


def srgb_to_linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def linear_to_srgb(c: float) -> float:
    return c * 12.92 if c <= 0.0031308 else 1.055 * (c ** (1.0 / 2.4)) - 0.055


def _cbrt(x: float) -> float:
    return math.copysign(abs(x) ** (1.0 / 3.0), x)


def linear_to_oklab(r: float, g: float, b: float) -> Tuple[float, float, float]:
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_, m_, s_ = _cbrt(l), _cbrt(m), _cbrt(s)
    return (
        0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
        1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
        0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_,
    )


def oklab_to_linear(L: float, a: float, b: float) -> Tuple[float, float, float]:
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    return (
        +4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
        -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
        -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s,
    )


def oklch_to_oklab(L: float, C: float, h_deg: float) -> Tuple[float, float, float]:
    h = math.radians(h_deg)
    return (L, C * math.cos(h), C * math.sin(h))


def oklab_to_oklch(L: float, a: float, b: float) -> Tuple[float, float, float]:
    C = math.hypot(a, b)
    h = math.degrees(math.atan2(b, a)) % 360.0
    return (L, C, h)


_EPS = (6.0 / 29.0) ** 3

_BISECT_L = 20
_BISECT_C = 12
_SCHEME_CACHE: Dict[Tuple[int, int, int], Dict[str, Dict[str, str]]] = {}
_TONE_CACHE: Dict[Tuple[float, float, float], Tuple[int, int, int]] = {}


def linear_to_lstar(r: float, g: float, b: float) -> float:
    y = 0.2126390058715104 * r + 0.7151686787677560 * g + 0.0721923153607337 * b
    f = y ** (1.0 / 3.0) if y > _EPS else y / (3.0 * (6.0 / 29.0) ** 2) + 4.0 / 29.0
    return 116.0 * f - 16.0


def _in_gamut(r: float, g: float, b: float, tol: float = 1e-4) -> bool:
    return all(-tol <= v <= 1.0 + tol for v in (r, g, b))


def hct_to_rgb(hue: float, chroma: float, tone: float) -> Tuple[int, int, int]:
    tone = max(0.0, min(100.0, tone))

    def rgb_at(L: float, C: float) -> Tuple[float, float, float]:
        _, a, b = oklch_to_oklab(L, C, hue)
        return oklab_to_linear(L, a, b)

    def lstar_at(L: float, C: float) -> float:
        return linear_to_lstar(*rgb_at(L, C))

    lo, hi = 0.0, 1.0
    for _ in range(_BISECT_L):
        mid = (lo + hi) / 2.0
        if lstar_at(mid, chroma) < tone:
            lo = mid
        else:
            hi = mid
    L = (lo + hi) / 2.0

    r, g, b = rgb_at(L, chroma)
    if not _in_gamut(r, g, b):
        clo, chi = 0.0, chroma
        for _ in range(_BISECT_C):
            cmid = (clo + chi) / 2.0
            rr, gg, bb = rgb_at(L, cmid)
            if _in_gamut(rr, gg, bb):
                clo = cmid
            else:
                chi = cmid
        r, g, b = rgb_at(L, clo)

    def _to8(v: float) -> int:
        return max(0, min(255, int(round(linear_to_srgb(max(0.0, min(1.0, v))) * 255.0))))

    return (_to8(r), _to8(g), _to8(b))


def rgb_to_oklch(rgb: Sequence[int]) -> Tuple[float, float, float]:
    r, g, b = (srgb_to_linear(c / 255.0) for c in rgb[:3])
    return oklab_to_oklch(*linear_to_oklab(r, g, b))


def rgb_to_lstar(rgb: Sequence[int]) -> float:
    r, g, b = (srgb_to_linear(c / 255.0) for c in rgb[:3])
    return linear_to_lstar(r, g, b)


def hex_of(rgb: Sequence[int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*(max(0, min(255, int(c))) for c in rgb[:3]))


def rgb_of(hex_str: str) -> Tuple[int, int, int]:
    h = hex_str.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    if len(h) != 6:
        raise ValueError("bad hex: " + hex_str)
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


@dataclass(frozen=True)
class TonalPalette:
    hue: float
    chroma: float

    def tone(self, t: float) -> Tuple[int, int, int]:
        return hct_to_rgb(self.hue, self.chroma, t)


def _scheme_palettes(source: Sequence[int]) -> Dict[str, TonalPalette]:
    _, _, hue = rgb_to_oklch(source)
    return {
        "primary": TonalPalette(hue, 0.120),
        "secondary": TonalPalette(hue, 0.055),
        "tertiary": TonalPalette((hue + 60.0) % 360.0, 0.085),
        "neutral": TonalPalette(hue, 0.008),
        "neutral_variant": TonalPalette(hue, 0.022),
        "error": TonalPalette(25.0, 0.220),
    }


_ROLE_TONES: Dict[str, Tuple[str, float, float]] = {
    "primary": ("primary", 80.0, 40.0),
    "on_primary": ("primary", 20.0, 100.0),
    "primary_container": ("primary", 30.0, 90.0),
    "on_primary_container": ("primary", 90.0, 10.0),
    "secondary": ("secondary", 80.0, 40.0),
    "on_secondary": ("secondary", 20.0, 100.0),
    "secondary_container": ("secondary", 30.0, 90.0),
    "on_secondary_container": ("secondary", 90.0, 10.0),
    "tertiary": ("tertiary", 80.0, 40.0),
    "on_tertiary": ("tertiary", 20.0, 100.0),
    "tertiary_container": ("tertiary", 30.0, 90.0),
    "on_tertiary_container": ("tertiary", 90.0, 10.0),
    "error": ("error", 80.0, 40.0),
    "on_error": ("error", 20.0, 100.0),
    "error_container": ("error", 30.0, 90.0),
    "on_error_container": ("error", 90.0, 10.0),
    "background": ("neutral", 6.0, 98.0),
    "on_background": ("neutral", 90.0, 10.0),
    "surface": ("neutral", 6.0, 98.0),
    "on_surface": ("neutral", 90.0, 10.0),
    "surface_dim": ("neutral", 6.0, 87.0),
    "surface_bright": ("neutral", 24.0, 98.0),
    "surface_variant": ("neutral_variant", 30.0, 90.0),
    "on_surface_variant": ("neutral_variant", 80.0, 30.0),
    "surface_container_lowest": ("neutral", 4.0, 100.0),
    "surface_container_low": ("neutral", 10.0, 96.0),
    "surface_container": ("neutral", 12.0, 94.0),
    "surface_container_high": ("neutral", 17.0, 92.0),
    "surface_container_highest": ("neutral", 22.0, 90.0),
    "outline": ("neutral_variant", 60.0, 50.0),
    "outline_variant": ("neutral_variant", 30.0, 80.0),
    "shadow": ("neutral", 0.0, 0.0),
    "scrim": ("neutral", 0.0, 0.0),
}

PALETTE_ROLES: Tuple[str, ...] = tuple(_ROLE_TONES)


def generate_scheme(source: Sequence[int]) -> Dict[str, Dict[str, str]]:
    key = (int(source[0]), int(source[1]), int(source[2]))
    cached = _SCHEME_CACHE.get(key)
    if cached is not None:
        return cached
    palettes = _scheme_palettes(source)
    out: Dict[str, Dict[str, str]] = {"dark": {}, "light": {}}
    for role, (pname, dark_tone, light_tone) in _ROLE_TONES.items():
        p = palettes[pname]
        out["dark"][role] = hex_of(p.tone(dark_tone))
        out["light"][role] = hex_of(p.tone(light_tone))
    if len(_SCHEME_CACHE) > 32:
        _SCHEME_CACHE.clear()
    _SCHEME_CACHE[key] = out
    return out


def render_palette_toml(scheme: Dict[str, Dict[str, str]], mode: str = "dark",
                        source_hex: str = "", wallpaper: str = "") -> str:
    colors = scheme.get(mode) or scheme["dark"]
    lines = ["# mode = " + mode]
    if source_hex:
        lines.append("# source = " + source_hex)
    if wallpaper:
        lines.append("# wallpaper = " + wallpaper)
    lines.append("")
    for role in PALETTE_ROLES:
        if role in colors:
            lines.append(role + ' = "' + colors[role] + '"')
    lines.append("")
    return "\n".join(lines)


def _self_check() -> List[str]:
    problems: List[str] = []

    white = hct_to_rgb(0.0, 0.0, 100.0)
    black = hct_to_rgb(0.0, 0.0, 0.0)
    if white != (255, 255, 255):
        problems.append(f"tone 100 -> {white}")
    if black != (0, 0, 0):
        problems.append(f"tone 0 -> {black}")

    for tone in (10, 30, 50, 70, 90):
        got = rgb_to_lstar(hct_to_rgb(250.0, 0.0, float(tone)))
        if abs(got - tone) > 1.5:
            problems.append(f"tone {tone} roundtrip {got:.2f}")

    scheme = generate_scheme((0x67, 0x5F, 0xC4))
    for mode in ("dark", "light"):
        missing = [r for r in PALETTE_ROLES if r not in scheme[mode]]
        if missing:
            problems.append(f"{mode} missing {missing}")

    for role in PALETTE_ROLES:
        for mode in ("dark", "light"):
            try:
                rgb_of(scheme[mode][role])
            except ValueError:
                problems.append(f"{mode}.{role} unparsable")

    return problems


if __name__ == "__main__":
    import sys

    issues = _self_check()
    if issues:
        print("self-check failed:")
        for p in issues:
            print("  -", p)
        sys.exit(1)

    src = (0x67, 0x50, 0xA4)
    scheme = generate_scheme(src)
    print(f"source {hex_of(src)} oklch={tuple(round(v, 3) for v in rgb_to_oklch(src))}")
    for role in ("primary", "on_primary", "primary_container", "surface", "on_surface"):
        print(f"  {role:22s} dark={scheme['dark'][role]}  light={scheme['light'][role]}")
    print("ok")
