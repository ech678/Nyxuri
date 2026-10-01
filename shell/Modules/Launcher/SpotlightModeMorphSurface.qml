pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Effects
import qs.Common

Item {
    id: root

    required property real railProgress
    required property real mainLeft
    required property real collapsedMainWidth
    required property real expandedMainWidth
    required property real shapeCenterY
    required property real shapeHeight
    required property real buttonDiameter
    required property real buttonGap
    required property real blurEdgeInset

    property color surfaceColor: Appearance.colors.colSurfaceContainerHigh
    property color shadowColor: Appearance.colors.colShadow
    property real shadowBlur: 0.72
    property real shadowVerticalOffset: 7
    readonly property var blurRegionItems: [mainBlurRegion, button0BlurRegion, button1BlurRegion,
        button2BlurRegion, button3BlurRegion, neck0BlurRegion, neck1BlurRegion, neck2BlurRegion,
        neck3BlurRegion]

    // The pill leads the motion; the trailing buttons follow with progressively
    // slower responses. Continuous damping avoids stops between authored poses.
    readonly property real mainWidth: interpolate(collapsedMainWidth, expandedMainWidth, response(0, 6.2, 7.5,
                                                                                                  0.4))
    readonly property real mainCenterX: mainLeft + mainWidth / 2
    readonly property real mainRight: mainLeft + mainWidth
    readonly property real expandedMainRight: mainLeft + expandedMainWidth
    readonly property vector4d mainShape: Qt.vector4d(mainCenterX, shapeCenterY, mainWidth, shapeHeight)
    readonly property var buttonShapes: [buttonShape(0), buttonShape(1), buttonShape(2), buttonShape(3)]
    readonly property var travelDelays: [0.06, 0.036, 0.032]
    readonly property var travelDecays: [7.2, 5.4, 5.4]
    readonly property var travelFrequencies: [8.9, 6.2, 5.35]
    readonly property var growthRates: [3.8, 3.1, 2.7]

    function smoothstep(value) {
        const progress = Math.max(0, Math.min(1, value));
        return progress * progress * (3 - 2 * progress);
    }

    function stage(start, end) {
        return smoothstep((root.railProgress - start) / (end - start));
    }

    function interpolate(from, to, progress) {
        return from + (to - from) * progress;
    }

    // Normalize the damped response at the endpoint so interruption/reversal
    // remains a pure function of railProgress and the final layout is exact.
    function response(delay, decay, frequency, phase) {
        const time = Math.max(0, Math.min(1, root.railProgress) - delay);
        const end = 1 - delay;
        const value = 1 - Math.exp(-decay * time) * (Math.cos(frequency * time) + phase * Math.sin(frequency
                                                                                                   * time));
        const terminal = 1 - Math.exp(-decay * end) * (Math.cos(frequency * end) + phase * Math.sin(frequency
                                                                                                    * end));
        return value / terminal;
    }

    function buttonGrowth(index) {
        if (index === 0)
            return response(0.055, 10.5, 10.5, 1);
        const rate = root.growthRates[index - 1];
        return response(0, rate, rate, 0);
    }

    function buttonCenterX(index) {
        const diameter = root.buttonDiameter;
        const emergence = diameter * 0.3 * (buttonGrowth(0) - 1);
        const firstCenter = root.expandedMainRight + root.buttonGap + diameter / 2 + emergence;
        if (index === 0)
            return firstCenter;
        const decay = root.travelDecays[index - 1];
        const frequency = root.travelFrequencies[index - 1];
        const travel = response(root.travelDelays[index - 1], decay, frequency, decay / frequency);
        return firstCenter + index * (diameter + root.buttonGap) * travel;
    }

    function buttonShape(index) {
        const diameter = root.buttonDiameter * buttonGrowth(index);
        return Qt.vector4d(buttonCenterX(index), root.shapeCenterY, diameter, diameter);
    }

    function buttonBlend(index) {
        const shape = root.buttonShapes[index];
        // Suppress blending while one lobe is still buried in another; this
        // keeps the pill from inflating as the chain emerges. The same short
        // fade follows each lobe, so receding buttons cannot reconnect later.
        const previous = index === 0 ? root.mainShape : root.buttonShapes[index - 1];
        const previousCenter = index === 0 ? root.mainRight - root.shapeHeight / 2 : previous.x;
        const radii = (Math.min(previous.z, previous.w) + Math.min(shape.z, shape.w)) / 2;
        const separation = radii > 0 ? Math.abs(shape.x - previousCenter) / radii : 0;
        const exposed = smoothstep((separation - 0.5) / 0.5);
        const release = stage(0.27 + index * 0.063, 0.47 + index * 0.063);
        return Math.min(shape.z, shape.w, root.buttonDiameter) * 0.78 * exposed * (1 - release);
    }

    function iconProgress(index) {
        return stage(0.36 + index * 0.025, 0.55 + index * 0.025);
    }

    // A conservative blur-only rectangle inside the natural SDF neck. The
    // inscribed equal circles give a lower bound even for unequal capsules.
    // This never draws a bridge or blurs across an already detached gap.
    function neckBlurShape(index) {
        const shape = root.buttonShapes[index];
        const previous = index === 0 ? root.mainShape : root.buttonShapes[index - 1];
        const previousX = index === 0 ? root.mainRight - root.shapeHeight / 2 : previous.x;
        const radius = Math.min(shape.z, shape.w, previous.z, previous.w) / 2;
        const distance = Math.abs(shape.x - previousX);
        const reach = radius + buttonBlend(index) / 4;
        const halfHeight = Math.max(0, Math.min(radius, Math.sqrt(Math.max(0, reach * reach - distance * distance
                                                                           / 4))) - root.blurEdgeInset);
        return Qt.vector4d((previousX + shape.x) / 2, root.shapeCenterY, distance, halfHeight * 2);
    }

    ShaderEffect {
        id: surfaceSource

        anchors.fill: parent
        visible: false

        property vector2d resolution: Qt.vector2d(width, height)
        // Keep the intermediate texture opaque. MultiEffect's shadow mixing
        // otherwise changes the alpha/color of an already translucent fill.
        property color fillColor: Qt.rgba(root.surfaceColor.r, root.surfaceColor.g, root.surfaceColor.b, 1)
        property vector4d mainShape: root.mainShape
        property vector4d button0Shape: root.buttonShapes[0]
        property vector4d button1Shape: root.buttonShapes[1]
        property vector4d button2Shape: root.buttonShapes[2]
        property vector4d button3Shape: root.buttonShapes[3]
        property vector4d blends: Qt.vector4d(root.buttonBlend(0), root.buttonBlend(1), root.buttonBlend(2),
                                              root.buttonBlend(3))

        // A distinct resource URL for this uniform layout also invalidates
        // Qt's process-wide cache of the previous circle/bridge shader.
        fragmentShader: Paths.fileUrl(Paths.assetsDir + "/shaders/launcher/qsb/spotlight_mode_field.frag.qsb")
    }

    MultiEffect {
        anchors.fill: surfaceSource
        source: surfaceSource
        opacity: root.surfaceColor.a
        autoPaddingEnabled: true
        shadowEnabled: true
        shadowColor: root.shadowColor
        shadowBlur: root.shadowBlur
        shadowVerticalOffset: root.shadowVerticalOffset
        shadowHorizontalOffset: 0
    }

    component ShapeBlurRegion: Item {
        required property vector4d shape
        property real inset: root.blurEdgeInset
        x: shape.x - width / 2
        y: shape.y - height / 2
        width: Math.max(0, shape.z - inset * 2)
        height: Math.max(0, shape.w - inset * 2)
        property real radius: Math.min(width, height) / 2
        visible: width > 0 && height > 0
    }

    ShapeBlurRegion {
        id: mainBlurRegion
        shape: root.mainShape
    }

    ShapeBlurRegion {
        id: button0BlurRegion
        shape: root.buttonShapes[0]
    }

    ShapeBlurRegion {
        id: button1BlurRegion
        shape: root.buttonShapes[1]
    }

    ShapeBlurRegion {
        id: button2BlurRegion
        shape: root.buttonShapes[2]
    }

    ShapeBlurRegion {
        id: button3BlurRegion
        shape: root.buttonShapes[3]
    }

    ShapeBlurRegion {
        id: neck0BlurRegion
        shape: root.neckBlurShape(0)
        inset: 0
        radius: 0
    }

    ShapeBlurRegion {
        id: neck1BlurRegion
        shape: root.neckBlurShape(1)
        inset: 0
        radius: 0
    }

    ShapeBlurRegion {
        id: neck2BlurRegion
        shape: root.neckBlurShape(2)
        inset: 0
        radius: 0
    }

    ShapeBlurRegion {
        id: neck3BlurRegion
        shape: root.neckBlurShape(3)
        inset: 0
        radius: 0
    }
}
