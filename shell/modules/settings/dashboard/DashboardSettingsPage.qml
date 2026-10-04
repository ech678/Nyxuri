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

    readonly property real rowHeight: 140
    readonly property real headerHeight: 36
    readonly property real gap: 12

    readonly property var shapePool: [MaterialShapeCanvas.Shape.Cookie6Sided, MaterialShapeCanvas.Shape.Gem,
        MaterialShapeCanvas.Shape.Pentagon, MaterialShapeCanvas.Shape.Flower, MaterialShapeCanvas.Shape.Puffy,
        MaterialShapeCanvas.Shape.Clover8Leaf, MaterialShapeCanvas.Shape.Sunny]

    function spanOf(entry) {
        return entry.w ? [entry.w, 1] : baseSpan(entry.type);
    }

    function baseSpan(type) {
        if (type === "slider")
            return [2, 2];
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
    // sections never interleave.
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

    function packRows(cards, capacity) {
        const fulls = cards.filter(c => spanOf(c)[0] === 4);
        const wides = cards.filter(c => spanOf(c)[0] === 2);
        const smalls = cards.filter(c => spanOf(c)[0] === 1);
        const placed = [];
        let remaining = capacity;
        fulls.concat(wides, smalls).forEach(card => {
            const span = spanOf(card)[0];
            if (span > remaining)
                remaining = capacity;
            placed.push({
                            "entry": card,
                            "w": span,
                            "h": spanOf(card)[1]
                        });
            remaining -= span;
            if (remaining === 0)
                remaining = capacity;
        });
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

                    active: slot.place !== null && (slot.modelData.kind === "header" || slot.inView)
                    sourceComponent: slot.modelData.kind === "header" ? headerComponent : slot.modelData.type
                                                                        === "toggle" ? toggleComponent :
                                                                                       slot.modelData.type
                                                                                       === "select"
                                                                                       ? selectComponent :
                                                                                         slot.modelData.type
                                                                                         === "slider"
                                                                                         ? sliderComponent :
                                                                                           slot.modelData.type
                                                                                           === "spin"
                                                                                           ? spinComponent :
                                                                                             slot.modelData.type
                                                                                             === "combo"
                                                                                             ? comboComponent :
                                                                                               slot.modelData.type
                                                                                               === "text"
                                                                                               ? textComponent :
                                                                                                 null

                    Component {
                        id: headerComponent

                        Item {
                            RowLayout {
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: 10

                                MaterialSymbol {
                                    text: slot.modelData.icon ?? "tune"
                                    iconSize: 22
                                    fill: 1
                                    color: Appearance.colors.colPrimary
                                }

                                StyledText {
                                    Layout.fillWidth: true
                                    text: slot.modelData.title
                                    font.pixelSize: Typography.titleLarge.pixelSize
                                    font.weight: Font.DemiBold
                                    color: Appearance.colors.colOnLayer0
                                }

                                StyledText {
                                    text: slot.modelData.count ?? ""
                                    font.pixelSize: Typography.bodySmall.pixelSize
                                    color: Appearance.colors.colSubtext
                                    opacity: 0.7
                                }
                            }
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
                }
            }
        }
    }
}
