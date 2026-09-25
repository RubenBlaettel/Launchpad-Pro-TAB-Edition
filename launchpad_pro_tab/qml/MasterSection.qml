import QtQuick
import QtQuick.Layouts

// Optionen › Master-Lautstärke: roter, horizontaler Master-Fader für die
// System-Master-Lautstärke (Windows) plus Stereo-Pegelanzeige der App.
Card {
    id: card
    implicitHeight: col.implicitHeight + 2 * padding

    ColumnLayout {
        id: col
        anchors.left: parent.left
        anchors.right: parent.right
        spacing: 10

        SectionHeader {
            text: "Master-Lautstärke"
            iconName: "volume"
            iconColor: Theme.master
            Text {
                text: master.backendName
                color: Theme.textMute
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontTiny
                elide: Text.ElideRight
                width: Math.min(implicitWidth, card.width * 0.42)
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            AppButton {
                Layout.preferredWidth: Theme.touch
                iconName: master.muted ? "volume-mute" : "volume"
                variant: "solid"
                active: master.muted
                activeColor: Theme.danger
                toolTipText: master.muted ? "Stummschaltung aufheben" : "Systemton stummschalten"
                onClicked: master.toggleMute()
            }
            HFader {
                id: fader
                Layout.fillWidth: true
                Layout.preferredHeight: 64
                value: master.volume
                opacity: master.muted ? 0.55 : 1
                onMoved: (v) => master.setVolume(v)
            }
            Column {
                Layout.preferredWidth: 62
                spacing: 0
                Text {
                    anchors.right: parent.right
                    text: Math.round(master.volume * 100) + " %"
                    color: master.muted ? Theme.textMute : "#FFFFFF"
                    font.family: Theme.fontFamily
                    font.pixelSize: 18
                    font.weight: Font.Bold
                    font.features: { "tnum": 1 }
                }
                Text {
                    anchors.right: parent.right
                    text: master.muted ? "STUMM" : "SYSTEM"
                    color: master.muted ? Theme.danger : Theme.textMute
                    font.family: Theme.fontFamily
                    font.pixelSize: 9
                    font.weight: Font.Bold
                    font.letterSpacing: 1.2
                }
            }
        }

        LevelMeter {
            Layout.fillWidth: true
            levelL: backend.levelL
            levelR: backend.levelR
            limiting: backend.limiting
        }
    }
}
