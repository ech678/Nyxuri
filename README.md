<a id="readme-top"></a>

<div align="right">
  <strong>English</strong> | <a href="README.zh-CN.md">简体中文</a>
</div>

<div align="center">

<h1>Nyxuri</h1>

<p><strong>/nɪkˈsuːri/ · A Material You desktop experience for Arch / CachyOS</strong><br />
<sub>Built on Niri and Noctalia V5 — and stays out of your way.</sub></p>

<p>
  <a href="https://github.com/ech678/Nyxuri/stargazers"><img height="22" src="https://m3-markdown-badges.vercel.app/stars/3/3/ech678/Nyxuri" alt="Stars" /></a>
  &nbsp;
  <a href="https://archlinux.org"><img height="22" src="https://ziadoua.github.io/m3-Markdown-Badges/badges/Arch/arch2.svg" alt="Arch Linux" /></a>
  &nbsp;
  <a href="LICENSE"><img height="22" src="https://ziadoua.github.io/m3-Markdown-Badges/badges/LicenceGPLv3/licencegplv33.svg" alt="GPL-3.0" /></a>
</p>

<a href="https://github.com/user-attachments/assets/9ef4da30-54c0-491b-916f-2f2a3beac6be">
  <img src="https://github.com/user-attachments/assets/9ef4da30-54c0-491b-916f-2f2a3beac6be" alt="Nyxuri Preview" width="92%" />
</a>

<p>
  <sub><em><a href="https://nyxniri.com">Website</a> · Watch demo on <a href="https://www.bilibili.com/video/BV1c63n6dEEG">Bilibili</a> · Join discussion on <a href="https://www.reddit.com/r/niri/comments/1vf53le/nyxniri_a_material_you_desktop_config_for_niri/">Reddit</a> · Read <a href="https://github.com/ech678/Nyxuri/wiki/Home">Wiki</a></em></sub>
</p>
<br />

</div>

> Upgrading from **NyxNiri**? The project is rebranded to **Nyxuri** (/nɪkˈsuːri/) as we expand toward a custom desktop shell and multi-window manager support. Running `nyxuri` automatically migrates your existing configs, snapshots, and state, then safely cleans up legacy paths.

## Features

- **Wallpaper Picker** (`Super+W`) — static + live, search and categories.
- **Color Sync** — Noctalia V5 extracts palettes from wallpaper; `mpvpaper` + `ffmpeg` for video frames.
- **Light/Dark Sync** — GTK 3/4, XDG portal, Kitty, and browsers switch together.
- **Eye Care** (`Super+N`) — warmer color temperature, no blur, opaque windows.
- **Scratchpad** (`Super+~`) — persistent Kitty floating terminal.
- **Orbit Launcher** (`Super+A` / `Super+MouseForward`) — vector radial; apps, tools, links, AI/search dial (TOML-configurable).
- **Shell & Terminal** — Fish aliases for proxy/cache, Kitty cursor trails, Windows-familiar shortcuts (smart Ctrl+C/Ctrl+V, right-click paste, selection without overriding clipboard).
- **NyxMellow** — dynamic fcitx5 skin: mellow geometry + Noctalia Material You palette.
- **Presets** — per-app flavor variants (e.g. kitty transparent); switch with one command, save your setup as a private preset, or edit it in `$EDITOR`.

## Install

### From a git checkout (recommended)

```bash
# shallow clone: latest snapshot only; drop --depth 1 for full history
git clone --depth 1 https://github.com/ech678/Nyxuri.git ~/Nyxuri
cd ~/Nyxuri && ./install.sh
```

### Standalone (online)

```bash
curl -fsSL --connect-timeout 10 https://raw.githubusercontent.com/ech678/Nyxuri/main/install.sh | bash
```

> [!TIP]
> Auto-detects Shelly, paru, and yay; if none are installed, `nyxuri install full` automatically bootstraps `paru`.

<details>
<summary>Mirrors for China (gh-proxy / CDN)</summary>

```bash
# Standalone via gh-proxy.org
curl -fsSL --connect-timeout 10 https://gh-proxy.org/https://raw.githubusercontent.com/ech678/Nyxuri/main/install.sh | bash

# git clone via gh-proxy.org
git clone --depth 1 https://gh-proxy.org/https://github.com/ech678/Nyxuri.git ~/Nyxuri
cd ~/Nyxuri && ./install.sh
```
</details>

## Included Configs

```text
Nyxuri
├── install.sh                  # lightweight bootstrap entrypoint
├── nyxuri/                     # Python core engine (zero pip dependencies)
├── assets/                     # static assets (wallpapers, fcitx5 skin templates)
└── configs/
    ├── niri/                   # window manager (.kdl, .toml)
    │   └── scripts/            # glue scripts & action gateways
    ├── noctalia/               # shell + theme sync & companion tools (Orbit, wallpaper picker)
    ├── xdg-desktop-portal/     # portal routing (Settings / screencast)
    ├── kitty/                  # terminal
    ├── fish/                   # aliases + functions
    ├── fastfetch/              # system info
    ├── zed/                    # editor
    └── starship.toml           # prompt
```

Configs deploy atomically. Personal tweaks survive updates via the Dunder protocol: any file or folder containing `__custom__` (e.g. `__custom__.kdl`, `__custom__.conf`) and `monitor.kdl` are preserved.

For detailed customization rules and post-deploy hooks, see [Configuration Guide (Wiki)](https://github.com/ech678/Nyxuri/wiki/Configuration).

## Presets

Presets layer between defaults and your `__custom__` files, so switching never touches your own tweaks. Supports modular Parts slots.

See full official preset list, Parts architecture, and private preset setup in [Presets Guide (Wiki)](https://github.com/ech678/Nyxuri/wiki/Presets).

## Keybindings

Core keybindings dispatch through `shell-action.sh`. Quick reference: `nyxhelp keys`.

See complete window navigation and monitor moving shortcuts in [Keybindings (Wiki)](https://github.com/ech678/Nyxuri/wiki/Keybindings).

## Extensions

Optional extensions include dynamic Material You fcitx5 skin (NyxMellow), companion wallpaper and video pack, and greetd login screen matching Noctalia.

For extension setup and lifecycle commands, see [Extensions Guide (Wiki)](https://github.com/ech678/Nyxuri/wiki/CLI-Reference#extensions).

## Tooling

`nyxuri` manages install, update, snapshots, and diagnostics. Use `nyxhelp` in terminal for instant cheatsheet lookup.

See full command matrix and options in [CLI Reference (Wiki)](https://github.com/ech678/Nyxuri/wiki/CLI-Reference).

## Troubleshooting

When encountering issues, run `./install.sh doctor` first.

See full diagnostic guides and step-by-step solutions in [Troubleshooting (Wiki)](https://github.com/ech678/Nyxuri/wiki/Troubleshooting).

## Credits

**Contact & Community:**
- Telegram Channel: [@linux_ricing](https://t.me/linux_ricing)
- QQ: `2040244628` · Linux Ricing Group: `631425889`
- Sponsor: [Afdian](https://afdian.com/a/Echoes678) · Bug reports: [GitHub Issues](https://github.com/ech678/Nyxuri/issues)

**Special Thanks & Contributors:**
- [Google Gemini](https://deepmind.google/technologies/gemini/) — burned through a pile of free Google tokens
- [@zhuhuaian](https://github.com/zhuhuaian), [@Krits03](https://github.com/Krits03), [@Yulljie](https://github.com/Yulljie) — community management & support
- [@TyhLxxxhLrqTq](https://github.com/TyhLxxxhLrqTq) — companion wallpaper site (in development)

**Thanks to:**
- [RanXOM/glassy-niri](https://github.com/RanXOM/glassy-niri) — blur effects reference
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
