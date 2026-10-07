import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import QtQuick.Dialogs
import QtQuick.Templates as T
import QtCore

// Optionen › Projekt: aktuelles Projekt (mit Auswahl der zuletzt geöffneten Projekte), Öffnen,
// Neu, Speichern, Speichern unter, Export.
Card {
    id: card
    signal openRequested()
    signal newRequested()
    signal deleteRequested(string path, string name, bool exists, bool open)   // Papierkorb in der Auswahl
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
            // Aktuelles Projekt – zugleich Projektauswahl (Dropdown der zuletzt geöffneten Projekte)
            T.AbstractButton {
                id: field
                objectName: "projectField"
                Layout.fillWidth: true
                Layout.preferredHeight: Theme.touch
                hoverEnabled: true
                focusPolicy: Qt.NoFocus
                leftPadding: 12
                rightPadding: 12
                onClicked: picker.open()
                background: Rectangle {
                    radius: Theme.radiusSmall
                    color: field.pressed ? Theme.cardPressed : (field.hovered ? Theme.cardHover : Theme.field)
                    border.color: picker.visible ? Theme.accent : Theme.border
                }
                contentItem: RowLayout {
                    spacing: 10
                    Rectangle {
                        implicitWidth: 10; implicitHeight: 10; radius: 5
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
                    Icon {
                        name: "chevron-down"
                        size: 16
                        color: Theme.textDim
                        rotation: picker.visible ? 180 : 0
                        Behavior on rotation { NumberAnimation { duration: 120 } }
                    }
                }
                ToolTipLite { text: "Zuletzt geöffnete Projekte"; shown: field.hovered && !field.pressed && !picker.visible }
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

    // Projektauswahl: zuletzt geöffnete Projekte; offene springen zu ihrer Registerkarte,
    // alle anderen öffnen sich in einer neuen Karte.
    Popup {
        id: picker
        objectName: "projectPicker"
        parent: field
        y: field.height + 6
        width: field.width
        height: Math.min(implicitHeight, 440)
        padding: 6
        modal: true            // Klick daneben schließt nur – nichts dahinter wird ausgelöst
        dim: false
        focus: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        onVisibleChanged: UiState.modalCount = Math.max(0, UiState.modalCount + (visible ? 1 : -1))

        background: Rectangle {
            radius: Theme.radiusSmall
            color: Theme.panel
            border.color: Theme.borderStrong
        }
        contentItem: ColumnLayout {
            spacing: 4
            FieldLabel {
                Layout.leftMargin: 8
                Layout.topMargin: 4
                text: "Zuletzt geöffnete Projekte"
            }
            ListView {
                id: recentView
                Layout.fillWidth: true
                Layout.preferredHeight: Math.min(contentHeight, 320)
                clip: true
                spacing: 2
                model: backend.recentProjects
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar { policy: recentView.contentHeight > recentView.height ? ScrollBar.AsNeeded : ScrollBar.AlwaysOff }
                delegate: ProjectRow {
                    width: ListView.view.width
                    onClicked: { picker.close(); backend.openProject(path) }
                    onDeleteRequested: { picker.close(); card.deleteRequested(path, name, exists, open) }
                }
            }
            Text {
                Layout.fillWidth: true
                Layout.margins: 10
                visible: recentView.count === 0
                horizontalAlignment: Text.AlignHCenter
                text: "Noch keine Projekte geöffnet."
                color: Theme.textMute
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSmall
            }
            AppButton {
                Layout.fillWidth: true
                implicitHeight: 42
                visible: !backend.showMode
                text: "Weitere Projekte öffnen …"
                iconName: "folder"
                variant: "ghost"
                onClicked: { picker.close(); card.openRequested() }
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
