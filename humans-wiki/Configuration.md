```text
Nyxuri
├── install.sh                  # lightweight bootstrap entrypoint
├── nyxuri/                     # Python core engine (zero pip dependencies)
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

Configs deploy atomically. Personal tweaks survive updates via the Dunder protocol:
- Any file (e.g. `__custom__.kdl`, `__custom__.conf`) or folder containing `__custom__` is preserved.
- `~/.config/niri/monitor.kdl` is kept across deployments.

---

## How to customize (Dunder Protocol)

Any file or folder containing `__custom__` survives updates and preset switches:

- **Loaded per-app**: each app uses its native include mechanism — Niri includes `__custom__.kdl`, Kitty includes `__custom__.conf`, while Fish autoloads files under `conf.d/`.
- **Modular & composable**: to split tweaks across multiple files, simply include them from your main custom file (e.g. put `include "my_rules__custom__.kdl"` inside `__custom__.kdl` — all files containing `__custom__` remain preserved).
- **Dedicated files**: files referenced by name like `~/.config/niri/monitor.kdl` are preserved automatically; edit them directly.

---

## Post-deploy hooks

Put shell scripts in `~/.config/nyxuri/hooks/` to run your own finishing work after every normal config deploy. Scripts ending in `.sh` run in filename order with a 30-second limit; a failed or timed-out script is reported without blocking the rest. `nyxuri test` skips these hooks, and ordinary uninstall keeps them.
