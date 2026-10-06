# Noctalia: Theming, Color Palettes & Template Engine

This document provides a comprehensive technical reference for Noctalia's theme engine, 16 core color roles, custom palette JSON schemas, template syntax (`<* *>` and `{{ }}`), color filters, and application theming integration.

---

## 1. Theme Configuration (`[theme]`)

```toml
[theme]
mode              = "dark"        # "dark" | "light" | "auto" (follows solar schedule in [location])
source            = "builtin"     # "builtin" | "wallpaper" | "community" | "custom"
builtin           = "Noctalia"    # Bundled palette name
community_palette = "Oxocarbon"   # Community palette from api.noctalia.dev
custom_palette    = "MyPalette"   # Filename in ~/.config/noctalia/palettes/ (without .json)
wallpaper_scheme  = "m3-content"  # Algorithm when source = "wallpaper"
pure_black_dark   = false         # Replace dark background roles with #000000 (OLED mode)
```

### 1.1 Palette Sources
1. **`builtin`**: Compiled-in presets: `Ayu`, `Catppuccin`, `Dracula`, `Eldritch`, `Gruvbox`, `Kanagawa`, `Noctalia`, `Nord`, `Rosé Pine`, `Tokyo-Night`.
2. **`wallpaper`**: Material 3 / Custom algorithmic palette derived from current wallpaper image.
   - Schemes: `m3-tonal-spot` (default M3), `m3-content` (higher chroma), `m3-fruit-salad`, `m3-rainbow`, `m3-monochrome`, `vibrant`, `faithful`, `soft`, `dysfunctional`, `muted`.
3. **`community`**: Downloaded from `https://api.noctalia.dev/palette/<name>` and cached in `~/.local/state/noctalia/community-palettes/`. Auto-syncs on MD5 hash updates.
4. **`custom`**: Loaded from `~/.config/noctalia/palettes/<name>.json`.

---

## 2. Color Roles & Palette JSON Specification

### 2.1 The 16 Core Color Roles

| Role Name (`snake_case`) | Internal Key | Description |
|--------------------------|--------------|-------------|
| `primary` | `mPrimary` | Primary accent for buttons, highlights, active states |
| `on_primary` | `mOnPrimary` | Text/icons on top of `primary` |
| `secondary` | `mSecondary` | Secondary accent |
| `on_secondary` | `mOnSecondary` | Text/icons on top of `secondary` |
| `tertiary` | `mTertiary` | Tertiary accent |
| `on_tertiary` | `mOnTertiary` | Text/icons on top of `tertiary` |
| `error` | `mError` | Error/destructive action color |
| `on_error` | `mOnError` | Text/icons on top of `error` |
| `surface` | `mSurface` | Main surface/background |
| `on_surface` | `mOnSurface` | Primary text and icons on `surface` |
| `surface_variant` | `mSurfaceVariant` | Secondary surface (cards, capsules, panel tiles) |
| `on_surface_variant` | `mOnSurfaceVariant` | Subdued text/icons on `surface_variant` |
| `outline` | `mOutline` | Borders, dividers, subtle outlines |
| `shadow` | `mShadow` | Drop shadow tint |
| `hover` | `mHover` | Hover/interactive highlight fill |
| `on_hover` | `mOnHover` | Text/icons on hover surfaces |

### 2.2 Custom Palette File Schema (`palettes/<name>.json`)

```json
{
  "dark": {
    "mPrimary": "#a6e22e",
    "mOnPrimary": "#272822",
    "mSecondary": "#66d9ef",
    "mOnSecondary": "#272822",
    "mTertiary": "#f92672",
    "mOnTertiary": "#272822",
    "mError": "#f92672",
    "mOnError": "#272822",
    "mSurface": "#272822",
    "mOnSurface": "#f8f8f2",
    "mSurfaceVariant": "#3e3d32",
    "mOnSurfaceVariant": "#a6e22e",
    "mOutline": "#75715e",
    "mShadow": "#272822",
    "mHover": "#3a3a32",
    "mOnHover": "#f8f8f2",
    "terminal": {
      "background": "#272822",
      "foreground": "#f8f8f2",
      "cursor": "#f8f8f2",
      "cursorText": "#272822",
      "selectionBg": "#f8f8f2",
      "selectionFg": "#272822",
      "normal": {
        "black": "#272822", "red": "#f92672", "green": "#a6e22e", "yellow": "#f4bf75",
        "blue": "#66d9ef", "magenta": "#ae81ff", "cyan": "#a1efe4", "white": "#f8f8f2"
      },
      "bright": {
        "black": "#75715e", "red": "#f92672", "green": "#a6e22e", "yellow": "#f4bf75",
        "blue": "#66d9ef", "magenta": "#ae81ff", "cyan": "#a1efe4", "white": "#f9f8f5"
      }
    }
  },
  "light": {
    "mPrimary": "#a6e22e",
    "mOnPrimary": "#f8f8f2",
    "mSecondary": "#66d9ef",
    "mOnSecondary": "#f8f8f2",
    "mTertiary": "#f92672",
    "mOnTertiary": "#f8f8f2",
    "mError": "#f92672",
    "mOnError": "#f8f8f2",
    "mSurface": "#f8f8f2",
    "mOnSurface": "#272822",
    "mSurfaceVariant": "#e6e1dc",
    "mOnSurfaceVariant": "#272822",
    "mOutline": "#a6e22e",
    "mShadow": "#d8d8d8",
    "mHover": "#e6e1dc",
    "mOnHover": "#272822",
    "terminal": {
      "background": "#f8f8f2",
      "foreground": "#272822",
      "cursor": "#272822",
      "cursorText": "#f8f8f2",
      "selectionBg": "#272822",
      "selectionFg": "#f8f8f2",
      "normal": {
        "black": "#f8f8f2", "red": "#f92672", "green": "#a6e22e", "yellow": "#f4bf75",
        "blue": "#66d9ef", "magenta": "#ae81ff", "cyan": "#a1efe4", "white": "#272822"
      },
      "bright": {
        "black": "#d8d8d2", "red": "#f92672", "green": "#a6e22e", "yellow": "#f4bf75",
        "blue": "#66d9ef", "magenta": "#ae81ff", "cyan": "#a1efe4", "white": "#1e1e19"
      }
    }
  }
}
```

---

## 3. Template Engine Specification

The Noctalia `TemplateEngine` generates external application themes (e.g. Foot, Alacritty, GTK, Qt, Neovim, Discord).

### 3.1 Syntax Rules

- **Inline Expressions**: `{{ ... }}`
- **Block Directives**: `<* ... *>` (supports `for`, `endfor`, `if`, `else`, `endif`)
- **Standalone Block Trimming**: Lines containing only a block tag with whitespace are stripped from output.

### 3.2 Token Access Syntax

```text
{{ colors.<name>.<mode>.<format> }}
```
- `<name>`: Any Material 3 role (e.g. `primary`, `surface_container_high`), terminal token (e.g. `terminal_background`, `terminal_normal_red`), or custom color token.
- `<mode>`: `default` (active theme mode), `dark`, or `light`.
- `<format>`: `hex` (`#RRGGBB`), `hex_stripped` (`RRGGBB`), `rgb` (`rgb(r, g, b)`), `rgb_csv` (`r,g,b`), `rgba` (`rgba(r, g, b, a)`), `hsl` (`hsl(h, s%, l%)`), `hsla`, `red`, `green`, `blue`, `alpha`, `hue`, `saturation`, `lightness`.

### 3.3 Built-in Color Tokens
- **Primary**: `primary`, `on_primary`, `primary_container`, `on_primary_container`, `primary_fixed`, `primary_fixed_dim`, `on_primary_fixed`, `on_primary_fixed_variant`
- **Secondary**: `secondary`, `on_secondary`, `secondary_container`, `on_secondary_container`, `secondary_fixed`, `secondary_fixed_dim`, `on_secondary_fixed`, `on_secondary_fixed_variant`
- **Tertiary**: `tertiary`, `on_tertiary`, `tertiary_container`, `on_tertiary_container`, `tertiary_fixed`, `tertiary_fixed_dim`, `on_tertiary_fixed`, `on_tertiary_fixed_variant`
- **Error**: `error`, `on_error`, `error_container`, `on_error_container`
- **Surface**: `surface`, `on_surface`, `surface_variant`, `on_surface_variant`, `surface_dim`, `surface_bright`, `surface_container_lowest`, `surface_container_low`, `surface_container`, `surface_container_high`, `surface_container_highest`
- **Outline & Utility**: `outline`, `outline_variant`, `shadow`, `scrim`
- **Inverse**: `inverse_surface`, `inverse_on_surface`, `inverse_primary`
- **Background**: `background`, `on_background`
- **Terminal Tokens**: `terminal_foreground`, `terminal_background`, `terminal_cursor`, `terminal_cursor_text`, `terminal_selection_fg`, `terminal_selection_bg`, `terminal_normal_black` .. `white`, `terminal_bright_black` .. `white`.

### 3.4 Filters Reference

| Filter | Syntax | Description |
|--------|--------|-------------|
| `grayscale` | `{{ ... \| grayscale }}` | Converts color to grayscale using luminance |
| `invert` | `{{ ... \| invert }}` | Inverts RGB channels |
| `set_alpha` | `{{ ... \| set_alpha 0.5 }}` | Sets alpha (0.0–1.0) |
| `set_lightness` | `{{ ... \| set_lightness 80 }}` | Sets HSL lightness (0–100) |
| `set_hue` | `{{ ... \| set_hue 180 }}` | Sets absolute hue (0–360) |
| `rotate_hue` | `{{ ... \| rotate_hue 30 }}` | Rotates hue relative degrees |
| `set_saturation`| `{{ ... \| set_saturation 50 }}` | Sets HSL saturation (0–100) |
| `lighten` | `{{ ... \| lighten 10 }}` | Adds percentage points to lightness |
| `darken` | `{{ ... \| darken 10 }}` | Subtracts percentage points from lightness |
| `saturate` | `{{ ... \| saturate 10 }}` | Adds percentage points to saturation |
| `desaturate` | `{{ ... \| desaturate 10 }}` | Subtracts percentage points from saturation |
| `auto_lightness`| `{{ ... \| auto_lightness 15 }}`| Lightens dark colors, darkens light colors |
| `blend` | `{{ ... \| blend: "#ff0000", 0.5 }}` | Interpolates toward target color |
| `harmonize` | `{{ ... \| harmonize: "#00ff88" }}`| Nudges hue toward color (max 15°) |
| `to_color` | `{{ "#ffaa00" \| to_color \| darken 10 }}` | Converts string to color for subsequent filters |
| `replace` | `{{ mode \| replace: "dark", "night" }}` | String replacement |
| `snake_case`, `kebab_case`, `camel_case`, `pascal_case`, `lower_case` | `{{ "Foo Bar" \| snake_case }}` | Casing conversions |

### 3.5 Loops & Conditionals

```text
<* for name, value in colors *>
{{ name }} = {{ value.default.hex }}
<* endfor *>

<* if {{ loop.first }} *>
# Header
<* else *>
# Item
<* endif *>

# Tonal palettes direct access & iteration:
{{ palettes.primary.40.hex }}
<* for tone in palettes.secondary *>
{{ tone.default }}
<* endfor *>

# Numeric ranges:
<* for i in 0..16 *>
color{{ i }} = ...
<* endfor *>
```

---

## 4. App Theming Configuration (`[theme.templates]`)

```toml
[theme.templates]
enable_builtin_templates   = true
builtin_ids                = ["gtk3", "gtk4", "qt", "kcolor_scheme", "foot", "alacritty", "umbriel"]
enable_community_templates = true
community_ids              = ["discord", "neovim", "obsidian"]

# Custom Colors Definitions:
[theme.templates.custom_colors.warning]
color       = "#f97316"
color_dark  = "#f97316"
color_light = "#c2410c"
blend       = true       # Harmonize with active palette

# User-Defined Custom Template:
[theme.templates.user.my_app]
input_path           = "$XDG_CONFIG_HOME/noctalia/templates/my-app.css"
output_path          = "$XDG_CONFIG_HOME/my-app/theme.css"
output_path_dynamic  = ""                       # Optional shell command yielding extra paths
input_path_modes     = { dark = "./d.css", light = "./l.css" }
pre_hook             = ""                       # Shell command before writing
post_hook            = "pkill -USR1 my-app"     # Shell command after writing
post_action          = ""                       # "kde-color-scheme"
requires_path        = ""                       # Skip template if path does not exist
enabled              = true
```

### 4.1 CLI Tools for Theming

```sh
# Render a single template file:
noctalia theme ~/Pictures/wall.png -r template.in:output.out

# Process a template config:
noctalia theme ~/Pictures/wall.png -c templates.toml

# List all available built-in, community, and user templates:
noctalia theme --list-templates

# Process shipped built-in templates:
noctalia theme ~/Pictures/wall.png --builtin-config
```
