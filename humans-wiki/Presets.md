Some apps ship flavor variants — presets layer between defaults and your `__custom__` files, so switching never touches your own tweaks.

Built-in official presets:
- **`kitty`**:
  - `default`: standard 90% opacity
  - `transparent`: 75% higher translucency flavor
- **`niri`**:
  - `default`: minimalist frameless look (default)
  - `glow`: enables 2px outline and 28px soft diffused ambient glow (improves focus visibility across tiled windows)
  - `glow-material-you`: focus glow follows Noctalia's active Material You wallpaper palette (dynamically re-rendered in real time)

The preset architecture also supports modular Parts slots (e.g. `glow` and `effects` in `niri`), allowing full preset switching as well as granular piece-by-piece overlay.

---

## Preset commands

| Command | Description |
| :--- | :--- |
| `nyxuri preset <app> list` | List presets (`*` marks the active one) |
| `nyxuri preset <app> apply <name>` | Switch preset (`apply default` resets) |
| `nyxuri preset <app> save <name>` | Save the current config as a private preset |
| `nyxuri preset <app> edit <name>` | Edit a private preset in `$EDITOR` |
| `nyxuri preset <app> delete <name>` | Delete a private preset (official ones are read-only) |

Official presets update with `nyxuri update`; private ones live in `~/.config/nyxuri/presets/`.
