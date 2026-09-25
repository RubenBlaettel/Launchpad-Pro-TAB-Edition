import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import QtQuick.Dialogs

// Liste der zuletzt verwendeten Audiodateien (links oben).
// Einträge per Drag & Drop (waagrecht ziehen) auf eine Kachel legen.
Card {
    id: card
    property Item dragProxy

    ColumnLayout {
        anchors.fill: parent
        spacing: 12

        SectionHeader {
            text: "Zuletzt verwendet"
            iconName: "music"
            Rectangle {
                width: countText.implicitWidth + 16
                height: 24
                radius: 12
                color: Theme.card
                border.color: Theme.border
                Text {
                    id: countText
                    anchors.centerIn: parent
                    text: backend.recentAudio.count
                    color: Theme.textDim
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSmall
                    font.weight: Font.DemiBold
                }
            }
            AppButton {
                width: 40; height: 36
                implicitHeight: 36
                iconName: "plus"
                iconSize: 18
                variant: "solid"
                toolTipText: "Audiodateien zur Liste hinzufügen"
                onClicked: addDialog.open()
            }
        }

        // Suche
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 38
            radius: Theme.radiusSmall
            color: Theme.field
            border.color: search.activeFocus ? Theme.accent : Theme.border
            visible: backend.recentAudio.count > 8
            Icon { x: 12; anchors.verticalCenter: parent.verticalCenter; name: "search"; size: 16; color: Theme.textMute }
            TextField {
                id: search
                anchors.fill: parent
                leftPadding: 36
                rightPadding: 10
                placeholderText: "Suchen …"
                placeholderTextColor: Theme.textMute
                color: Theme.text
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontBody
                background: null
                verticalAlignment: TextInput.AlignVCenter
            }
        }

        ListView {
            id: list
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: 4
            model: backend.recentAudio
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar { policy: list.contentHeight > list.height ? ScrollBar.AsNeeded : ScrollBar.AlwaysOff }

            delegate: Item {
                id: row
                required property int index
                required property string path
                required property string fileUrl
                required property string name
                required property string ext
                required property string durationText
                required property bool exists
                readonly property bool matches: search.text === "" || name.toLowerCase().indexOf(search.text.toLowerCase()) >= 0
                width: ListView.view.width
                height: matches ? 52 : 0
                visible: matches

                Rectangle {
                    anchors.fill: parent
                    radius: Theme.radiusSmall
                    color: rowDrag.active ? Theme.alpha(Theme.accent, 0.15) : (rowHover.hovered ? Theme.cardHover : Theme.card)
                    border.color: rowDrag.active ? Theme.accent : "transparent"
                }
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 6
                    anchors.rightMargin: 4
                    spacing: 10
                    Icon { name: "grip"; size: 18; color: Theme.textMute; Layout.alignment: Qt.AlignVCenter }
                    Rectangle {
                        Layout.preferredWidth: 44
                        Layout.preferredHeight: 24
                        radius: 6
                        color: row.exists ? Theme.alpha(Theme.accent, 0.13) : Theme.alpha(Theme.warning, 0.15)
                        Text {
                            anchors.centerIn: parent
                            text: row.exists ? row.ext : "FEHLT"
                            color: row.exists ? Theme.accent : Theme.warning
                            font.family: Theme.fontFamily
                            font.pixelSize: 10
                            font.weight: Font.Bold
                        }
                    }
                    Text {
                        Layout.fillWidth: true
                        text: row.name
                        color: row.exists ? Theme.text : Theme.textMute
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBody
                        elide: Text.ElideMiddle
                    }
                    Text {
                        text: row.durationText
                        color: Theme.textDim
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSmall
                        font.features: { "tnum": 1 }
                    }
                    AppButton {
                        Layout.preferredWidth: 40
                        Layout.preferredHeight: 40
                        implicitHeight: 40
                        iconName: "close"
                        iconSize: 14
                        variant: "flat"
                        tint: Theme.textMute
                        toolTipText: "Aus der Liste entfernen"
                        onClicked: backend.removeRecent(row.path)
                    }
                }
                HoverHandler { id: rowHover }
                TapHandler {
                    onTapped: backend.notify(row.exists
                        ? "„" + row.name + "“ nach rechts auf eine Kachel ziehen – oder eine Kachel lange drücken und die Datei dort auswählen."
                        : "Die Datei „" + row.name + "“ wurde nicht gefunden (verschoben oder gelöscht).", row.exists ? "info" : "warning")
                }
                // Waagrecht ziehen startet Drag & Drop, senkrecht scrollt die Liste
                DragHandler {
                    id: rowDrag
                    target: null
                    enabled: row.exists && !backend.showMode
                    yAxis.enabled: false
                    onActiveChanged: {
                        if (active) card.dragProxy.begin(row.fileUrl, row.name, centroid.scenePosition)
                        else card.dragProxy.finish()
                    }
                    onCentroidChanged: if (active) card.dragProxy.moveTo(centroid.scenePosition)
                }
            }

            // Leerer Zustand
            Column {
                anchors.centerIn: parent
                width: parent.width - 40
                spacing: 10
                visible: list.count === 0
                Icon { anchors.horizontalCenter: parent.horizontalCenter; name: "drop"; size: 34; color: Theme.textMute }
                Text {
                    width: parent.width
                    horizontalAlignment: Text.AlignHCenter
                    wrapMode: Text.Wrap
                    text: "Noch keine Audiodateien.\nDateien aus dem Explorer direkt auf eine Kachel ziehen oder mit „+“ hinzufügen."
                    color: Theme.textMute
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSmall
                    lineHeight: 1.2
                }
            }
        }
    }

    // Dateien aus dem Explorer direkt auf die Liste ziehen
    DropArea {
        anchors.fill: parent
        keys: ["text/uri-list"]
        onEntered: (drag) => { if (!drag.hasUrls) drag.accepted = false }
        onDropped: (drop) => { if (drop.hasUrls) { backend.addRecentFiles(drop.urls); drop.accept(Qt.CopyAction) } }
    }

    FileDialog {
        id: addDialog
        title: "Audiodateien hinzufügen"
        fileMode: FileDialog.OpenFiles
        nameFilters: [backend.audioFilterString(), "Alle Dateien (*)"]
        onAccepted: backend.addRecentFiles(selectedFiles)
    }
}
