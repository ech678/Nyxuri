import QtQuick
import QtTest
import "../../Common/functions/DockMedia.js" as DockMedia

TestCase {
    name: "DockMedia"

    function test_onlyExplicitDesktopIdentityMatches() {
        const players = [
                  {
                      desktopEntry: "org.example.Music",
                      identity: "Music"
                  },
                  {
                      desktopEntry: "org.example.Browser.desktop"
                  },
                  {
                      desktopEntry: "",
                      identity: "org.example.Browser"
                  },
                  {
                      desktopEntry: "org.example.browser"
                  }
              ];
        compare(DockMedia.matchingPlayers(players, "org.example.Music.desktop"), [players[0]]);
        compare(DockMedia.matchingPlayers(players, "org.example.Browser"), [players[1]]);
        compare(DockMedia.matchingPlayers(players, ""), []);
        compare(DockMedia.matchingPlayers(players, "unknown"), []);
    }

    function test_targetStaysUntilItLeavesMatchingPlayers() {
        const first = {
            desktopEntry: "browser",
            isPlaying: false
        };
        const second = {
            desktopEntry: "browser",
            isPlaying: true
        };
        let selected = DockMedia.selectPlayer([first], null);
        compare(selected, first);
        selected = DockMedia.selectPlayer([second, first], selected);
        compare(selected, first);
        first.isPlaying = true;
        second.isPlaying = false;
        compare(DockMedia.selectPlayer([second, first], selected), first);
        first.desktopEntry = "other-app";
        selected = DockMedia.selectPlayer(DockMedia.matchingPlayers([first, second], "browser"), selected);
        compare(selected, second);
        compare(DockMedia.selectPlayer([first], selected), first);
        compare(DockMedia.selectPlayer([], selected), null);
    }
}
