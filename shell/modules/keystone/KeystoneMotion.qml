pragma Singleton

import QtQuick
import Quickshell
import qs.shared.theme

Singleton {
    readonly property int type: Easing.BezierSpline
    readonly property int expandingDuration: Appearance.motionDuration(500)
    readonly property int shrinkingDuration: Appearance.motionDuration(360)
    readonly property int radiusDuration: Appearance.motionDuration(350)
    readonly property int hoverDuration: Appearance.motionDuration(360)
    readonly property var expandingBezier: Animations.curves.keystoneExpand
    readonly property var shrinkingBezier: Animations.curves.keystoneCollapse
    readonly property var hoverBezier: Animations.curves.standard
    readonly property var radiusBezier: shrinkingBezier
    readonly property int hoverWidthDelta: 20
    readonly property int hoverHeightDelta: 8
    readonly property int hoverRadiusDelta: 3
    readonly property int audioRecordingWidth: 320
    readonly property int audioRecordingHeight: 56
    readonly property int verticalAudioRecordingWidth: 56
    readonly property int verticalAudioRecordingHeight: 320
    readonly property int audioExpandDuration: Appearance.motionDuration(300)
    readonly property int audioContentEnterDuration: Appearance.motionDuration(180)
    readonly property int audioContentExitDuration: Appearance.motionDuration(120)
    readonly property int audioCollapseDuration: Appearance.motionDuration(240)
}
