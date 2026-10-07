import QtQuick
import QtQuick.Layouts
import QtQuick.Templates as T

// Eine Zeile "zuletzt geöffnetes Projekt" (Projektauswahl, Startseite) – Delegate für
// backend.recentProjects. Ein Klick öffnet das Projekt in einer neuen Registerkarte bzw.
// wechselt zu seiner Karte, wenn es schon offen ist. Der Papierkorb rechts meldet
// ``deleteRequested`` (Rückfrage übernimmt Main.qml); nicht im Show-Modus.
Item {
    id: row
    required property string path
    required property string name
    required property string openedText
    required property bool exists
    required property bool current      // Projekt der aktiven Registerkarte
    required property bool open         // in irgendeiner Registerkarte geöffnet

    signal clicked()
    signal deleteRequested()

    readonly property bool deletable: !backend.showMode

    implicitWidth: 320
    implicitHeight: 54

    T.AbstractButton {
        id: button
        anchors.fill: parent
        hoverEnabled: true
        focusPolicy: Qt.NoFocus
        rightPadding: row.deletable ? trash.width + 8 : 0
        // im Show-Modus nur zwischen bereits offenen Karten wechseln (kein Öffnen)
        enabled: row.exists && (row.open || !backend.showMode)
        onClicked: row.clicked()

        background: Rectangle {
            radius: Theme.radiusSmall
            color: button.pressed ? Theme.cardPressed
                 : button.hovered || trash.hovered ? Theme.cardHover
                 : row.current ? Theme.alpha(Theme.accent, 0.08) : "transparent"
            border.color: row.current ? Theme.alpha(Theme.accent, 0.6) : "transparent"
        }

        contentItem: RowLayout {
            spacing: 12
            opacity: button.enabled ? 1 : 0.45
            Icon {
                Layout.leftMargin: 10
                name: row.exists ? "masks" : "warning"
                size: 20
                color: row.exists ? Theme.magenta : Theme.warning
            }
            Column {
                Layout.fillWidth: true
                spacing: 1
                Text {
                    width: parent.width
                    text: row.name + (row.exists ? "" : "  – nicht gefunden")
                    color: Theme.text
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontBody
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                }
                Text {
                    width: parent.width
                    text: row.path
                    color: Theme.textMute
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontTiny
                    elide: Text.ElideMiddle
                }
            }
            Rectangle {
                visible: row.current || row.open
                Layout.rightMargin: row.deletable ? 0 : 10
                implicitWidth: badge.implicitWidth + 16
                implicitHeight: 22
                radius: 11
                color: Theme.alpha(row.current ? Theme.accent : Theme.info, 0.14)
                Text {
                    id: badge
                    anchors.centerIn: parent
                    text: row.current ? "AKTIV" : "OFFEN"
                    color: row.current ? Theme.accent : Theme.info
                    font.family: Theme.fontFamily
                    font.pixelSize: 10
                    font.weight: Font.Bold
                    font.letterSpacing: 0.8
                }
            }
            Text {
                visible: !row.current && !row.open && row.openedText !== ""
                Layout.rightMargin: row.deletable ? 0 : 10
                text: row.openedText
                color: Theme.textMute
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSmall
                font.features: { "tnum": 1 }
            }
        }
    }

    AppButton {
        id: trash
        objectName: "deleteProjectButton"
        visible: row.deletable
        anchors.right: parent.right
        anchors.rightMargin: 6
        anchors.verticalCenter: parent.verticalCenter
        width: 42
        implicitHeight: 42
        iconName: "trash"
        iconSize: 17
        variant: "flat"
        tint: hovered ? Theme.danger : Theme.textMute
        toolTipText: row.exists ? "Projekt löschen (in den Papierkorb)" : "Aus der Liste entfernen"
        onClicked: row.deleteRequested()
    }
}
