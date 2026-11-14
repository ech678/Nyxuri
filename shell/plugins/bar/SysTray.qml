import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Services.SystemTray
import qs.services
import qs.commons
import qs.ui

Item {
    id: root
    property bool vertical: false
    property bool invertSide: false
    property bool trayOverflowOpen: false
    property bool showSeparator: true
    property bool showOverflowMenu: true
    property var activeMenu: null
    readonly property bool isOnLeft: Config.options.bar.m3.layouts.leftLayout.includes("sysTray")
    readonly property bool isMaterial: PersonalizationConfig.barIsMaterial

    visible: SystemTray.items.values.length > 0
    implicitWidth: vertical ? Appearance.sizes.verticalBarWidth : (isMaterial ? pill.implicitWidth - 4 : gridLayout.implicitWidth)
    implicitHeight: vertical ? gridLayout.implicitHeight + 6 : Appearance.sizes.barHeight

    property list<var> pinnedItems: TrayService.pinnedItems
    property list<var> unpinnedItems: TrayService.unpinnedItems
    // Probe surface (scripts/dev/probe-bar.sh): the overflow decision is a
    // runtime fact, so expose the evaluated counts instead of grepping the
    // source for `unpinnedItems.length`.
    readonly property int pinnedCount: pinnedItems.length
    readonly property int unpinnedCount: unpinnedItems.length
    readonly property bool overflowVisible: showOverflowMenu && unpinnedItems.length > 0
    onUnpinnedItemsChanged: {
        if (unpinnedItems.length == 0)
            root.closeOverflowMenu();
    }

    function grabFocus() {
        focusGrab.active = true;
    }
    function setExtraWindowAndGrabFocus(window) {
        if (root.activeMenu && root.activeMenu !== window) {
            if (typeof root.activeMenu.close === "function")
                root.activeMenu.close();
            root.activeMenu = null;
        }
        root.activeMenu = window;
        root.grabFocus();
    }
    function releaseFocus() {
        root.activeMenu = null;
        focusGrab.active = false;
    }
    function closeOverflowMenu() {
        root.trayOverflowOpen = false;
        focusGrab.active = false;
    }

    onTrayOverflowOpenChanged: {
        if (root.trayOverflowOpen)
            root.grabFocus();
        else
            focusGrab.active = false;
    }

    // Focus grab state for the item menus that open from the tray. On Niri the
    // layer-shell keyboard focus owns the grab; the overflow popup closes
    // through StyledPopup's outside-click backdrop below, not through this Item.
    Item {
        id: focusGrab
        property bool active: false
        property var windows: []
        signal cleared
        onCleared: {
            root.trayOverflowOpen = false;
            if (root.activeMenu) {
                root.activeMenu.close();
                root.activeMenu = null;
            }
        }
    }

    Rectangle {
        id: pill
        visible: false
        anchors.centerIn: parent
        color: "transparent"
        radius: Appearance.rounding.full
        implicitWidth: root.vertical ? 32 : gridLayout.implicitWidth
        implicitHeight: root.vertical ? gridLayout.implicitHeight + 12 : 32
    }

    GridLayout {
        id: gridLayout
        columns: root.vertical ? 1 : -1
        anchors.centerIn: parent
        rowSpacing: 4
        columnSpacing: -6

        RippleButton {
            id: trayOverflowButton
            visible: root.showOverflowMenu && root.unpinnedItems.length > 0
            toggled: root.trayOverflowOpen
            downAction: () => root.trayOverflowOpen = !root.trayOverflowOpen

            Layout.alignment: Qt.AlignVCenter | Qt.AlignHCenter
            background.implicitWidth: 24
            background.implicitHeight: 24
            background.anchors.centerIn: this
            colBackgroundToggled: M3Palette.secondaryContainer
            colBackgroundToggledHover: M3Palette.secondaryContainerHover
            colRippleToggled: M3Palette.secondaryContainerActive

            contentItem: MaterialSymbol {
                anchors.centerIn: parent
                iconSize: Appearance.font.pixelSize.larger
                text: Config.options.bar.bottom ? "keyboard_control_key" : "expand_more"
                horizontalAlignment: Text.AlignHCenter
                color: root.isMaterial ? M3Palette.pillInk("sysTray") : Appearance.colors.colOnLayer2
                rotation: (root.trayOverflowOpen ? 180 : 0) - (90 * root.vertical) + (180 * root.invertSide)
                Behavior on rotation {
                    animation: Appearance.animation.elementMoveFast.numberAnimation.createObject(this)
                }
            }

            StyledPopup {
                id: overflowPopup
                hoverTarget: trayOverflowButton
                hoverActivates: false
                closeOnOutsideClick: true
                active: root.trayOverflowOpen && root.unpinnedItems.length > 0
                onRequestClose: root.closeOverflowMenu()

                GridLayout {
                    id: trayOverflowLayout
                    anchors.centerIn: parent
                    columns: Math.ceil(Math.sqrt(root.unpinnedItems.length))
                    columnSpacing: 6
                    rowSpacing: 6

                    Repeater {
                        model: root.unpinnedItems
                        delegate: SysTrayItem {
                            required property SystemTrayItem modelData
                            item: modelData
                            Layout.fillHeight: !root.vertical
                            Layout.fillWidth: root.vertical
                            onMenuClosed: root.releaseFocus()
                            onMenuOpened: qsWindow => root.setExtraWindowAndGrabFocus(qsWindow)
                        }
                    }
                }
            }
        }

        Repeater {
            model: ScriptModel {
                values: root.pinnedItems
            }
            delegate: SysTrayItem {
                required property SystemTrayItem modelData
                item: modelData
                Layout.alignment: Qt.AlignVCenter | Qt.AlignHCenter
                Layout.fillHeight: !root.vertical
                Layout.fillWidth: root.vertical
                Layout.leftMargin: 6
                Layout.rightMargin: 6
                onMenuClosed: root.releaseFocus()
                onMenuOpened: qsWindow => root.setExtraWindowAndGrabFocus(qsWindow)
            }
        }
    }
}
