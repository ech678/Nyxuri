When encountering issues, run `./install.sh doctor` first.

---

## Noctalia hangs on startup
`ddcutil` can time out scanning the I2C bus (common on NVIDIA).

Disable `ddcutil` in `~/.config/noctalia/noctalia-config.toml`:

```toml
[brightness]
enable_ddcutil = false
```

Brightness keys still work: internal panels go through Noctalia backlight, external monitors keep the `ddcutil` fallback. Leave this setting off unless you want Noctalia itself to own DDC.

---

## Browser video looks stacked, black, or see-through
Hybrid GPU (AMD/Intel iGPU + NVIDIA dGPU) used to force NVIDIA video decode for every app.

Nyxuri used to uncomment `GBM_BACKEND=nvidia-drm` and `LIBVA_DRIVER_NAME=nvidia` whenever `lspci` mentioned NVIDIA. On hybrid laptops the compositor stays on the iGPU, so Chromium/Brave can decode on NVIDIA and present on AMD/Intel — a few videos then corrupt the window.

Update and redeploy Nyxuri. The default configuration no longer selects a GPU driver, and deployment no longer rewrites environment variables based on PCI devices. A PCI listing cannot identify the active rendering GPU. Put any driver settings you need in `~/.config/niri/__custom__.kdl`.

The old `ELECTRON_OZONE_PLATFORM_HINT "auto"` setting has also been removed; some older Electron apps may use XWayland instead. Normal deployment updates the main configuration but leaves personal overrides, personal presets, historical snapshots, and the current session environment alone. Log out and back in before checking the result.

---

## Plugin repo corrupted
Noctalia hangs while checking out plugins.

Run the following commands to reset the plugin repos:

```bash
git -C ~/.local/state/noctalia/plugins/sources/community/repo reset --hard HEAD
git -C ~/.local/state/noctalia/plugins/sources/official/repo reset --hard HEAD
```

---

## Greeter sync asks for a password
Add a Polkit rule (`nyxuri greeter install` does this for you).

Install the Polkit rule manually if needed:

```bash
sudo bash -c 'cat > /etc/polkit-1/rules.d/50-noctalia-greeter.rules << EOF
polkit.addRule(function(action, subject) {
    if (action.id == "org.noctalia.greeter.sync-appearance" &&
        subject.isInGroup("wheel")) {
        return polkit.Result.YES;
    }
});
EOF'
```

---

## Nautilus or Libadwaita apps stuck in light mode
Leftover user CSS overrides dark mode.

If Noctalia's built-in GTK templates or old tools generated `noctalia.css` or `gtk.css` in `~/.config/gtk-4.0/`, GTK4 forces those CSS color definitions over system dark mode.

Run theme sync or remove the stale override files:

```bash
nyxuri theme sync
# Or manually:
rm -f ~/.config/gtk-4.0/gtk.css ~/.config/gtk-4.0/noctalia.css ~/.config/gtk-3.0/gtk.css ~/.config/gtk-3.0/noctalia.css
```

---

## Brave doesn't follow theme toggle
Brave cold-start bug (not a Nyxuri issue).

On non-GNOME Wayland compositors, Brave's portal theme-signal subscription fails to initialize on cold start, so `nyxuri theme toggle` doesn't recolor it. Open `brave://settings/appearance` and switch theme mode once (e.g. Classic → GTK → Classic) to wake it up; it follows live afterwards without restarting Brave. Needs re-waking after each Brave restart.
