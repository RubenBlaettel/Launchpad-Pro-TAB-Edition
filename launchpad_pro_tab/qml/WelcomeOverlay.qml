import QtQuick
import QtQuick.Layouts

// Startbildschirm, solange kein Projekt geöffnet ist.
Item {
    id: welcome
    signal newRequested()
    signal openRequested()

    ColumnLayout {
        anchors.centerIn: parent
        spacing: 18
        width: Math.min(parent.width - 60, 560)

        Logo { size: 92; Layout.alignment: Qt.AlignHCenter }
        Text {
            Layout.alignment: Qt.AlignHCenter
            text: "Willkommen bei Launchpad Pro"
            color: Theme.text
            font.family: Theme.fontFamily
            font.pixelSize: 30
            font.weight: Font.Bold
        }
        Text {
            Layout.fillWidth: true
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.Wrap
            text: "Lege ein neues Projekt an oder öffne ein bestehendes. In einem Projekt werden alle Kacheln, Audiodateien, Coverbilder und Bearbeitungen gespeichert."
            color: Theme.textDim
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontLarge
            lineHeight: 1.3
        }
        RowLayout {
            Layout.alignment: Qt.AlignHCenter
            Layout.topMargin: 8
            spacing: 14
            AppButton {
                text: "Neues Projekt"
                iconName: "new"
                variant: "accent"
                implicitHeight: 58
                Layout.preferredWidth: 230
                font.pixelSize: Theme.fontLarge
                onClicked: welcome.newRequested()
            }
            AppButton {
                text: "Projekt öffnen"
                iconName: "folder"
                implicitHeight: 58
                Layout.preferredWidth: 230
                font.pixelSize: Theme.fontLarge
                onClicked: welcome.openRequested()
            }
        }
    }
}
