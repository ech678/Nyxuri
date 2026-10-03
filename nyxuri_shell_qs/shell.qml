import QtQuick
import Quickshell
import Quickshell.Io
import qs
import qs.core
import qs.panels

ShellRoot {
    id: shell

    property string panel: ""
    property bool orbitOpen: false
    property string clockText: ""
    property int trayCount: 0
    property int notifCount: 0

    readonly property bool launcherOpen: panel === "launcher"
    readonly property bool notifOpen: panel === "notifications"
    readonly property bool trayOpen: panel === "tray"

    property string initialAction: ""

    function togglePanel(name) {
        if (panel === name) {
            panel = ""
        } else {
            panel = name
            orbitOpen = false
        }
    }

    function closeAll() {
        panel = ""
        orbitOpen = false
    }

    function toggleOrbit() {
        orbitOpen = !orbitOpen
        panel = ""
    }

    function doAction(a) {
        if (!a || a.length === 0) return
        if (a === "launcher") togglePanel("launcher")
        else if (a === "session") togglePanel("session")
        else if (a === "settings") togglePanel("settings")
        else if (a === "clipboard") togglePanel("clipboard")
        else if (a === "lock") Quickshell.execDetached(["sh", "-c",
            "loginctl lock-session 2>/dev/null || swaylock -f 2>/dev/null || hyprlock 2>/dev/null || true"])
        else if (a === "wallpaper-random") Wall.random()
        else if (a === "wallpaper-picker") togglePanel("wallpaper")
        else if (a === "radial-launcher") toggleOrbit()
        else if (a === "notifications") togglePanel("notifications")
        else if (a === "tray") togglePanel("tray")
        else if (a === "sysmon") togglePanel("sysmon")
        else if (a === "calendar") togglePanel("calendar")
        else if (a === "volume-up") { Sys.bumpVolume(0.05); flashVolume() }
        else if (a === "volume-down") { Sys.bumpVolume(-0.05); flashVolume() }
        else if (a === "volume-mute") { Sys.toggleMute(); flashVolume() }
        else if (a === "workspace-next") Workspaces.cycle(1)
        else if (a === "workspace-prev") Workspaces.cycle(-1)
        else if (a === "quit") Qt.quit()
    }

    function flashVolume() {
        osdRef.flash(Sys.muted ? "\u266B" : "\u266A", "Volume", Sys.volume)
    }

    readonly property var panelDefs: ({
        launcher: { title: "Launcher", w: 560, h: 460 },
        session: { title: "Session", w: 420, h: 480 },
        settings: { title: "Settings", w: 520, h: 520 },
        clipboard: { title: "Clipboard", w: 560, h: 460 },
        wallpaper: { title: "Wallpaper", w: 720, h: 520 },
        notifications: { title: "Notifications", w: 520, h: 460 },
        tray: { title: "System Tray", w: 460, h: 400 },
        sysmon: { title: "System Monitor", w: 520, h: 440 },
        calendar: { title: "Calendar", w: 420, h: 440 }
    })

    function defFor(name) {
        var d = shell.panelDefs[name]
        return d ? d : { title: name, w: 520, h: 420 }
    }

    Component.onCompleted: {
        var args = Quickshell.env("NYXURI_QS_ACTION")
        if (args && args.length > 0) initialAction = args
        warmup()
    }

    function warmup() {
        var probe = [
            Apps.apps.length,
            Apps.groups.length,
            Workspaces.items.length,
            Wall.files.length,
            Wall.scanning,
            Clip.items.length,
            Notif.items.length,
            Sys.cpu
        ]
        return probe.length
    }

    IpcHandler {
        target: "nyxuri"

        function open(what: string): void {
            shell.doAction(what)
        }

        function close(): void {
            shell.closeAll()
        }

        function toggle(what: string): void {
            if (what === "orbit") shell.toggleOrbit()
            else shell.togglePanel(what)
        }

        function orbit(): void {
            shell.toggleOrbit()
        }

        function status(): string {
            return "panel=" + shell.panel
                + " orbit=" + (shell.orbitOpen ? "1" : "0")
                + " backend=" + Workspaces.backend
                + " wallpapers=" + Wall.files.length
                + " clipboard=" + Clip.items.length
                + " notifications=" + Notif.items.length
                + " apps=" + Apps.apps.length
                + " groups=" + Apps.groups.length
        }

        function panelName(): string {
            return shell.panel
        }

        function wallpaperRandom(): void {
            Wall.random()
        }

        function wallpaperIndex(i: int): void {
            Wall.pick(i)
        }

        function wallpaperPath(p: string): void {
            Wall.apply(p)
        }

        function colors(): string {
            return "seed=" + Color.seed.join(",")
                + " hue=" + Color.hue
                + " chroma=" + Color.chroma
                + " primary=" + Theme.p("primary")
                + " surface=" + Theme.p("surface")
                + " dark=" + (Color.dark ? "1" : "0")
        }

        function themeMode(mode: string): void {
            Color.dark = (mode === "dark")
        }

        function lock(): void {
            shell.doAction("lock")
        }

        function quit(): void {
            Qt.quit()
        }
    }

    Timer {
        interval: 1000
        running: true
        repeat: true
        triggeredOnStart: true
        onTriggered: {
            var d = new Date()
            var hh = d.getHours() < 10 ? "0" + d.getHours() : String(d.getHours())
            var mm = d.getMinutes() < 10 ? "0" + d.getMinutes() : String(d.getMinutes())
            shell.clockText = hh + ":" + mm
            shell.notifCount = Notif.count
        }
    }

    Variants {
        model: Quickshell.screens

        delegate: Component {
            Item {
                required property var modelData

                Bar {
                    host: shell
                    targetScreen: modelData
                }

                Osd {
                    id: osdItem
                    host: shell
                    targetScreen: modelData
                    Component.onCompleted: osdRef = osdItem
                }

                Panel {
                    host: shell
                    targetScreen: modelData
                    open: shell.panel !== ""
                    title: shell.defFor(shell.panel).title
                    panelWidth: shell.defFor(shell.panel).w
                    panelHeight: shell.defFor(shell.panel).h

                    Loader {
                        anchors.fill: parent
                        sourceComponent: shell.panel === "launcher" ? launcherComp
                            : shell.panel === "session" ? sessionComp
                            : shell.panel === "settings" ? settingsComp
                            : shell.panel === "clipboard" ? clipboardComp
                            : shell.panel === "wallpaper" ? wallpaperComp
                            : shell.panel === "notifications" ? notifComp
                            : shell.panel === "tray" ? trayComp
                            : shell.panel === "sysmon" ? sysmonComp
                            : shell.panel === "calendar" ? calendarComp
                            : null

                        Component {
                            id: launcherComp
                            LauncherPanel { host: shell }
                        }

                        Component {
                            id: sessionComp
                            SessionPanel { host: shell }
                        }

                        Component {
                            id: settingsComp
                            SettingsPanel { host: shell }
                        }

                        Component {
                            id: clipboardComp
                            ClipboardPanel { host: shell }
                        }

                        Component {
                            id: wallpaperComp
                            WallpaperPanel { host: shell }
                        }

                        Component {
                            id: notifComp
                            NotificationsPanel { host: shell }
                        }

                        Component {
                            id: trayComp
                            TrayPanel { host: shell }
                        }

                        Component {
                            id: sysmonComp
                            SysmonPanel { host: shell }
                        }

                        Component {
                            id: calendarComp
                            CalendarPanel { host: shell }
                        }
                    }
                }

                Orbit {
                    host: shell
                    targetScreen: modelData
                    open: shell.orbitOpen
                }
            }
        }
    }

    property var osdRef: null

    Connections {
        target: Sys
        ignoreUnknownSignals: true
        function onVolumeChanged() {
            if (shell.osdRef) shell.osdRef.flash(Sys.muted ? "\u266B" : "\u266A", "Volume", Sys.volume)
        }
    }
}