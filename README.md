<a id="readme-top"></a>

<div align="right">
<strong>English</strong> | <a href="README.zh-CN.md">简体中文</a>
</div>

<div align="center">

<h1>Nyxuri</h1>

<p><strong>A plugin-based desktop setup system for Arch-based distros</strong><br />
<sub>Take it easy, build your own clean daily setup. ゆっくりしていってね！</sub></p>

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
<a href="https://nyxniri.com">Website</a> · <a href="https://www.bilibili.com/video/BV1c63n6dEEG">Demo</a> · <a href="https://www.reddit.com/r/niri/comments/1vf53le/nyxniri_a_material_you_desktop_config_for_niri/">Reddit</a> · <a href="https://github.com/ech678/Nyxuri/wiki/Home">Wiki</a>
</p>

</div>

Nyxuri manages the pile of configs that make up a desktop: WM, shell, input method skin, terminal… Each one is a plugin you turn on or off on its own, and turning it off takes its files with it. I want it to be transparent: it tells you what it'll change before it does, and `nyxuri doctor` shows you where things drifted.

## Features

<table>
<tr>
<td width="50%" valign="top">
<strong>Multi-WM</strong><br />
Niri and MangoWM for now. Keybinds go through one action bridge, so switching WM or shell doesn't mean relearning your keys.
</td>
<td width="50%" valign="top">
<strong>Multi-Shell</strong><br />
Noctalia V5, plus Nyxuri Shell: our own, built on Quickshell, plugin-based, still early.
</td>
</tr>
<tr>
<td width="50%" valign="top">
<strong>Monet everywhere</strong><br />
Colors pulled from static or video wallpapers and applied to the shell, GTK, kitty, fcitx5 and more. Nyxuri Shell can use Noctalia V5's app templates too.
</td>
<td width="50%" valign="top">
<strong>Plugins all the way</strong><br />
NyxMellow skin, Fastfetch, Kitty, Starship, Greeter, Zed, wallpapers… A plugin you haven't turned on doesn't run.
</td>
</tr>
<tr>
<td width="50%" valign="top">
<strong>Your edits stay</strong><br />
Files named <code>__custom__</code> and <code>monitor.kdl</code> survive updates. Forms, like Kitty's transparency levels, switch in one command.
</td>
<td width="50%" valign="top">
<strong>Clean exit</strong><br />
Pure Python standard library, no pip. Turning a plugin off cleans up after it, and snapshots let you roll back.
</td>
</tr>
</table>

<details>
<summary>Extra tools for Noctalia</summary>

- **Orbit Launcher**: a vector ring menu for favorite apps, web links, and an AI/search wheel, all configurable in TOML.
- **Wallpaper Picker**: search and live preview for both static images and video wallpapers.
- **Pop-up Translator**: select any text and get a quick translation.
- **Night Light** and **Scratchpad**: <kbd>Super</kbd> + <kbd>~</kbd> drops down a floating Kitty terminal.

</details>

## Installation

> [!WARNING]
> `main` moves fast right now. If you want something stable, use the latest [Release](https://github.com/ech678/Nyxuri/releases). Nyxuri Shell is far from finished, and both its look and structure will still change a lot, so don't daily-drive it yet.

**From the Git repo (recommended)**

```bash
# Shallow clone: grabs only the latest snapshot; drop --depth 1 if you want full git history
git clone --depth 1 https://github.com/ech678/Nyxuri.git ~/Nyxuri
cd ~/Nyxuri && ./install.sh
```

**Standalone online install**

```bash
curl -fsSL --connect-timeout 10 https://raw.githubusercontent.com/ech678/Nyxuri/main/install.sh | bash
```

> [!TIP]
> Works out of the box with Shelly, paru, and yay. If none are installed, `nyxuri install full` sets up `paru` for you.

**From the AUR**

```bash
paru -S nyxuri-git
```

<details>
<summary>No AUR helper yet? Build it by hand</summary>

```bash
# Clone the PKGBUILD repo
git clone https://aur.archlinux.org/nyxuri-git.git

# Build and install
cd nyxuri-git && makepkg -si
```

</details>

## Usage

Everything goes through one command:

```bash
nyxuri list                    # every plugin and its state
nyxuri on <plugin>             # turn a plugin on
nyxuri off <plugin>            # turn it off and clean up
nyxuri use <plugin> <form>     # switch forms
nyxuri doctor                  # check what's off
nyxhelp                        # cheat sheet (nyxhelp keys for keybinds)
```

> [!NOTE]
> Put your own tweaks in files or folders with `__custom__` in the name (like `__custom__.kdl` or `__custom__.conf`), or in `monitor.kdl`. Updates and form switches never touch them.

## Documentation

| Topic | What's in it |
| :--- | :--- |
| [Configuration](https://github.com/ech678/Nyxuri/wiki/Configuration) | How plugins are laid out, and how your edits are kept |
| [Forms](https://github.com/ech678/Nyxuri/wiki/Forms) | Built-in forms, slot axes, making your own |
| [Keybindings](https://github.com/ech678/Nyxuri/wiki/Keybindings) | Every key, and how the action bridge works |
| [CLI Reference](https://github.com/ech678/Nyxuri/wiki/CLI-Reference) | All commands |
| [Troubleshooting](https://github.com/ech678/Nyxuri/wiki/Troubleshooting) | Can't reach the desktop, dual-GPU glitches, themes not applying |

## Community

**Chat**: Telegram [@linux_ricing](https://t.me/linux_ricing) · QQ group `631425889` · Author's QQ `2040244628`<br />
**Feedback & support**: [GitHub Issues](https://github.com/ech678/Nyxuri/issues) · [Afdian](https://afdian.com/a/Echoes678)

## Thanks

Special thanks to these folks for helping me out with so much odd work~❤️

<p>
<a href="https://github.com/zhuhuaian"><img src="https://images.weserv.nl/?url=github.com/zhuhuaian.png&w=128&h=128&fit=cover&mask=circle" width="64" height="64" alt="@zhuhuaian" title="@zhuhuaian" /></a>
<a href="https://github.com/Krits03"><img src="https://images.weserv.nl/?url=github.com/Krits03.png&w=128&h=128&fit=cover&mask=circle" width="64" height="64" alt="@Krits03" title="@Krits03" /></a>
<a href="https://github.com/TyhLxxxhLrqTq"><img src="https://images.weserv.nl/?url=github.com/TyhLxxxhLrqTq.png&w=128&h=128&fit=cover&mask=circle" width="64" height="64" alt="@TyhLxxxhLrqTq" title="@TyhLxxxhLrqTq" /></a>
<a href="https://github.com/Yulliil"><img src="https://images.weserv.nl/?url=avatars.githubusercontent.com/u/78137234&w=128&h=128&fit=cover&mask=circle" width="64" height="64" alt="@Yulliil" title="@Yulliil" /></a>
<a href="https://github.com/StarWhiteIsBusy"><img src="https://images.weserv.nl/?url=github.com/StarWhiteIsBusy.png&w=128&h=128&fit=cover&mask=circle" width="64" height="64" alt="@StarWhiteIsBusy" title="@StarWhiteIsBusy" /></a>
</p>

And everyone who has contributed:

<p>
<a href="https://github.com/ech678/Nyxuri/graphs/contributors"><img src="https://contrib.rocks/image?repo=ech678/Nyxuri" alt="Contributors" /></a>
</p>

**Borrowed from**

- [RanXOM/glassy-niri](https://github.com/RanXOM/glassy-niri): blur effects
- [SHORiN-KiWATA/shorin-niri](https://github.com/SHORiN-KiWATA/shorin-niri): copied a ton from here!
- [sanweiya/fcitx5-mellow-themes](https://github.com/sanweiya/fcitx5-mellow-themes): NyxMellow's rounded corners
- [StarWhiteIsBusy/Round-Simple-Fcitx5-Skin](https://github.com/StarWhiteIsBusy/Round-Simple-Fcitx5-Skin): NyxMellow reference
- [doctorlogix](https://github.com/doctorlogix): website design inspiration

<details>
<summary>The little secret behind the name</summary>

Pronounced `/nɪkˈsuːri/`, it's a mashup of a few things I really like:

- **Nyx**: goddess of the night, company for quiet nights (and a nod to the old name, NyxNiri).
- **Yukkuri** (ゆっくり / にゅっくり): take it easy, take your time tinkering.
- **Yuri** (百合 / ゆり): sweet everyday life and the bonds between girls (a little personal bias from the author).
- **…URI?** Early on I made up a fancy backronym in the architecture docs, "Unified Runtime Interface". Just forget about it~ QWQ

</details>

---

<div align="right">
<a href="#readme-top">↑ Back to top</a>
</div>
