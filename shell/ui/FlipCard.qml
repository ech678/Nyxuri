import QtQuick

// Two-face card that flips on its vertical axis. Ported 1:1 from end4-pC's
// FlipCard; used by the dashboard home page for the profile card.
Item {
    id: root

    signal flipped

    function flip() {
        flipAnim.start();
    }

    transform: Scale {
        id: flipScale

        origin.x: root.width / 2
        origin.y: root.height / 2
        xScale: 1
    }

    SequentialAnimation {
        id: flipAnim

        NumberAnimation {
            target: flipScale
            property: "xScale"
            to: 0
            duration: 150
            easing.type: Easing.InQuad
        }
        ScriptAction {
            script: root.flipped()
        }
        NumberAnimation {
            target: flipScale
            property: "xScale"
            to: 1
            duration: 150
            easing.type: Easing.OutQuad
        }
    }
}
