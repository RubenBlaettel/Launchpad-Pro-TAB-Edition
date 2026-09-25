import QtQuick
import QtQuick.Layouts
import QtQuick.Dialogs

// Pop-up "Neues Projekt": Projektname, Ablageort, Kachelanzahl.
// Unten links "Abbrechen", unten rechts "Projekt erstellen".
AppDialog {
    id: dlg
    title: "Neues Projekt"
    iconName: "new"
    dialogWidth: 620

    function openFresh() {
        nameField.text = backend.suggestProjectName()
        locationField.text = backend.defaultProjectsDir
        sizeBox.currentIndex = 1   // 4 × 4
        open()
        nameField.forceActiveFocus()
        nameField.selectAll()
    }

    function create() {
        if (nameField.text.trim() === "") {
            nameField.forceActiveFocus()
            return
        }
        if (backend.newProject(nameField.text, locationField.text, backend.gridOptions[sizeBox.currentIndex]))
            dlg.close()
    }

    ColumnLayout {
        width: parent.width
        spacing: 8

        FieldLabel { text: "Projektname" }
        AppTextField {
            id: nameField
            Layout.fillWidth: true
            placeholderText: "z. B. Sommerstück 2026"
            onAccepted: dlg.create()
        }

        FieldLabel { text: "Ablageort"; Layout.topMargin: 10 }
        RowLayout {
            Layout.fillWidth: true
            spacing: 8
            AppTextField {
                id: locationField
                Layout.fillWidth: true
                font.pixelSize: Theme.fontBody
            }
            AppButton {
                text: "Durchsuchen …"
                iconName: "folder"
                onClicked: folderDialog.open()
            }
        }
        Text {
            Layout.fillWidth: true
            text: "Projektordner: " + locationField.text + "/" + (nameField.text.trim() || "…")
            color: Theme.textMute
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontTiny
            elide: Text.ElideMiddle
        }

        FieldLabel { text: "Kachelanzahl"; Layout.topMargin: 10 }
        RowLayout {
            Layout.fillWidth: true
            spacing: 16
            AppComboBox {
                id: sizeBox
                Layout.preferredWidth: 220
                model: backend.gridOptions.map(n => n + " × " + n + "  (" + (n * n) + " Kacheln)")
                currentIndex: 1
            }
            // Vorschau des Rasters
            Grid {
                readonly property int n: backend.gridOptions[sizeBox.currentIndex] || 4
                columns: n
                spacing: 3
                Repeater {
                    model: parent.n * parent.n
                    Rectangle {
                        width: 70 / 7 + 2; height: width; radius: 2
                        color: Theme.alpha(Theme.magenta, 0.75)
                    }
                }
            }
            Item { Layout.fillWidth: true }
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
            text: "Projekt erstellen"
            iconName: "check"
            variant: "accent"
            Layout.preferredWidth: 220
            enabled: nameField.text.trim() !== "" && locationField.text.trim() !== ""
            onClicked: dlg.create()
        }
    ]

    FolderDialog {
        id: folderDialog
        title: "Ablageort für das neue Projekt"
        onAccepted: locationField.text = backend.localPath(selectedFolder)
    }
}
