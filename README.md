<a id="readme-top"></a>

<div align="right">
<strong>English</strong> | <a href="README.zh-CN.md">简体中文</a>
</div>

<div align="center">

<h1>Nyxuri</h1>

<p><strong>A plugin-based desktop setup system for Arch-based distros</strong><br />
<sub>Material Design & take it easy, build your own clean daily setup (ゆっくりしていってね！)</sub></p>

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
<sub><em><a href="https://nyxniri.com">Website</a> · Watch <a href="https://www.bilibili.com/video/BV1c63n6dEEG">Bilibili Demo</a> · Join <a href="https://www.reddit.com/r/niri/comments/1vf53le/nyxniri_a_material_you_desktop_config_for_niri/">Reddit Discussion</a> · Read the <a href="https://github.com/ech678/Nyxuri/wiki/Home">Wiki</a></em></sub>
</p>
<br />

</div>

> **Things to note**: The `main` branch is under heavy, fast-moving development right now. If you want something stable — please stick to the latest Release~ (Also, our own Shell is nowhere near finished yet; both its look and structure will change a lot, so it's not recommended for daily use yet)

### The Little Secret Behind the Name

Pronounced `/nɪkˈsuːri/`, the name is a mashup of a few things I really like:

- **Nyx**: Goddess of the night, keeping you company through quiet nights (and a nod to the old name, NyxNiri).
- **Yukkuri** (ゆっくり / にゅっくり): **Take it easy, take your time tinkering**.
- **Yuri** (百合 / ゆり): Pure, sweet everyday life and the bonds between girls (a little personal bias from the author).
- **…As for URI?**: Earlier on, I made up a fancy-sounding backronym in the architecture docs called "Unified Runtime Interface"... just forget about it~! QWQ

## What is Nyxuri

Simply put, **Nyxuri is a plugin-based desktop config system for Arch-based distros**.
Our philosophy is to be as transparent as possible and give users full control and choice. And since I love tinkering, I packed in a bunch of fun features while keeping things as clean and simple as I could:

- **Multi-WM Support**: Right now we support Niri and MangoWM (and maybe Hyprland later!?). We built a small bridge for keybind actions between different WMs and Shells, making it super easy to switch between them!
- **Multi-Shell Support**: Currently we actively maintain configs for Noctalia V5 alongside our own custom Shell.
- **Nyxuri Shell**: Our own Shell (built on Quickshell), currently in development. It uses a plugin-based design, so it definitely won't get bloated like other Quickshell setups.
- **Global Monet Color Generation**: Generates Monet (Material You) color schemes from both static and live video wallpapers across almost your whole system (Shell, GTK themes, kitty, fcitx5... and lots more). Plus, Nyxuri Shell can directly use Noctalia V5's third-party app color templates!
- **Rich Plugins (Dotfiles)**: NyxMellow (fcitx5 input method theme), Fastfetch dashboard, Kitty, Starship, Noctalia Greeter login screen, Zed editor, wallpaper packs... When disabled, nothing runs in the background — zero overhead.
- **Good User Experience**
  - **Never overwrites your custom changes**: Any file with `__custom__` in its name (like `__custom__.kdl`, `__custom__.conf`) or your display config `monitor.kdl` is automatically kept safe across updates and preset switches!
  - **Easy preset switching**: Switch between presets (like Kitty transparency levels) in one command, or write your own presets to play around with.
  - **Clean with no leftover junk**: The management tool is written purely with Python's standard library — no need to install a pile of pip dependencies. Turning off a plugin cleans up its configs neatly, plus you get 30 rolling backup snapshots and a `nyxuri doctor` checkup tool.

<details>
<summary>Also made some extra little tools for Noctalia~</summary>

- **Orbit Launcher**: Vector ring menu with quick access to favorite apps, web links, and an AI/search wheel (fully customizable via TOML).
- **Wallpaper Picker**: Unified search and live preview for both static images and live video wallpapers.
- **Pop-up Translator**: Select any text to get a quick, lightweight translation pop-up.
- **Night Light** & **Scratchpad** (`Super+~` floating Kitty terminal).
</details>

## Installation

### From Git Repo (Recommended)

```bash
# Shallow clone: grabs only the latest snapshot; drop --depth 1 if you want full git history
git clone --depth 1 https://github.com/ech678/Nyxuri.git ~/Nyxuri
cd ~/Nyxuri && ./install.sh
```

### Standalone Online Install

```bash
curl -fsSL --connect-timeout 10 https://raw.githubusercontent.com/ech678/Nyxuri/main/install.sh | bash
```

> [!TIP]
> Works out of the box with Shelly, paru, and yay; if none are installed, `nyxuri install full` will automatically set up `paru` for you.

### From AUR

```bash
paru -S nyxuri-git
```

If you don't have an AUR helper installed yet, you can build and install `nyxuri-git` manually:

```bash
# Clone the PKGBUILD repo
git clone https://aur.archlinux.org/nyxuri-git.git

# Build and install
cd nyxuri-git && makepkg -si
```

## Directory Structure

```text
Nyxuri
├── install.sh                  # Bootstrap install script
├── nyxuri/                     # Core Python management scripts (zero pip dependencies)
├── shell/                      # Nyxuri Shell (in-house QML/Qt6 desktop shell, experimental)
└── plugins/                    # Standalone plugin configs
    ├── fastfetch/              # System info display
    ├── fcitx5-rime/            # Dynamic color input method theme & config
    ├── fish/                   # Shell aliases & handy helper functions
    ├── greeter/                # Noctalia Greeter login screen
    ├── kitty/                  # Terminal config & transparency presets
    ├── mango/                  # MangoWM window manager config
    ├── niri/                   # Niri window manager config
    ├── noctalia/               # Noctalia shell, theme sync & extra tools
    ├── starship/               # Shell prompt
    ├── theme/                  # Shared matugen color templates
    ├── wallpapers/             # Companion wallpapers & video download scripts
    ├── xdg-desktop-portal/     # Portal config files
    └── zed/                    # Code editor config
```

As long as you put your personal tweaks inside files or folders with `__custom__` in the name (like `__custom__.kdl` or `__custom__.conf`), or in `monitor.kdl`, they'll stay untouched when updating and won't get overwritten.

For more details on custom rules, check out [Configuration & Customization (Wiki)](https://github.com/ech678/Nyxuri/wiki/Configuration).

## Presets

Presets sit right between the default configs and your `__custom__` files, so switching presets won't mess up your own edits. You can also mix and match different parts like building blocks.

For the preset list and how to make your own, see the [Presets Guide (Wiki)](https://github.com/ech678/Nyxuri/wiki/Forms).

## Keybindings

Common keybinds are routed through the `shell-action.sh` script, so you don't have to relearn a whole new set of keys when switching WMs or Shells. If you forget a keybind, just run `nyxhelp keys` in the terminal.

For the full list of keybinds, see the [Keybindings Overview (Wiki)](https://github.com/ech678/Nyxuri/wiki/Keybindings).

## Toggling Plugins & CLI Tool

Every desktop component is an independent plugin — like the Fcitx5 theme (`fcitx5-rime`), wallpaper pack (`wallpapers`), login screen (`greeter`), and so on. To turn any of them on or off, just run `nyxuri on <plugin>` or `nyxuri off <plugin>`.

Installing, updating, rolling back backups, and checking for issues are all handled by the `nyxuri` command. Type `nyxhelp` in your terminal for a quick cheat sheet. For all commands and details, check the [CLI Reference (Wiki)](https://github.com/ech678/Nyxuri/wiki/CLI-Reference).

## Troubleshooting

If you can't get into the desktop, run into dual-GPU display glitches, or themes aren't applying properly, try running `nyxuri doctor` first to see what's up.

For common issues and fixes, check the [Troubleshooting Guide (Wiki)](https://github.com/ech678/Nyxuri/wiki/Troubleshooting).

## Community

**Chat & Feedback:**

* TG Channel: [@linux_ricing](https://t.me/linux_ricing)
* QQ: `2040244628` · Linux Ricing Group: `631425889`
* Sponsor: [Afdian](https://afdian.com/a/Echoes678) · Bug Reports: [GitHub Issues](https://github.com/ech678/Nyxuri/issues)

**Thanks:**

* [@zhuhuaian](https://github.com/zhuhuaian) · [@Krits03](https://github.com/Krits03) · [@TyhLxxxhLrqTq](https://github.com/TyhLxxxhLrqTq) · [@Yulljie](https://github.com/Yulljie) — Helped me out with so much odd work~❤️
* [RanXOM/glassy-niri](https://github.com/RanXOM/glassy-niri) — Reference for blur effects
* [SHORiN-KiWATA/shorin-niri](https://github.com/SHORiN-KiWATA/shorin-niri) — Copied a ton from here!
* [sanweiya/fcitx5-mellow-themes](https://github.com/sanweiya/fcitx5-mellow-themes) — Rounded corner shapes for the NyxMellow skin
* [StarWhiteIsBusy/Round-Simple-Fcitx5-Skin](https://github.com/StarWhiteIsBusy/Round-Simple-Fcitx5-Skin) — NyxMellow reference
* [doctorlogix](https://github.com/doctorlogix) — Website design inspiration

**Recommended Projects:**

* [h465855hgg/noctalia-lyrics](https://github.com/h465855hgg/noctalia-lyrics) — Status bar lyrics widget
* [Ocfeather/chrome-niri-opacity](https://github.com/Ocfeather/chrome-niri-opacity) — Browser transparency script

---

<div align="right">
<a href="#readme-top">↑ Back to top</a>
</div>
