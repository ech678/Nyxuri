pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.shared.theme
import qs.shared.controls

// Dashboard "Settings" page: a packed grid of setting tiles.
//
// The layout engine is ported from end4-pC's DashboardSettingsPage — same
// header rows, same span vocabulary, same bin packing and spring-animated
// reflow. What changed is the content source: end4-pC's catalog keys do not
// exist in nyxuri, so the entries come from DashboardSettingsCatalog, which
// describes nyxuri's own config.
Item {
    id: root

    required property Item pager
    property int staggerMs: 45

    readonly property string query: pager.searchQuery ?? ""

    // Row metrics. Copied verbatim from end4-pC's DashboardSettingsPage: the
    // grid is a fixed-geometry design with no breakpoints, and introducing
    // adaptive values here (as an earlier pass did) diverged from it without
    // actually fixing anything.
    readonly property real rowHeight: 140
    readonly property real headerHeight: 36
    readonly property real gap: 12

    readonly property var shapePool: [MaterialShapeCanvas.Shape.Cookie6Sided, MaterialShapeCanvas.Shape.Gem,
        MaterialShapeCanvas.Shape.Pentagon, MaterialShapeCanvas.Shape.Flower, MaterialShapeCanvas.Shape.Puffy,
        MaterialShapeCanvas.Shape.Clover8Leaf, MaterialShapeCanvas.Shape.Sunny]

    function spanOf(entry) {
        return entry.w ? [entry.w, 1] : baseSpan(entry.type);
    }

    // Span table. Only the types nyxuri actually renders are listed; upstream's
    // remaining branches (schemes / barpos / weathermap / shape / barlayout /
    // palette / iconpicker) come back as their tiles land. `slider` is absent
    // upstream too, so it falls through to the [2, 1] default.
    function baseSpan(type) {
        if (type === "style")
            return [2, 2];
        if (type === "palette")
            return [4, 1];
        if (type === "barlayout")
            return [4, 3];
        if (type === "toggle" || type === "spin")
            return [1, 1];
        return [2, 1];
    }

    readonly property var allEntries: {
        const list = [];
        DashboardSettingsCatalog.sections.forEach((section, si) => {
            list.push({
                          "id": "section:" + si,
                          "kind": "header",
                          "title": section.title,
                          "icon": section.icon,
                          "section": section.title,
                          "count": section.cards.length
                      });
            section.cards.forEach(card => list.push(Object.assign({
                                                                      "id": card.key,
                                                                      "kind": "card",
                                                                      "section": section.title
                                                                  }, card)));
        });
        return list.map(e => Object.assign(e, {
                                               "shape": shapePool[Math.floor(Math.random()
                                                                             * shapePool.length)],
                                               "travelX": (Math.random() - 0.5) * 500,
                                               "travelY": (Math.random() - 0.5) * 400
                                           }));
    }

    function normalized(text) {
        return String(text || "").toLowerCase().replace(/[_\-.:/]+/g, " ");
    }

    function matches(tokens) {
        if (tokens.length === 0)
            return null;
        return allEntries.filter(e => {
            if (e.kind !== "card")
                return false;
            const haystack = normalized([e.title, e.section, e.kw ?? "", e.key ?? ""].join(" "));
            return tokens.every(token => haystack.indexOf(token) >= 0);
        });
    }

    // Packs a run of cards into rows of four, then places every item into the
    // first free slot. Headers always occupy a whole row and reset the floor, so
    // sections never interleave. The literal 4s are end4-pC's: the grid has no
    // breakpoints upstream and this port does not add any.
    function computeLayout(tokens) {
        const filtered = matches(tokens);
        const items = [];
        if (filtered) {
            filtered.forEach(e => {
                const s = spanOf(e);
                items.push({
                               "entry": e,
                               "w": s[0],
                               "h": s[1]
                           });
            });
        } else {
            let i = 0;
            while (i < allEntries.length) {
                const e = allEntries[i];
                if (e.kind === "header") {
                    items.push({
                                   "entry": e,
                                   "w": 4,
                                   "h": 1,
                                   "header": true
                               });
                    const cards = [];
                    i++;
                    while (i < allEntries.length && allEntries[i].kind === "card") {
                        cards.push(allEntries[i]);
                        i++;
                    }
                    packRows(cards, 4).forEach(p => items.push(p));
                } else {
                    const s = spanOf(e);
                    items.push({
                                   "entry": e,
                                   "w": s[0],
                                   "h": s[1]
                               });
                    i++;
                }
            }
        }

        const occ = [];
        const rowH = [];
        const map = {};
        let floor = 0;

        function ensure(r) {
            while (occ.length <= r) {
                occ.push([false, false, false, false]);
                rowH.push(root.rowHeight);
            }
        }

        function fits(r, c, w, h) {
            for (let dr = 0; dr < h; dr++) {
                ensure(r + dr);
                for (let dc = 0; dc < w; dc++) {
                    if (occ[r + dr][c + dc])
                        return false;
                }
            }
            return true;
        }

        items.forEach(it => {
            if (it.header) {
                const r = occ.length;
                ensure(r);
                occ[r] = [true, true, true, true];
                rowH[r] = root.headerHeight;
                map[it.entry.id] = {
                    "col": 0,
                    "row": r,
                    "w": 4,
                    "h": 1,
                    "header": true
                };
                floor = r + 1;
                return;
            }
            let r = floor;
            for (; ; r++) {
                let found = -1;
                for (let c = 0; c + it.w <= 4; c++) {
                    if (fits(r, c, it.w, it.h)) {
                        found = c;
                        break;
                    }
                }
                if (found >= 0) {
                    for (let dr = 0; dr < it.h; dr++) {
                        for (let dc = 0; dc < it.w; dc++)
                            occ[r + dr][found + dc] = true;
                    }
                    map[it.entry.id] = {
                        "col": found,
                        "row": r,
                        "w": it.w,
                        "h": it.h
                    };
                    break;
                }
            }
        });

        const rowY = [];
        let y = 0;
        rowH.forEach(h => {
            rowY.push(y);
            y += h + root.gap;
        });
        Object.keys(map).forEach(id => {
            const p = map[id];
            let height = 0;
            for (let dr = 0; dr < p.h; dr++)
                height += rowH[p.row + dr] + (dr > 0 ? root.gap : 0);
            p.y = rowY[p.row];
            p.height = height;
        });
        return {
            "map": map,
            "total": Math.max(0, y - root.gap),
            "count": items.filter(i => !i.header).length
        };
    }

    // Fills each row widest-first, then widens the cards on the last row so the
    // row does not end in a ragged hole. Copied from end4-pC's packRows,
    // including the trailing distribution pass — the `remaining` counter cannot
    // go negative here because every span is 1, 2 or 4 and the capacity is 4.
    function packRows(cards, capacity) {
        const fulls = cards.filter(c => spanOf(c)[0] === 4);
        const wides = cards.filter(c => spanOf(c)[0] === 2);
        const smalls = cards.filter(c => spanOf(c)[0] === 1);
        const placed = [];
        let remaining = capacity;
        let rowStart = 0;
        fulls.concat(wides, smalls).forEach(card => {
            const span = spanOf(card)[0];
            if (span > remaining) {
                remaining = capacity;
                rowStart = placed.length;
            }
            placed.push({
                            "entry": card,
                            "w": span,
                            "h": spanOf(card)[1]
                        });
            remaining -= span;
            if (remaining === 0) {
                remaining = capacity;
                rowStart = placed.length;
            }
        });
        // Spread whatever is left of the final row across its cards, right to
        // left, so the grid closes flush against the right edge.
        let leftover = remaining === capacity ? 0 : remaining;
        let i = placed.length - 1;
        while (leftover > 0 && i >= rowStart) {
            placed[i].w += 1;
            leftover--;
            i = i === rowStart ? placed.length - 1 : i - 1;
        }
        return placed;
    }

    readonly property var tokens: normalized(query).split(/\s+/).filter(t => t.length > 0)
    readonly property var layoutResult: computeLayout(tokens)
    readonly property var layoutMap: layoutResult.map

    onTokensChanged: flick.contentY = 0

    function scrollBy(delta) {
        flick.contentY = Math.max(0, Math.min(Math.max(0, flick.contentHeight - flick.height), flick.contentY
                                              + delta));
    }

    Flickable {
        id: flick

        anchors.fill: parent
        clip: true
        contentWidth: width
        contentHeight: root.layoutResult.total
        boundsBehavior: Flickable.StopAtBounds
        flickDeceleration: 4000
        maximumFlickVelocity: 2500

        ScrollBar.vertical: StyledScrollBar {}

        // Same shared wheel policy as the other scrolling views: the default step

        // Wheel input goes through the shared controller (bigger steps than Qt's
        // default). It writes contentY directly, so a Behaviour on contentY here
        // would animate against it and stutter — the controller owns scrolling.
        WheelScrollController {
            flickable: flick
        }

        Item {
            id: canvas

            width: flick.width
            height: root.layoutResult.total

            Repeater {
                model: root.allEntries

                delegate: Loader {
                    id: slot

                    required property int index
                    required property var modelData

                    readonly property var place: root.layoutMap[slot.modelData.id] ?? null
                    readonly property var shown: slot.place ?? slot.lastPlace
                    // Column pitch for the fixed 4-column grid: the width minus
                    // the three interior gaps, split four ways.
                    readonly property real colW: (canvas.width - root.gap * 3) / 4
                    readonly property bool inView: slot.place !== null && slot.place.y + slot.place.height
                                                   > flick.contentY - 240 && slot.place.y < flick.contentY
                                                   + flick.height + 240

                    property var lastPlace: null
                    property bool ready: false

                    onPlaceChanged: {
                        if (slot.place)
                            slot.lastPlace = slot.place;
                    }
                    Component.onCompleted: Qt.callLater(() => {
                        slot.ready = true;
                    })

                    x: slot.shown ? slot.shown.col * (slot.colW + root.gap) : 0
                    y: slot.shown ? slot.shown.y : 0
                    width: slot.shown ? slot.shown.w * slot.colW + (slot.shown.w - 1) * root.gap : 0
                    height: slot.shown ? slot.shown.height : 0
                    opacity: slot.place ? 1 : 0
                    scale: slot.place ? 1 : 0.6
                    visible: opacity > 0.01

                    Behavior on x {
                        enabled: slot.ready

                        SpringAnimation {
                            spring: 3.2
                            damping: 0.28
                        }
                    }

                    Behavior on y {
                        enabled: slot.ready

                        SpringAnimation {
                            spring: 3.2
                            damping: 0.28
                        }
                    }

                    Behavior on width {
                        enabled: slot.ready

                        SpringAnimation {
                            spring: 3.2
                            damping: 0.28
                        }
                    }

                    Behavior on height {
                        enabled: slot.ready

                        SpringAnimation {
                            spring: 3.2
                            damping: 0.28
                        }
                    }

                    Behavior on opacity {
                        enabled: slot.ready

                        NumberAnimation {
                            duration: 180
                        }
                    }

                    Behavior on scale {
                        enabled: slot.ready

                        SpringAnimation {
                            spring: 3.2
                            damping: 0.3
                        }
                    }

                    // Type → tile table. Upstream writes this as a nested
                    // ternary that grows one indent level per card type; with
                    // eight more tiles still to port that chain is unreadable,
                    // so the mapping is explicit here instead.
                    readonly property var tileFor: ({
                                                        "style": styleComponent,
                                                        "palette": paletteComponent,
                                                        "toggle": toggleComponent,
                                                        "select": selectComponent,
                                                        "slider": sliderComponent,
                                                        "spin": spinComponent,
                                                        "combo": comboComponent,
                                                        "text": textComponent,
                                                        "barlayout": barLayoutComponent
                                                    })

                    active: slot.place !== null && (slot.modelData.kind === "header" || slot.inView)
                    sourceComponent: slot.modelData.kind === "header" ? headerComponent : (
                                                                            slot.tileFor[slot.modelData.type]
                                                                            ?? null)

                    Component {
                        id: headerComponent

                        Item {
                            RowLayout {
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: 10

                                // Section title in a pill, then the entry count
                                // outside it. Copied from end4-pC's
                                // headerComponent: the pill carries 10px of
                                // horizontal padding over its content, sits at
                                // colPrimaryContainer, and the icon+label inside
                                // are spaced 8.
                                Rectangle {
                                    radius: height / 2
                                    color: Appearance.colors.colPrimaryContainer
                                    implicitHeight: 32
                                    implicitWidth: headerChip.implicitWidth + 22

                                    RowLayout {
                                        id: headerChip

                                        anchors.centerIn: parent
                                        spacing: 8

                                        MaterialSymbol {
                                            text: slot.modelData.icon ?? "tune"
                                            iconSize: 18
                                            fill: 1
                                            color: Appearance.colors.colOnPrimaryContainer
                                        }

                                        StyledText {
                                            text: slot.modelData.title
                                            font.pixelSize: Typography.bodyLarge.pixelSize
                                            font.weight: Font.DemiBold
                                            color: Appearance.colors.colOnPrimaryContainer
                                        }
                                    }
                                }

                                StyledText {
                                    text: slot.modelData.count ?? ""
                                    font.pixelSize: Typography.bodySmall.pixelSize
                                    color: Appearance.colors.colSubtext
                                }

                                Rectangle {
                                    Layout.fillWidth: true
                                    implicitHeight: 2
                                    radius: 1
                                    gradient: Gradient {
                                        orientation: Gradient.Horizontal
                                        GradientStop {
                                            position: 0
                                            color: Appearance.colors.colPrimary
                                        }
                                        GradientStop {
                                            position: 0.35
                                            color: Appearance.colors.colOutlineVariant
                                        }
                                        GradientStop {
                                            position: 1
                                            color: "transparent"
                                        }
                                    }
                                }
                            }
                        }
                    }

                    Component {
                        id: styleComponent

                        // style / schemes / palette carry their own headings and
                        // artwork, so unlike the generic tiles they take no
                        // title, icon or shape from the catalog entry.
                        DashboardStyleCard {
                            anchors.fill: parent
                            controlKey: slot.modelData.key
                            override: DashboardSettingsCatalog.controlFor(slot.modelData.key)
                            pager: root.pager
                            staggerMs: root.staggerMs
                            animIndex: slot.index % 6
                            travelX: slot.modelData.travelX
                            travelY: slot.modelData.travelY
                        }
                    }

                    Component {
                        id: paletteComponent

                        // Unlike style/schemes this tile *does* take its title and
                        // icon from the catalog: the heading sits in a fixed-width
                        // left column beside the option rows, not above them.
                        DashboardPaletteCard {
                            anchors.fill: parent
                            controlKey: slot.modelData.key
                            override: DashboardSettingsCatalog.controlFor(slot.modelData.key)
                            title: slot.modelData.title
                            icon: slot.modelData.icon
                            tileShape: slot.modelData.shape
                            pager: root.pager
                            staggerMs: root.staggerMs
                            animIndex: slot.index % 6
                            travelX: slot.modelData.travelX
                            travelY: slot.modelData.travelY
                        }
                    }

                    Component {
                        id: toggleComponent

                        DashboardToggleCard {
                            anchors.fill: parent
                            controlKey: slot.modelData.key
                            override: DashboardSettingsCatalog.controlFor(slot.modelData.key)
                            title: slot.modelData.title
                            icon: slot.modelData.icon
                            tileShape: slot.modelData.shape
                            pager: root.pager
                            staggerMs: root.staggerMs
                            animIndex: slot.index % 6
                            travelX: slot.modelData.travelX
                            travelY: slot.modelData.travelY
                        }
                    }

                    Component {
                        id: selectComponent

                        DashboardSelectCard {
                            anchors.fill: parent
                            controlKey: slot.modelData.key
                            override: DashboardSettingsCatalog.controlFor(slot.modelData.key)
                            title: slot.modelData.title
                            icon: slot.modelData.icon
                            tileShape: slot.modelData.shape
                            pager: root.pager
                            staggerMs: root.staggerMs
                            animIndex: slot.index % 6
                            travelX: slot.modelData.travelX
                            travelY: slot.modelData.travelY
                        }
                    }

                    Component {
                        id: sliderComponent

                        DashboardSliderCard {
                            anchors.fill: parent
                            controlKey: slot.modelData.key
                            override: DashboardSettingsCatalog.controlFor(slot.modelData.key)
                            title: slot.modelData.title
                            icon: slot.modelData.icon
                            tileShape: slot.modelData.shape
                            showPercent: slot.modelData.percent !== false
                            pager: root.pager
                            staggerMs: root.staggerMs
                            animIndex: slot.index % 6
                            travelX: slot.modelData.travelX
                            travelY: slot.modelData.travelY
                        }
                    }

                    Component {
                        id: spinComponent

                        DashboardSpinCard {
                            anchors.fill: parent
                            controlKey: slot.modelData.key
                            override: DashboardSettingsCatalog.controlFor(slot.modelData.key)
                            title: slot.modelData.title
                            icon: slot.modelData.icon
                            tileShape: slot.modelData.shape
                            pager: root.pager
                            staggerMs: root.staggerMs
                            animIndex: slot.index % 6
                            travelX: slot.modelData.travelX
                            travelY: slot.modelData.travelY
                        }
                    }

                    Component {
                        id: comboComponent

                        DashboardComboCard {
                            anchors.fill: parent
                            controlKey: slot.modelData.key
                            override: DashboardSettingsCatalog.controlFor(slot.modelData.key)
                            title: slot.modelData.title
                            icon: slot.modelData.icon
                            tileShape: slot.modelData.shape
                            pager: root.pager
                            staggerMs: root.staggerMs
                            animIndex: slot.index % 6
                            travelX: slot.modelData.travelX
                            travelY: slot.modelData.travelY
                        }
                    }

                    Component {
                        id: textComponent

                        DashboardTextCard {
                            anchors.fill: parent
                            controlKey: slot.modelData.key
                            override: DashboardSettingsCatalog.controlFor(slot.modelData.key)
                            title: slot.modelData.title
                            icon: slot.modelData.icon
                            tileShape: slot.modelData.shape
                            placeholder: slot.modelData.placeholder ?? ""
                            pager: root.pager
                            staggerMs: root.staggerMs
                            animIndex: slot.index % 6
                            travelX: slot.modelData.travelX
                            travelY: slot.modelData.travelY
                        }
                    }

                    Component {
                        id: barLayoutComponent

                        DashboardBarLayoutCard {
                            anchors.fill: parent
                            title: slot.modelData.title
                            icon: slot.modelData.icon
                            tileShape: slot.modelData.shape
                            pager: root.pager
                            staggerMs: root.staggerMs
                            animIndex: slot.index % 6
                            travelX: slot.modelData.travelX
                            travelY: slot.modelData.travelY
                        }
                    }
                }
            }
        }
    }
}
