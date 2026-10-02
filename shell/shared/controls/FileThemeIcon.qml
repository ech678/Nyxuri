import QtQuick
import QtQuick.Window
import Quickshell
import qs.Common
import qs.Services

Item {
    id: root

    property string entryKey: ""
    property string themeIcon: ""
    property string mimeType: ""
    property string category: ""
    property bool active: true
    property bool directory: false
    property string fallbackSymbol: directory ? "folder" : "draft"
    property real iconSize: 40
    // Animated consumers can keep the decoded image stable while scaling it.
    property real rasterSize: 0
    property bool transformed: false
    readonly property int themeRevision: ThemeService.iconThemeRevision
    readonly property var candidates: {
        if (directory)
            return themeIcon && themeIcon !== "folder" ? [themeIcon, "folder"] : ["folder"];
        const mime = mimeType.split(";", 1)[0];
        const family = mime.indexOf("/") > 0 ? mime.split("/", 1)[0] : ["video", "audio", "image"].indexOf(
                                                   category) >= 0 ? category : "text";
        const names = [themeIcon || mime.replace("/", "-"), family + "-x-generic", "text-x-generic"];
        return names.filter((name, index) => name !== "" && names.indexOf(name) === index);
    }
    property var attemptedSources: []
    property int candidateIndex: 0
    property int generation: 0
    property bool initialized: false

    implicitWidth: iconSize
    implicitHeight: iconSize

    function nextSource() {
        while (candidateIndex < candidates.length) {
            const name = candidates[candidateIndex++];
            // Check before resolving: the resolver's image-missing fallback
            // must not short-circuit the remaining semantic candidates.
            if (!Quickshell.hasThemeIcon(name))
                continue;
            const resolved = Quickshell.iconPath(name, true);
            if (resolved !== "" && attemptedSources.indexOf(resolved) < 0) {
                attemptedSources = attemptedSources.concat([resolved]);
                artwork.iconSource = resolved;
                return;
            }
        }
        artwork.iconSource = "";
    }
    function reset() {
        generation += 1;
        candidateIndex = 0;
        attemptedSources = [];
        artwork.iconSource = "";
        if (active)
            nextSource();
    }
    onActiveChanged: {
        if (initialized)
            reset();
    }
    onCandidatesChanged: {
        if (initialized)
            reset();
    }
    onEntryKeyChanged: {
        if (initialized)
            reset();
    }
    onThemeRevisionChanged: {
        if (initialized)
            reset();
    }
    Component.onCompleted: {
        initialized = true;
        reset();
    }

    ThemeIcon {
        id: artwork
        anchors.fill: parent
        smooth: true
        antialiasing: root.transformed
        mipmap: root.transformed
        asynchronous: true
        retainWhileLoading: false
        fillMode: Image.PreserveAspectFit
        sourceSize: Qt.size(Math.ceil((root.rasterSize || width) * Screen.devicePixelRatio), Math.ceil((root.rasterSize
                                                                                                        || height)
                                                                                                       * Screen.devicePixelRatio))
        visible: status === Image.Ready
        onStatusChanged: {
            if (status !== Image.Error)
                return;
            const failedGeneration = root.generation;
            const failedSource = source.toString();
            Qt.callLater(() => {
                if (root.generation === failedGeneration && artwork.iconSource.toString() === failedSource)
                    root.nextSource();
            });
        }
    }
    MaterialSymbol {
        anchors.centerIn: parent
        visible: !artwork.visible
        text: root.fallbackSymbol || (root.directory ? "folder" : "draft")
        iconSize: Math.min(root.width, root.height)
        color: Appearance.colors.colOnSurfaceVariant
    }
}
