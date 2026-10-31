//@ pragma UseQApplication
//@ pragma Env QT_QUICK_FLICKABLE_WHEEL_DECELERATION=10000
//@ pragma Env QT_WAYLAND_DISABLE_WINDOWDECORATION=1

// Pragmas must stay contiguous at the top of the file: a plain comment between
// two //@ lines ends the block and silently drops the rest. The wheel pragma
// matches end4-pC's feel; the dashboard's long lists and wallpaper grid crawl at
// Qt's default deceleration.

import QtQuick
import Quickshell
import qs.app
// Shared layers, imported here on purpose (loader-form.md rule 3): the
// startup scan closure synthesises a qmldir per imported directory, and this
// top-level import list is the guarantee that the pools dynamically loaded
// plugins import (qs.commons / qs.commons.cards / qs.commons.i18n / qs.ui /
// qs.services / qs.app) exist before the first plugin resolves one.
import qs.commons
import qs.commons.cards
import qs.commons.i18n
import qs.services
import qs.ui

ShellRoot {
    AppShell {}
}
