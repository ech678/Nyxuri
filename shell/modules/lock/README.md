# Lock screen styles

Settings Center → Theme → Lock screen selects `default` or `caelestia`.
The selection is saved as `theme.lockScreenStyle` in the personalization config.
Missing or invalid values use `default`; each lock session keeps its initial selection.

`CaelestiaLock.qml` preserves the original card layout. `DefaultLock.qml` reveals a
blurred wallpaper over a frozen pre-lock desktop frame, with authentication UI
in `DefaultLockContent.qml`. Both styles share the session lock and PAM context.

## Password capture is input-method free

Both styles take passwords through `PasswordCapture.qml`, a `FocusScope` that
accumulates raw key events. The lock module must never instantiate
`TextInput`/`TextField`: with `QT_IM_MODULE=fcitx` the Qt input context engages
on focus, and fcitx5-qt can raise a parentless `xdg_popup` from the
session-lock surface. niri rejects that with a fatal protocol error
("xdg_popup must have parent before mapping"), quickshell's Wayland connection
dies, the session stays locked, and niri shows its solid red dead-locker
screen. Consequences, in exchange for never hitting that crash class:

- No IME composition on the lock screen: passwords are typed with hardware
  layout mapping only, same as swaylock/hyprlock/DMS.
- No clipboard paste on the lock surface (shortcut keys are swallowed).

## Red-screen recovery (dead locker)

If the shell process ever dies while the session is locked, niri keeps the
session locked on a solid red background with only the cursor alive. The lock
writes `<runtimeHome>/lock-active` (owning `XDG_SESSION_ID` + start time) for
as long as it holds the session lock and removes it on unlock. A freshly
started shell detects a same-session marker younger than 15 minutes and takes
the session lock back over, so pressing `Mod+L` (`shell-action.sh lock`, which
relaunches the shell when it is gone) turns the red screen back into the
normal lock screen. Last resorts: switch VT and run `niri msg action quit`,
or let the marker age out.

The new style uses Qt Quick MultiEffect for blur and the circular reveal mask.
Both styles capture through a short-lived Quickshell `ScreencopyView` config before
acquiring the session lock. No external screenshot program is required. The helper
uses a private temporary directory in XDG_RUNTIME_DIR (TMPDIR fallback) for a BMP.
It returns the local path and holds the file until the main shell releases its stdin
lease at unlock/cancellation. Main-shell Image preloading completes before requesting
the session lock; display Images reuse the same URL and decoded image cache.
There is no PNG/base64/data-URL round trip. Default keeps
the snapshot underneath its wallpaper layer for the top-left disc reveal and exit
fade. The wallpaper itself is still sourced from the current wallpaper image.

Manual visual checks in a graphical session:

- Select each style and lock using the normal shell action.
- Verify the default style with image/solid-color wallpaper and multiple outputs.
- Verify 12-hour AM/PM and 24-hour clocks, and the date at midnight.
- Type, delete, submit an incorrect password, then authenticate successfully.
  Repeat three failures in a row: the field flashes pink, typing stays possible,
  and the desktop must never turn red.
- With fcitx5 running and an input method active, press the IM toggle keys
  (e.g. Shift / Ctrl+Space) on the lock screen: nothing may pop up or crash.
- Press Escape to clear input and restore the clock; click to reveal authentication.
- Verify entrance reveals the blurred wallpaper over the desktop snapshot without a black flash.
- Kill the shell while locked (red screen appears), then press `Mod+L`: the
  shell relaunches, takes the lock over, and unlocks normally.

If capture fails or times out, locking still proceeds. Default shows the wallpaper
without a disc reveal or a fade to a missing snapshot. The main shell does not
create a ScreencopyView: native capture stays on a separate Wayland connection
until the helper exits. The helper is bounded by a 1.5-second timeout.

No real session lock is started by development checks.
