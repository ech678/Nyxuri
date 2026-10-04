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

ShellRoot {
    AppShell {}
}
