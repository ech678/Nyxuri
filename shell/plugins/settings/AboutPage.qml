pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import Quickshell
import qs.commons
import qs.ui
import qs.commons.i18n
import qs.app
import qs.services
import qs.ui

// About page (Caelestia Nexus AboutPage): hero card with the product mark,
// then System / Software / Configuration sections. Built entirely from the
// M1 atom suite — the pilot for the M3 page rebuilds. Version data comes
// from SystemIdentityService (views never spawn processes themselves).
NexusPageBase {
    id: root

    title: I18n.tr("About")

    property bool justCopied: false

    Component.onCompleted: SystemIdentityService.ensureRuntimeVersions()

    ColumnLayout {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        width: root.cappedWidth
        spacing: 2

        // Hero
        ConnectedRect {
            Layout.fillWidth: true
            first: true
            last: true
            implicitHeight: heroColumn.implicitHeight + NexusStyle.padding.extraLarge * 2

            ColumnLayout {
                id: heroColumn

                anchors.centerIn: parent
                width: parent.width - NexusStyle.padding.largeIncreased * 2
                spacing: NexusStyle.padding.small

                MaterialSymbol {
                    Layout.alignment: Qt.AlignHCenter
                    Layout.topMargin: NexusStyle.padding.small
                    iconSize: NexusStyle.icon.extraLarge
                    fill: 1
                    grade: 25
                    text: "nightlight"
                    color: Appearance.m3colors.m3primary
                }

                StyledText {
                    Layout.alignment: Qt.AlignHCenter
                    text: "Nyxuri Shell"
                    color: Appearance.m3colors.m3onSurface
                    font.pixelSize: NexusStyle.font.headlineLarge
                    font.weight: NexusStyle.font.headlineWeight
                }

                StyledText {
                    Layout.alignment: Qt.AlignHCenter
                    text: SystemIdentityService.quickshellVersion ? `Quickshell 
${SystemIdentityService.quickshellVersion}` : "…"
                    color: Appearance.m3colors.m3onSurfaceVariant
                    font.pixelSize: NexusStyle.font.bodyMedium
                }
            }
        }

        // System
        PreferenceHeader {
            Layout.topMargin: NexusStyle.spacing.medium
            text: I18n.tr("System")
        }

        PreferenceInfo {
            first: true
            label: I18n.tr("Hostname")
            value: SystemIdentityService.hostName
        }

        PreferenceInfo {
            label: I18n.tr("Device")
            value: SystemIdentityService.productName || SystemIdentityService.boardName
        }

        PreferenceInfo {
            label: I18n.tr("Distro")
            value: SystemIdentityService.distroName
        }

        PreferenceInfo {
            label: I18n.tr("Kernel")
            value: SystemIdentityService.kernelRelease
        }

        PreferenceInfo {
            last: true
            label: I18n.tr("Firmware")
            value: SystemIdentityService.biosVersion
        }

        // Software — no Qt row: Quickshell's QML global exposes no Qt
        // version (Qt.version/qtVersion/qmlVersion are all undefined there)
        // and a process probe for a trivia row is not worth its lifecycle.
        PreferenceHeader {
            Layout.topMargin: NexusStyle.spacing.medium
            text: I18n.tr("Software")
        }

        PreferenceInfo {
            first: true
            label: I18n.tr("Quickshell")
            value: SystemIdentityService.quickshellVersion || "…"
        }

        PreferenceInfo {
            last: true
            label: I18n.tr("Compositor")
            value: SystemIdentityService.wmName
        }

        // Configuration — the quick actions the NavPane footer used to carry
        // (author decision 2026-10-25: the nav list stays pure like the
        // original, the plumbing lives here with the rest of the shell info).
        PreferenceHeader {
            Layout.topMargin: NexusStyle.spacing.medium
            text: I18n.tr("Configuration")
        }

        PreferenceAction {
            first: true
            icon: "edit"
            text: I18n.tr("Edit configuration file")
            subtext: PersonalizationConfig.filePath
            trailingIcon: ""
            onClicked: ApplicationService.openUrl(Paths.fileUrl(PersonalizationConfig.filePath))
        }

        PreferenceAction {
            last: true
            icon: "content_copy"
            text: I18n.tr("Copy configuration path")
            subtext: root.justCopied ? I18n.tr("Path copied") : ""
            trailingIcon: ""
            onClicked: {
                Quickshell.clipboardText = PersonalizationConfig.filePath;
                copiedTimer.restart();
            }
        }

        // Non-visual child of the content column: NexusPageBase's default
        // property is a single Item, so a page-level Timer must not sit on
        // the page root (type error kills the whole page — 2026-10-25).
        Timer {
            id: copiedTimer

            interval: 1400
            onTriggered: root.justCopied = false
        }
    }
}
