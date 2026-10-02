import QtQuick
import qs.app

Item {
    id: root

    function runWithoutOwner() {
        ActionGateway.execute(["notify-send", "test"]);
    }
}
