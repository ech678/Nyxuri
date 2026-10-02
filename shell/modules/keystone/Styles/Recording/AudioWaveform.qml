import QtQuick
import qs.Common

Item {
    id: root

    property bool active: false
    property bool vertical: false
    property bool acceptSamples: false
    property bool sourceAvailable: false
    property double amplitude: 0
    property double sampleTimestampMs: 0
    property int activeBars: 19
    property int waitingBars: 8
    property real barWidth: 3
    property real barGap: 3
    property real minimumHeight: 2
    property real maximumHeight: 36
    property color activeColor: Appearance.colors.colError
    property color waitingColor: Appearance.applyAlpha(Appearance.colors.colOnSurfaceVariant, 0.32)
    property var _levels: []
    property var _bornAt: []
    property bool _hasConvertingSample: false
    property double _convertingLevel: 0
    property double _convertingBornAt: 0
    property double _lastSourceTimestamp: 0
    property double _lastPushAt: 0
    property double _frozenAt: 0
    property real _frozenPhase: 0
    readonly property int _sampleInterval: 160
    readonly property int _totalBars: activeBars + waitingBars
    readonly property real timelineExtent: _totalBars * (barWidth + barGap) - barGap

    function clamp01(value) {
        return Math.max(0, Math.min(1, Number(value) || 0));
    }

    function resetHistory() {
        _levels = [];
        _bornAt = [];
        _hasConvertingSample = false;
        _convertingLevel = 0;
        _convertingBornAt = 0;
        _lastSourceTimestamp = 0;
        _lastPushAt = Date.now();
        _frozenAt = 0;
        _frozenPhase = 0;
        waveformCanvas.requestPaint();
    }

    function movementPhase(now) {
        if (!_hasConvertingSample)
            return 0;

        return Math.max(0, Math.min(1, (now - _lastPushAt) / _sampleInterval));
    }

    function pushSample(value, timestamp) {
        const now = Date.now();
        if (_hasConvertingSample) {
            if (_levels.length >= activeBars) {
                _levels.shift();
                _bornAt.shift();
            }
            _levels.push(_convertingLevel);
            _bornAt.push(_convertingBornAt);
        }
        _convertingLevel = sourceAvailable ? clamp01(value) : 0;
        _convertingBornAt = now;
        _hasConvertingSample = true;
        _lastSourceTimestamp = timestamp;
        _lastPushAt = now;
        _frozenAt = 0;
        _frozenPhase = 0;
        waveformCanvas.requestPaint();
    }

    function animatedHeightFor(level, bornAt, now) {
        const targetHeight = minimumHeight + clamp01(level) * (maximumHeight - minimumHeight);
        const age = Math.max(0, now - bornAt);
        if (bornAt <= 0)
            return minimumHeight;

        if (age < 90) {
            const progress = age / 90;
            const eased = 1 - Math.pow(1 - progress, 3);
            return minimumHeight + (targetHeight * 1.08 - minimumHeight) * eased;
        }
        if (age < 220) {
            const progress = (age - 90) / 130;
            const eased = 1 - Math.pow(1 - progress, 3);
            return targetHeight * (1.08 - 0.08 * eased);
        }
        return targetHeight;
    }

    function mixedColor(fromColor, toColor, progress) {
        const amount = clamp01(progress);
        return Qt.rgba(fromColor.r + (toColor.r - fromColor.r) * amount, fromColor.g + (toColor.g - fromColor.g) * amount, fromColor.b + (toColor.b - fromColor.b) * amount, fromColor.a + (toColor.a - fromColor.a) * amount);
    }

    function paintBar(context, timelinePosition, amplitudeExtent, fillColor) {
        const crossCenter = vertical ? width / 2 : height / 2;
        const radius = Math.min(barWidth / 2, amplitudeExtent / 2);
        context.fillStyle = fillColor;
        context.beginPath();
        if (vertical) {
            const x = crossCenter - amplitudeExtent / 2;
            context.roundedRect(x, timelinePosition, amplitudeExtent, barWidth, radius, radius);
        } else {
            const y = crossCenter - amplitudeExtent / 2;
            context.roundedRect(timelinePosition, y, barWidth, amplitudeExtent, radius, radius);
        }
        context.fill();
    }

    implicitWidth: vertical ? maximumHeight : timelineExtent
    implicitHeight: vertical ? timelineExtent : maximumHeight
    onSampleTimestampMsChanged: {
        if (active && acceptSamples && sampleTimestampMs > _lastSourceTimestamp)
            pushSample(amplitude, sampleTimestampMs);

    }
    onActiveChanged: {
        if (active)
            resetHistory();

    }
    onAcceptSamplesChanged: {
        if (acceptSamples) {
            _frozenAt = 0;
            _frozenPhase = 0;
        } else if (active) {
            _frozenAt = Date.now();
            _frozenPhase = movementPhase(_frozenAt);
        }
        waveformCanvas.requestPaint();
    }
    onActiveBarsChanged: resetHistory()
    onWaitingBarsChanged: resetHistory()
    Component.onCompleted: resetHistory()

    FrameAnimation {
        running: root.active && root.acceptSamples
        onTriggered: waveformCanvas.requestPaint()
    }

    Canvas {
        id: waveformCanvas

        anchors.fill: parent
        antialiasing: true
        renderTarget: Canvas.FramebufferObject
        renderStrategy: Canvas.Cooperative
        onPaint: {
            const context = getContext("2d");
            context.reset();
            const now = root._frozenAt > 0 ? root._frozenAt : Date.now();
            const pitch = root.barWidth + root.barGap;
            const timelineExtent = root.timelineExtent;
            const phase = root._frozenAt > 0 ? root._frozenPhase : root.movementPhase(now);
            context.save();
            context.beginPath();
            context.rect(0, 0, width, height);
            context.clip();
            const firstSlot = root.activeBars - root._levels.length;
            for (let slot = 0; slot < root._levels.length; ++slot) {
                const barHeight = root.animatedHeightFor(root._levels[slot], root._bornAt[slot], now);
                const position = (firstSlot + slot - phase) * pitch;
                root.paintBar(context, position, barHeight, root.activeColor);
            }
            if (root._hasConvertingSample) {
                const colorProgress = 1 - Math.pow(1 - phase, 3);
                const convertingColor = root.mixedColor(root.waitingColor, root.activeColor, colorProgress);
                const convertingHeight = root.animatedHeightFor(root._convertingLevel, root._convertingBornAt, now);
                const convertingPosition = (root.activeBars - phase) * pitch;
                root.paintBar(context, convertingPosition, convertingHeight, convertingColor);
                for (let slot = 1; slot < root.waitingBars; ++slot) {
                    const position = (root.activeBars + slot - phase) * pitch;
                    root.paintBar(context, position, root.minimumHeight, root.waitingColor);
                }
                const enteringPosition = (root._totalBars - phase) * pitch;
                root.paintBar(context, enteringPosition, root.minimumHeight, root.waitingColor);
            } else {
                for (let slot = 0; slot < root.waitingBars; ++slot) {
                    const position = (root.activeBars + slot) * pitch;
                    root.paintBar(context, position, root.minimumHeight, root.waitingColor);
                }
            }
            context.restore();
        }
    }

}
