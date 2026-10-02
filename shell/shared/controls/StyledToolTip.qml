import QtQuick
import qs.shared.theme
import qs.shared.controls

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
