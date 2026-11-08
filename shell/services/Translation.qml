pragma Singleton

import QtQuick
import Quickshell
import qs.commons.i18n

Singleton {
    id: root

    function tr(text: string): string {
        return I18n.tr(text);
    }
}
