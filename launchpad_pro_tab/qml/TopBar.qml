import QtQuick
import QtQuick.Layouts

// Kopfleiste: Marke, Status, Raster-Auswahl, Show-Modus, ALLES STOPPEN, Einstellungen.
Rectangle {
    id: bar
    signal gridSizeRequested(int n)
    signal settingsRequested()
    implicitHeight: 68
    color: Theme.bgRaised

    Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.border }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 18
        anchors.rightMargin: 16
        spacing: 12

        Logo { size: 38 }
        Column {
            spacing: 0
            Text {
                text: "Launchpad Pro"
                color: Theme.text
                font.family: Theme.fontFamily
                font.pixelSize: 19
                font.weight: Font.Bold
            }
            Text {
                text: "TAB EDITION"
                color: Theme.magenta
                font.family: Theme.fontFamily
                font.pixelSize: 11
                font.weight: Font.Bold
                font.letterSpacing: 2.6
            }
        }

        Item { Layout.fillWidth: true }

        // Audio-Status
        Rectangle {
            Layout.preferredHeight: 36
            Layout.preferredWidth: audioRow.implicitWidth + 24
            radius: 18
            color: Theme.card
            border.color: Theme.border
            Row {
                id: audioRow
                anchors.centerIn: parent
                spacing: 8
                Rectangle {
                    anchors.verticalCenter: parent.verticalCenter
                    width: 9; height: 9; radius: 5
                    color: backend.audioOk ? Theme.accent : Theme.danger
                }
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: backend.audioInfo
                    color: Theme.textDim
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSmall
                }
            }
        }

        // Anzahl laufender Kacheln
        Rectangle {
            Layout.preferredHeight: 36
            Layout.preferredWidth: activeRow.implicitWidth + 24
            radius: 18
            color: backend.activeCount > 0 ? Theme.alpha(Theme.accent, 0.14) : Theme.card
            border.color: backend.activeCount > 0 ? Theme.alpha(Theme.accent, 0.55) : Theme.border
            Row {
                id: activeRow
                anchors.centerIn: parent
                spacing: 8
                Icon { anchors.verticalCenter: parent.verticalCenter; name: "play"; size: 14; color: backend.activeCount > 0 ? Theme.accent : Theme.textMute }
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: backend.activeCount === 1 ? "1 läuft" : backend.activeCount + " laufen"
                    color: backend.activeCount > 0 ? Theme.accent : Theme.textDim
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSmall
                    font.weight: Font.DemiBold
                }
            }
        }

        // Raster-Auswahl (Dropdown 3×3 … 7×7)
        AppComboBox {
            id: gridBox
            Layout.preferredWidth: 150
            enabled: backend.hasProject && !backend.showMode
            prefix: "Raster  "
            model: backend.gridOptions.map(n => n + " × " + n)
            currentIndex: Math.max(0, backend.gridSize - 3)
            onActivated: (i) => {
                const n = backend.gridOptions[i]
                currentIndex = Qt.binding(() => Math.max(0, backend.gridSize - 3))
                bar.gridSizeRequested(n)
            }
        }

        // Show-Modus (Sperre gegen versehentliches Bearbeiten)
        AppButton {
            text: "Show-Modus"
            iconName: backend.showMode ? "lock" : "unlock"
            variant: "solid"
            active: backend.showMode
            activeColor: Theme.warning
            toolTipText: backend.showMode ? "Show-Modus aktiv: Kacheln lösen sofort aus, Bearbeiten gesperrt"
                                          : "In den Show-Modus wechseln (Bearbeiten sperren)"
            onClicked: backend.setShowMode(!backend.showMode)
        }

        // Panik-Taste
        AppButton {
            text: "ALLES STOPPEN"
            iconName: "stop"
            variant: "danger"
            Layout.preferredWidth: 184
            font.letterSpacing: 0.8
            onClicked: backend.stopAll()
            toolTipText: "Alle Kacheln sofort (kurz ausgeblendet) stoppen  [Esc]"
        }

        AppButton {
            iconName: "settings"
            variant: "ghost"
            Layout.preferredWidth: Theme.touch
            toolTipText: "Audio-Einstellungen"
            onClicked: bar.settingsRequested()
        }
    }
}
