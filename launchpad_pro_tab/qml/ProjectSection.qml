import QtQuick
import QtQuick.Layouts
import QtQuick.Dialogs
import QtCore

// Optionen › Projekt: aktuelles Projekt, Öffnen, Neu, Speichern, Speichern unter, Export.
Card {
    id: card
    signal openRequested()
    signal newRequested()
    implicitHeight: col.implicitHeight + 2 * padding

    ColumnLayout {
        id: col
        anchors.left: parent.left
        anchors.right: parent.right
        spacing: 12

        SectionHeader {
            text: "Projekt"
            iconName: "masks"
            Text {
                visible: backend.hasProject
                text: backend.saveStateText
                color: backend.dirty ? Theme.warning : Theme.textMute
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSmall
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 8
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: Theme.touch
                radius: Theme.radiusSmall
                color: Theme.field
                border.color: Theme.border
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 12
                    anchors.rightMargin: 12
                    spacing: 10
                    Rectangle {
                        width: 10; height: 10; radius: 5
                        color: !backend.hasProject ? Theme.textMute : (backend.dirty ? Theme.warning : Theme.accent)
                    }
                    Column {
                        Layout.fillWidth: true
                        spacing: 1
                        Text {
                            width: parent.width
                            text: backend.hasProject ? backend.projectName : "Kein Projekt geöffnet"
                            color: backend.hasProject ? Theme.text : Theme.textMute
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontLarge
                            font.weight: Font.DemiBold
                            elide: Text.ElideRight
                        }
                        Text {
                            width: parent.width
                            visible: backend.hasProject
                            text: backend.projectPath
                            color: Theme.textMute
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontTiny
                            elide: Text.ElideMiddle
                        }
                    }
                }
            }
            AppButton {
                text: "Öffnen"
                iconName: "folder"
                enabled: !backend.showMode
                onClicked: card.openRequested()
            }
            AppButton {
                text: "Neu"
                iconName: "new"
                variant: "accent"
                enabled: !backend.showMode
                onClicked: card.newRequested()
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 8
            enabled: backend.hasProject
            AppButton {
                Layout.fillWidth: true
                implicitHeight: 42
                text: "Speichern"
                iconName: "save"
                variant: "ghost"
                toolTipText: "Projekt jetzt speichern  [Strg+S]"
                onClicked: backend.saveProject()
            }
            AppButton {
                Layout.fillWidth: true
                implicitHeight: 42
                text: "Speichern unter …"
                iconName: "save-as"
                variant: "ghost"
                enabled: !backend.showMode
                toolTipText: "Projekt an einen anderen Ort kopieren  [Strg+Umschalt+S]"
                onClicked: saveAsDialog.open()
            }
            AppButton {
                Layout.fillWidth: true
                implicitHeight: 42
                text: "Exportieren"
                iconName: "export"
                variant: "ghost"
                enabled: !backend.showMode
                toolTipText: "Projekt als ZIP-Datei exportieren  [Strg+E]"
                onClicked: card.exportZip()
            }
        }
    }

    function saveAs() { saveAsDialog.open() }
    function exportZip() {
        const folder = StandardPaths.writableLocation(StandardPaths.DocumentsLocation)
        exportDialog.currentFolder = folder
        exportDialog.selectedFile = folder + "/" + backend.suggestedExportName()
        exportDialog.open()
    }

    FolderDialog {
        id: saveAsDialog
        title: "Speichern unter – Zielordner wählen"
        onAccepted: backend.saveProjectAs(selectedFolder)
    }
    FileDialog {
        id: exportDialog
        title: "Projekt exportieren"
        fileMode: FileDialog.SaveFile
        defaultSuffix: "zip"
        nameFilters: ["ZIP-Archiv (*.zip)"]
        onAccepted: backend.exportProject(selectedFile)
    }
}
