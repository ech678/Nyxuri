import QtQuick
import qs.app.services
import "./SpotlightCommands.js" as Commands
import qs.shared.i18n

QtObject {
    id: root
    property bool active: false
    property bool slash: false
    property string query: ""
    property var sessionState: ({
                                    mode: "search",
                                    tool: ""
                                })
    readonly property string language: Qt.uiLanguage
    readonly property var results: {
        const currentLanguage = language;
        if (!active)
            return [];
        return SpotlightCatalog.commandMatches(query, !slash).map(entry => ({
            id: entry.id,
            title: SpotlightCatalog.commandTitle(entry),
            icon: entry.icon,
            subtitle: Commands.available(entry, sessionState) ? "/" + entry.slashName : I18n.tr(
                                                                    "Available in %1 only").arg(entry.scope
                                                                                                === "apps"
                                                                                                ? I18n.tr(
                                                                                                      "Apps") : I18n.tr(
                                                                                                      "Clipboard")),
            entry: entry
        }));
    }
    }
