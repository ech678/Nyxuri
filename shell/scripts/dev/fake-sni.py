#!/usr/bin/env python3
"""Minimal StatusNotifierItem publisher for probe-bar.sh.

Publishes a few tray items on the probe's private session bus so the bar's tray
surface (pin, overflow arrow, passive filtering, persistence) can be exercised
at runtime instead of asserted as strings. This is a dev harness, not a user
tool: it holds no state and disappears with the probe.

Usage: fake-sni.py [count]
Prints "READY <n>" once every item registered, then blocks until SIGTERM.
"""

from __future__ import annotations

import os
import signal
import sys

import dbus
import dbus.mainloop.glib
import dbus.service
from gi.repository import GLib

ITEM_IFACE = "org.kde.StatusNotifierItem"
WATCHER_IFACE = "org.kde.StatusNotifierWatcher"
WATCHER_SERVICE = "org.kde.StatusNotifierWatcher"
WATCHER_PATH = "/StatusNotifierWatcher"

# 16x16 ARGB32, network byte order. Distinct colours per item make a screenshot
# review able to tell which icon moved into the overflow menu.
COLORS = (0xFF66CC99, 0xFF99AACC, 0xFFCC9966, 0xFFAA88CC)


def _pixmap(argb: int, size: int = 16):
    pixel = int(argb).to_bytes(4, "big")
    return dbus.Array(
        [dbus.Struct((size, size, dbus.ByteArray(pixel * size * size)), signature="iiay")],
        signature="(iiay)",
    )


class TrayItem(dbus.service.Object):
    def __init__(self, connection, index: int, status: str):
        self.index = index
        self._conn = connection
        self.bus_name = dbus.service.BusName(
            f"org.kde.StatusNotifierItem-probe-{os.getpid()}-{index}", connection
        )
        self.path = "/StatusNotifierItem"
        self.title = f"Probe Item {index + 1}"
        icon = _pixmap(COLORS[index % len(COLORS)])
        self._props = {
            "Category": dbus.String("ApplicationStatus"),
            "Id": dbus.String(f"probe-item-{index + 1}"),
            "Title": dbus.String(self.title),
            "Status": dbus.String(status),
            "WindowId": dbus.Int32(0),
            "IconName": dbus.String("application-x-executable"),
            "IconPixmap": icon,
            "OverlayIconName": dbus.String(""),
            "OverlayIconPixmap": dbus.Array([], signature="(iiay)"),
            "AttentionIconName": dbus.String(""),
            "AttentionIconPixmap": dbus.Array([], signature="(iiay)"),
            "AttentionMovieName": dbus.String(""),
            "ToolTip": dbus.Struct(
                (
                    dbus.String("application-x-executable"),
                    icon,
                    dbus.String(self.title),
                    dbus.String(f"probe item {index + 1}"),
                ),
                signature="sa(iiay)ss",
            ),
            "ItemIsMenu": dbus.Boolean(False),
            "Menu": dbus.ObjectPath("/NO_DBUSMENU"),
            "IconThemePath": dbus.String(""),
            "XAyatanaLabel": dbus.String(""),
            "XAyatanaLabelGuide": dbus.String(""),
            "XAyatanaOrderingIndex": dbus.UInt32(index),
        }
        super().__init__(connection, self.path)

    @dbus.service.method(dbus.PROPERTIES_IFACE, in_signature="ss", out_signature="v")
    def Get(self, interface, prop):
        return self._props.get(prop, "")

    @dbus.service.method(dbus.PROPERTIES_IFACE, in_signature="s", out_signature="a{sv}")
    def GetAll(self, interface):
        return self._props

    @dbus.service.method(dbus.PROPERTIES_IFACE, in_signature="ssv", out_signature="")
    def Set(self, interface, prop, value):
        self._props[prop] = value

    @dbus.service.method(ITEM_IFACE, in_signature="ii", out_signature="")
    def Activate(self, x, y):
        pass

    @dbus.service.method(ITEM_IFACE, in_signature="ii", out_signature="")
    def SecondaryActivate(self, x, y):
        pass

    @dbus.service.method(ITEM_IFACE, in_signature="ii", out_signature="")
    def ContextMenu(self, x, y):
        pass

    @dbus.service.method(ITEM_IFACE, in_signature="is", out_signature="")
    def Scroll(self, delta, orientation):
        pass

    def register(self) -> None:
        watcher = self._conn.get_object(WATCHER_SERVICE, WATCHER_PATH)
        watcher.RegisterStatusNotifierItem(
            self.bus_name.get_name(), dbus_interface=WATCHER_IFACE
        )


def main() -> int:
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    address = os.environ.get("DBUS_SESSION_BUS_ADDRESS", "")

    # One connection per item: dbus-python allows a single object per path per
    # connection, and the SNI convention fixes the path at /StatusNotifierItem.
    items = []
    for index in range(count):
        connection = dbus.bus.BusConnection(address)
        items.append(TrayItem(connection, index, "Passive" if index == count - 1 else "Active"))

    pending = list(items)

    def try_register() -> bool:
        still = []
        for item in pending:
            try:
                item.register()
            except dbus.DBusException:
                still.append(item)
        pending[:] = still
        if not pending:
            print(f"READY {count}", flush=True)
            return False
        return True

    if try_register():
        GLib.timeout_add(200, try_register)

    loop = GLib.MainLoop()

    def stop(*_args):
        loop.quit()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    loop.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
