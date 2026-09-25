import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Hinweis auf eine neue Version: Versionshinweise, Download mit Fortschritt, Installation.
AppDialog {
    id: dlg
    title: updater.state === "installing" ? "Update wird installiert" : "Update verfügbar"
    iconName: "sparkle"
    dialogWidth: 700
    closePolicy: updater.state === "installing" ? Popup.NoAutoClose : (Popup.CloseOnEscape | Popup.CloseOnPressOutside)

    readonly property bool busy: updater.state === "downloading" || updater.state === "installing"

    ColumnLayout {
        width: parent.width
        spacing: 12

        // ------------------------------------------------ Versionen
        RowLayout {
            Layout.fillWidth: true
            spacing: 14
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2
                RowLayout {
                    spacing: 10
                    Text {
                        objectName: "updateVersionText"
                        text: "Version " + updater.latestVersion
                        color: Theme.text
                        font.family: Theme.fontFamily
                        font.pixelSize: 24
                        font.weight: Font.Bold
                    }
                    Rectangle {
                        visible: updater.prerelease
                        implicitWidth: betaText.implicitWidth + 16
                        implicitHeight: 24
                        radius: 12
                        color: Theme.alpha(Theme.warning, 0.16)
                        border.color: Theme.alpha(Theme.warning, 0.6)
                        Text { id: betaText; anchors.centerIn: parent; text: "BETA"; color: Theme.warning
                               font.family: Theme.fontFamily; font.pixelSize: Theme.fontTiny; font.weight: Font.Bold; font.letterSpacing: 1 }
                    }
                }
                Text {
                    text: "Installiert: " + updater.currentVersion
                          + (updater.releaseDate !== "" ? "   ·   veröffentlicht am " + updater.releaseDate : "")
                          + (updater.downloadSize !== "" ? "   ·   " + updater.downloadSize : "")
                    color: Theme.textDim
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBody
                }
            }
        }

        // ------------------------------------------------ Versionshinweise
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: Math.min(260, Math.max(90, notes.implicitHeight + 24))
            radius: Theme.radiusSmall
            color: Theme.field
            border.color: Theme.border
            clip: true
            Flickable {
                id: notesFlick
                anchors.fill: parent
                anchors.margins: 12
                contentWidth: width
                contentHeight: notes.implicitHeight
                boundsBehavior: Flickable.StopAtBounds
                clip: true
                ScrollBar.vertical: ScrollBar { policy: notesFlick.contentHeight > notesFlick.height ? ScrollBar.AsNeeded : ScrollBar.AlwaysOff }
                Text {
                    id: notes
                    width: notesFlick.width - 8
                    text: updater.releaseNotes !== "" ? updater.releaseNotes : "Für diese Version liegen keine Versionshinweise vor."
                    textFormat: Text.MarkdownText
                    wrapMode: Text.Wrap
                    color: Theme.text
                    linkColor: Theme.accent
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBody
                    lineHeight: 1.15
                    onLinkActivated: (link) => Qt.openUrlExternally(link)
                }
            }
        }

        // ------------------------------------------------ Hinweise
        Text {
            Layout.fillWidth: true
            visible: !dlg.busy
            text: updater.installHint
            color: Theme.textDim
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontSmall
            wrapMode: Text.Wrap
            lineHeight: 1.2
        }
        Rectangle {
            Layout.fillWidth: true
            visible: !dlg.busy && (backend.showMode || backend.activeCount > 0)
            implicitHeight: warnRow.implicitHeight + 18
            radius: Theme.radiusSmall
            color: Theme.alpha(Theme.warning, 0.12)
            border.color: Theme.alpha(Theme.warning, 0.5)
            RowLayout {
                id: warnRow
                anchors.fill: parent
                anchors.margins: 9
                spacing: 10
                Icon { name: backend.showMode ? "lock" : "warning"; size: 18; color: Theme.warning }
                Text {
                    Layout.fillWidth: true
                    text: backend.showMode
                          ? "Show-Modus aktiv – bitte das Update erst nach der Vorstellung installieren (Show-Modus beenden)."
                          : "Laufende Wiedergaben werden beim Update beendet."
                    color: Theme.warning
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSmall
                    font.weight: Font.DemiBold
                    wrapMode: Text.Wrap
                }
            }
        }
        Text {
            Layout.fillWidth: true
            visible: updater.state === "error"
            text: updater.message
            color: Theme.danger
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontBody
            wrapMode: Text.Wrap
        }

        // ------------------------------------------------ Fortschritt
        ColumnLayout {
            Layout.fillWidth: true
            visible: dlg.busy
            spacing: 6
            RowLayout {
                Layout.fillWidth: true
                spacing: 10
                Spinner { size: 20; running: dlg.busy && dlg.visible }
                Text {
                    Layout.fillWidth: true
                    text: updater.message
                    color: Theme.text
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBody
                    font.weight: Font.DemiBold
                    wrapMode: Text.Wrap
                }
            }
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: 10
                radius: 5
                color: Theme.railBg
                Rectangle {
                    width: parent.width * Math.max(0, Math.min(1, updater.state === "installing" ? 1 : updater.progress))
                    height: parent.height
                    radius: 5
                    color: Theme.accent
                    Behavior on width { NumberAnimation { duration: 120 } }
                }
            }
            Text {
                text: updater.progressText
                color: Theme.textMute
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSmall
                font.features: { "tnum": 1 }
            }
        }
    }

    buttons: [
        AppButton {
            visible: !dlg.busy
            text: "Überspringen"
            variant: "ghost"
            toolTipText: "Diese Version nicht mehr anbieten"
            onClicked: { updater.skipVersion(); dlg.close() }
        },
        AppButton {
            visible: !dlg.busy
            text: "Später"
            onClicked: dlg.close()
        },
        Item { Layout.fillWidth: true },
        AppButton {
            visible: updater.state === "downloading"
            text: "Abbrechen"
            iconName: "close"
            onClicked: updater.cancelDownload()
        },
        AppButton {
            visible: !dlg.busy && !updater.canInstall
            text: "Download-Seite öffnen"
            iconName: "external"
            variant: "accent"
            onClicked: updater.openReleasePage()
        },
        AppButton {
            objectName: "installUpdateButton"
            visible: !dlg.busy && updater.canInstall
            enabled: (updater.state === "available" || updater.state === "error") && !backend.showMode
            text: "Jetzt aktualisieren"
            iconName: "download"
            variant: "accent"
            Layout.preferredWidth: 220
            onClicked: updater.startUpdate()
        }
    ]
}
