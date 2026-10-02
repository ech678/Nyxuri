import QtQuick
import qs.shared.theme

Rectangle {
    id: root

    property string baseProvider: "openfreemap"
    property string overlayProvider: ""
    function credit(url, label) {
        return '<a href="' + url + '" style="color:#111111;text-decoration:none">' + label + '</a>';
    }

    implicitWidth: attribution.implicitWidth + 2 * Metrics.spacingS
    implicitHeight: attribution.implicitHeight + 2 * Metrics.spacingXS
    radius: Metrics.spacingS
    color: "#DDEEEEEE"

    MouseArea {
        anchors.fill: parent
        acceptedButtons: Qt.AllButtons
        onWheel: wheel => wheel.accepted = true
    }

    Text {
        id: attribution

        x: Metrics.spacingS
        y: Metrics.spacingXS
        width: root.width - 2 * Metrics.spacingS
        text: (root.baseProvider === "maptiler" ? root.credit("https://www.maptiler.com/copyright/",
                                                              "© MapTiler") : root.credit(
                                                      "https://openfreemap.org/", "OpenFreeMap") + " · "
                                                  + root.credit("https://openmaptiles.org/",
                                                                "© OpenMapTiles")) + " · " + root.credit(
                  "https://www.openstreetmap.org/copyright", "© OpenStreetMap") + (root.overlayProvider
                                                                                   === "rainviewer" ? " · "
                                                                                                      + root.credit(
                                                                                                          "https://www.rainviewer.com/",
                                                                                                          "© RainViewer") :
                                                                                                      root.overlayProvider
                                                                                                      === "openweather"
                                                                                                      ? " · " + root.credit(
                                                                                                            "https://openweathermap.org/",
                                                                                                            "© OpenWeather") :
                                                                                                        "")
        textFormat: Text.RichText
        color: "#FF111111"
        font.family: Typography.labelSmall.family
        font.pixelSize: Typography.labelSmall.pixelSize
        wrapMode: Text.Wrap
        onLinkActivated: link => Qt.openUrlExternally(link)

        HoverHandler {
            cursorShape: attribution.hoveredLink !== "" ? Qt.PointingHandCursor : Qt.ArrowCursor
        }
    }
}
