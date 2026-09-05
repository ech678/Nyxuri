<a id="readme-top"></a>

<div align="right">
  <strong>English</strong> | <a href="README.zh-CN.md">简体中文</a>
</div>

<div align="center">

<h1>NyxNiri</h1>

<p><strong>A Material You desktop experience for Arch / CachyOS</strong><br />
<sub>Built on Niri and Noctalia V5 — and stays out of your way.</sub></p>

<p>
  <a href="https://github.com/ech678/NyxNiri/stargazers"><img height="22" src="https://m3-markdown-badges.vercel.app/stars/3/3/ech678/NyxNiri" alt="Stars" /></a>
  &nbsp;
  <a href="https://archlinux.org"><img height="22" src="https://ziadoua.github.io/m3-Markdown-Badges/badges/Arch/arch2.svg" alt="Arch Linux" /></a>
  &nbsp;
  <a href="LICENSE"><img height="22" src="https://ziadoua.github.io/m3-Markdown-Badges/badges/LicenceGPLv3/licencegplv33.svg" alt="GPL-3.0" /></a>
</p>

<a href="https://github.com/user-attachments/assets/9ef4da30-54c0-491b-916f-2f2a3beac6be">
  <img src="https://github.com/user-attachments/assets/9ef4da30-54c0-491b-916f-2f2a3beac6be" alt="NyxNiri Preview" width="92%" />
</a>

<p>
  <sub><em><a href="https://nyxniri.com">Website</a> · Watch demo on <a href="https://www.bilibili.com/video/BV1c63n6dEEG">Bilibili</a> · Join discussion on <a href="https://www.reddit.com/r/niri/comments/1vf53le/nyxniri_a_material_you_desktop_config_for_niri/">Reddit</a></em></sub>
</p>

</div>

## Features

- **Wallpaper Picker** (`Super+W`) — static + live, search and categories.
- **Color Sync** — Noctalia V5 extracts palettes from wallpaper; `mpvpaper` + `ffmpeg` for video frames.
- **Light/Dark Sync** — GTK 3/4, XDG portal, Kitty, and browsers switch together.
- **Eye Care** (`Super+N`) — warmer color temperature, no blur, opaque windows.
- **Scratchpad** (`Super+~`) — persistent Kitty floating terminal.
- **Orbit Launcher** (`Super+A` / `Super+MouseForward`) — vector radial; apps, tools, links, AI/search dial (TOML-configurable).
- **Shell & Terminal** — Fish aliases for proxy/cache, Kitty cursor trails, Windows-style shortcuts.
- **NyxMellow** — dynamic fcitx5 skin: mellow geometry + Noctalia Material You palette.
- **Presets** — per-app flavor variants (e.g. kitty transparent); switch with one command, save your setup as a private preset, or edit it in `$EDITOR`.

## Install

> [!IMPORTANT]
> **Upgrading from the legacy Bash release (`lib/` + `v2/`):** its `nyxniri update` cannot switch to the current Python layout. Run the current bootstrap once before updating. Configs, `~/.config/NyxNiri/backups/`, and legacy `~/.config/dotfiles_backup_*` snapshots are preserved.

### Standalone (online)

```bash
curl -fsSL --connect-timeout 10 https://raw.githubusercontent.com/ech678/NyxNiri/main/install.sh | bash
```

> [!TIP]
> Without an AUR helper, `nyxniri install full` can bootstrap `paru` for you.

### From a git checkout (recommended)

```bash
# shallow clone: latest snapshot only; drop --depth 1 for full history
git clone --depth 1 https://github.com/ech678/NyxNiri.git ~/NyxNiri
cd ~/NyxNiri && ./install.sh
```

### System package (AUR)

> Coming soon — `paru -S nyxniri-git`, with updates handled by pacman.

<details>
<summary>Mirrors for China (gh-proxy / CDN)</summary>

```bash
# Standalone via gh-proxy.org
curl -fsSL --connect-timeout 10 https://gh-proxy.org/https://raw.githubusercontent.com/ech678/NyxNiri/main/install.sh | bash

# git clone via gh-proxy.org
git clone --depth 1 https://gh-proxy.org/https://github.com/ech678/NyxNiri.git ~/NyxNiri
cd ~/NyxNiri && ./install.sh
```

For repository downloads, `install.sh` tries GitHub first, then gh-proxy.
</details>

## Included Configs

```text
NyxNiri
├── install.sh                  # lightweight bootstrap entrypoint
├── nyxniri/                    # Python core engine (zero pip dependencies)
├── assets/                     # static assets (wallpapers, fcitx5 skin templates)
└── configs/
    ├── niri/                   # window manager (.kdl, .toml)
    │   └── scripts/            # Orbit launcher, wallpaper picker & scratchpad scripts
    ├── noctalia/               # shell + theme sync
    ├── xdg-desktop-portal/     # portal routing (Settings / screencast)
    ├── kitty/                  # terminal
    ├── fish/                   # aliases + functions
    ├── fastfetch/              # system info
    ├── zed/                    # editor
    └── starship.toml           # prompt
```

> [!NOTE]
> Configs deploy atomically. Personal tweaks survive updates via the Dunder protocol:
> - `*__custom__*` files (e.g. `01__custom__.kdl`) and folders are preserved — number prefixes control load order.
> - `~/.config/niri/monitor.kdl` is kept across deployments.

## Presets

Some apps ship flavor variants — `kitty` comes with a `transparent` preset out of the box. Presets layer between defaults and your `__custom__` files, so switching never touches your own tweaks.

| Command | Description |
| :--- | :--- |
| `nyxniri preset <app> list` | List presets (`*` marks the active one) |
| `nyxniri preset <app> apply <name>` | Switch preset (`apply default` resets) |
| `nyxniri preset <app> save <name>` | Save the current config as a private preset |
| `nyxniri preset <app> edit <name>` | Edit a private preset in `$EDITOR` |
| `nyxniri preset <app> delete <name>` | Delete a private preset (official ones are read-only) |

Official presets update with `nyxniri update`; private ones live in `~/.config/NyxNiri/presets/`.

## Keybindings

<details>
<summary>Window management</summary>

| Shortcut | Action |
| :--- | :--- |
| <kbd>Super</kbd> + <kbd>Enter</kbd> | Open terminal |
| <kbd>Super</kbd> + <kbd>Q</kbd> | Close window |
| <kbd>Super</kbd> + <kbd>T</kbd> | Toggle floating/tiling |
| <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>T</kbd> | Switch focus between floating and tiling |
| <kbd>Super</kbd> + <kbd>G</kbd> | Toggle tabbed column display (Tabbed Group) |
| <kbd>Super</kbd> + <kbd>F</kbd> | Maximize current column |
| <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>F</kbd> | Fullscreen |
| <kbd>Super</kbd> + <kbd>Tab</kbd> | Workspace overview |
| <kbd>Super</kbd> + <kbd>Z</kbd> / <kbd>C</kbd> | Focus left / right column |
| <kbd>Super</kbd> + <kbd>Arrows</kbd> | Smart focus (column/monitor/workspace) |
| <kbd>Super</kbd> + <kbd>Ctrl</kbd> + <kbd>Arrows</kbd> | Smart move (column/monitor/workspace) |
| <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>Arrows</kbd> | Precision local move (incl. within column) |
| <kbd>Super</kbd> + <kbd>D</kbd> / <kbd>U</kbd> | Workspace down/up |
| <kbd>Super</kbd> + <kbd>Space</kbd> | Switch preset column widths |
| <kbd>Super</kbd> + <kbd>-</kbd> / <kbd>=</kbd> | Decrease/increase column width |

</details>

<details>
<summary>System & components</summary>

| Shortcut | Action |
| :--- | :--- |
| <kbd>Super</kbd> + <kbd>R</kbd> | App launcher |
| <kbd>Super</kbd> + <kbd>E</kbd> | File manager |
| <kbd>Super</kbd> + <kbd>X</kbd> | Power menu |
| <kbd>Super</kbd> + <kbd>I</kbd> | Control center |
| <kbd>Super</kbd> + <kbd>V</kbd> | Clipboard history |
| <kbd>Super</kbd> + <kbd>W</kbd> | Wallpaper picker (static & live) |
| <kbd>Super</kbd> + <kbd>Ctrl</kbd> + <kbd>W</kbd> | Switch to random wallpaper |
| <kbd>Super</kbd> + <kbd>N</kbd> | Toggle Eye Care Mode |
| <kbd>Super</kbd> + <kbd>~</kbd> | Toggle Kitty scratchpad terminal |
| <kbd>Super</kbd> + <kbd>A</kbd> / <kbd>Super</kbd> + <kbd>Mouse Forward</kbd> | Orbit vector radial launcher |
| <kbd>Super</kbd> + <kbd>L</kbd> | Lock screen |
| <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>S</kbd> | Screenshot |
| <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>R</kbd> | Reload Niri |
| <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>Q</kbd> | Quit Niri |

</details>

> [!TIP]
> Quick reference: `nyxhelp keys`. For Niri's full overlay, press <kbd>Super</kbd> + <kbd>/</kbd>.

## Extensions

> The GTK theme and fisher plugin manager deploy automatically with a full install; the items below are opt-in.

**NyxMellow fcitx5 skin:** mellow rounded shape matching Noctalia color palette (auto light/dark switch). `nyxniri fcitx install` registers it as a template and re-renders on wallpaper/theme changes. Opt-in only.

<p align="center">
  <img src="https://github.com/user-attachments/assets/3f861e8e-55da-408e-a9d5-7f337a039b74" alt="NyxMellow skin (light)" width="48%" />
  <img src="https://github.com/user-attachments/assets/291918e9-4532-480f-b777-7ebe0691eaf9" alt="NyxMellow skin (dark)" width="48%" />
  <br />
  <sub><em>NyxMellow skin in light and dark mode</em></sub>
</p>

**Wallpaper & video pack:** high-res wallpapers and live videos (~100MB) live in [wallpaper-collection](https://github.com/ech678/wallpaper-collection). Opt-in during `install` or download anytime via `nyxniri wallpapers`.

**Noctalia Greeter:** greetd login screen matching Noctalia style, `nyxniri greeter install` installs `greetd` + `noctalia-greeter` (AUR), backs up existing configuration, configures Polkit rules, then switches the next boot to greetd without ending the current session, a failed switch or `nyxniri greeter uninstall` restores the previous display manager

## Tooling

`nyxniri` manages install, snapshots and diagnostics. Interactive deployments create a snapshot in `~/.config/NyxNiri/backups/` by default.

> Legacy Bash users must run the current bootstrap shown above before using these commands. The old `nyxniri update` cannot perform the directory migration.

**Top-level**

| Command | Description |
| :--- | :--- |
| `nyxniri` | Interactive menu |
| `nyxniri test` | Developer test deploy (no backup, keep monitor.kdl) |

**Deploy**

| Command | Description |
| :--- | :--- |
| `nyxniri install [full\|config]` | Deploy everything, or sync configs only |
| `nyxniri update [--force\|--no-deploy]` | Update source; force config deployment or skip it |

**Snapshots**

| Command | Description |
| :--- | :--- |
| `nyxniri snapshot [note]` | Save current config state |
| `nyxniri snapshot delete [idx]` | Delete snapshots (multi-select if no index) |
| `nyxniri rollback [index]` | Restore a snapshot |
| `nyxniri list` | List snapshots |

**System**

| Command | Description |
| :--- | :--- |
| `nyxniri doctor` | Dependency + system health check |
| `nyxniri deps` | Open dependency check & install menu |
| `nyxniri apps` | Category-grouped recommended apps installer (Brave, Steam, WeChat, ...) |
| `nyxniri wallpapers` | Download the full wallpaper & video pack from the external repo |
| `nyxniri theme [toggle\|dark\|light\|sync\|status]` | Switch or sync system dark/light theme |
| `nyxniri bug` / `nyxniri report` | Generate diagnostic bug report |

**Uninstall**

| Command | Description |
| :--- | :--- |
| `nyxniri uninstall [--all\|standard\|restore\|purge]` | Checkbox uninstall — pick what to remove (configs, CLI, modules, snapshots, wallpapers); defaults to the standard range |
| `nyxniri purge` | Shorthand for `uninstall --all` |

**Extensions**

| Command | Description |
| :--- | :--- |
| `nyxniri fcitx [install\|status\|uninstall]` | NyxMellow fcitx5 skin |
| `nyxniri greeter [install\|status\|uninstall]` | Noctalia Greeter (login screen) |
| `nyxniri gtk [install\|status\|uninstall]` | Material You GTK3/4 theme |
| `nyxniri fisher [install\|status\|uninstall]` | fisher plugin manager for Fish |

`nyxhelp` is a compact fzf-based reference for the CLI, shell helpers, and core keybindings:

| Command | Description |
| :--- | :--- |
| `nyxhelp` | Interactive dual-panel cheatsheet |
| `nyxhelp keys` | Niri keybindings |
| `nyxhelp proxy` | Proxy controls (`proxy_on [port]`, `proxy_off`, `proxy_status`) |
| `nyxhelp pkg` | Package shortcuts (`up`, `in`, `se`, `un`, `clean`) |
| `nyxhelp all` | Full cheatsheet |

## Troubleshooting

<details>
<summary><b>Noctalia hangs on startup</b> — <code>ddcutil</code> can time out scanning the I2C bus (common on NVIDIA).</summary>

Disable `ddcutil` in `~/.config/noctalia/noctalia-config.toml`:

```toml
[brightness]
enable_ddcutil = false
```

Brightness keys still work: internal panels go through Noctalia backlight, external monitors keep the `ddcutil` fallback. Leave this setting off unless you want Noctalia itself to own DDC.

</details>

<details>
<summary><b>Plugin repo corrupted</b> — Noctalia hangs while checking out plugins.</summary>

Run the following commands to reset the plugin repos:

```bash
git -C ~/.local/state/noctalia/plugins/sources/community/repo reset --hard HEAD
git -C ~/.local/state/noctalia/plugins/sources/official/repo reset --hard HEAD
```

</details>

<details>
<summary><b>Greeter sync asks for a password</b> — add a Polkit rule (<code>nyxniri greeter install</code> does this for you).</summary>

Install the Polkit rule manually if needed:

```bash
sudo bash -c 'cat > /etc/polkit-1/rules.d/50-noctalia-greeter.rules << EOF
polkit.addRule(function(action, subject) {
    if (action.id == "org.noctalia.greeter.apply-appearance" &&
        subject.isInGroup("wheel")) {
        return polkit.Result.YES;
    }
});
EOF'
```

</details>

<details>
<summary><b>Nautilus or Libadwaita apps stuck in light mode</b> — leftover user CSS overrides dark mode.</summary>

If Noctalia's built-in GTK templates or old tools generated `noctalia.css` or `gtk.css` in `~/.config/gtk-4.0/`, GTK4 forces those CSS color definitions over system dark mode.

Run theme sync or remove the stale override files:

```bash
nyxniri theme sync
# Or manually:
rm -f ~/.config/gtk-4.0/gtk.css ~/.config/gtk-4.0/noctalia.css ~/.config/gtk-3.0/gtk.css ~/.config/gtk-3.0/noctalia.css
```

</details>

<details>
<summary><b>Brave doesn't follow theme toggle</b> — Brave cold-start bug (not a NyxNiri issue).</summary>

On non-GNOME Wayland compositors, Brave's portal theme-signal subscription fails to initialize on cold start, so `nyxniri theme toggle` doesn't recolor it. Open `brave://settings/appearance` and switch theme mode once (e.g. Classic → GTK → Classic) to wake it up; it follows live afterwards without restarting Brave. Needs re-waking after each Brave restart.

</details>

## Credits

**Contact & Community:**

- Telegram Channel: [@linux_ricing](https://t.me/linux_ricing)
- QQ: `2040244628` · Linux Ricing Group: `631425889`
- Sponsor: [Afdian](https://afdian.com/a/Echoes678) · Bug reports: [GitHub Issues](https://github.com/ech678/NyxNiri/issues)

**Special Thanks & Contributors:**

- [@zhuhuaian](https://github.com/zhuhuaian), [@Krits03](https://github.com/Krits03), [@Yulljie](https://github.com/Yulljie) — community management & support
- [@TyhLxxxhLrqTq](https://github.com/TyhLxxxhLrqTq) — companion wallpaper site (in development)

**Thanks to:**

- [RanXOM/glassy-niri](https://github.com/RanXom/glassy-niri) — blur effects reference
- [SHORiN-KiWATA/shorin-niri](https://github.com/SHORiN-KiWATA/shorin-niri) — heavily referenced
- [sanweiya/fcitx5-mellow-themes](https://github.com/sanweiya/fcitx5-mellow-themes) — mellow shape source for NyxMellow skin
- [StarWhiteIsBusy/Round-Simple-Fcitx5-Skin](https://github.com/StarWhiteIsBusy/Round-Simple-Fcitx5-Skin) — Noctalia color-sync pattern reference
- [doctorlogix](https://github.com/doctorlogix) — website design inspiration

**Recommended:**

- [h465855hgg/noctalia-lyrics](https://github.com/h465855hgg/noctalia-lyrics) — status bar lyrics widget
- [Ocfeather/chrome-niri-opacity](https://github.com/Ocfeather/chrome-niri-opacity) — browser opacity script

---

<div align="right">
  <a href="#readme-top">↑ Back to Top</a>
</div>
