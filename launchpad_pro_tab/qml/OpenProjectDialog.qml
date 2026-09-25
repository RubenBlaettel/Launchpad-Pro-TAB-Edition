import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import QtQuick.Dialogs

// Pop-up "Projekt öffnen": zuletzt geöffnete Projekte + Durchsuchen (Ordner/Datei/ZIP-Export).
AppDialog {
    id: dlg
    title: "Projekt öffnen"
    iconName: "folder"
    dialogWidth: 680

    ColumnLayout {
        width: parent.width
        spacing: 10

        FieldLabel { text: "Zuletzt geöffnet" }

        ListView {
            id: list
            Layout.fillWidth: true
            Layout.preferredHeight: Math.min(Math.max(contentHeight, 80), 360)
            clip: true
            spacing: 6
            model: backend.recentProjects
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar {}

            delegate: Rectangle {
                id: row
                required property string path
                required property string name
                required property string openedText
                required property bool exists
                required property bool current
                width: ListView.view.width
                height: 64
                radius: Theme.radiusSmall
                color: rowTap.pressed ? Theme.cardPressed : (rowHover.hovered ? Theme.cardHover : Theme.card)
                border.color: row.current ? Theme.alpha(Theme.accent, 0.7) : Theme.border
                opacity: row.exists ? 1 : 0.5

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 14
                    anchors.rightMargin: 8
                    spacing: 12
                    Icon { name: row.exists ? "masks" : "warning"; size: 24; color: row.exists ? Theme.magenta : Theme.warning }
                    Column {
                        Layout.fillWidth: true
                        spacing: 2
                        Text {
                            width: parent.width
                            text: row.name + (row.current ? "  (geöffnet)" : "") + (row.exists ? "" : "  – nicht gefunden")
                            color: Theme.text
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontLarge
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
                    Text {
                        text: row.openedText
                        color: Theme.textMute
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSmall
                    }
                    AppButton {
                        width: 40; implicitHeight: 40
                        iconName: "close"
                        iconSize: 14
                        variant: "flat"
                        tint: Theme.textMute
                        toolTipText: "Aus der Liste entfernen"
                        onClicked: backend.forgetProject(row.path)
                    }
                }
                HoverHandler { id: rowHover }
                TapHandler {
                    id: rowTap
                    enabled: row.exists
                    onTapped: { if (backend.openProject(row.path)) dlg.close() }
                }
            }

            Text {
                anchors.centerIn: parent
                visible: list.count === 0
                text: "Noch keine Projekte geöffnet."
                color: Theme.textMute
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontBody
            }
        }

        Text {
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            text: "Tipp: Über „Durchsuchen“ lassen sich Projektordner (Datei „projekt.lptab“) und exportierte Projekte (.zip) öffnen. ZIP-Exporte werden automatisch in den Projekte-Ordner entpackt."
            color: Theme.textMute
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontSmall
            lineHeight: 1.2
        }
    }

    buttons: [
        AppButton {
            text: "Abbrechen"
            Layout.preferredWidth: 150
            onClicked: dlg.close()
        },
        Item { Layout.fillWidth: true },
        AppButton {
            text: "Durchsuchen …"
            iconName: "folder"
            variant: "accent"
            Layout.preferredWidth: 200
            onClicked: fileDialog.open()
        }
    ]

    FileDialog {
        id: fileDialog
        title: "Projekt öffnen"
        fileMode: FileDialog.OpenFile
        nameFilters: ["Launchpad-Projekt (projekt.lptab *.lptab)", "Projekt-Export (*.zip)", "Alle Dateien (*)"]
        onAccepted: { if (backend.openProject(selectedFile)) dlg.close() }
    }
}
