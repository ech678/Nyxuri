// Fork & Trim: end4-pC modules/ii/bar/BarGroup.qml
// SPDX-License-Identifier: GPL-3.0-or-later
//
// Trimmed for Nyxuri:
//   - widgetStyles persistence lives in PersonalizationConfig (the bridge's
//     options object is read-only), so setStyle/resetStyle call its setters.
//   - followFrameColor / frameColor paths dropped (no UI, constant false).
//   - spectrumClip* / backgroundVisible / empty helpers dropped with the bar
//     background spectrum.
//
// D4c: the style overrides ride the lane entry (uid addressed — duplicate
// widgets style independently), and the fusion radii come from the lane's
// SegmentRoles run (hidden end widgets no longer strand the "last" radius
// on an invisible group). The capsule padding resolves through
// BarDefaults (sentinel -1 = per-style baseline).

import QtQuick
import QtQuick.Layouts
import qs.commons
import qs.services

Item {
    id: root
    property bool vertical: false
    // SegmentRoles run role for this group: solo | first | middle | last.
    // The lane hosts (BarContent/VerticalBarContent) resolve the run over
    // the whole lane, so a hidden neighbour re-shapes this group's corners
    // instead of leaving the fusion wrong.
    property string segmentRole: "solo"
    // D4d overflow: the entry moved into the lane's overflow popout. The
    // group collapses exactly like a self-hidden widget (run participation
    // drops out, so neighbours re-fuse) while its widget Loader stays
    // alive — the instance is relocated (lane group <-> overflow popup),
    // never destroyed.
    property bool inOverflow: false
    readonly property bool isMaterial: PersonalizationConfig.barIsMaterial
    property bool paintMaterialPill: false
    property bool paintBackground: true
    property color bgColor: Appearance.colors.colPrimaryContainer
    property string widgetName: ""
    // D4a injection protocol: the lane entry flows through the group into
    // the loaded widget (the Loader's onLoaded pushes it). The group keys
    // its own style overrides off the entry too (D4c — uid addressed).
    property var widgetEntry: null

    readonly property string borderlessMode: Config.options?.bar.borderless ?? "pills"
    readonly property bool isFlat: root.borderlessMode === "flat"
    // In flat the capsule chrome is off by default; a per-instance color
    // override is the one way a widget gets its background back.
    readonly property bool styleEditable: !root.isMaterial && root.paintBackground && root.widgetName !== ""
    property var stylePreview: ({})
    readonly property var style: {
        const entry = root.widgetEntry && root.widgetEntry.overrides ? root.widgetEntry.overrides : {};
        return Object.assign({}, entry, root.stylePreview);
    }

    function previewStyle(key, value) {
        root.stylePreview = Object.assign({}, root.stylePreview, {
            [key]: value
        });
    }

    function commitPreview() {
        const preview = root.stylePreview;
        root.stylePreview = ({});
        for (const key in preview)
            root.setStyle(key, preview[key]);
    }

    readonly property bool rightClickFree: !["updatesCount", "weatherBar", "bluetooth", "workspaces", "sysTray", "media", "docktoPanel"].includes(root.widgetName)

    readonly property Item loadedWidget: gridLayout.children[0]?.item ?? null
    // Qt Quick Layouts can leave GridLayout.implicitWidth stale (child Loader
    // activates after a startup cornerStyle flip, or a widget's implicit size
    // changes while the group was hidden); the single widget host is
    // authoritative, so never collapse below its implicit width.
    readonly property real contentWidth: Math.max(gridLayout.implicitWidth, root.loadedWidget ? root.loadedWidget.implicitWidth : 0)
    readonly property bool hasContentOverride: !root.isMaterial && root.style.color !== undefined && root.style.color !== "transparent"
    readonly property color contentColor: {
        const name = root.style.color ?? "";
        const special = {
            surfaceContainer: "onSurface",
            onError: "error",
            onLayer0: "layer0"
        };
        const onName = special[name] ?? `on${name.charAt(0).toUpperCase()}${name.slice(1)}`;
        return root.resolveColorName(onName) ?? Appearance.colors.colOnLayer1;
    }

    Binding {
        target: root.loadedWidget && "contentColor" in root.loadedWidget ? root.loadedWidget : null
        property: "contentColor"
        value: root.contentColor
        when: root.hasContentOverride
    }

    Binding {
        target: root.loadedWidget && "contentColorOverridden" in root.loadedWidget ? root.loadedWidget : null
        property: "contentColorOverridden"
        value: true
        when: root.hasContentOverride
    }

    Connections {
        target: root.loadedWidget
        ignoreUnknownSignals: true
        function onStyleEditorRequested() {
            root.toggleStyleEditor();
        }
    }

    function toggleStyleEditor() {
        if (!root.styleEditable)
            return;
        if (stylePopupLoader.item)
            stylePopupLoader.item.close();
        else
            stylePopupLoader.active = true;
    }

    function resolveColorName(name) {
        if (name === undefined)
            return undefined;
        if (name === "transparent")
            return "transparent";
        return Appearance.colors[`col${name.charAt(0).toUpperCase()}${name.slice(1)}`] ?? undefined;
    }

    function setStyle(key, value) {
        PersonalizationConfig.setBarEntryStyle(root.widgetEntry ? root.widgetEntry.uid : "", key, value);
    }

    function resetStyle() {
        PersonalizationConfig.resetBarEntryStyle(root.widgetEntry ? root.widgetEntry.uid : "");
    }

    readonly property color resolvedGroupColor: {
        const name = Config.options.bar.groupColor;
        const key = `col${name.charAt(0).toUpperCase()}${name.slice(1)}`;
        return Appearance.colors[key] ?? Appearance.colors.colLayer1;
    }

    readonly property real currentRadius: background.topLeftRadius
    readonly property real currentBorderWidth: background.border.width

    // Per-instance padding override (style popup) beats the bar-level
    // widgetPadding axis; -1 on the axis falls back to the per-style
    // baseline (5, or 0 for unpilled material groups).
    property real padding: root.style.padding ?? PersonalizationConfig.resolvedBarWidgetPadding(root.paintMaterialPill)

    readonly property bool isSegmented: Config.options?.bar.borderless === "segmented"
    readonly property bool isPanel: Config.options.bar.cornerStyle === 5
    // D4c widget-layer axes: widgetTransparency transparentizes whatever
    // color the chain below resolved; widgetOutline* overrides the
    // segmented baseline border (defaults keep it untouched).
    readonly property real panelRadius: Appearance.rounding.unsharpenmore + 4

    readonly property real fullRadius: root.isPanel ? root.panelRadius : height / 2
    readonly property real midRadius: root.isPanel ? root.panelRadius : root.isSegmented ? 0 : (Config.options.bar.cornerStyle === 2 ? Appearance.rounding.unsharpenmore + 2 : Appearance.rounding.unsharpenmore)

    // SegmentRoles run radii: solo keeps the full pill, first/last round
    // only their outer corners, middle groups take the mid radius. The
    // per-instance style.radius override (right-click popup) still wins
    // over all four corners.
    property real startRadius: root.segmentRole === "first" || root.segmentRole === "solo" ? root.fullRadius : root.midRadius
    property real endRadius: root.segmentRole === "last" || root.segmentRole === "solo" ? root.fullRadius : root.midRadius

    // A widget may hide itself at runtime (Media with no track). The grouping
    // chrome (padding + capsule) is BarGroup's own, so the group has to
    // collapse with the widget instead of leaving a 10px empty capsule.
    // Item.visible reports *effective* visibility, so reading it would deadlock:
    // a group that hid once masks its child and could never observe the widget
    // asking to come back. Widgets that hide themselves expose
    // `barWidgetVisible`; anything else counts as shown. A widget that is not
    // loaded yet also counts as content so the bar does not flicker while the
    // Loader instantiates. D4d: an overflowed group reports no content even
    // though its Loader may sit emptied in the lane (the widget is parked in
    // the overflow popup) — "not loaded" must not resurrect it.
    // qmllint disable missing-property
    readonly property bool hasContent: root.inOverflow ? false : (root.loadedWidget === null || !("barWidgetVisible" in root.loadedWidget) || root.loadedWidget.barWidgetVisible)
    // qmllint enable missing-property
    visible: root.hasContent

    // D4d measurement protocol (dux SectionEntry lineage): what the resolver
    // needs is the size the LANE would consume, read off the widget itself —
    // the group's own implicitWidth collapses to 0 while overflowed, so it
    // cannot feed the resolver (hysteresis still measures parked widgets).
    // Flexible widgets expose naturalPrimarySize/minimumPrimarySize (Media);
    // everything else measures at its current implicit size.
    readonly property var overflowWidget: root.widgetLoader ? root.widgetLoader.item : null
    readonly property real overflowEntrySize: {
        const widget = root.overflowWidget;
        if (!widget)
            return 0;
        if ("barWidgetVisible" in widget && !widget.barWidgetVisible)
            return 0;
        const natural = "naturalPrimarySize" in widget ? widget.naturalPrimarySize : (root.vertical ? widget.implicitHeight : widget.implicitWidth);
        return (natural || 0) + root.padding * 2;
    }
    readonly property real overflowEntryMin: {
        const widget = root.overflowWidget;
        if (!widget || !("minimumPrimarySize" in widget))
            return root.overflowEntrySize;
        return Math.min(widget.minimumPrimarySize + root.padding * 2, root.overflowEntrySize);
    }

    // The widget Loader (gridLayout.children[0]) relocates between its lane
    // group and the overflow popup while the entry is overflowed. A bound
    // lookup over `children` dies mid-relocation (the binding re-evaluates
    // to null the moment the loader leaves the layout, so restoreWidget
    // would find nothing and the loader would ride the popup window into
    // destruction) — capture the reference once at completion instead.
    property Item widgetLoader: null
    Component.onCompleted: {
        if (gridLayout.children.length > 0)
            root.widgetLoader = gridLayout.children[0];
    }

    function setWidgetHost(host: Item): void {
        const loader = root.widgetLoader;
        if (!loader || loader.parent === host)
            return;
        loader.parent = host;
    }

    function restoreWidget(): void {
        root.setWidgetHost(gridLayout);
    }

    // Flexible allotment (resolver shrink phase): forwarded to widgets that
    // accept one; everything else ignores it.
    function setOverflowAllotment(size: real): void {
        const widget = root.overflowWidget;
        if (widget !== null && "allottedPrimarySize" in widget)
            widget.allottedPrimarySize = size;
    }

    implicitWidth: !root.hasContent ? 0 : vertical && root.isMaterial ? Appearance.sizes.baseVerticalBarWidth - 6 : (root.contentWidth + padding * 2)
    implicitHeight: vertical ? (gridLayout.implicitHeight + padding * 2) : Appearance.sizes.baseBarHeight

    default property alias items: gridLayout.children

    // The capsule color chain (style overrides > mode semantics > group
    // color), before the D4c widget-layer transparency applies.
    readonly property color baseBackgroundColor: {
        if (!root.paintBackground)
            return "transparent";
        const override = root.resolveColorName(root.style.color);
        if (root.isFlat)
            return override ?? "transparent";
        if (override !== undefined)
            return override;
        if (root.isMaterial && !root.paintMaterialPill)
            return "transparent";
        if (root.isMaterial && root.paintMaterialPill)
            return root.bgColor;
        if (root.borderlessMode === "transparent")
            return "transparent";
        if (Config.options.bar.cornerStyle === 2 || (root.isSegmented && !Config.options.bar.showBackground))
            return Appearance.colors.colLayer0;
        return root.resolvedGroupColor;
    }

    Rectangle {
        id: background
        anchors {
            fill: parent
            topMargin: root.vertical ? 0 : 4
            bottomMargin: root.vertical ? 0 : 4
            leftMargin: root.vertical ? 4 : 0
            rightMargin: root.vertical ? 4 : 0
        }
        color: PersonalizationConfig.resolvedBarWidgetColor(root.baseBackgroundColor)

        // Priority: per-instance style override (popup) > bar-level
        // widgetOutline axes > segmented baseline.
        border.width: root.style.borderWidth !== undefined ? root.style.borderWidth : PersonalizationConfig.barWidgetOutlineWidth(root.paintBackground && root.isSegmented && !root.isMaterial && !root.isFlat ? 1 : 0)
        border.color: root.style.borderColor !== undefined ? (root.resolveColorName(root.style.borderColor) ?? Appearance.colors.colLayer0Border) : PersonalizationConfig.barWidgetOutlineColor(Appearance.colors.colLayer0Border)

        topLeftRadius: root.style.radius ?? ((root.isMaterial && root.paintMaterialPill) ? root.fullRadius : (root.borderlessMode === "separated" ? root.fullRadius : root.vertical ? root.endRadius : root.startRadius))
        bottomLeftRadius: root.style.radius ?? ((root.isMaterial && root.paintMaterialPill) ? root.fullRadius : (root.borderlessMode === "separated" ? root.fullRadius : root.vertical ? root.startRadius : root.endRadius))
        topRightRadius: root.style.radius ?? ((root.isMaterial && root.paintMaterialPill) ? root.fullRadius : (root.borderlessMode === "separated" ? root.fullRadius : root.vertical ? root.startRadius : root.endRadius))
        bottomRightRadius: root.style.radius ?? ((root.isMaterial && root.paintMaterialPill) ? root.fullRadius : (root.borderlessMode === "separated" ? root.fullRadius : root.endRadius))

        Behavior on color {
            animation: Appearance.animation.elementMoveFast.colorAnimation.createObject(this)
        }
    }

    GridLayout {
        id: gridLayout
        columns: root.vertical ? 1 : -1
        anchors.centerIn: parent
        columnSpacing: 0
        rowSpacing: 0
    }

    Item {
        anchors.fill: parent
        z: 1
        TapHandler {
            enabled: root.styleEditable && root.rightClickFree
            acceptedButtons: Qt.RightButton
            gesturePolicy: TapHandler.ReleaseWithinBounds
            onTapped: root.toggleStyleEditor()
            onLongPressed: root.toggleStyleEditor()
        }
    }

    Loader {
        id: stylePopupLoader
        active: false
        sourceComponent: BarGroupStylePopup {
            group: root
            onDismissed: stylePopupLoader.active = false
        }
    }
}
