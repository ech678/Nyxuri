Plugins ship flavor variants — forms layer between the defaults and your own tweaks, so switching never touches your content. One verb covers everything: `nyxuri use`.

Built-in official forms:
- **`kitty`**:
  - `default`: standard 90% opacity
  - `transparent`: 75% higher translucency flavor
- **`niri`**:
  - `default`: minimalist frameless layout (default)

---

## Slot axes (Niri)

Beyond whole-config forms, a plugin can declare **slot axes** for granular hot-swapping of individual visual components:

- **`glow`** (window focus outline & diffused glow):
  - `default`: frameless minimal look without outline or glow
  - `glow`: 2px outline and 28px soft diffused ambient glow for distinct tiling window focus
  - `glow-material-you`: focus glow follows Noctalia's active Material You wallpaper palette (dynamically re-rendered in real time)
- **`effects`** (compositor shader & blur pipeline):
  - `default`: standard window rendering
  - `xray-blur`: backdrop blur and window transparency

Switch a slot axis with `nyxuri use niri slot <axis> <name>`.

---

## Form commands

| Command | Description |
| :--- | :--- |
| `nyxuri use <plugin> list` | List forms (`*` marks the active one) |
| `nyxuri use <plugin> <form>` | Switch form (`use <plugin> default` resets) |
| `nyxuri use <plugin> slots` | Inspect available slot axes and variants |
| `nyxuri use <plugin> slot <axis> <name>` | Hot-swap one slot axis (e.g. glow, effects) |
| `nyxuri use <plugin> save <name>` | Save the current config as a private form |
| `nyxuri use <plugin> edit <name>` | Edit a private form in `$EDITOR` |
| `nyxuri use <plugin> delete <name>` | Delete a private form (official ones are read-only) |

Official forms update with `nyxuri update`; private ones live in `~/.config/nyxuri/forms/`.
