import QtQuick
import qs.Common
import qs.Widgets.common

PopupToolTip {
    id: root

    property font font

    horizontalPadding: 10
    verticalPadding: 5
    font {
        family: Fonts.ui
        pixelSize: 12
        hintingPreference: Font.PreferNoHinting
    }

}
