pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import qs.commons
import qs.services
import qs.commons.i18n

Singleton {
    id: root

    readonly property bool runningOnNiri: CompositorDriver.available
    property bool compositorSupported: false
    readonly property bool available: root.runningOnNiri && root.compositorSupported
    readonly property bool enabled: root.available && PersonalizationConfig.shellBlurEnabled
    readonly property bool xray: PersonalizationConfig.shellBlurXray
    readonly property bool integrationBusy: NiriConfigService.busy && NiriConfigService.activeFeature
                                            === "effects"

    readonly property bool niriIntegrationReady: NiriConfigService.ready("effects")
    property string versionErrorText: ""
    readonly property string lastError: versionErrorText || NiriConfigService.error
    readonly property string niriVersion: CompositorDriver.compositorVersion

    signal integrationConfigured
    signal integrationFailed(string message)

    // Publish the capability into the shared layer, which cannot read config or
    // probe the compositor itself. CompositorBlurRegion gates submission on it.
    Binding {
        target: Appearance
        property: "compositorBlurEnabled"
        value: root.enabled
    }

    function backgroundColor(baseColor) {
        return Appearance.applyAlpha(baseColor, PersonalizationConfig.shellBackgroundOpacity);
    }

    // A shell-managed Material surface. It starts from an opaque base but
    // intentionally follows the shell's configurable glass opacity.
    function opaqueBackgroundColor(baseColor) {
        return backgroundColor(Appearance.applyAlpha(baseColor, 1));
    }

    // A material surface that must remain opaque independently from the
    // shell's configurable glass opacity.
    function solidBackgroundColor(baseColor) {
        return Appearance.applyAlpha(baseColor, 1);
    }

    function supportsVersion(versionText) {
        const match = String(versionText || "").match(/(?:^|\s)(\d+)\.(\d+)(?:\D|$)/);
        if (!match)
            return false;
        const major = Number(match[1]);
        const minor = Number(match[2]);
        return major > 26 || (major === 26 && minor >= 4);
    }

    function refreshIntegrationState() {
        NiriConfigService.refresh();
    }
    function writeEffectsConfig() {
        if (root.available)
            NiriConfigService.update("effects");
    }
    function configureNiriIntegration() {
        NiriConfigService.setup("effects");
    }

    // The version probe lives in the compositor driver (S0-5); this service
    // only interprets the reported version against its own requirement.
    function _evaluateCompositorVersion() {
        if (!CompositorDriver.compositorVersionReady)
            return;
        const version = CompositorDriver.compositorVersion;
        root.compositorSupported = version.length > 0 && root.supportsVersion(version);
        if (!root.compositorSupported) {
            root.versionErrorText = version.length > 0 ? I18n.tr(
                                                             "The current Niri version does not support background blur") :
                                                         (CompositorDriver.compositorVersionError || I18n.tr(
                                                              "Unable to detect the Niri version"));
            return;
        }

        root.versionErrorText = "";
        root.refreshIntegrationState();
    }

    Component.onCompleted: root._evaluateCompositorVersion()

    Connections {
        target: CompositorDriver

        function onCompositorVersionReadyChanged() {
            root._evaluateCompositorVersion();
        }
    }

    Connections {
        target: PersonalizationConfig

        function onShellBlurXrayChanged() {
            root.writeEffectsConfig();
        }

        function onShellBlurEnabledChanged() {
            root.writeEffectsConfig();
        }
    }
}
