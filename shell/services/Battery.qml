pragma Singleton

import QtQuick
import Quickshell
import qs.services

// Bridge singleton adapting PowerService to end4/iNiR Battery contracts
Singleton {
    id: root

    readonly property bool available: PowerService.present
    readonly property real percentage: isFinite(PowerService.percentage) ? PowerService.percentage : 0
    readonly property bool isCharging: PowerService.charging
    readonly property bool isPluggedIn: PowerService.powerConnected || PowerService.charging || PowerService.full
    readonly property int chargeState: PowerService.state
    readonly property real health: isFinite(PowerService.healthPercentage) ? PowerService.healthPercentage : 100
    readonly property int chargeCycles: 0
    readonly property real energyRate: isFinite(PowerService.changeRate) ? Math.abs(PowerService.changeRate) : 0
    readonly property real timeToFull: isFinite(PowerService.timeToFull) ? PowerService.timeToFull : 0
    readonly property real timeToEmpty: isFinite(PowerService.timeToEmpty) ? PowerService.timeToEmpty : 0
    readonly property bool isCriticalAndNotCharging: available && percentage <= 0.1 && !isCharging
    readonly property bool isLowAndNotCharging: available && percentage <= 0.2 && !isCharging
}
