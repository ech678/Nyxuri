import QtQuick
import qs.shared.theme

Item {
    id: root

    property int weatherCode: -1
    property string iconName: ""
    property bool night: false
    property string style: "flat"
    property bool animated: true
    property bool playing: visible
    property real baseSize: 128
    property color color: Appearance.colors.colPrimary

    readonly property string iconSymbol: symbolForCode(weatherCode, iconName, night)

    function symbolForCode(code, name, isNight) {
        if (code === 0)
            return isNight ? "bedtime" : "wb_sunny";
        if (code === 1)
            return isNight ? "partly_cloudy_night" : "partly_cloudy_day";
        if (code === 2)
            return isNight ? "partly_cloudy_night" : "partly_cloudy_day";
        if (code === 3)
            return "cloud";
        if (code === 45 || code === 48)
            return "foggy";
        if (code >= 51 && code <= 57)
            return "rainy";
        if (code === 61 || code === 63 || code === 65)
            return "rainy";
        if (code === 66 || code === 67)
            return "weather_mix";
        if (code >= 71 && code <= 77)
            return "ac_unit";
        if (code >= 80 && code <= 82)
            return "rainy";
        if (code === 85 || code === 86)
            return "weather_snowy";
        if (code === 95)
            return "thunderstorm";
        if (code === 96 || code === 99)
            return "thunderstorm";

        if (name && name.length > 0) {
            const lower = name.toLowerCase();
            if (lower.includes("clear_night") || lower.includes("night"))
                return "bedtime";
            if (lower.includes("sun") || lower.includes("sunny"))
                return "wb_sunny";
            if (lower.includes("partly"))
                return isNight ? "partly_cloudy_night" : "partly_cloudy_day";
            if (lower.includes("cloud"))
                return "cloud";
            if (lower.includes("fog"))
                return "foggy";
            if (lower.includes("drizzle") || lower.includes("rain"))
                return "rainy";
            if (lower.includes("snow"))
                return "ac_unit";
            if (lower.includes("thunder"))
                return "thunderstorm";
        }
        return isNight ? "bedtime" : "wb_sunny";
    }

    Text {
        anchors.centerIn: parent
        text: root.iconSymbol
        font.family: Fonts.materialSymbolsOutlined
        font.pixelSize: Math.max(1, Math.round(Math.min(root.width, root.height) * 0.85))
        color: root.color
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }
}
