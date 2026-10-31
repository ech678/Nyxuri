<a id="readme-top"></a>

<div align="right">
  <strong>English</strong> | <a href="README.zh-CN.md">简体中文</a>
</div>

<div align="center">

<h1>Nyxuri</h1>

<p><strong>/nɪkˈsuːri/ · A modular desktop configuration system for Arch / CachyOS</strong><br />
<sub>Supports Niri and Noctalia — take it easy, snap your setup together, and enjoy.</sub></p>

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

> ⚠️ **Under Heavy Development**: The `main` branch is actively undergoing refactoring and rapid evolution. For a stable daily experience, checking out the latest release tag is recommended.
>
> Upgrading from **NyxNiri**? The project is rebranded to **Nyxuri** (/nɪkˈsuːri/) — no longer just a rigid set of configs, but an evolving modular desktop configuration system. Running `nyxuri` automatically migrates your existing configs, snapshots, and state, then safely cleans up legacy paths.
>
> **Note:** The built-in **Nyxuri Shell** is experimental — fully in development, known to be buggy, its look is unfinished, and it is not recommended for daily use yet. Stay on Noctalia; `nyxuri shell` is for testing only. Known issues: [shell/KNOWN-ISSUES.md](shell/KNOWN-ISSUES.md).

### The Story Behind the Name

Pronounced `/nɪkˈsuːri/`, it's a quiet blend of things we love:

- **Nyx**: Night, calmness, and a fond nod to the project's roots as *NyxNiri*.
- **Yukkuri** (「ゆっくり」): **Take it easy**. Ricing your Linux desktop should be a fun, relaxing journey — never a source of stress.
- **Yuri** (「百合」): Pure, gentle everyday connections (a little personal affection from the author).
- **...And "URI"?**: We once jokingly called it "Unified Runtime Interface" in architectural notes to sound fancy... forget that! It's honestly just here because the syllables sound so soft and sweet together (⁄ ⁄•⁄ω⁄•⁄ ⁄).

## What is Nyxuri?

In short, **Nyxuri is a modular desktop configuration system and management engine for Arch / CachyOS**.

We are committed to long-term support for dual desktop shells (the polished **Noctalia** and our in-house **Nyxuri Shell** in active incubation), debuting on Niri and progressively expanding to more window managers. Adhering to a strict **zero-bloat, transparent, and zero-residue** philosophy, it provides:

- **Multi-WM & Dual Shell Architecture**: Actions dispatch through a decoupled `shell-action.sh` gateway; natively supports **Niri** (scrolling layout) and **MangoWM** (with more Wayland compositors coming), allowing seamless transitions between Noctalia and Nyxuri Shell.
- **Global Theme & Palette Sync**: Wallpaper sampling (with video frame extraction) drives Material You palettes across GTK 3/4, XDG Portal, Kitty, web browsers, and desktop shells in lockstep.
- **Noctalia Companion Tools (Noctalia Tools)**:
  - **Orbit Launcher** (`Super+A` / Mouse Forward): Vector radial menu for apps, bookmarks, and search/AI dials (TOML-configurable).
  - **Wallpaper Picker** (`Super+W`): Unified static and live video wallpaper selector with live preview.
  - **Selection Translate**: Fast popup translation for highlighted text.
  - **Eye Care** (`Super+N`) & **Scratchpad** (`Super+~` drop-down Kitty floating terminal).
- **NyxMellow Input Skin**: Dynamic theme-synced Fcitx5 skin with mellow geometry, bundled with a tuned Rime setup.
- **Modern Terminal Experience**: Kitty terminal optimizations (smooth cursor trails, clipboard-preserving shortcuts), paired with Fish aliases and Starship prompt.
- **Modular Plugins**: Fastfetch, Noctalia Greeter login screen, Zed config, and wallpapers toggle independently anytime (`nyxuri on` / `nyxuri off`), incurring zero background overhead when inactive.
- **Atomic Deployment, Presets & Zero Bloat**:
  - **Dunder Protocol**: Any file or directory containing `__custom__` (e.g. `__custom__.kdl`, `__custom__.conf`) and `monitor.kdl` is permanently preserved across updates and preset swaps.
  - **Presets**: Easily switch application flavor presets (e.g. Kitty opacity variants) or create custom private presets.
  - **Zero Bloat & Clean State**: Pure Python standard library with zero pip dependencies; disabling a plugin wipes deployed files with zero residue; 30-roll automatic snapshots with instant rollback, and `nyxuri doctor` for status audits.

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

### From AUR

```bash
paru -S nyxuri-git
```

If no AUR helper is installed in your system, build and install the `nyxuri-git` package manually:

```bash
# clone PKGBUILD repository
git clone https://aur.archlinux.org/nyxuri-git.git

# build & install
cd nyxuri-git && makepkg -si
```

## Architecture & Plugins

```text
Nyxuri
├── install.sh                  # lightweight bootstrap entrypoint
├── catalog.toml                # package catalogue (18 standalone apps without dotfiles)
├── nyxuri/                     # Python core engine (zero pip dependencies)
├── shell/                      # Nyxuri Shell (QML/Qt6 desktop shell, experimental)
└── plugins/                    # 13 modular desktop plugins
    ├── fastfetch/              # system information
    ├── fcitx5-rime/            # dynamic Material You input skin & Rime config
    ├── fish/                   # shell aliases & functions
    ├── greeter/                # Noctalia Greeter login integration
    ├── kitty/                  # terminal emulator & opacity presets
    ├── mango/                  # MangoWM window manager & session scripts
    ├── niri/                   # window manager & session scripts
    ├── noctalia/               # desktop shell, theme sync, Orbit & wallpaper picker
    ├── starship/               # prompt styling
    ├── theme/                  # shared matugen theme template pool
    ├── wallpapers/             # companion wallpapers & video pack hooks
    ├── xdg-desktop-portal/     # portal routing (theme sync, screencast)
    └── zed/                    # editor configuration
```

Configs deploy atomically. Personal tweaks survive updates via the Dunder protocol: any file or folder containing `__custom__` (e.g. `__custom__.kdl`, `__custom__.conf`) and `monitor.kdl` are preserved.

For detailed customization rules and hooks, see [Configuration Guide (Wiki)](https://github.com/ech678/Nyxuri/wiki/Configuration).

## Presets

Presets layer between defaults and your `__custom__` files, so switching never touches your own tweaks. Supports modular Parts slots.

See full official preset list, Parts architecture, and private preset setup in [Presets Guide (Wiki)](https://github.com/ech678/Nyxuri/wiki/Presets).

## Keybindings

Core keybindings dispatch through `shell-action.sh`. Quick reference: `nyxhelp keys`.

See complete window navigation and monitor moving shortcuts in [Keybindings (Wiki)](https://github.com/ech678/Nyxuri/wiki/Keybindings).

## Plugins & Capabilities

Desktop capabilities are atomic, modular plugins. Optional plugins include dynamic Material You fcitx5 input skin (`fcitx5-rime`), companion wallpaper and video pack (`wallpapers`), and Noctalia Greeter login screen (`greeter`). Toggle them on or off anytime: `nyxuri on <plugin>` / `nyxuri off <plugin>`.

For unit lifecycle commands, see [CLI Reference (Wiki)](https://github.com/ech678/Nyxuri/wiki/CLI-Reference#units-the-market-verbs).

## Tooling

`nyxuri` manages install, update, snapshots, and diagnostics. Use `nyxhelp` in terminal for instant cheatsheet lookup.

See full command matrix and options in [CLI Reference (Wiki)](https://github.com/ech678/Nyxuri/wiki/CLI-Reference).

## Troubleshooting

When encountering issues, run `nyxuri doctor` first.

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
