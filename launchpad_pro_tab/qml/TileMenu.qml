import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import QtQuick.Dialogs

// Auswahlliste einer Kachel (Rechtsklick / lang drücken):
// Audio-Datei wählen, Coverbild, Titel, Farbe, Schleife, Bearbeiten, Löschen.
AppDialog {
    id: menu
    property int tileIndex: -1
    property var info: ({})
    readonly property bool empty: info.empty === undefined ? true : info.empty

    title: "Kachel " + (tileIndex + 1) + (info.title ? "  ·  " + info.title : "")
    iconName: "grid"
    iconColor: info.color || Theme.magenta
    dialogWidth: 860

    function openFor(index) {
        tileIndex = index
        refresh()
        filter.text = ""
        open()
    }
    function refresh() {
        if (tileIndex >= 0) info = backend.tileInfo(tileIndex)
        titleField.text = info.customTitle || ""
    }

    Connections {
        target: backend.tiles
        function onDataChanged(topLeft, bottomRight, roles) {
            if (menu.opened && topLeft.row <= menu.tileIndex && menu.tileIndex <= bottomRight.row) {
                const keepFocus = titleField.activeFocus
                const txt = titleField.text
                menu.refresh()
                if (keepFocus) titleField.text = txt
            }
        }
        function onModelReset() { if (menu.opened) menu.close() }
    }

    RowLayout {
        width: parent.width
        spacing: 22

        // ------------------------------------------------ Audio-Dateien
        ColumnLayout {
            Layout.preferredWidth: 400
            Layout.fillHeight: true
            spacing: 8
            FieldLabel { text: menu.empty ? "Audio-Datei wählen" : "Audio-Datei (aktuell: " + (menu.info.sourceName || "–") + ")" ; elide: Text.ElideRight; Layout.fillWidth: true }
            AppTextField {
                id: filter
                Layout.fillWidth: true
                implicitHeight: 42
                font.pixelSize: Theme.fontBody
                placeholderText: "Zuletzt verwendete durchsuchen …"
                visible: backend.recentAudio.count > 6
            }
            ListView {
                id: audioList
                Layout.fillWidth: true
                Layout.preferredHeight: 300
                clip: true
                spacing: 4
                model: backend.recentAudio
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar {}
                delegate: Rectangle {
                    id: arow
                    required property string path
                    required property string name
                    required property string ext
                    required property string durationText
                    required property bool exists
                    readonly property bool matches: filter.text === "" || name.toLowerCase().indexOf(filter.text.toLowerCase()) >= 0
                    readonly property bool isCurrent: menu.info.sourceName === name
                    width: ListView.view.width
                    height: matches ? 50 : 0
                    visible: matches
                    radius: Theme.radiusSmall
                    color: aTap.pressed ? Theme.cardPressed : (aHover.hovered ? Theme.cardHover : Theme.card)
                    border.color: arow.isCurrent ? Theme.accent : "transparent"
                    opacity: exists ? 1 : 0.45
                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 12
                        anchors.rightMargin: 12
                        spacing: 10
                        Icon { name: arow.isCurrent ? "check" : "music"; size: 18; color: arow.isCurrent ? Theme.accent : Theme.textDim }
                        Text {
                            Layout.fillWidth: true
                            text: arow.name
                            color: Theme.text
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontBody
                            elide: Text.ElideMiddle
                        }
                        Text { text: arow.ext; color: Theme.textMute; font.family: Theme.fontFamily; font.pixelSize: 10; font.weight: Font.Bold }
                        Text { text: arow.durationText; color: Theme.textDim; font.family: Theme.fontFamily; font.pixelSize: Theme.fontSmall; font.features: { "tnum": 1 } }
                    }
                    HoverHandler { id: aHover }
                    TapHandler {
                        id: aTap
                        enabled: arow.exists
                        onTapped: backend.assignAudio(menu.tileIndex, arow.path)
                    }
                }
                Text {
                    anchors.centerIn: parent
                    width: parent.width - 30
                    visible: audioList.count === 0
                    horizontalAlignment: Text.AlignHCenter
                    wrapMode: Text.Wrap
                    text: "Noch keine zuletzt verwendeten Dateien –\nüber „Datei durchsuchen …“ eine Audiodatei wählen."
                    color: Theme.textMute
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSmall
                }
            }
            AppButton {
                Layout.fillWidth: true
                text: "Datei durchsuchen …"
                iconName: "folder"
                variant: menu.empty ? "accent" : "solid"
                onClicked: audioDialog.open()
            }
        }

        // ------------------------------------------------ Eigenschaften
        ColumnLayout {
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignTop
            spacing: 8

            FieldLabel { text: "Coverbild (JPG, PNG, ICO)" }
            RowLayout {
                spacing: 12
                Rectangle {
                    width: 96; height: 96
                    radius: 12
                    color: Theme.field
                    border.color: menu.info.color || Theme.border
                    border.width: 2
                    clip: true
                    Image {
                        anchors.fill: parent
                        anchors.margins: 3
                        source: menu.info.cover || ""
                        fillMode: Image.PreserveAspectCrop
                        asynchronous: true
                        sourceSize: Qt.size(200, 200)
                        visible: source != ""
                    }
                    Icon { anchors.centerIn: parent; visible: !menu.info.cover; name: "image"; size: 30; color: Theme.textMute }
                }
                ColumnLayout {
                    spacing: 8
                    AppButton {
                        text: "Bild wählen …"
                        iconName: "image"
                        enabled: !menu.empty
                        Layout.fillWidth: true
                        onClicked: coverDialog.open()
                    }
                    AppButton {
                        text: "Entfernen"
                        iconName: "close"
                        variant: "ghost"
                        enabled: !!menu.info.cover
                        Layout.fillWidth: true
                        onClicked: backend.removeCover(menu.tileIndex)
                    }
                }
            }

            FieldLabel { text: "Titel"; Layout.topMargin: 6 }
            AppTextField {
                id: titleField
                Layout.fillWidth: true
                enabled: !menu.empty
                placeholderText: menu.info.sourceName ? menu.info.sourceName.replace(/\.[^.]+$/, "") : "Titel der Kachel"
                onEditingFinished: backend.setTileTitle(menu.tileIndex, text)
            }

            FieldLabel { text: "Farbe"; Layout.topMargin: 6 }
            Flow {
                Layout.fillWidth: true
                spacing: 8
                Repeater {
                    model: backend.tileColors
                    Rectangle {
                        required property string modelData
                        readonly property bool selected: String(menu.info.color || "").toUpperCase() === modelData.toUpperCase()
                        width: 40; height: 40; radius: 20
                        color: modelData
                        border.width: selected ? 3 : 1
                        border.color: selected ? "#FFFFFF" : Qt.darker(modelData, 1.5)
                        scale: sTap.pressed ? 0.9 : 1
                        Icon { anchors.centerIn: parent; visible: parent.selected; name: "check"; size: 18; color: "#10131A" }
                        TapHandler { id: sTap; onTapped: backend.setTileColor(menu.tileIndex, modelData) }
                    }
                }
            }

            AppSwitch {
                Layout.fillWidth: true
                Layout.topMargin: 8
                text: "Schleife (Loop)"
                subText: "Wiederholt die Audiospur, bis die Kachel erneut getippt wird"
                enabled: !menu.empty
                checked: !!menu.info.loop
                onToggled: backend.setTileLoop(menu.tileIndex, checked)
            }
        }
    }

    buttons: [
        AppButton {
            text: "Bearbeiten"
            iconName: "scissors"
            enabled: !menu.empty
            Layout.preferredWidth: 170
            onClicked: { backend.editTile(menu.tileIndex); menu.close() }
        },
        AppButton {
            text: "Löschen"
            iconName: "trash"
            variant: "danger"
            enabled: !menu.empty || !!menu.info.cover
            Layout.preferredWidth: 150
            onClicked: { backend.clearTile(menu.tileIndex); menu.close() }
        },
        Item { Layout.fillWidth: true },
        AppButton {
            text: "Fertig"
            iconName: "check"
            variant: "accent"
            Layout.preferredWidth: 150
            onClicked: menu.close()
        }
    ]

    onClosed: if (titleField.activeFocus || titleField.text !== (info.customTitle || "")) backend.setTileTitle(tileIndex, titleField.text)

    FileDialog {
        id: audioDialog
        title: "Audio-Datei für Kachel " + (menu.tileIndex + 1)
        fileMode: FileDialog.OpenFile
        nameFilters: [backend.audioFilterString(), "Alle Dateien (*)"]
        onAccepted: backend.assignAudio(menu.tileIndex, selectedFile)
    }
    FileDialog {
        id: coverDialog
        title: "Coverbild für Kachel " + (menu.tileIndex + 1)
        fileMode: FileDialog.OpenFile
        nameFilters: ["Bilder (*.jpg *.jpeg *.png *.ico)"]
        onAccepted: backend.assignCover(menu.tileIndex, selectedFile)
    }
}
