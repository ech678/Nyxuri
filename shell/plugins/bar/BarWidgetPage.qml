import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.services
import qs.ui
import qs.commons.i18n
import "../../services/BarWidgetDefaults.js" as BarWidgetDefaults
import "../../services/BarDefaults.js" as BarDefaults
import "BarStyle.js" as BarStyle

// Per-instance widget editor (D4b, dux BarWidgetTab pattern): resolves one
// lane entry by uid, exposes the value()/set() facade every options page
// consumes, and loads the widget's options file from plugins/bar/options/
// (catalog registration point 4). The generic card carries the instance
// facts (visibility, placement); everything widget-specific rides the
// loaded page. Not a manifest route on purpose: the page is meaningless
// without a uid, so it stays off the nav pane and search index.
Item {
    id: root

    signal backRequested
    signal routeRequested(string section)

    function openRoute(section) {
        root.routeRequested(section);
    }

    // Session identity of the edited entry (chip gear → GeneralBarPage).
    property string widgetUid: ""

    readonly property var entry: PersonalizationConfig.barEntryByUid(root.widgetUid)
    readonly property string widgetId: root.entry ? root.entry.widgetId : ""
    readonly property bool entryAlive: root.entry !== null
    // D4g batch two: the editor edits the selected bar; on a rail, widgets
    // without a catalog rail face get the capability note.
    readonly property bool editingOnRail: root.entryAlive && (PersonalizationConfig.barAxes.position === "left" || PersonalizationConfig.barAxes.position === "right")
    readonly property bool hasOverrides: !!(root.entry && root.entry.overrides && Object.keys(root.entry.overrides).length > 0)
    // dux OverflowLayout.pinned: spacer/separator/island never leave the
    // bar, so their editor pages carry no overflow group.
    readonly property bool showOverflowGroup: root.entryAlive && ["spacer", "separator", "island"].indexOf(root.widgetId) === -1

    BarWidgetCatalog {
        id: widgetCatalog
    }

    // The facade the options pages consume (dux `page` precedent): pages
    // never touch storage — they read and write through these two.
    function value(key) {
        return BarWidgetDefaults.option(root.widgetId, root.entry, key);
    }

    function set(key, value) {
        PersonalizationConfig.setBarEntryOverride(root.widgetUid, key, value);
    }

    readonly property var clickActionOptions: BarWidgetActions.ids.map(id => ({
                value: id,
                label: BarWidgetActions.label(id)
            }))

    readonly property string zoneLabel: {
        const uid = root.widgetUid;
        if (PersonalizationConfig.barLayoutEntriesLeft.some(entry => entry.uid === uid))
            return I18n.tr("Left");
        if (PersonalizationConfig.barLayoutEntriesMiddle.some(entry => entry.uid === uid))
            return I18n.tr("Center");
        if (PersonalizationConfig.barLayoutEntriesRight.some(entry => entry.uid === uid))
            return I18n.tr("Right");
        return "";
    }

    // Dead-entry guard: a drag/remove can drop the edited entry while the
    // page is open (the page outlives its target for one interaction).
    onEntryAliveChanged: {
        if (root.widgetUid !== "" && !root.entryAlive)
            root.backRequested();
    }

    NexusPageBase {
        id: pageBase

        anchors.fill: parent
        isSubPage: true
        title: widgetCatalog.displayName(widgetCatalog.byId(root.widgetId))
        onBackRequested: root.backRequested()

        Item {
            id: content

            width: parent.width
            implicitHeight: contentColumn.implicitHeight

            ColumnLayout {
                id: contentColumn

                anchors.horizontalCenter: parent.horizontalCenter
                anchors.top: parent.top
                width: pageBase.cappedWidth
                spacing: NexusStyle.padding.extraSmall / 2

                PreferenceHeader {
                    first: true
                    text: I18n.tr("Widget")
                    showReset: root.hasOverrides
                    resetText: I18n.tr("Reset widget options")
                    onResetRequested: PersonalizationConfig.resetBarWidgetOverrides(root.widgetUid)
                }

                PreferenceGroup {
                    PreferenceToggle {
                        text: I18n.tr("Show in bar")
                        checked: root.entryAlive && root.entry.enabled !== false
                        onToggled: checked => PersonalizationConfig.setBarEntryEnabled(root.widgetUid, checked)
                    }

                    PreferenceInfo {
                        label: I18n.tr("Lane")
                        value: root.zoneLabel
                        icon: "view_agenda"
                    }

                    // D4g batch two: capability note — factual today-state,
                    // not a promise (see the catalog header for the audit).
                    PreferenceInfo {
                        visible: root.editingOnRail && !widgetCatalog.supportsVertical(root.widgetId)
                        label: I18n.tr("Vertical bar")
                        value: I18n.tr("This widget has no vertical face yet")
                        icon: "info"
                    }
                }

                // D4d shared overflow group (bar-config.md D4d): entry axes
                // every widget owns — the resolver's placement vocabulary and
                // yield order. Pinned widgets (spacer/separator/island) never
                // overflow, so the group hides for them.
                PreferenceHeader {
                    visible: root.showOverflowGroup
                    text: I18n.tr("Overflow")
                }

                PreferenceGroup {
                    visible: root.showOverflowGroup

                    PreferenceSelect {
                        label: I18n.tr("When the bar is full")
                        model: [
                            {
                                "value": "section",
                                "label": I18n.tr("Follow lane")
                            },
                            {
                                "value": "auto",
                                "label": I18n.tr("May collapse into the overflow menu")
                            },
                            {
                                "value": "bar",
                                "label": I18n.tr("Always stay in the bar")
                            },
                            {
                                "value": "always",
                                "label": I18n.tr("Always in the overflow menu")
                            }
                        ]
                        currentValue: root.entry && root.entry.overrides && root.entry.overrides.overflowMode !== undefined ? root.entry.overrides.overflowMode : "section"
                        inputRegionService: PopupInputRegionService
                        modified: !!(root.entry && root.entry.overrides && root.entry.overrides.overflowMode !== undefined)
                        onSelected: value => root.set("overflowMode", String(value) === "section" ? undefined : String(value))
                        onResetRequested: root.set("overflowMode", undefined)
                    }

                    PreferenceSlider {
                        label: I18n.tr("Overflow priority")
                        value: root.entry && root.entry.overrides && root.entry.overrides.overflowPriority !== undefined ? root.entry.overrides.overflowPriority : 0
                        valueLabel: Math.round(root.entry && root.entry.overrides && root.entry.overrides.overflowPriority !== undefined ? root.entry.overrides.overflowPriority : 0)
                        from: -10
                        to: 10
                        stepSize: 1
                        modified: !!(root.entry && root.entry.overrides && root.entry.overrides.overflowPriority !== undefined)
                        onMoved: value => root.set("overflowPriority", Math.round(value) === 0 ? undefined : Math.round(value))
                        onResetRequested: root.set("overflowPriority", undefined)
                    }
                }

                // Per-widget capsule style overrides (shared with BarGroupStylePopup).
                PreferenceCollapsibleGroup {
                    visible: root.entryAlive && root.widgetId !== "island" && root.widgetId !== "spacer" && root.widgetId !== "separator"
                    title: I18n.tr("Appearance")
                    subtitle: I18n.tr("Per-widget color, opacity, corner radius, and padding")
                    icon: "palette"
                    expanded: !!(root.entry && root.entry.overrides && (root.entry.overrides.color !== undefined || root.entry.overrides.opacity !== undefined || root.entry.overrides.radius !== undefined || root.entry.overrides.padding !== undefined || root.entry.overrides.borderWidth !== undefined))

                    readonly property bool tintedBar: BarStyle.isTinted(PersonalizationConfig.barAxes)
                    readonly property var styleColors: [
                        {
                            value: "",
                            label: I18n.tr("Bar default")
                        },
                        {
                            value: "transparent",
                            label: I18n.tr("Transparent")
                        },
                        {
                            value: "layer0",
                            label: I18n.tr("Background")
                        },
                        {
                            value: "layer1",
                            label: I18n.tr("Surface layer")
                        },
                        {
                            value: "surfaceContainer",
                            label: I18n.tr("Surface container")
                        },
                        {
                            value: "primaryContainer",
                            label: I18n.tr("Primary container")
                        },
                        {
                            value: "secondaryContainer",
                            label: I18n.tr("Secondary container")
                        },
                        {
                            value: "tertiaryContainer",
                            label: I18n.tr("Tertiary container")
                        },
                        {
                            value: "primary",
                            label: I18n.tr("Primary")
                        },
                        {
                            value: "custom",
                            label: I18n.tr("Custom")
                        }
                    ]

                    PreferenceControlledBy {
                        visible: parent.tintedBar
                        icon: "palette"
                        title: I18n.tr("Controlled by Material tint")
                        reason: I18n.tr("Material tint overrides per-widget colors")
                        actionLabel: I18n.tr("Disable tint")
                        onActionClicked: PersonalizationConfig.setBarTint(false)
                    }

                    PreferenceSelect {
                        visible: !parent.tintedBar
                        label: I18n.tr("Background color")
                        model: parent.styleColors
                        currentValue: {
                            const c = root.entry?.overrides?.color ?? "";
                            return BarDefaults.isCustomColor(String(c)) ? "custom" : String(c);
                        }
                        inputRegionService: PopupInputRegionService
                        modified: !!(root.entry?.overrides?.color !== undefined)
                        onSelected: value => {
                            const v = String(value);
                            if (v === "")
                                root.set("color", undefined);
                            else if (v === "custom")
                                root.set("color", BarDefaults.isCustomColor(String(root.entry?.overrides?.color ?? "")) ? root.entry.overrides.color : "#252b2d");
                            else
                                root.set("color", v);
                        }
                        onResetRequested: root.set("color", undefined)
                    }

                    PreferenceInput {
                        visible: !parent.tintedBar && BarDefaults.isCustomColor(String(root.entry?.overrides?.color ?? ""))
                        label: I18n.tr("Custom background color")
                        placeholderText: "#252b2d"
                        value: String(root.entry?.overrides?.color ?? "")
                        validate: /^#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?$/
                        errorText: I18n.tr("Hex color, e.g. #252b2d")
                        onEditingFinished: value => root.set("color", String(value || "").trim() || undefined)
                    }

                    PreferenceSlider {
                        visible: !parent.tintedBar
                        label: I18n.tr("Background opacity")
                        value: Math.round((root.entry?.overrides?.opacity ?? PersonalizationConfig.barAxes.widgetTransparency ?? 1) * 100)
                        valueLabel: root.entry?.overrides?.opacity === undefined ? I18n.tr("Auto") : Math.round(root.entry.overrides.opacity * 100) + " %"
                        from: 0
                        to: 100
                        stepSize: 5
                        modified: root.entry?.overrides?.opacity !== undefined
                        onMoved: value => root.set("opacity", Math.round(value) / 100)
                        onResetRequested: root.set("opacity", undefined)
                    }

                    PreferenceSlider {
                        visible: !parent.tintedBar
                        label: I18n.tr("Corner radius")
                        value: root.entry?.overrides?.radius ?? -1
                        valueLabel: (root.entry?.overrides?.radius ?? -1) < 0 ? I18n.tr("Auto") : Math.round(root.entry.overrides.radius) + " px"
                        from: -1
                        to: 30
                        stepSize: 1
                        modified: root.entry?.overrides?.radius !== undefined
                        onMoved: value => root.set("radius", Math.round(value) < 0 ? undefined : Math.round(value))
                        onResetRequested: root.set("radius", undefined)
                    }

                    PreferenceSlider {
                        visible: !parent.tintedBar
                        label: I18n.tr("Padding")
                        value: root.entry?.overrides?.padding ?? -1
                        valueLabel: (root.entry?.overrides?.padding ?? -1) < 0 ? I18n.tr("Auto") : Math.round(root.entry.overrides.padding) + " px"
                        from: -1
                        to: 15
                        stepSize: 1
                        modified: root.entry?.overrides?.padding !== undefined
                        onMoved: value => root.set("padding", Math.round(value) < 0 ? undefined : Math.round(value))
                        onResetRequested: root.set("padding", undefined)
                    }

                    PreferenceSlider {
                        visible: !parent.tintedBar
                        label: I18n.tr("Border width")
                        value: root.entry?.overrides?.borderWidth ?? -1
                        valueLabel: (root.entry?.overrides?.borderWidth ?? -1) < 0 ? I18n.tr("Auto") : Math.round(root.entry.overrides.borderWidth) + " px"
                        from: -1
                        to: 4
                        stepSize: 1
                        modified: root.entry?.overrides?.borderWidth !== undefined
                        onMoved: value => root.set("borderWidth", Math.round(value) < 0 ? undefined : Math.round(value))
                        onResetRequested: root.set("borderWidth", undefined)
                    }
                }

                Loader {
                    id: optionsLoader

                    Layout.fillWidth: true
                    Layout.topMargin: NexusStyle.padding.small
                    active: root.entryAlive && widgetCatalog.hasOptions(root.widgetId)
                    source: active ? Qt.resolvedUrl("options/") + widgetCatalog.optionsFile(root.widgetId) : ""
                    onLoaded: {
                        if (item)
                            item.page = root;
                    }
                }

                StyledText {
                    Layout.fillWidth: true
                    Layout.leftMargin: NexusStyle.padding.extraSmall
                    visible: root.entryAlive && !widgetCatalog.hasOptions(root.widgetId)
                    text: I18n.tr("This widget has no per-instance options yet")
                    color: Appearance.m3colors.m3onSurfaceVariant
                    font.pixelSize: NexusStyle.font.bodySmall
                    wrapMode: Text.Wrap
                }
            }
        }
    }
}
