`nyxuri` manages installation, snapshots and diagnostics. Interactive deployments create a snapshot in `~/.config/nyxuri/backups/` by default.

> Legacy Bash users must run the bootstrap entrypoint before using these commands. The old `nyxniri update` cannot perform the directory migration.

---

## Plugin verbs

| Command | Description |
| :--- | :--- |
| `nyxuri list [plugin]` | Every plugin with its switch state and active form, or one plugin in detail |
| `nyxuri on <plugin> [--form <name>]` | Enable a plugin (dependencies and missing packages disclosed first); same as `enable`; `--preset` is the deprecated alias |
| `nyxuri off <plugin> [--cascade]` | Disable a plugin — custom files archived, managed files wiped; same as `disable` |
| `nyxuri use <plugin> [list\|<form>\|save\|edit\|delete\|slots\|slot <axis> <name>]` | Switch / manage forms (see [Forms & Slot Axes](Forms)); `preset` is the deprecated alias |
| `nyxuri doctor [plugin]` | Three-state reconciliation (`Synced` / `Drifted` / `Ghost`) plus a system checkup |

Everything on the desktop is a plugin — including wallpapers: `nyxuri on wallpapers`
deploys the built-in fallback into `~/Pictures/Wallpapers`; the full video pack is
user-domain content installed via `plugins/wallpapers/hooks/install-pack`.

---

## Deployment & themes

| Command | Description |
| :--- | :--- |
| `nyxuri install [full\|config]` | Legacy full pipeline (configs + wallpapers plugin + hook replay), or configs only |
| `nyxuri update [--force\|--no-deploy] [--to <tag\|commit>]` | Update source; force config deployment or skip it; pin a version |
| `nyxuri theme [toggle\|dark\|light\|sync\|status]` | Switch or sync the dark/light axis |
| `nyxuri shell [get\|set <noctalia\|nyxuri-shell> [bin_path]\|switch [<target> [bin_path]]\|status]` | Inspect or hot-switch the desktop shell slot (experimental) |

---

## Supply

| Command | Description |
| :--- | :--- |
| `nyxuri deps [core\|apps]` | Core dependency checklist, or the everyday-apps checklist (Nautilus / Steam and 16 more — all plugin declarations) |
| `nyxuri pkg <install\|upgrade\|remove\|search\|info\|installed>` | Direct package management; search accepts `aur` / `pac` prefixes |
| `nyxuri clean [-n] [--only <tasks>]` | Cache sweeper; `-n` previews only |

---

## Snapshots

| Command | Description |
| :--- | :--- |
| `nyxuri snapshot [note]` | Save current config state |
| `nyxuri snapshot list` | List snapshots |
| `nyxuri snapshot delete [index]` | Delete snapshots (multi-select if no index) |
| `nyxuri rollback [index]` | Restore a snapshot |

---

## System

| Command | Description |
| :--- | :--- |
| `nyxuri doctor [plugin]` | Plugin reconciliation + dependency and system health check |
| `nyxuri bug` | Export a diagnostic report |
| `nyxuri test` | Developer sandbox deploy (no backup, keeps monitor.kdl) |
| `nyxuri uninstall [--all\|standard\|restore\|purge]` | Checkbox uninstall — pick what gets cleaned (or run standard, restore, purge, --all directly) |
| `nyxuri help` | Show CLI help and usage |

---

## Retired names (KM3.5)

`deploy` `backup` `restore` `remove` `purge` `recommended` `apps` `wp` `wallpapers`
`report` and the module verbs `greeter` `fcitx` `gtk` `fisher` are gone — they are
plain unknown commands now. Use the plugin verbs (`on` / `off` / `use`) and the state
verbs (`snapshot` / `rollback` / `uninstall`) instead.

---

## Quick reference: nyxhelp

`nyxhelp` is an `fzf`-based cheat sheet covering the CLI, shell helpers and core keybindings:

| Command | Description |
| :--- | :--- |
| `nyxhelp` | Two-pane interactive cheat menu |
| `nyxhelp keys` | Niri keybindings |
| `nyxhelp proxy` | Proxy control (`proxy_on [port]`, `proxy_off`, `proxy_status`) |
| `nyxhelp pkg` | Package shortcuts (`up`, `in`, `se`, `un`, `clean`) |
| `nyxhelp all` | Full cheat sheet |
