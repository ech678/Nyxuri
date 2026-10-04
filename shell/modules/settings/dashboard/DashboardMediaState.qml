import QtQuick
import qs.app.services
import qs.modules.keystone.media
import qs.shared.theme

// Cover-art state for the dashboard's media page: which artwork to show, and
// the palette derived from it.
//
// Ported from end4-pC's modules/ii/settings/DashboardMediaState.qml. In end4-pC
// this is what makes the media page stop looking like the settings panel and
// start looking like the record that is playing — the whole surface, toolbar
// and controls take the cover's colour while a track is on.
//
// Difference from end4-pC: it downloads remote covers itself with a curl
// Process and caches under Directories.coverArt, then quantises with a
// ColorQuantizer. nyxuri already has that entire pipeline behind MediaPalette
// (native Oklab binning plus a python fetch script, see
// app/services/…/fetch_cover.py), so this object is only the adapter: it picks
// the active player, hands the art URL to MediaPalette, and exposes the result
// in the shape the dashboard reads.
Item {
    id: root

    visible: false
    width: 0
    height: 0

    // The active player, as resolved by MediaService. Going through the service
    // rather than Mpris directly is what keeps this consistent with every other
    // media surface in the shell (the bar, the keystone panel) when several
    // players are open.
    readonly property var player: MediaService.active
    readonly property string artUrl: root.player ? String(root.player.trackArtUrl ?? "") : ""

    // True when there is artwork to show at all. Named for the upstream field
    // so the call sites that were written against end4-pC's shape still read
    // correctly; here it is the URL rather than a resolved file path, because
    // MediaPalette owns the download and the Image element accepts the remote
    // URL directly.
    readonly property bool hasArt: root.artUrl !== ""
    readonly property string displayedArtFilePath: root.artUrl

    // Whether the cover palette should replace the theme.
    //
    // Gated on "there is artwork", not on "the extraction has finished". An
    // earlier version added a `paletteReady` flag for that and it was wrong
    // twice over: it made the flag read MediaPalette.primary while the scheme
    // colour read the flag, which is a genuine cycle — Qt reported it as a
    // binding loop and stops updating a property it considers looping, so the
    // theming would have quietly never switched on. Upstream gates on the
    // artwork alone and lets the palette's own fallback cover the gap, which is
    // also what happens here: MediaPalette resolves to the theme primary until
    // an extraction lands.
    readonly property bool active: root.hasArt

    // The cover colour the scheme is built from, or the theme primary when the
    // extractor has not produced one. The `a > 0` test is for the invalid
    // QColor the native plugin returns before its first palette.
    readonly property color artDominantColor: MediaPalette.primary.a > 0 ? MediaPalette.primary :
                                                                           Appearance.colors.colPrimary

    // The derived palette. Declared unconditionally so the page can bind to its
    // properties without a null guard; `active` says whether to use it.
    readonly property CoverScheme blendedColors: CoverScheme {
        color: root.artDominantColor
    }

    // Hands the current artwork to the extractor. MediaPalette debounces and
    // de-duplicates internally, so calling this on every artUrl change is
    // cheap and is exactly what it expects.
    function refresh() {
        MediaPalette.extract(root.hasArt ? root.artUrl : "", Appearance.colors.colPrimary);
    }

    onArtUrlChanged: root.refresh()
    // The fallback colour is the theme primary, so a theme change has to
    // re-run the extraction or the palette keeps the old scheme's hues.
    Connections {
        function onColPrimaryChanged() {
            root.refresh();
        }

        target: Appearance.colors
    }
    // Deliberately no Component.onDestruction that clears the palette.
    // MediaPalette is a singleton shared with the keystone media panel, which
    // reads the same extraction; clearing it here would blank that panel's
    // colours whenever the dashboard closed, and it would not recover until the
    // next track change. Re-entering the dashboard re-runs refresh() above, so
    // there is nothing to clean up.
    Component.onCompleted: root.refresh()
}
