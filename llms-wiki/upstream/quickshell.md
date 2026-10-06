# Quickshell Complete Reference Handbook (LLMs Full Edition)

> Comprehensive, authoritative reference for Quickshell v0.3.1. Optimized for direct LLM ingestion and code generation.

---

# Getting Started & Architecture Hub

Welcome to the foundational module of the Quickshell knowledge base. Quickshell is a next-generation desktop shell framework engineered in C++ and QtQuick (QML), specifically optimized for Wayland compositors (with support for X11 environments).

## Topic Overview

This module covers the system architecture, runtime execution model, configuration layout, and foundational QML concepts required to build desktop environments with Quickshell.

| Document | Primary Scope | Key Concepts Covered |
| :---- | :---- | :---- |
| [Architecture & Lifecycle](http://01-getting-started/architecture.md) | Runtime engine, lifecycle, CLI options, hot-reloading | `shell.qml`, Scope, Reloadable, Retainable, XDG paths, CLI flags |
| [QML Primer & Tooling](http://01-getting-started/qml-primer.md) | QML syntax, Singletons, Layouts, LSP setup | `pragma Singleton`, `RowLayout`, implicit sizing, `qmlls`, diagnostics |

## High-Level Workflow

1. **Config Location**: Place your entry file at `~/.config/quickshell/<config-name>/shell.qml` or `~/.config/quickshell/shell.qml`.  
2. **Execution**: Run `quickshell` (loads default) or `quickshell --config <config-name>`.  
3. **Hot Reload**: Keep Quickshell running in a terminal. Every save to your QML files reloads the live surfaces instantly while preserving session state where configured.  
4. **Window Definition**: Define one or more `PanelWindow` (bars, docks) or `FloatingWindow` (dialogs, widgets) objects in your QML files.

Next, read [Architecture & Lifecycle](http://01-getting-started/architecture.md) for execution details, or jump to [QML Primer & Tooling](http://01-getting-started/qml-primer.md).

---

# Quickshell Architecture & Lifecycle

Quickshell bridges modern Linux desktop protocols (Wayland Layer Shell, Session Lock, Screencopy, PipeWire, BlueZ, NetworkManager, UPower, MPRIS, DBusMenu) with QtQuick's GPU-accelerated declarative scene graph.

## 1\. Runtime Architecture

\+-------------------------------------------------------+

|                   User QML Shell                      |

| (PanelWindow, PopupWindow, FloatingWindow, Widgets)   |

\+-------------------------------------------------------+

                           |

                           v

\+-------------------------------------------------------+

|               Quickshell C++ Core Runtime             |

|   \- QML Engine & Type Registry (Quickshell.\*)         |

|   \- Reload Manager & Object Lifecycle Scope           |

|   \- Event Sockets & IPC Controller                    |

\+-------------------------------------------------------+

       |                  |                  |

       v                  v                  v

\+--------------+   \+---------------+   \+----------------+

| Wayland / X11|   | Linux Daemons |   | Audio / Media  |

| \- zwlr\_layer |   | \- NetworkMgr  |   | \- PipeWire     |

| \- ext\_lock   |   | \- BlueZ       |   | \- MPRIS        |

| \- screencopy |   | \- UPower      |   | \- WirePlumber  |

| \- hypr-ipc   |   | \- Polkit/PAM  |   |                |

\+--------------+   \+---------------+   \+----------------+

### Components

1. **QtDeclarative Engine**: Executes JavaScript bindings, instantiates QML components, and coordinates property changes.  
2. **Native Platform Integrations**: High-performance C++ adapters communicating directly with system sockets (`wayland-0`, `pipewire-0`, `/var/run/dbus/system_bus_socket`) without Electron or Node.js overhead.  
3. **Hot-Reload Subsystem**: Watches project directories via inotify. When files change, Quickshell tears down outdated component trees and reconstructs updated trees while persisting marked state objects.

---

## 2\. Configuration & Discovery Hierarchy

Quickshell adheres to the XDG Base Directory specification:

1. **Default Config**:  
   - `~/.config/quickshell/shell.qml`  
   - If this file exists directly in `~/.config/quickshell/`, Quickshell runs this single config. Subdirectories are ignored.  
2. **Named Configs**:  
   - `~/.config/quickshell/<name>/shell.qml`  
   - Subdirectories containing `shell.qml` are registered as named configs.  
   - Example: `~/.config/quickshell/desktop/shell.qml` and `~/.config/quickshell/lockscreen/shell.qml`.  
3. **Explicit Paths**:  
   - Arbitrary paths or single files can be launched using the `-p` or `--path` option.

---

## 3\. Command-Line Interface (CLI)

quickshell \[OPTIONS\]

### Supported CLI Flags

| Flag | Long Option | Description |
| :---- | :---- | :---- |
| `-c <name>` | `--config <name>` | Selects a named configuration directory under `~/.config/quickshell/`. |
| `-p <path>` | `--path <path>` | Runs a specific QML file or directory anywhere on the filesystem. |
| `-d` | `--debug` | Enables verbose debug logging across internal C++ modules. |
| `-v` | `--version` | Displays Quickshell version and build flags. |
| `--layer <layer>` | `--layer <layer>` | Overrides the default Wayland layer (e.g. `top`, `bottom`, `overlay`, `background`). |

---

## 4\. State Lifecycle & Reload Model

### Reload Mechanics

When a `.qml` file is edited and saved:

1. File watcher detects the file modification.  
2. The active QML engine re-evaluates the component tree.  
3. Windows marked as `Reloadable` are re-instantiated.  
4. Transient objects are discarded unless protected by `Retainable` or state persistence.

### Key Lifecycle Primitives

- **`ShellRoot`**: The root container for non-visual top-level definitions and multi-window managers.  
- **`Scope`**: Creates an isolated lifecycle scope for grouping components that share identical reload properties.  
- **`Variants`**: Dynamic multi-instance generator. Commonly used to duplicate a `PanelWindow` across all connected `Quickshell.screens`.  
- **`Reloadable`**: Base interface for objects that can be selectively reloaded without restarting the process.  
- **`Retainable` & `RetainableLock`**: Prevents an object (such as a notification queue or active audio link) from being destroyed during a hot reload.

// Example: Preserving state across live reloads

import Quickshell

import QtQuick

ShellRoot {

    Variants {

        model: Quickshell.screens

        delegate: Component {

            PanelWindow {

                required property var modelData

                screen: modelData

                // Window will hot reload when updated without crashing

            }

        }

    }

}

Next, read [QML Primer & Tooling](http://01-getting-started/qml-primer.md) to understand syntax and language features.

---

# QML Language Primer & Developer Tooling

QML is a declarative, reactive language tailored for user interfaces. It combines JSON-like object hierarchies with inline JavaScript expressions and automatic property binding.

## 1\. Syntax Fundamentals

### Object Declaration & Properties

import QtQuick

import Quickshell

Rectangle {

    id: root

    width: 200

    height: 40

    color: "\#1e1e2e"

    radius: 8

    // Custom property declarations

    property string labelText: "Active"

    property int counter: 0

    readonly property bool isPositive: counter \> 0

    // Signal handler

    MouseArea {

        anchors.fill: parent

        onClicked: root.counter \+= 1

    }

}

### Reactive Property Bindings

In QML, assigning an expression creates a dynamic relationship. If any dependency changes, the target property recomputes automatically:

Text {

    // Automatically updates whenever root.counter changes

    text: "Clicks: " \+ root.counter

    color: root.isPositive ? "\#a6e3a1" : "\#f38ba8"

}

> **Warning**: Assigning a static value inside JavaScript (e.g. `onClicked: width = 200`) breaks the reactive binding on `width`. Use conditional expressions or explicit binding helpers (`Binding {}`) to preserve reactivity.

---

## 2\. Singletons in Quickshell

Singletons provide centralized application state (audio state, workspace trackers, settings) accessible across all files without passing properties through parent trees.

### Creating a Singleton

Place a QML file in your config directory (e.g. `Theme.qml`) with `pragma Singleton`:

// Theme.qml

pragma Singleton

import QtQuick

QtObject {

    readonly property color background: "\#181825"

    readonly property color surface: "\#313244"

    readonly property color accent: "\#cba6f7"

    readonly property color text: "\#cdd6f4"

    readonly property int defaultRadius: 10

}

### Using a Singleton

In any neighboring QML file in the same directory:

import QtQuick

Rectangle {

    color: Theme.background

    border.color: Theme.accent

    radius: Theme.defaultRadius

}

---

## 3\. Sizing, Anchors, and Layouts

### Item Size Types

- **`width` / `height`**: Explicit pixel bounds.  
- **`implicitWidth` / `implicitHeight`**: Natural dimensions computed from contents (e.g., text length or child item bounds).  
- **`anchors`**: Used to pin items relative to sibling or parent edges (`anchors.top`, `anchors.bottom`, `anchors.centerIn`).

### Anchors vs Layouts Rule of Thumb

- Use **`anchors`** for aligning standalone components to a parent boundary (e.g., sticking a button to the top-right corner).  
- Use **`RowLayout`**, **`ColumnLayout`**, or **`GridLayout`** (from `QtQuick.Layouts`) when arranging lists of dynamic items with spacing and automatic flow.

---

## 4\. LSP & Developer Tooling (`qmlls`)

Quickshell supports the official Qt Language Server (`qmlls`).

### Editor Configuration (Neovim / VSCode)

Ensure `qmlls` is in your `$PATH`. Set `QML2_IMPORT_PATH` to include Quickshell's imported QML modules:

export QML2\_IMPORT\_PATH="/usr/lib/qt6/qml:/usr/local/lib/qt6/qml:\$HOME/.nix-profile/lib/qt-6/qml"

### Known Linter Diagnostics (`isCreatable: false`)

Most Quickshell window interfaces (`PanelWindow`, `WlrLayershell`) are marked with `isCreatable: false` in their internal `.qmltypes` metadata because they are resolved via factory interfaces. `qmlls` might display false warnings:

Type PanelWindow is not creatable.

These warnings can be safely ignored; Quickshell instantiates these types seamlessly at runtime.

Continue to [Windows, Surfaces & Menus](http://02-windows-and-surfaces/index.md).

---

# Windows, Surfaces & Menus Hub

Quickshell provides dedicated window abstractions designed for shell surfaces, including top bars, side docks, application launchers, desktop widgets, and context menus.

## Topic Overview

| Document | Primary Scope | Key Types & Primitives |
| :---- | :---- | :---- |
| [Panel Windows](http://02-windows-and-surfaces/panel-window.md) | Attached desktop bars, docks, panels | `PanelWindow`, `ExclusionMode`, `anchors`, `margins`, `exclusiveZone` |
| [Floating & Popup Windows](http://02-windows-and-surfaces/floating-and-popups.md) | Floating widgets, modal overlays, popups | `FloatingWindow`, `PopupWindow`, `PopupAnchor`, `PopupAdjustment`, `QsWindow` |
| [Menus & Popovers](http://02-windows-and-surfaces/menus.md) | Context menus, system tray menus | `QsMenuAnchor`, `QsMenuOpener`, `QsMenuHandle`, `QsMenuEntry`, `QsMenuButtonType` |

---

## Architectural Distinctions

                       \+-------------------+

                       |     QsWindow      |  (Base window interface)

                       \+-------------------+

                                 |

                 \+---------------+---------------+

                 |                               |

                 v                               v

       \+-------------------+           \+-------------------+

       |    PanelWindow    |           |  FloatingWindow   |

       \+-------------------+           \+-------------------+

        (Bars, Docks, OSDs)             (Modals, Free Tools)

                 |

                 v

       \+-------------------+

       |    PopupWindow    |

       \+-------------------+

        (Flyouts, Tooltips)

1. **`PanelWindow`**: Tied to screen edges. Interacts with the window manager or Wayland layer shell to reserve space (`exclusiveZone`).  
2. **`FloatingWindow`**: Unanchored floating desktop windows that behave like standard GUI application windows.  
3. **`PopupWindow`**: Positioned dynamically relative to a parent window or anchor point (e.g. clicking a tray icon to open a volume slider).

Start with [Panel Windows](http://02-windows-and-surfaces/panel-window.md).

---

# PanelWindow: Bars, Docks & Overlays

`PanelWindow` is the central component for creating status bars, taskbars, side panels, and desktop overlays. It interfaces with the Wayland Layer Shell protocol (`zwlr_layer_shell_v1`) or X11 struts.

## Module Import

import Quickshell

---

## 1\. Property Reference

| Property | Type | Default | Description |
| :---- | :---- | :---- | :---- |
| `anchors` | `[top, right, bottom, left]` | all `false` | Edges of the monitor to attach the window to. |
| `margins` | `[top, right, bottom, left]` | `0` for all | Offset in pixels from attached monitor edges. |
| `exclusiveZone` | `int` | `0` | Reserved space (in pixels) for the panel. Pushes other client windows away. |
| `exclusionMode` | `ExclusionMode` | `Auto` | Dictates how exclusive space is calculated (`Auto`, `Normal`, `Ignore`). |
| `aboveWindows` | `bool` | `true` | If true, renders above normal application windows. Maps to Wayland `Top` layer. |
| `focusable` | `bool` | `false` | If true, accepts keyboard focus and key events. |
| `screen` | `ShellScreen` | primary | The monitor on which this panel appears. |
| `color` | `color` | `"transparent"` | Background fill color of the surface. |
| `visible` | `bool` | `true` | Visibility state of the panel surface. |

---

## 2\. Anchor & Margin Dynamics

### Anchor Constraints

- Anchoring both opposite edges (`left: true` AND `right: true`) causes the width to automatically stretch to the screen width minus horizontal margins.  
- Anchoring both `top: true` AND `bottom: true` forces height to the screen height minus vertical margins.  
- If only one horizontal or vertical anchor is set, the panel takes its size from its child items' `implicitWidth` / `implicitHeight`.

### Margins

Margins only apply to edges where anchors are active.

PanelWindow {

    // Floating island dock at the top center

    anchors {

        top: true

    }

    margins {

        top: 10

    }

    // Panel will be centered horizontally by default with 10px gap from top

}

---

## 3\. Exclusion Modes & Zones

### `ExclusionMode` Values

- **`ExclusionMode.Auto`**: Quickshell automatically computes the required exclusive zone based on the panel's height or width.  
- **`ExclusionMode.Normal`**: Uses the explicit integer assigned to `exclusiveZone`.  
- **`ExclusionMode.Ignore`**: No space is reserved. Tiling window managers will place windows directly underneath or over the panel.

PanelWindow {

    anchors {

        top: true

        left: true

        right: true

    }

    height: 36

    // Windows cannot overlap this 36px bar:

    exclusionMode: ExclusionMode.Normal

    exclusiveZone: 36

}

---

## 4\. Multi-Monitor Replication Pattern

To replicate a panel across all active displays, wrap `PanelWindow` in `Variants`:

import Quickshell

import QtQuick

ShellRoot {

    Variants {

        model: Quickshell.screens

        delegate: Component {

            PanelWindow {

                required property ShellScreen modelData

                screen: modelData

                anchors {

                    top: true

                    left: true

                    right: true

                }

                height: 32

                color: "\#1e1e2e"

                Text {

                    anchors.centerIn: parent

                    text: "Display: " \+ screen.name

                    color: "white"

                }

            }

        }

    }

}

Next, see [Floating & Popup Windows](http://02-windows-and-surfaces/floating-and-popups.md).

---

# Floating & Popup Windows

Beyond fixed edge panels, Quickshell offers `FloatingWindow` for unconstrained floating surfaces and `PopupWindow` for reactive, anchored popups.

## 1\. `FloatingWindow`

`FloatingWindow` is a standard desktop window that does not reserve space or dock to screen edges. It is ideal for application launchers, system monitors, audio mixers, or detached settings dashboards.

### Import

import Quickshell

### Property Specification

| Property | Type | Description |
| :---- | :---- | :---- |
| `title` | `string` | Window title exposed to the compositor / taskbar. |
| `width` / `height` | `int` | Explicit window dimensions. |
| `color` | `color` | Background color. Use `"transparent"` for custom shapes. |
| `screen` | `ShellScreen` | The screen where the window is initially created. |
| `visible` | `bool` | Toggles window visibility. |

### Example: Modal Dialog

import Quickshell

import QtQuick

FloatingWindow {

    id: win

    title: "System Dashboard"

    width: 400

    height: 300

    color: "\#181825"

    visible: true

    Rectangle {

        anchors.fill: parent

        anchors.margins: 16

        color: "\#313244"

        radius: 12

        Text {

            anchors.centerIn: parent

            text: "Hello from Quickshell FloatingWindow"

            color: "\#cdd6f4"

            font.pixelSize: 16

        }

    }

}

---

## 2\. `PopupWindow`

`PopupWindow` creates a lightweight overlay positioned relative to an anchor point or another window surface (such as a drop-down menu or tray popup).

### Anchoring with `PopupAnchor`

A `PopupWindow` contains a `PopupAnchor` object:

PopupWindow {

    id: popup

    anchor {

        window: parentPanel

        rect.x: 100

        rect.y: 0

        rect.width: 40

        rect.height: 32

        edges: Edges.Bottom

        gravity: Edges.Bottom

        adjustment: PopupAdjustment.SlideX | PopupAdjustment.FlipY

    }

}

### `PopupAdjustment` Flags

When the popup hits the screen edge, `PopupAdjustment` handles repositioning:

- **`SlideX` / `SlideY`**: Slides the window along the axis to remain on-screen.  
- **`FlipX` / `FlipY`**: Flips the anchor side (e.g. displays above instead of below).  
- **`None`**: Enforces strict coordinates without constraint checks.

Next, see [Menus & Popovers](http://02-windows-and-surfaces/menus.md).

---

# Menus & Popovers (`QsMenu`)

Quickshell provides native support for hierarchical menus, primarily used for System Tray context menus, application global menus, and right-click actions.

## Module Import

import Quickshell

---

## 1\. Core Menu Primitives

| Type | Nature | Description |
| :---- | :---- | :---- |
| `QsMenuAnchor` | Object | The positioner and controller that binds a menu handle to screen geometry. |
| `QsMenuOpener` | Component | Opens submenus or attached menu structures. |
| `QsMenuHandle` | Interface | Opaque handle representing a system or DBus menu tree. |
| `QsMenuEntry` | Object | Individual item inside a menu tree. |
| `QsMenuButtonType` | Enum | Button state representation: `None`, `CheckBox`, `RadioButton`. |

---

## 2\. `QsMenuEntry` Properties

| Property | Type | Description |
| :---- | :---- | :---- |
| `text` | `string` | Label of the menu entry. |
| `icon` | `string` | Icon URL / freedesktop icon name. |
| `enabled` | `bool` | Whether the item is interactive. |
| `isSeparator` | `bool` | If true, renders as a visual separator line. |
| `hasChildren` | `bool` | If true, item contains a nested submenu. |
| `buttonType` | `QsMenuButtonType` | Indicates whether item has a check or radio button. |
| `checkState` | `Qt.CheckState` | `Qt.Unchecked`, `Qt.PartiallyChecked`, or `Qt.Checked`. |

---

## 3\. Opening a System Tray Menu

import Quickshell

import Quickshell.Services.SystemTray

import QtQuick

Item {

    id: trayItemDelegate

    required property SystemTrayItem modelData

    QsMenuAnchor {

        id: menuAnchor

        menu: modelData.menu

        anchor.window: parentWindow

    }

    MouseArea {

        anchors.fill: parent

        acceptedButtons: Qt.LeftButton | Qt.RightButton

        onClicked: mouse \=\> {

            if (mouse.button \=== Qt.RightButton && modelData.hasMenu) {

                menuAnchor.open();

            } else {

                modelData.activate();

            }

        }

    }

}

Continue to [Wayland & Compositor Protocols](http://03-wayland-and-compositor/index.md).

---

# Wayland & Compositor Protocols Hub

The `Quickshell.Wayland` module provides native implementations of modern Wayland protocols. It enables low-level integration with compositors like Hyprland, Sway, Wayfire, River, and KDE KWin.

## Topic Overview

| Document | Primary Scope | Protocols / Key Types |
| :---- | :---- | :---- |
| [Layer Shell](http://03-wayland-and-compositor/layer-shell.md) | Surface layering & exclusive monitor space | `WlrLayershell`, `WlrLayer`, `WlrKeyboardFocus` (`zwlr_layer_shell_v1`) |
| [Session Lock](http://03-wayland-and-compositor/session-lock.md) | Secure lockscreen surfaces | `WlSessionLock`, `WlSessionLockSurface` (`ext_session_lock_v1`) |
| [Screencopy & Effects](http://03-wayland-and-compositor/screencopy-and-effects.md) | Screen capture, background blur, idle control | `ScreencopyView`, `BackgroundEffect`, `IdleInhibitor`, `IdleMonitor` |
| [Toplevel Management](http://03-wayland-and-compositor/toplevel-management.md) | Taskbars, window control, app switchers | `ToplevelManager`, `Toplevel` (`zwlr_foreign_toplevel_management_v1`) |

---

## Wayland Protocol Matrix

| Feature | Protocol Identifier | Supported Compositors |
| :---- | :---- | :---- |
| **Layer Shell** | `zwlr_layer_shell_v1` | Hyprland, Sway, River, Wayfire, Niri |
| **Session Lock** | `ext_session_lock_v1` | Hyprland, Sway, River, Niri, Labwc |
| **Screencopy** | `wlr-screencopy-unstable-v1` / `ext-image-copy-capture-v1` | Hyprland, Sway, wlroots-based |
| **Background Blur** | `ext-background-effect-v1` | Hyprland, Wayfire (compositors with blur protocol) |
| **Toplevel Mgmt** | `zwlr_foreign_toplevel_management_v1` | Hyprland, Sway, River |
| **Idle Control** | `ext_idle_notifier_v1` / `zwp_idle_inhibit_manager_v1` | Most modern Wayland compositors |

Start with [Layer Shell](http://03-wayland-and-compositor/layer-shell.md).

---

# Wayland Layer Shell (`WlrLayershell`)

The Layer Shell protocol (`zwlr_layer_shell_v1`) allows desktop components to attach themselves to specific Z-order layers on Wayland outputs.

## Module Import

import Quickshell

import Quickshell.Wayland

---

## 1\. Attached Object: `WlrLayershell`

While `PanelWindow` wraps layer-shell automatically, accessing the attached `WlrLayershell` object unlocks Wayland-specific features:

PanelWindow {

    id: win

    // Attach Wayland layer shell properties

    WlrLayershell.layer: WlrLayer.Top

    WlrLayershell.keyboardFocus: WlrKeyboardFocus.OnDemand

    WlrLayershell.namespace: "my-custom-bar"

}

---

## 2\. Layer Levels (`WlrLayer`)

| Value | Stacking Position | Primary Use Case |
| :---- | :---- | :---- |
| `WlrLayer.Background` | Bottom-most layer, below wallpaper and icons | Desktop wallpaper rendering, desktop live canvases |
| `WlrLayer.Bottom` | Above background, below normal windows | Desktop widgets, system monitoring backdrops |
| `WlrLayer.Top` | Above normal windows, below lock/popups | Status bars, docks, taskbars |
| `WlrLayer.Overlay` | Above all standard surfaces | Notifications, full-screen launchers, OSDs |

---

## 3\. Keyboard Focus Modes (`WlrKeyboardFocus`)

| Enum Value | Focus Behavior | Details |
| :---- | :---- | :---- |
| `WlrKeyboardFocus.None` | Never receives key events | Standard top bars, hardware stats, clock widgets. |
| `WlrKeyboardFocus.OnDemand` | Receives focus when clicked | Text entry dialogs, search inputs, interactive applets. |
| `WlrKeyboardFocus.Exclusive` | Locks all keyboard input to this window | Fullscreen launchers, modal dialogs. **Do not use for lockscreens.** |

> **Security Note**: Never use `WlrKeyboardFocus.Exclusive` to build a lockscreen. If Quickshell crashes while using layer shell, the compositor exposes the underlying desktop. Use [WlSessionLock](http://03-wayland-and-compositor/session-lock.md) instead.

---

## 4\. Fullscreen Overlay Launcher Example

import Quickshell

import Quickshell.Wayland

import QtQuick

PanelWindow {

    id: launcher

    anchors {

        top: true

        bottom: true

        left: true

        right: true

    }

    color: "\#80000000" // Dimmed backdrop

    WlrLayershell.layer: WlrLayer.Overlay

    WlrLayershell.keyboardFocus: WlrKeyboardFocus.Exclusive

    Rectangle {

        anchors.centerIn: parent

        width: 500

        height: 350

        color: "\#1e1e2e"

        radius: 12

        TextInput {

            id: searchInput

            anchors.top: parent.top

            anchors.left: parent.left

            anchors.right: parent.right

            anchors.margins: 20

            font.pixelSize: 18

            color: "white"

            focus: true

        }

    }

}

Next, see [Session Lock](http://03-wayland-and-compositor/session-lock.md).

---

# Wayland Session Lock (`WlSessionLock`)

Quickshell implements secure screen locking via the official `ext_session_lock_v1` Wayland protocol.

## Module Import

import Quickshell

import Quickshell.Wayland

---

## 1\. Security Architecture

1. **Protocol Guarantee**: When `WlSessionLock.locked` is set to `true`, the compositor grants a dedicated lock surface for each connected screen. Normal windows are hidden and user input is isolated.  
2. **Crash-Safe (Fail-Closed)**: If Quickshell crashes or terminates while locked without setting `locked = false`, compliant Wayland compositors keep the displays blanked with a solid color. Your desktop is never exposed.  
3. **Exclusive Surface**: Only one session lock client can be active at any given moment.

---

## 2\. API Reference

### `WlSessionLock`

| Property | Type | Description |
| :---- | :---- | :---- |
| `locked` | `bool` | Controls lock activation. Set to `true` to engage lock, `false` upon successful unlock. |
| `secure` | `bool` (readonly) | `true` once the compositor confirms all outputs are securely covered. |
| `surface` | `Component` | Delegate component instantiated once per connected screen. Must produce a `WlSessionLockSurface`. |

### `WlSessionLockSurface`

Represents the fullscreen locking surface on an individual output.

| Property | Type | Description |
| :---- | :---- | :---- |
| `screen` | `ShellScreen` | The monitor assigned to this surface instance. |
| `color` | `color` | Background fill color. |

---

## 3\. Minimal Functional Lockscreen Example

import Quickshell

import Quickshell.Wayland

import QtQuick

import QtQuick.Controls

ShellRoot {

    WlSessionLock {

        id: sessionLock

        locked: true // Engages the lock immediately

        surface: Component {

            WlSessionLockSurface {

                id: lockSurface

                color: "\#11111b"

                Column {

                    anchors.centerIn: parent

                    spacing: 20

                    Text {

                        anchors.horizontalCenter: parent.horizontalCenter

                        text: "Screen Locked"

                        color: "\#cdd6f4"

                        font.pixelSize: 28

                    }

                    TextField {

                        id: passwordInput

                        anchors.horizontalCenter: parent.horizontalCenter

                        echoMode: TextInput.Password

                        placeholderText: "Enter password"

                        focus: true

                        onAccepted: {

                            // Validate with PAM (see Quickshell.Services.Pam)

                            if (passwordInput.text \=== "secret") {

                                sessionLock.locked \= false;

                            } else {

                                passwordInput.text \= "";

                            }

                        }

                    }

                }

            }

        }

    }

}

Next, see [Screencopy & Effects](http://03-wayland-and-compositor/screencopy-and-effects.md).

---

# Screencopy, Blur & Idle Controls

## 1\. Screencopy (`ScreencopyView`)

`ScreencopyView` renders live video frames or still images captured from monitors or windows via `wlr-screencopy-unstable-v1` or `ext-image-copy-capture-v1`.

### Module Import

import Quickshell.Wayland

### Properties

| Property | Type | Description |
| :---- | :---- | :---- |
| `captureSource` | `QtObject` | Target to capture: `ShellScreen` (monitor) or `Toplevel` (window). |
| `live` | `bool` | `true` for continuous live streaming, `false` for a static snapshot. |
| `hasContent` | `bool` (readonly) | `true` when valid frame data is ready to display. |
| `paintCursor` | `bool` | If true, draws the hardware cursor over the capture. Defaults to `false`. |
| `sourceSize` | `size` (readonly) | Physical dimensions of the captured stream. |
| `constraintSize` | `size` | Constrains implicit size while maintaining source aspect ratio. |

### Example: Live Monitor Mirror / Thumbnail

import Quickshell

import Quickshell.Wayland

import QtQuick

Rectangle {

    width: 320

    height: 180

    color: "black"

    ScreencopyView {

        anchors.fill: parent

        captureSource: Quickshell.screens\[0\]

        live: true

        paintCursor: true

    }

}

---

## 2\. Background Blur (`BackgroundEffect`)

`BackgroundEffect` is an attached object that directs compatible compositors to apply real-time background blur and translucency effects behind a `QsWindow`.

### Properties

| Property | Type | Description |
| :---- | :---- | :---- |
| `radius` | `real` | Blur kernel radius. |
| `noise` | `real` | Grain/noise overlay factor. |

### Usage

PanelWindow {

    color: "\#801e1e2e" // Semi-transparent background

    BackgroundEffect.radius: 20

}

---

## 3\. Idle Controls

- **`IdleInhibitor`**: When enabled inside a window, prevents the compositor from blanking the screen or entering power-saving sleep.  
- **`IdleMonitor`**: Listens for user inactivity notifications and triggers lockscreens or sleep routines.  
- **`ShortcutInhibitor`**: Inhibits global compositor shortcuts when active, passing keypresses directly to the surface.

Next, see [Toplevel Management](http://03-wayland-and-compositor/toplevel-management.md).

---

# Foreign Toplevel Management

The `ToplevelManager` interface interacts with `zwlr_foreign_toplevel_management_v1` to track and control open application windows across the compositor.

## Module Import

import Quickshell.Wayland

---

## 1\. `ToplevelManager` Singleton

| Property | Type | Description |
| :---- | :---- | :---- |
| `toplevels` | `ObjectModel<Toplevel>` | Live collection of all active client windows. |

---

## 2\. `Toplevel` Object Properties & Methods

| Property | Type | Description |
| :---- | :---- | :---- |
| `title` | `string` (readonly) | Window title reported by the client application. |
| `appId` | `string` (readonly) | Desktop application ID (e.g. `org.mozilla.firefox`, `kitty`). |
| `activated` | `bool` (readonly) | `true` if the window currently holds keyboard focus. |
| `maximized` | `bool` (readonly) | Whether the window is currently maximized. |
| `minimized` | `bool` (readonly) | Whether the window is minimized. |
| `fullscreen` | `bool` (readonly) | Whether the window is in fullscreen mode. |

### Control Methods

- **`activate()`**: Focuses and raises the window.  
- **`close()`**: Requests the client window to close.  
- **`requestMaximized(bool state)`**: Toggles maximized state.  
- **`requestMinimized(bool state)`**: Toggles minimized state.  
- **`requestFullscreen(bool state)`**: Toggles fullscreen state.

---

## 3\. Example: Dynamic Taskbar / Window Switcher

import Quickshell

import Quickshell.Wayland

import QtQuick

import QtQuick.Layouts

RowLayout {

    spacing: 6

    Repeater {

        model: ToplevelManager.toplevels

        delegate: Rectangle {

            required property Toplevel modelData

            Layout.preferredWidth: 140

            Layout.preferredHeight: 28

            color: modelData.activated ? "\#45475a" : "\#313244"

            radius: 4

            Text {

                anchors.fill: parent

                anchors.margins: 4

                text: modelData.title

                color: "\#cdd6f4"

                elide: Text.ElideRight

                verticalAlignment: Text.AlignVCenter

            }

            MouseArea {

                anchors.fill: parent

                onClicked: modelData.activate()

            }

        }

    }

}

Continue to [System I/O, Processes & IPC](http://04-io-and-system/index.md).

---

# System I/O, Processes & IPC Hub

The `Quickshell.Io` module provides asynchronous, non-blocking input/output abstractions that integrate directly into the QtQuick event loop.

## Topic Overview

| Document | Primary Scope | Key Types |
| :---- | :---- | :---- |
| [Process Execution & Parsers](http://04-io-and-system/process.md) | Spawning subprocesses and reading streams | `Process`, `StdioCollector`, `SplitParser`, `DataStream` |
| [File Watching & JSON Adapters](http://04-io-and-system/file-view.md) | Reactive file watching and persistent JSON state | `FileView`, `FileViewAdapter`, `JsonAdapter`, `JsonObject` |
| [Sockets & IPC Handlers](http://04-io-and-system/sockets-and-ipc.md) | Unix domain sockets and external CLI control | `Socket`, `SocketServer`, `IpcHandler` |

---

## Architectural Principles of `Quickshell.Io`

1. **Non-Blocking Execution**: Never freeze the UI thread while awaiting system data.  
2. **Stream Pipelining**: Decouple raw binary/text data sources (`DataStream`) from interpretation logic (`DataStreamParser`).  
3. **Reactive Persistence**: File changes on disk propagate directly into QML property bindings.

Start with [Process Execution & Parsers](http://04-io-and-system/process.md).

---

# Process Execution & Parsers

The `Process` API executes external binaries and scripts asynchronously, while `StdioCollector` and `SplitParser` process standard output.

## Module Import

import Quickshell.Io

---

## 1\. `Process` API Specification

### Properties

| Property | Type | Default | Description |
| :---- | :---- | :---- | :---- |
| `command` | `list<string>` | `[]` | Binary executable followed by arguments. |
| `running` | `bool` | `false` | Setting to `true` spawns the process; setting to `false` terminates it. |
| `environment` | `list<string>` | inherited | Additional environment variables (`KEY=VALUE`). |
| `workingDirectory` | `string` | current dir | Working directory for the spawned process. |
| `stdout` | `DataStream` | readonly | Standard output data stream. |
| `stderr` | `DataStream` | readonly | Standard error data stream. |

### Methods & Signals

- **`exec(list<string> args)`**: Spawns process with new arguments, terminating any running instance.  
- **`terminate()`**: Sends `SIGTERM`.  
- **`kill()`**: Sends `SIGKILL`.  
- **`exited(int exitCode)`**: Emitted when the process terminates.

---

## 2\. Reading Output with `StdioCollector`

Use `StdioCollector` when you want the complete output of a short-lived command as a single text string:

import Quickshell

import Quickshell.Io

import QtQuick

Item {

    property string uptimeText: "Loading..."

    Process {

        id: uptimeProc

        command: \["uptime", "-p"\]

        running: true

        stdout: StdioCollector {

            onStreamFinished: {

                uptimeText \= text.trim();

            }

        }

    }

    Timer {

        interval: 10000

        running: true

        repeat: true

        onTriggered: uptimeProc.running \= true

    }

}

---

## 3\. Streaming Continuous Output with `SplitParser`

For long-running monitoring daemons (e.g. listening to compositor events, `playerctl -F`, or system sensors), use `SplitParser` to receive line-by-line updates without waiting for process exit:

import Quickshell.Io

import QtQuick

Item {

    property string currentTitle: ""

    Process {

        id: playerctl

        command: \["playerctl", "metadata", "--format", "{{title}}", "--follow"\]

        running: true

        stdout: SplitParser {

            splitMarker: "\\n"

            onRead: data \=\> {

                currentTitle \= data.trim();

            }

        }

    }

}

Next, see [File Watching & JSON Adapters](http://04-io-and-system/file-view.md).

---

# File Watching & JSON Adapters

`FileView` provides reactive file access, watching files on disk and automatically notifying QML when contents change.

## Module Import

import Quickshell.Io

---

## 1\. `FileView` Specification

### Properties

| Property | Type | Description |
| :---- | :---- | :---- |
| `path` | `string` | Path to the target file on disk. |
| `text` | `string` (readonly) | File content interpreted as UTF-8 text. |
| `raw` | `ArrayBuffer` (readonly) | Raw binary content of the file. |
| `adapter` | `FileViewAdapter` | Optional data adapter (e.g. `JsonAdapter`). |
| `watchChanges` | `bool` | If true, watches for inotify disk changes. Defaults to `true`. |
| `error` | `FileViewError` | Current error status if file cannot be read. |

### Reading System Statistics (`/sys` / `/proc`)

import Quickshell.Io

import QtQuick

Item {

    FileView {

        id: cpuTemp

        path: "/sys/class/thermal/thermal\_zone0/temp"

    }

    Text {

        text: "Temp: " \+ (parseInt(cpuTemp.text) / 1000).toFixed(1) \+ " °C"

    }

}

---

## 2\. Persistent State with `JsonAdapter` & `JsonObject`

`JsonAdapter` automatically parses JSON files into reactive objects and writes back changes to disk.

import Quickshell

import Quickshell.Io

import QtQuick

Item {

    FileView {

        id: settingsFile

        path: Quickshell.stateDir \+ "/settings.json"

        adapter: JsonAdapter {

            id: jsonState

            // Structure synced bidirectionally to disk

        }

    }

    // Access parsed JSON properties directly

    property bool darkMode: jsonState.data ? jsonState.data.darkMode : true

    function toggleDarkMode() {

        if (jsonState.data) {

            jsonState.data.darkMode \= \!darkMode;

            jsonState.save(); // Commits back to settings.json

        }

    }

}

Next, see [Sockets & IPC Handlers](http://04-io-and-system/sockets-and-ipc.md).

---

# Unix Sockets & External IPC

Quickshell enables bidirectional communication between external shell scripts/CLI commands and running QML interfaces.

## Module Import

import Quickshell.Io

---

## 1\. `IpcHandler` (Exposing Shell Functions to External CLI)

`IpcHandler` allows you to register named endpoints that can be invoked via external commands or keybindings.

### Example: Toggle a Quickshell Window via Keybinding

// In your shell.qml or singleton

import Quickshell

import Quickshell.Io

import QtQuick

Scope {

    property bool launcherVisible: false

    IpcHandler {

        target: "launcher"

        function toggle(): void {

            launcherVisible \= \!launcherVisible;

        }

        function show(): void {

            launcherVisible \= true;

        }

        function hide(): void {

            launcherVisible \= false;

        }

    }

}

### Triggering via CLI or Window Manager

External shell scripts or Hyprland keybinds invoke the IPC handler using `quickshell ipc call`:

\# In hyprland.conf:

\# bind \= SUPER, SPACE, exec, qs ipc call launcher toggle

qs ipc call launcher toggle

---

## 2\. Unix Domain Sockets (`Socket` & `SocketServer`)

### `SocketServer`

Listens on a Unix domain socket path:

import Quickshell.Io

SocketServer {

    path: "/tmp/quickshell-custom.sock"

    active: true

    onClientConnected: client \=\> {

        client.onMessageReceived: msg \=\> {

            console.log("Received socket message:", msg);

            client.send("ACK: " \+ msg);

        }

    }

}

### `Socket` (Client)

Connects to an existing Unix socket (e.g. Sway IPC, custom daemon):

Socket {

    id: clientSocket

    path: "/tmp/custom-daemon.sock"

    connected: true

    onDataReceived: data \=\> console.log(data)

}

Continue to [Desktop Services](http://05-desktop-services/index.md).

---

# Desktop Services Hub (`Quickshell.Services.*`)

Quickshell embeds native C++ service daemons and clients for standard Linux desktop integrations under `Quickshell.Services.*`.

## Topic Overview

| Document | Primary Scope | Key Singletons & Types |
| :---- | :---- | :---- |
| [System Tray](http://05-desktop-services/system-tray.md) | StatusNotifierItem (SNI) tray host | `SystemTray`, `SystemTrayItem`, `QsMenuAnchor` |
| [Notifications](http://05-desktop-services/notifications.md) | Desktop Notifications daemon | `NotificationServer`, `Notification`, `NotificationAction` |
| [Media Player (MPRIS)](http://05-desktop-services/mpris.md) | MPRIS2 media controller | `Mpris`, `MprisPlayer`, `MprisPlaybackState` |
| [PipeWire Audio](http://05-desktop-services/pipewire.md) | PipeWire graph, volume, VU meters | `Pipewire`, `PwNode`, `PwNodeAudio`, `PwNodePeakMonitor` |
| [UPower & Power Profiles](http://05-desktop-services/upower.md) | Battery status and power modes | `UPower`, `UPowerDevice`, `PowerProfiles` |
| [Polkit, PAM & Greetd](http://05-desktop-services/polkit-pam-greetd.md) | Privilege auth, lockscreens, greeters | `PolkitAgent`, `PamContext`, `Greetd` |

Start with [System Tray](http://05-desktop-services/system-tray.md).

---

# System Tray Service (`Quickshell.Services.SystemTray`)

Quickshell provides a complete StatusNotifierItem (SNI) system tray host implementation.

## Module Import

import Quickshell.Services.SystemTray

---

## 1\. `SystemTray` Singleton

Referencing `SystemTray` automatically starts tracking the tray bus.

| Property | Type | Description |
| :---- | :---- | :---- |
| `items` | `ObjectModel<SystemTrayItem>` | Live list of all active system tray items. |

---

## 2\. `SystemTrayItem` Specification

| Property | Type | Description |
| :---- | :---- | :---- |
| `id` | `string` | Unique identifier of the tray item. |
| `title` | `string` | Human-readable title. |
| `icon` | `string` | Freedesktop icon name or icon path. |
| `tooltipTitle` | `string` | Tooltip headline text. |
| `tooltipDescription` | `string` | Tooltip descriptive body. |
| `hasMenu` | `bool` | `true` if item provides a DBus context menu. |
| `menu` | `QsMenuHandle` | Opaque handle for binding with `QsMenuAnchor`. |

### Methods

- **`activate(int x, int y)`**: Triggers default action (usually left-click).  
- **`secondaryActivate(int x, int y)`**: Triggers secondary action (middle-click).  
- **`scroll(int delta, bool horizontal)`**: Forwards mouse wheel events.

---

## 3\. Complete Tray Implementation

import Quickshell

import Quickshell.Services.SystemTray

import Quickshell.Widgets

import QtQuick

import QtQuick.Layouts

RowLayout {

    spacing: 6

    Repeater {

        model: SystemTray.items

        delegate: Item {

            required property SystemTrayItem modelData

            Layout.preferredWidth: 22

            Layout.preferredHeight: 22

            QsMenuAnchor {

                id: trayMenu

                menu: modelData.menu

                anchor.window: parentWindow

            }

            IconImage {

                anchors.fill: parent

                source: modelData.icon

            }

            MouseArea {

                anchors.fill: parent

                acceptedButtons: Qt.LeftButton | Qt.RightButton

                onClicked: mouse \=\> {

                    if (mouse.button \=== Qt.RightButton && modelData.hasMenu) {

                        trayMenu.open();

                    } else {

                        modelData.activate(0, 0);

                    }

                }

            }

        }

    }

}

Next, see [Notifications](http://05-desktop-services/notifications.md).

---

# Notifications Daemon (`Quickshell.Services.Notifications`)

Quickshell implements the freedesktop Desktop Notifications specification (`org.freedesktop.Notifications`).

## Module Import

import Quickshell.Services.Notifications

---

## 1\. `NotificationServer` Singleton

Instantiating or referencing `NotificationServer` claims the DBus name and begins receiving system notifications.

| Capability Property | Type | Default | Description |
| :---- | :---- | :---- | :---- |
| `trackedNotifications` | `ObjectModel<Notification>` | readonly | List of all active/unclosed notifications. |
| `bodySupported` | `bool` | `true` | Advertises notification body support. |
| `bodyMarkupSupported` | `bool` | `true` | Advertises HTML/Pango markup support in body. |
| `actionsSupported` | `bool` | `true` | Advertises action button support. |
| `persistenceSupported` | `bool` | `true` | Advertises notification center storage. |
| `keepOnReload` | `bool` | `true` | Preserves notifications across Quickshell reloads. |

---

## 2\. `Notification` Object Specification

| Property | Type | Description |
| :---- | :---- | :---- |
| `id` | `int` | Unique notification ID assigned to the client. |
| `appName` | `string` | Sender application name (e.g. "Firefox", "Slack"). |
| `appIcon` | `string` | Icon name or path. |
| `summary` | `string` | Notification headline. |
| `body` | `string` | Notification text body. |
| `urgency` | `NotificationUrgency` | `Low`, `Normal`, or `Critical`. |
| `expireTimeout` | `real` | Timeout in seconds requested by sender (-1 for default). |
| `actions` | `list<NotificationAction>` | Action buttons attached to the notification. |
| `image` | `string` | Preview image URL/path if provided. |

### Methods

- **`dismiss()`**: Closes notification and notifies the client.  
- **`invokeAction(string actionId)`**: Invokes the selected action button callback.

---

## 3\. Popup Notification Banner Example

import Quickshell

import Quickshell.Services.Notifications

import QtQuick

import QtQuick.Layouts

PanelWindow {

    anchors.top: true

    anchors.right: true

    margins { top: 20; right: 20 }

    width: 320

    height: notifColumn.implicitHeight

    color: "transparent"

    Column {

        id notifColumn

        width: parent.width

        spacing: 10

        Repeater {

            model: NotificationServer.trackedNotifications

            delegate: Rectangle {

                required property Notification modelData

                width: 320

                height: 80

                color: modelData.urgency \=== NotificationUrgency.Critical ? "\#f38ba8" : "\#1e1e2e"

                radius: 8

                Column {

                    anchors.fill: parent

                    anchors.margins: 10

                    spacing: 4

                    Text {

                        text: modelData.summary

                        font.bold: true

                        color: "white"

                        elide: Text.ElideRight

                    }

                    Text {

                        text: modelData.body

                        color: "\#cdd6f4"

                        font.pixelSize: 12

                        elide: Text.ElideRight

                    }

                }

                MouseArea {

                    anchors.fill: parent

                    onClicked: modelData.dismiss()

                }

            }

        }

    }

}

Next, see [Media Player (MPRIS)](http://05-desktop-services/mpris.md).

---

# Media Player Controller (`Quickshell.Services.Mpris`)

`Quickshell.Services.Mpris` provides reactive bindings for controlling media players (Spotify, VLC, Chromium, Firefox) over the MPRIS2 DBus interface.

## Module Import

import Quickshell.Services.Mpris

---

## 1\. `Mpris` Singleton

| Property | Type | Description |
| :---- | :---- | :---- |
| `players` | `ObjectModel<MprisPlayer>` | Collection of all active media players. |

---

## 2\. `MprisPlayer` Specification

| Property | Type | Description |
| :---- | :---- | :---- |
| `identity` | `string` | Display name of the media player (e.g. "Spotify"). |
| `playbackState` | `MprisPlaybackState` | `Playing`, `Paused`, `Stopped`. |
| `loopState` | `MprisLoopState` | `None`, `Track`, `Playlist`. |
| `shuffle` | `bool` | Shuffle mode toggle. |
| `volume` | `real` | Player volume (0.0 to 1.0). |
| `position` | `real` | Current playback position in seconds. |
| `length` | `real` | Total duration of current track in seconds. |
| `trackTitle` | `string` | Title of currently playing media. |
| `trackArtists` | `list<string>` | Artist list. |
| `trackAlbum` | `string` | Album name. |
| `artUrl` | `string` | Album art image URL. |
| `canControl` | `bool` | If true, playback commands are supported. |

### Control Methods

- **`play()`**, **`pause()`**, **`playPause()`**, **`stop()`**  
- **`next()`**, **`previous()`**  
- **`setPosition(real positionSeconds)`**

---

## 3\. Mini Media Player Widget Example

import Quickshell

import Quickshell.Services.Mpris

import QtQuick

import QtQuick.Layouts

RowLayout {

    spacing: 12

    visible: Mpris.players.length \> 0

    readonly property MprisPlayer activePlayer: Mpris.players\[0\]

    Text {

        text: activePlayer ? (activePlayer.trackTitle \+ " \- " \+ activePlayer.trackArtists.join(", ")) : ""

        color: "\#cdd6f4"

        elide: Text.ElideRight

        Layout.preferredWidth: 200

    }

    Rectangle {

        Layout.preferredWidth: 24

        Layout.preferredHeight: 24

        radius: 12

        color: "\#cba6f7"

        Text {

            anchors.centerIn: parent

            text: activePlayer && activePlayer.playbackState \=== MprisPlaybackState.Playing ? "⏸" : "▶"

            color: "\#11111b"

        }

        MouseArea {

            anchors.fill: parent

            onClicked: activePlayer.playPause()

        }

    }

}

Next, see [PipeWire Audio](http://05-desktop-services/pipewire.md).

---

# PipeWire Audio (`Quickshell.Services.Pipewire`)

Quickshell connects directly to the PipeWire graph daemon via libpipewire, offering audio volume control, device switching, stream management, and real-time audio peak metering.

## Module Import

import Quickshell.Services.Pipewire

---

## 1\. `Pipewire` Singleton

| Property | Type | Description |
| :---- | :---- | :---- |
| `ready` | `bool` (readonly) | `true` after initial synchronization with PipeWire daemon completes. |
| `defaultAudioSink` | `PwNode` (readonly) | Current default audio output (speakers/headphones). |
| `defaultAudioSource` | `PwNode` (readonly) | Current default audio input (microphone). |
| `preferredDefaultAudioSink` | `PwNode` | Writable hint setting default audio output. |
| `nodes` | `ObjectModel<PwNode>` | All active audio/video nodes on the system. |

---

## 2\. `PwNode` & `PwNodeAudio` Specification

### `PwNode`

- **`name`** / **`description`**: Hardware or application stream label.  
- **`isSink`**: `true` if node accepts sound (output device).  
- **`isStream`**: `true` if node is an application stream (e.g. Spotify), `false` for hardware.  
- **`audio`**: `PwNodeAudio` object (null if node does not carry audio).

### `PwNodeAudio`

| Property | Type | Description |
| :---- | :---- | :---- |
| `volume` | `real` | Volume multiplier (1.0 \= 100%, can exceed 1.0 for amplification). |
| `muted` | `bool` | Mute state. |
| `channels` | `list<PwAudioChannel>` | Channel mapping. |

---

## 3\. Real-Time VU Meter (`PwNodePeakMonitor`)

`PwNodePeakMonitor` attaches to a node to provide real-time audio amplitude for visualizers:

import Quickshell.Services.Pipewire

import QtQuick

Rectangle {

    width: 100

    height: 10

    color: "\#313244"

    PwNodePeakMonitor {

        id: peak

        node: Pipewire.defaultAudioSink

    }

    Rectangle {

        height: parent.height

        width: parent.width \* Math.min(1.0, peak.peak)

        color: "\#a6e3a1"

    }

}

---

## 4\. Master Volume Controller Example

import Quickshell

import Quickshell.Services.Pipewire

import QtQuick

import QtQuick.Layouts

RowLayout {

    spacing: 8

    readonly property PwNodeAudio audio: Pipewire.defaultAudioSink ? Pipewire.defaultAudioSink.audio : null

    Text {

        text: audio && audio.muted ? "🔇" : "🔊"

        color: "white"

        MouseArea {

            anchors.fill: parent

            onClicked: if (audio) audio.muted \= \!audio.muted

        }

    }

    Text {

        text: audio ? Math.round(audio.volume \* 100\) \+ "%" : "0%"

        color: "\#cdd6f4"

    }

    MouseArea {

        Layout.fillWidth: true

        Layout.preferredHeight: 20

        onWheel: wheel \=\> {

            if (\!audio) return;

            if (wheel.angleDelta.y \> 0\) {

                audio.volume \= Math.min(1.5, audio.volume \+ 0.05);

            } else {

                audio.volume \= Math.max(0.0, audio.volume \- 0.05);

            }

        }

    }

}

Next, see [UPower & Power Profiles](http://05-desktop-services/upower.md).

---

# UPower & Power Profiles

Quickshell monitors system battery health, power source status, and ACPI power profiles via UPower and `power-profiles-daemon`.

## Module Import

import Quickshell.Services.UPower

---

## 1\. `UPower` Singleton

| Property | Type | Description |
| :---- | :---- | :---- |
| `displayDevice` | `UPowerDevice` | Composite battery representing the primary system battery. |
| `devices` | `ObjectModel<UPowerDevice>` | All individual power devices (mouse, keyboard, laptop battery). |
| `onBattery` | `bool` | `true` when running on battery; `false` when plugged into AC power. |
| `lidIsClosed` | `bool` | Laptop lid status. |

---

## 2\. `UPowerDevice` Specification

| Property | Type | Description |
| :---- | :---- | :---- |
| `percentage` | `real` | Battery charge percentage (0.0 to 100.0). |
| `state` | `UPowerDeviceState` | `Charging`, `Discharging`, `FullyCharged`, `Empty`. |
| `type` | `UPowerDeviceType` | `Battery`, `LinePower`, `Mouse`, `Keyboard`. |
| `timeToEmpty` | `real` | Estimated seconds remaining on battery. |
| `timeToFull` | `real` | Estimated seconds until battery is fully charged. |

---

## 3\. `PowerProfiles` Singleton

Interfaces with `power-profiles-daemon`:

| Property | Type | Description |
| :---- | :---- | :---- |
| `activeProfile` | `string` | `"performance"`, `"balanced"`, or `"power-saver"`. Writable. |
| `profiles` | `list<string>` | Available profiles supported by hardware. |

---

## 4\. Battery Widget Example

import Quickshell.Services.UPower

import QtQuick

Rectangle {

    width: 60

    height: 24

    radius: 4

    color: "\#313244"

    readonly property real pct: UPower.displayDevice ? UPower.displayDevice.percentage : 100

    readonly property bool charging: UPower.displayDevice && UPower.displayDevice.state \=== UPowerDeviceState.Charging

    Text {

        anchors.centerIn: parent

        text: Math.round(pct) \+ "%" \+ (charging ? " ⚡" : "")

        color: pct \< 20 && \!charging ? "\#f38ba8" : "\#cdd6f4"

        font.pixelSize: 12

    }

}

Next, see [Polkit, PAM & Greetd](http://05-desktop-services/polkit-pam-greetd.md).

---

# Polkit, PAM & Greetd Services

Quickshell enables writing custom privileged authentication agents, lockscreens, and display manager login greeters in pure QML.

## 1\. Polkit Authentication Agent (`Quickshell.Services.Polkit`)

Enables building a Polkit graphical agent to authenticate administrative tasks (e.g. `pkexec`, package installation).

import Quickshell

import Quickshell.Services.Polkit

import QtQuick

import QtQuick.Controls

Scope {

    PolkitAgent {

        id: agent

        onFlowStarted: flow \=\> {

            // flow.actionId: ID of action requesting privilege

            // flow.message: User-facing prompt message

            // flow.respond(password): Submits credentials

            // flow.cancel(): Dismisses dialog

        }

    }

}

---

## 2\. PAM Authentication (`Quickshell.Services.Pam`)

`Quickshell.Services.Pam` authenticates user credentials directly against Linux Pluggable Authentication Modules (PAM), ideal for lockscreens.

import Quickshell.Services.Pam

import QtQuick

Item {

    PamContext {

        id: pam

        user: "vanitasu" // or environment user

        onSuccess: {

            console.log("Authentication successful\! Unlocking session...");

            sessionLock.locked \= false;

        }

        onError: err \=\> {

            console.log("Auth error:", err);

            passwordField.text \= "";

        }

    }

    function checkPassword(pwd) {

        pam.authenticate(pwd);

    }

}

---

## 3\. Greetd Display Manager Integration (`Quickshell.Services.Greetd`)

Build custom Wayland login screens and display managers for `greetd`.

import Quickshell.Services.Greetd

import QtQuick

Item {

    function login(username, password) {

        Greetd.createSession(username);

        Greetd.respond(password);

        Greetd.launch(\["Hyprland"\], \[\]);

    }

}

Continue to [Hardware & Connectivity](http://06-hardware-and-networks/index.md).

---

# Hardware & Connectivity Hub

Quickshell includes native modules for wireless hardware: Bluetooth (via BlueZ) and Networking (via NetworkManager).

## Topic Overview

| Document | Primary Scope | Key Singletons & Types |
| :---- | :---- | :---- |
| [Bluetooth API](http://06-hardware-and-networks/bluetooth.md) | BlueZ adapters, paired devices, battery levels | `Bluetooth`, `BluetoothAdapter`, `BluetoothDevice` |
| [Networking API](http://06-hardware-and-networks/networking.md) | NetworkManager Wi-Fi, Ethernet, connectivity | `Networking`, `WifiDevice`, `WifiNetwork`, `WiredDevice` |

Start with [Bluetooth API](http://06-hardware-and-networks/bluetooth.md).

---

# Bluetooth Management (`Quickshell.Bluetooth`)

The `Quickshell.Bluetooth` module connects directly to the Linux BlueZ daemon.

## Module Import

import Quickshell.Bluetooth

---

## 1\. `Bluetooth` Singleton

| Property | Type | Description |
| :---- | :---- | :---- |
| `adapters` | `ObjectModel<BluetoothAdapter>` | List of all system Bluetooth adapters (e.g. `hci0`). |
| `defaultAdapter` | `BluetoothAdapter` | The primary system adapter. |
| `devices` | `ObjectModel<BluetoothDevice>` | All discovered and paired Bluetooth devices. |

---

## 2\. `BluetoothAdapter` & `BluetoothDevice` Specification

### `BluetoothAdapter`

| Property | Type | Description |
| :---- | :---- | :---- |
| `name` | `string` | Adapter display name. |
| `enabled` | `bool` | Writable. Toggles Bluetooth power state. |
| `discovering` | `bool` | Writable. Set to `true` to initiate device discovery. |
| `pairable` | `bool` | Allows incoming pairing requests. |

### `BluetoothDevice`

| Property | Type | Description |
| :---- | :---- | :---- |
| `name` | `string` | Device advertising name. |
| `address` | `string` | Hardware MAC address (e.g. `00:11:22:33:44:55`). |
| `connected` | `bool` | Live connection status. |
| `paired` | `bool` | Pairing status. |
| `batteryPercentage` | `real` | Peripheral battery level (0.0 to 100.0, or \-1 if unsupported). |
| `rssi` | `int` | Signal strength indicator in dBm. |

### Methods

- **`connect()`**: Connects to the device.  
- **`disconnect()`**: Disconnects from the device.  
- **`pair()`**: Initiates pairing handshake.

---

## 3\. Bluetooth Status & Toggle Widget Example

import Quickshell

import Quickshell.Bluetooth

import QtQuick

import QtQuick.Layouts

RowLayout {

    spacing: 8

    readonly property BluetoothAdapter adapter: Bluetooth.defaultAdapter

    Rectangle {

        Layout.preferredWidth: 32

        Layout.preferredHeight: 24

        radius: 4

        color: adapter && adapter.enabled ? "\#89b4fa" : "\#45475a"

        Text {

            anchors.centerIn: parent

            text: "󰂯"

            color: adapter && adapter.enabled ? "\#11111b" : "\#cdd6f4"

        }

        MouseArea {

            anchors.fill: parent

            onClicked: {

                if (adapter) adapter.enabled \= \!adapter.enabled;

            }

        }

    }

}

Next, see [Networking API](http://06-hardware-and-networks/networking.md).

---

# Networking API (`Quickshell.Networking`)

The `Quickshell.Networking` module connects to NetworkManager to expose Wi-Fi access points, Ethernet links, and Internet connectivity states.

## Module Import

import Quickshell.Networking

---

## 1\. `Networking` Singleton

| Property | Type | Description |
| :---- | :---- | :---- |
| `connectivity` | `NetworkConnectivity` | `NoConnectivity`, `Portal`, `Limited`, or `Full`. |
| `devices` | `ObjectModel<NetworkDevice>` | All network interfaces. |
| `wifiDevices` | `ObjectModel<WifiDevice>` | Filtered list of wireless adapters. |
| `wiredDevices` | `ObjectModel<WiredDevice>` | Filtered list of Ethernet adapters. |

---

## 2\. `WifiDevice` & `WifiNetwork` Specification

### `WifiDevice`

- **`activeNetwork`**: Currently associated `WifiNetwork`.  
- **`networks`**: `ObjectModel<WifiNetwork>` of visible SSIDs.  
- **`scanning`**: `bool` indicating active background scan.  
- **`scan()`**: Triggers an immediate Wi-Fi network survey.

### `WifiNetwork`

| Property | Type | Description |
| :---- | :---- | :---- |
| `ssid` | `string` | Network name. |
| `strength` | `real` | Signal percentage (0.0 to 100.0). |
| `frequency` | `int` | Operating channel frequency (2.4 GHz vs 5 GHz). |
| `securityType` | `WifiSecurityType` | Security level (Open, WPA2, WPA3). |

---

## 3\. Wi-Fi Scanner Widget Example

import Quickshell

import Quickshell.Networking

import QtQuick

import QtQuick.Layouts

ColumnLayout {

    spacing: 6

    readonly property WifiDevice wifi: Networking.wifiDevices.length \> 0 ? Networking.wifiDevices\[0\] : null

    Text {

        text: wifi && wifi.activeNetwork ? ("Connected: " \+ wifi.activeNetwork.ssid) : "Wi-Fi Disconnected"

        color: "white"

        font.bold: true

    }

    Repeater {

        model: wifi ? wifi.networks : null

        delegate: Rectangle {

            required property WifiNetwork modelData

            Layout.preferredWidth: 200

            Layout.preferredHeight: 28

            color: "\#313244"

            radius: 4

            RowLayout {

                anchors.fill: parent

                anchors.margins: 6

                Text {

                    text: modelData.ssid

                    color: "\#cdd6f4"

                    Layout.fillWidth: true

                    elide: Text.ElideRight

                }

                Text {

                    text: Math.round(modelData.strength) \+ "%"

                    color: "\#a6e3a1"

                }

            }

        }

    }

}

Continue to [Window Managers & Compositors](http://07-window-managers/index.md).

---

# Window Managers & Compositors Hub

Quickshell provides first-class integrations with Linux window managers, including deep IPC hooks for Hyprland, i3/Sway, and generic multi-monitor workspace abstractions.

## Topic Overview

| Document | Primary Scope | Key Singletons & Types |
| :---- | :---- | :---- |
| [Hyprland Integration](http://07-window-managers/hyprland.md) | Workspaces, dispatchers, focus grab, shortcuts | `Hyprland`, `HyprlandToplevel`, `HyprlandFocusGrab`, `GlobalShortcut` |
| [i3 & Sway Integration](http://07-window-managers/i3-sway.md) | i3/Sway IPC, workspaces, outputs | `I3`, `I3IpcListener`, `I3Workspace`, `I3Monitor` |
| [WindowManager Abstraction](http://07-window-managers/windowmanager.md) | Universal multi-monitor workspace projection | `WindowManager`, `Windowset`, `WindowsetProjection` |

Start with [Hyprland Integration](http://07-window-managers/hyprland.md).

---

# Hyprland Integration (`Quickshell.Hyprland`)

Quickshell includes native C++ integrations for the Hyprland Wayland compositor, connecting directly to Hyprland's IPC socket without spawning external `hyprctl` processes.

## Module Import

import Quickshell.Hyprland

---

## 1\. `Hyprland` Singleton

| Property | Type | Description |
| :---- | :---- | :---- |
| `focusedWorkspace` | `HyprlandWorkspace` | Currently active workspace on the active monitor. |
| `focusedMonitor` | `HyprlandMonitor` | Currently focused output display. |
| `workspaces` | `ObjectModel<HyprlandWorkspace>` | All active workspaces in the compositor. |
| `monitors` | `ObjectModel<HyprlandMonitor>` | All monitors managed by Hyprland. |

### Methods & Signals

- **`dispatch(string command)`**: Dispatches any Hyprland command (e.g. `Hyprland.dispatch("workspace 3")`, `Hyprland.dispatch("killactive")`).  
- **`monitorFor(ShellScreen screen)`**: Translates a Quickshell `ShellScreen` to its matching `HyprlandMonitor`.  
- **`rawEvent(string name, string data)`**: Signal fired on every native Hyprland IPC event.

---

## 2\. `HyprlandFocusGrab` (Modal Dismissal)

Uses the `hyprland_focus_grab_v1` protocol to hold focus on a group of shell windows and auto-dismiss when clicking outside.

import Quickshell.Hyprland

import QtQuick

Scope {

    HyprlandFocusGrab {

        id: focusGrab

        active: launcherWindow.visible

        windows: \[launcherWindow\]

        onCleared: {

            // User clicked outside the launcher: close it

            launcherWindow.visible \= false;

        }

    }

}

---

## 3\. `GlobalShortcut` (Direct Keybinding Hooks)

Uses `hyprland_global_shortcuts_v1` to register keybinds directly from QML without configuring them in `hyprland.conf`:

import Quickshell.Hyprland

GlobalShortcut {

    name: "toggle-dashboard"

    description: "Toggles the Quickshell system dashboard"

    onPressed: {

        dashboardWindow.visible \= \!dashboardWindow.visible;

    }

}

---

## 4\. Complete Workspace Bar Example

import Quickshell

import Quickshell.Hyprland

import QtQuick

import QtQuick.Layouts

RowLayout {

    spacing: 6

    Repeater {

        model: 10 // Numbers 1 through 10

        delegate: Rectangle {

            required property int index

            readonly property int wsId: index \+ 1

            readonly property bool isCurrent: Hyprland.focusedWorkspace && Hyprland.focusedWorkspace.id \=== wsId

            Layout.preferredWidth: 28

            Layout.preferredHeight: 28

            radius: 6

            color: isCurrent ? "\#cba6f7" : "\#313244"

            Text {

                anchors.centerIn: parent

                text: wsId.toString()

                color: isCurrent ? "\#11111b" : "\#cdd6f4"

                font.bold: isCurrent

            }

            MouseArea {

                anchors.fill: parent

                onClicked: Hyprland.dispatch("workspace " \+ wsId)

            }

        }

    }

}

Next, see [i3 & Sway Integration](http://07-window-managers/i3-sway.md).

---

# i3 & Sway Integration (`Quickshell.I3`)

Quickshell connects to the i3 / Sway IPC protocol for tiling window management.

## Module Import

import Quickshell.I3

---

## 1\. `I3` Singleton & `I3Workspace`

| Property | Type | Description |
| :---- | :---- | :---- |
| `workspaces` | `ObjectModel<I3Workspace>` | List of all i3/Sway workspaces. |
| `monitors` | `ObjectModel<I3Monitor>` | Outputs recognized by i3/Sway. |

### Methods

- **`command(string cmd)`**: Dispatches an i3/Sway command string (e.g. `I3.command("workspace number 2")`).

### `I3Workspace` Properties

- **`num`**: Workspace number.  
- **`name`**: Workspace name.  
- **`focused`**: `true` if currently active.  
- **`urgent`**: `true` if client requested attention.

---

## 2\. Sway Workspace Indicator

import Quickshell.I3

import QtQuick

import QtQuick.Layouts

RowLayout {

    spacing: 4

    Repeater {

        model: I3.workspaces

        delegate: Rectangle {

            required property I3Workspace modelData

            Layout.preferredWidth: 24

            Layout.preferredHeight: 24

            radius: 4

            color: modelData.focused ? "\#89b4fa" : "\#313244"

            Text {

                anchors.centerIn: parent

                text: modelData.name

                color: modelData.focused ? "\#11111b" : "\#cdd6f4"

            }

            MouseArea {

                anchors.fill: parent

                onClicked: I3.command("workspace " \+ modelData.name)

            }

        }

    }

}

Next, see [WindowManager Abstraction](http://07-window-managers/windowmanager.md).

---

# Universal WindowManager Abstraction

`Quickshell.WindowManager` provides a compositor-agnostic abstraction for workspace sets and monitor projections, allowing shell widgets to run unchanged on Hyprland, Sway, River, or X11.

## Module Import

import Quickshell.WindowManager

---

## 1\. Key Primitives

| Type | Nature | Description |
| :---- | :---- | :---- |
| `WindowManager` | Singleton | Global window management interface. |
| `Windowset` | Object | A group of windows/workspaces worked with by a user. |
| `WindowsetProjection` | Object | Projection of a windowset across displays. |
| `ScreenProjection` | Object | The projection of windows occupying one specific screen. |

Use `WindowManager` when writing modular shell themes meant for distribution across multiple desktop setups.

Continue to [Core Utilities, Types & Widgets](http://08-core-types-and-widgets/index.md).

---

# Core Utilities, Types & Widgets Hub

Quickshell contains foundational types and visual helpers that simplify screen handling, clock synchronization, application launching, and widget padding.

## Topic Overview

| Document | Primary Scope | Key Singletons & Types |
| :---- | :---- | :---- |
| [Core Types & Utilities](http://08-core-types-and-widgets/core-types.md) | Global singleton, screens, clock, desktop apps | `Quickshell`, `ShellScreen`, `SystemClock`, `DesktopEntries`, `Variants` |
| [Quickshell Widgets](http://08-core-types-and-widgets/widgets.md) | Visual UI utilities and wrappers | `WrapperItem`, `MarginWrapperManager`, `ClippingRectangle`, `IconImage` |

Start with [Core Types & Utilities](http://08-core-types-and-widgets/core-types.md).

---

# Core Types & Global Singletons

## 1\. `Quickshell` Global Singleton

The `Quickshell` singleton provides root environmental information and process state.

### Properties

| Property | Type | Description |
| :---- | :---- | :---- |
| `screens` | `list<ShellScreen>` | List of all currently connected monitor displays. |
| `clipboardText` | `string` | System clipboard text (bidirectional read/write). |
| `stateDir` | `string` | Path to persistent state directory (`~/.local/state/quickshell/<config>`). |
| `cacheDir` | `string` | Path to cache directory (`~/.cache/quickshell/<config>`). |
| `dataDir` | `string` | Path to shared data directory (`~/.local/share/quickshell/<config>`). |
| `processId` | `int` | PID of the running Quickshell process. |

### Methods

- **`reload()`**: Manually triggers a reload of all active configurations.

---

## 2\. `ShellScreen` Specification

Represents an individual physical display output:

- **`name`**: Connector label (`eDP-1`, `DP-1`, `HDMI-A-1`).  
- **`model`** / **`serialNumber`**: Hardware identifier strings.  
- **`x`**, **`y`**, **`width`**, **`height`**: Output geometry.  
- **`devicePixelRatio`**: Fractional or integer display scale factor.

---

## 3\. `SystemClock` Singleton

Provides efficient time updates synchronized with system time.

| Property | Type | Description |
| :---- | :---- | :---- |
| `date` | `Date` | Reactive JavaScript `Date` object. |
| `precision` | `SystemClock.Precision` | `Minutes` or `Seconds`. |

> **Battery Tip**: If your UI does not render seconds, set `SystemClock.precision = SystemClock.Precision.Minutes`. This prevents QtQuick from waking up the CPU every second.

import Quickshell

import QtQuick

Text {

    text: Qt.formatDateTime(SystemClock.date, "hh:mm AP")

    color: "\#cdd6f4"

}

---

## 4\. `DesktopEntries` & `DesktopEntry`

Parses system `.desktop` files in `/usr/share/applications` and `~/.local/share/applications`.

| `DesktopEntry` Property | Type | Description |
| :---- | :---- | :---- |
| `name` | `string` | Display name of the application. |
| `comment` | `string` | Tooltip or descriptive subtitle. |
| `icon` | `string` | Icon name or absolute image path. |
| `exec` | `string` | Command line string used to launch the app. |
| `categories` | `list<string>` | Freedesktop category strings. |

### Methods

- **`execute()`**: Launches the application asynchronously in its own process group.

---

## 5\. `Variants` Component

Used to instantiate non-visual items or windows dynamically based on a model. Most commonly used with `Quickshell.screens`:

Variants {

    model: Quickshell.screens

    delegate: Component {

        PanelWindow {

            required property ShellScreen modelData

            screen: modelData

        }

    }

}

Next, see [Quickshell Widgets](http://08-core-types-and-widgets/widgets.md).

---

# Quickshell UI Widgets (`Quickshell.Widgets`)

The `Quickshell.Widgets` module provides purpose-built UI components designed to solve layout quirks and icon handling in desktop shells.

## Module Import

import Quickshell.Widgets

---

## 1\. `WrapperItem` & `MarginWrapperManager`

In QtQuick, adding margins directly to children inside layouts can disrupt implicit sizing calculations. `WrapperItem` wraps an arbitrary child component, applying margins while properly propagating `implicitWidth` and `implicitHeight`.

### Properties

| Property | Type | Default | Description |
| :---- | :---- | :---- | :---- |
| `margin` | `real` | `0` | Uniform margin for all four sides. |
| `topMargin` / `bottomMargin` | `real` | `margin` | Specific vertical margins. |
| `leftMargin` / `rightMargin` | `real` | `margin` | Specific horizontal margins. |
| `extraMargin` | `real` | `0` | Additive margin applied on top of side margins. |
| `resizeChild` | `bool` | `true` | Expands child when wrapper grows beyond implicit size. |

### Example

import Quickshell.Widgets

import QtQuick

WrapperItem {

    margin: 8

    Rectangle {

        implicitWidth: 100

        implicitHeight: 40

        color: "\#45475a"

        radius: 6

    }

}

---

## 2\. `IconImage`

Renders icons dynamically from the current freedesktop system icon theme (e.g. Papirus, Breeze, Adwaita) with automatic PNG/SVG fallback:

import Quickshell.Widgets

IconImage {

    width: 24

    height: 24

    source: "firefox" // Resolves automatically via icon theme

}

---

## 3\. `ClippingRectangle`

A specialized `Rectangle` that cleanly clips child items to its rounded corners (`radius`) without jagged aliasing artifacts:

import Quickshell.Widgets

import QtQuick

ClippingRectangle {

    width: 200

    height: 100

    radius: 12

    color: "\#181825"

    Image {

        anchors.fill: parent

        source: "file:///path/to/wallpaper.jpg"

        fillMode: Image.PreserveAspectCrop

    }

}

Continue to [Practical Recipes & Best Practices](http://09-recipes-and-best-practices/index.md).

---

# Practical Recipes & Engineering Best Practices Hub

This module provides complete, copy-pasteable implementations of desktop components alongside optimization guidelines.

## Topic Overview

| Recipe / Guide | Description | Key Modules Used |
| :---- | :---- | :---- |
| [Multi-Monitor Status Bar](http://09-recipes-and-best-practices/status-bar-recipe.md) | Complete top bar with clock, audio, battery, tray | `PanelWindow`, `Variants`, `Pipewire`, `UPower`, `SystemTray` |
| [Application Launcher](http://09-recipes-and-best-practices/app-launcher-recipe.md) | Spotlight-style launcher with keyboard navigation | `PanelWindow`, `WlrLayershell`, `DesktopEntries` |
| [Notification Center](http://09-recipes-and-best-practices/notification-center-recipe.md) | Notification popups with action buttons | `NotificationServer`, `Notification` |
| [Wayland Lockscreen](http://09-recipes-and-best-practices/lockscreen-recipe.md) | Tamper-proof session locker with PAM authentication | `WlSessionLock`, `WlSessionLockSurface`, `PamContext` |
| [Performance & Best Practices](http://09-recipes-and-best-practices/best-practices.md) | Memory optimization, battery saving, debugging | Profiling, `LazyLoader`, `SystemClock`, `QS_LOG` |

Start with the [Multi-Monitor Status Bar Recipe](http://09-recipes-and-best-practices/status-bar-recipe.md).

---

# Complete Multi-Monitor Status Bar Recipe

A production-ready top bar automatically instantiated across every connected monitor with workspaces, audio controls, battery status, and a system clock.

// \~/.config/quickshell/bar/shell.qml

import Quickshell

import Quickshell.Wayland

import Quickshell.Services.Pipewire

import Quickshell.Services.UPower

import Quickshell.Services.SystemTray

import Quickshell.Widgets

import QtQuick

import QtQuick.Layouts

ShellRoot {

    Variants {

        model: Quickshell.screens

        delegate: Component {

            PanelWindow {

                id: barWindow

                required property ShellScreen modelData

                screen: modelData

                anchors {

                    top: true

                    left: true

                    right: true

                }

                height: 36

                color: "\#181825"

                exclusionMode: ExclusionMode.Normal

                exclusiveZone: 36

                WlrLayershell.layer: WlrLayer.Top

                WlrLayershell.namespace: "top-bar"

                RowLayout {

                    anchors.fill: parent

                    anchors.leftMargin: 12

                    anchors.rightMargin: 12

                    spacing: 12

                    // Left Section: Host / Screen Label

                    Text {

                        text: "󰣇  " \+ barWindow.screen.name

                        color: "\#89b4fa"

                        font.bold: true

                    }

                    Item { Layout.fillWidth: true } // Spacer

                    // Center Section: Real-time System Clock

                    Text {

                        text: Qt.formatDateTime(SystemClock.date, "ddd, MMM d  hh:mm AP")

                        color: "\#cdd6f4"

                        font.bold: true

                    }

                    Item { Layout.fillWidth: true } // Spacer

                    // Right Section: Audio, Battery, Tray

                    RowLayout {

                        spacing: 12

                        // Audio Volume Control

                        RowLayout {

                            spacing: 4

                            readonly property PwNodeAudio audio: Pipewire.defaultAudioSink ? Pipewire.defaultAudioSink.audio : null

                            Text {

                                text: audio && audio.muted ? "󰝟" : "󰕾"

                                color: "\#f38ba8"

                                MouseArea {

                                    anchors.fill: parent

                                    onClicked: if (audio) audio.muted \= \!audio.muted

                                }

                            }

                            Text {

                                text: audio ? Math.round(audio.volume \* 100\) \+ "%" : "--%"

                                color: "\#cdd6f4"

                            }

                        }

                        // Battery Indicator

                        RowLayout {

                            spacing: 4

                            visible: UPower.onBattery || (UPower.displayDevice && UPower.displayDevice.percentage \< 100\)

                            Text {

                                text: "󰁹"

                                color: "\#a6e3a1"

                            }

                            Text {

                                text: UPower.displayDevice ? Math.round(UPower.displayDevice.percentage) \+ "%" : ""

                                color: "\#cdd6f4"

                            }

                        }

                        // System Tray Icons

                        RowLayout {

                            spacing: 6

                            Repeater {

                                model: SystemTray.items

                                delegate: IconImage {

                                    required property SystemTrayItem modelData

                                    Layout.preferredWidth: 18

                                    Layout.preferredHeight: 18

                                    source: modelData.icon

                                    MouseArea {

                                        anchors.fill: parent

                                        acceptedButtons: Qt.LeftButton | Qt.RightButton

                                        onClicked: mouse \=\> {

                                            if (mouse.button \=== Qt.RightButton && modelData.hasMenu) {

                                                // DBus context menu

                                            } else {

                                                modelData.activate(0, 0);

                                            }

                                        }

                                    }

                                }

                            }

                        }

                    }

                }

            }

        }

    }

}

Next, see the [Application Launcher Recipe](http://09-recipes-and-best-practices/app-launcher-recipe.md).

---

# Application Launcher Recipe

A lightweight, centered application launcher modal with dynamic search filtering and keyboard support.

// \~/.config/quickshell/launcher/shell.qml

import Quickshell

import Quickshell.Wayland

import Quickshell.Widgets

import QtQuick

import QtQuick.Controls

import QtQuick.Layouts

PanelWindow {

    id: launcher

    anchors {

        top: true

        bottom: true

        left: true

        right: true

    }

    color: "\#60000000" // Backdrop blur area

    visible: true

    WlrLayershell.layer: WlrLayer.Overlay

    WlrLayershell.keyboardFocus: WlrKeyboardFocus.Exclusive

    // Dismiss when clicking backdrop

    MouseArea {

        anchors.fill: parent

        onClicked: launcher.visible \= false

    }

    Rectangle {

        anchors.centerIn: parent

        width: 520

        height: 400

        color: "\#1e1e2e"

        radius: 12

        border.color: "\#313244"

        border.width: 1

        // Prevent click propagation to backdrop

        MouseArea {

            anchors.fill: parent

            onClicked: {}

        }

        ColumnLayout {

            anchors.fill: parent

            anchors.margins: 16

            spacing: 12

            // Search input

            TextField {

                id: searchBox

                Layout.fillWidth: true

                placeholderText: "Search applications..."

                color: "\#cdd6f4"

                font.pixelSize: 16

                focus: true

                background: Rectangle {

                    color: "\#313244"

                    radius: 8

                }

                Keys.onEscapePressed: launcher.visible \= false

                Keys.onDownPressed: appList.forceActiveFocus()

            }

            // Results list

            ListView {

                id: appList

                Layout.fillWidth: true

                Layout.fillHeight: true

                clip: true

                spacing: 4

                model: DesktopEntries.applications.filter(app \=\> {

                    if (\!searchBox.text) return true;

                    return app.name.toLowerCase().includes(searchBox.text.toLowerCase());

                })

                delegate: Rectangle {

                    required property DesktopEntry modelData

                    required property int index

                    width: appList.width

                    height: 44

                    radius: 6

                    color: ListView.isCurrentItem ? "\#45475a" : "transparent"

                    RowLayout {

                        anchors.fill: parent

                        anchors.margins: 8

                        spacing: 12

                        IconImage {

                            Layout.preferredWidth: 28

                            Layout.preferredHeight: 28

                            source: modelData.icon

                        }

                        ColumnLayout {

                            spacing: 2

                            Text {

                                text: modelData.name

                                color: "\#cdd6f4"

                                font.bold: true

                            }

                            Text {

                                text: modelData.comment || ""

                                color: "\#6c7086"

                                font.pixelSize: 11

                                elide: Text.ElideRight

                                Layout.preferredWidth: 380

                            }

                        }

                    }

                    MouseArea {

                        anchors.fill: parent

                        hoverEnabled: true

                        onEntered: appList.currentIndex \= index

                        onClicked: {

                            modelData.execute();

                            launcher.visible \= false;

                        }

                    }

                }

                Keys.onReturnPressed: {

                    if (currentItem) {

                        model\[currentIndex\].execute();

                        launcher.visible \= false;

                    }

                }

                Keys.onEscapePressed: launcher.visible \= false

            }

        }

    }

}

Next, see the [Notification Center Recipe](http://09-recipes-and-best-practices/notification-center-recipe.md).

---

# Notification Center Recipe

A desktop notification daemon implementation with animated popup banners, urgency categorization, and action callbacks.

// \~/.config/quickshell/notifications/shell.qml

import Quickshell

import Quickshell.Wayland

import Quickshell.Services.Notifications

import Quickshell.Widgets

import QtQuick

import QtQuick.Layouts

PanelWindow {

    id: notifWindow

    anchors {

        top: true

        right: true

    }

    margins {

        top: 24

        right: 24

    }

    width: 340

    height: notifCol.implicitHeight

    color: "transparent"

    WlrLayershell.layer: WlrLayer.Overlay

    Column {

        id: notifCol

        width: parent.width

        spacing: 12

        Repeater {

            model: NotificationServer.trackedNotifications

            delegate: Rectangle {

                id: banner

                required property Notification modelData

                width: 340

                height: contentLayout.implicitHeight \+ 20

                color: "\#1e1e2e"

                radius: 10

                border.width: 1

                border.color: modelData.urgency \=== NotificationUrgency.Critical ? "\#f38ba8" : "\#313244"

                ColumnLayout {

                    id: contentLayout

                    anchors.fill: parent

                    anchors.margins: 10

                    spacing: 6

                    RowLayout {

                        Layout.fillWidth: true

                        spacing: 8

                        IconImage {

                            Layout.preferredWidth: 20

                            Layout.preferredHeight: 20

                            source: modelData.appIcon || "dialog-information"

                        }

                        Text {

                            text: modelData.appName

                            color: "\#89b4fa"

                            font.bold: true

                            Layout.fillWidth: true

                            elide: Text.ElideRight

                        }

                        Text {

                            text: "✕"

                            color: "\#6c7086"

                            MouseArea {

                                anchors.fill: parent

                                onClicked: modelData.dismiss()

                            }

                        }

                    }

                    Text {

                        text: modelData.summary

                        color: "\#cdd6f4"

                        font.bold: true

                        elide: Text.ElideRight

                        Layout.fillWidth: true

                    }

                    Text {

                        text: modelData.body

                        color: "\#a6adc8"

                        font.pixelSize: 12

                        wrapMode: Text.Wrap

                        Layout.fillWidth: true

                    }

                    // Action buttons

                    RowLayout {

                        spacing: 6

                        visible: modelData.actions.length \> 0

                        Repeater {

                            model: modelData.actions

                            delegate: Rectangle {

                                required property NotificationAction actionItem

                                Layout.preferredHeight: 24

                                Layout.preferredWidth: actionText.implicitWidth \+ 16

                                color: "\#313244"

                                radius: 4

                                Text {

                                    id: actionText

                                    anchors.centerIn: parent

                                    text: actionItem.text

                                    color: "\#cdd6f4"

                                    font.pixelSize: 11

                                }

                                MouseArea {

                                    anchors.fill: parent

                                    onClicked: actionItem.invoke()

                                }

                            }

                        }

                    }

                }

            }

        }

    }

}

Next, see the [Wayland Lockscreen Recipe](http://09-recipes-and-best-practices/lockscreen-recipe.md).

---

# Wayland Lockscreen Recipe

A tamper-proof screen lock built using `ext_session_lock_v1` and authenticated through Linux PAM.

// \~/.config/quickshell/lock/shell.qml

import Quickshell

import Quickshell.Wayland

import Quickshell.Services.Pam

import QtQuick

import QtQuick.Controls

ShellRoot {

    WlSessionLock {

        id: lock

        locked: true // Enforces lock immediately on startup

        surface: Component {

            WlSessionLockSurface {

                id: surface

                color: "\#11111b"

                // Center Unlock Box

                Rectangle {

                    anchors.centerIn: parent

                    width: 320

                    height: 260

                    color: "\#181825"

                    radius: 16

                    border.color: "\#313244"

                    border.width: 1

                    Column {

                        anchors.centerIn: parent

                        spacing: 16

                        width: parent.width \- 48

                        Text {

                            anchors.horizontalCenter: parent.horizontalCenter

                            text: Qt.formatDateTime(SystemClock.date, "hh:mm")

                            color: "\#cdd6f4"

                            font.pixelSize: 42

                            font.bold: true

                        }

                        Text {

                            anchors.horizontalCenter: parent.horizontalCenter

                            text: Qt.formatDateTime(SystemClock.date, "dddd, MMMM d")

                            color: "\#6c7086"

                            font.pixelSize: 14

                        }

                        TextField {

                            id: pwdField

                            width: parent.width

                            placeholderText: "Password"

                            echoMode: TextInput.Password

                            color: "\#cdd6f4"

                            focus: true

                            background: Rectangle {

                                color: "\#313244"

                                radius: 8

                            }

                            onAccepted: {

                                pam.authenticate(pwdField.text);

                            }

                        }

                        Text {

                            id: statusLabel

                            anchors.horizontalCenter: parent.horizontalCenter

                            text: ""

                            color: "\#f38ba8"

                            font.pixelSize: 12

                        }

                    }

                }

                // PAM Handler

                PamContext {

                    id: pam

                    // Automatically uses current user if left blank or specified

                    onSuccess: {

                        lock.locked \= false; // Graceful unlock

                    }

                    onError: err \=\> {

                        statusLabel.text \= "Incorrect password";

                        pwdField.text \= "";

                    }

                }

            }

        }

    }

}

Next, read [Performance & Best Practices](http://09-recipes-and-best-practices/best-practices.md).

---

# Performance Optimization & Engineering Best Practices

Follow these guidelines to maintain low memory usage, responsive animations, and minimal CPU wakeups in Quickshell configurations.

## 1\. Memory Optimization & Lazy Loading

### Avoid Instantiating Off-Screen Windows

Heavy menus, dashboards, and settings panels should not remain in memory when hidden. Use `LazyLoader` or `Loader`:

// Efficient: Loaded only when toggled

LazyLoader {

    id: dashboardLoader

    active: isDashboardOpen

    Component {

        FloatingWindow {

            // Complex UI components

        }

    }

}

---

## 2\. Power Consumption & CPU Wakeups

### Use Minutes Precision for Clocks

Updating a clock every second triggers 3,600 timer interrupts and scene graph re-renders per hour.

// In your clock definition

SystemClock.precision: SystemClock.Precision.Minutes

### Throttle Streaming Process Outputs

When running external monitor scripts with `Process`, avoid high-frequency loops (e.g. polling every 100ms). Leverage native IPC push events (`Hyprland.rawEvent`, `Pipewire.defaultAudioSink.audio.onVolumeChanged`) instead of polling `pactl` or `hyprctl`.

---

## 3\. Layout Best Practices

1. **Prefer `implicitWidth` / `implicitHeight` on Custom Widgets**: Never hardcode `width` and `height` inside modular QML widgets unless it is an icon or avatar. Defining implicit sizes allows parent `RowLayout` and `WrapperItem` to calculate dynamic spacing smoothly.  
2. **Avoid Circular Anchor Bindings**: Binding a child item's anchor to its parent while simultaneously sizing the parent based on child item `childrenRect` causes infinite binding loops.

---

## 4\. Diagnostics & Debugging

### Verbose Logging

Launch Quickshell from a terminal with debug flags:

QS\_LOG=debug quickshell \-c bar

### Inspecting Wayland Protocols

Verify layer-shell placement and dimensions:

\# On Hyprland:

hyprctl layers

\# Check running process PID and logs

ps aux | grep quickshell

Back to [Knowledge Base Index](http://index.md).

---

