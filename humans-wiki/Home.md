Nyxuri is a Material You desktop suite and management engine for Arch Linux / CachyOS.
Start with the root README to install Nyxuri. This Wiki covers configuration, forms, keybindings, CLI commands, and troubleshooting.

### Install from the AUR (Arch / CachyOS, recommended)

```bash
paru -S nyxuri-git        # management engine + config plugins + Nyxuri Shell, one package
nyxuri install full       # or assemble the desktop per plugin: nyxuri on <plugin>
```
> Installing enters system-package mode: updates are handled by pacman. Desktop apps are not bundled — enabling a plugin installs only what that plugin needs.

---

## Documentation Index

| Topic | Summary | Reference |
| :--- | :--- | :--- |
| Plugins, Configs & Customization | Directory tree, personal-change preservation, hooks architecture | [Read guide](Configuration) |
| Forms & Slot Axes | Official Kitty/Niri forms, slot axes, private forms | [Read guide](Forms) |
| Complete Keybindings | Window & column navigation, shell action gateway, nyxhelp | [Read guide](Keybindings) |
| CLI Reference Manual | Plugins, install, update, snapshot rollback, doctor, uninstall commands | [Read guide](CLI-Reference) |
| Troubleshooting Guide | DDC bus conflict, hybrid GPU video artifacts, CSS cleanups | [Read guide](Troubleshooting) |
