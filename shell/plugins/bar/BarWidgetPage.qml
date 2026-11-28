import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.services
import qs.ui
import qs.commons.i18n
import "../../services/BarWidgetDefaults.js" as BarWidgetDefaults

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
