```text
Nyxuri
├── install.sh                  # lightweight bootstrap entrypoint
├── nyxuri/                     # Python core engine (zero pip dependencies)
├── shell/                      # Nyxuri Shell (QML/Qt6 desktop shell, experimental)
└── plugins/                    # everything is a plugin: capability × supply
    ├── fastfetch/              # system information
    ├── fcitx5-rime/            # dynamic Material You input skin & Rime config
    ├── fish/                   # shell aliases & functions
    ├── greeter/                # Noctalia Greeter login integration
    ├── kitty/                  # terminal emulator & opacity forms
    ├── mango/                  # MangoWM window manager & session scripts
    ├── niri/                   # window manager & session scripts
    ├── noctalia/               # desktop shell, theme sync, Orbit & wallpaper picker
    ├── starship/               # prompt styling
    ├── theme/                  # shared matugen theme template pool
    ├── wallpapers/             # companion wallpapers & video pack hooks
    ├── xdg-desktop-portal/     # portal routing (theme sync, screencast)
    ├── zed/                    # editor configuration
    └── …                       # nautilus qq steam and 15 more packages-only plugins
```

Configs deploy atomically, and your personal tweaks survive updates and form
switches: each app's main config ships a personal mount file (Niri and Kitty both
have one) — edit it directly and deployments never clobber it. Files referenced
by name (like `~/.config/niri/monitor.kdl`) are preserved automatically.

---

## Hooks Architecture

Nyxuri separates finishing automation into two isolated layers:

### 1. User Post-Deploy Hooks (`~/.config/nyxuri/hooks/`)
Put personal finishing scripts in `~/.config/nyxuri/hooks/`. Any script ending in `.sh` runs in alphanumeric filename order after normal config deployments (`nyxuri install` or updates) with a 30-second timeout. A failed or timed-out script prints a diagnostic warning without interrupting the rest. `nyxuri test` skips user hooks, and uninstallation preserves them.

### 2. Plugin Lifecycle Hooks (`plugins/<plugin>/hooks/`)
Plugins declare their own lifecycle side effects in `plugins/<plugin>/manifest.toml` (e.g. `post_install = "setup-rime"`, `install-pack` for wallpaper downloads). These scripts are plugin-owned and run strictly through the transaction engine during activation (`nyxuri on`), deactivation (`nyxuri off`), or hook replay after updates (`transaction.replay_enabled_hooks()`). Users do not manually place scripts here.
