import QtQuick

// Schwebende "Karte", die beim Ziehen unter dem Finger/der Maus hängt. Zwei Arten:
//  • "file": Audiodatei aus der Liste (keys: text/uri-list) – Kacheln lesen ``filePath``
//  • "tile": Kachel wird verschoben (keys: application/x-lptab-tile) – Kacheln lesen ``tileIndex``
// Kacheln (und der Bereich „Bearbeiten & Schneiden“) erkennen die Karte über ihre DropArea.
Item {
    id: proxy
    property string kind: "file"
    property string filePath: ""
    property string label: ""
    property int tileIndex: -1
    property color tileColor: Theme.magenta
    property string coverUrl: ""
    property bool dragging: false
    readonly property bool isTile: kind === "tile"

    width: isTile ? 128 : Math.min(300, labelText.implicitWidth + 56)
    height: isTile ? 128 : 46
    visible: dragging
    z: 10000

    Drag.active: dragging
    Drag.keys: isTile ? ["application/x-lptab-tile"] : ["text/uri-list"]
    Drag.dragType: Drag.Internal
    Drag.supportedActions: Qt.CopyAction | Qt.MoveAction
    Drag.hotSpot.x: isTile ? width / 2 : 20
    // Kachel schwebt über dem Finger/Zeiger – so bleibt der Hinweis auf der Zielkachel sichtbar
    Drag.hotSpot.y: isTile ? height + 14 : height / 2

    // --- Audiodatei
    Rectangle {
        anchors.fill: parent
        visible: !proxy.isTile
        radius: 10
        color: Theme.popup
        border.color: Theme.accent
        border.width: 2
        Row {
            anchors.verticalCenter: parent.verticalCenter
            x: 14
            spacing: 10
            Icon { anchors.verticalCenter: parent.verticalCenter; name: "music"; size: 18; color: Theme.accent }
            Text {
                id: labelText
                anchors.verticalCenter: parent.verticalCenter
                text: proxy.label
                color: Theme.text
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontBody
                font.weight: Font.DemiBold
                elide: Text.ElideMiddle
                width: Math.min(implicitWidth, 240)
            }
        }
    }

    // --- Kachel (Miniatur in Kachelfarbe bzw. mit Coverbild)
    Rectangle {
        anchors.fill: parent
        visible: proxy.isTile
        radius: 14
        rotation: -3
        border.width: 2
        border.color: "#FFFFFF"
        gradient: Gradient {
            GradientStop { position: 0.0; color: Qt.lighter(proxy.tileColor, 1.1) }
            GradientStop { position: 1.0; color: Qt.darker(proxy.tileColor, 1.4) }
        }
        Image {
            anchors.fill: parent
            anchors.margins: 3
            visible: proxy.coverUrl !== ""
            source: proxy.isTile ? proxy.coverUrl : ""
            fillMode: Image.PreserveAspectCrop
            asynchronous: true
            sourceSize: Qt.size(256, 256)
        }
        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.margins: 2
            height: parent.height * 0.5
            radius: 12
            gradient: Gradient {
                GradientStop { position: 0.0; color: "transparent" }
                GradientStop { position: 1.0; color: "#B0000000" }
            }
        }
        Text {
            x: 10
            y: 8
            text: proxy.tileIndex + 1
            color: "#FFFFFF"
            font.family: Theme.fontFamily
            font.pixelSize: 13
            font.weight: Font.Bold
        }
        Text {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.margins: 10
            text: proxy.label
            color: "#FFFFFF"
            font.family: Theme.fontFamily
            font.pixelSize: 14
            font.weight: Font.Bold
            wrapMode: Text.Wrap
            maximumLineCount: 2
            elide: Text.ElideRight
        }
    }

    // Kartenwechsel während des Verschiebens (z. B. Strg+Tab): abbrechen, sonst würde die Kachel
    // im falschen Projekt abgelegt
    Connections {
        target: backend
        function onTabsChanged() { if (proxy.dragging && proxy.isTile) proxy.dragging = false }
    }

    function begin(path, name, scenePos) {
        kind = "file"
        tileIndex = -1
        coverUrl = ""
        filePath = path
        label = name
        moveTo(scenePos)
        dragging = true
    }
    function beginTile(index, title, color, cover, scenePos) {
        kind = "tile"
        filePath = ""
        tileIndex = index
        label = title
        tileColor = color
        coverUrl = cover
        moveTo(scenePos)
        dragging = true
    }
    function moveTo(scenePos) {
        const p = parent.mapFromItem(null, scenePos.x, scenePos.y)
        x = p.x - Drag.hotSpot.x
        y = p.y - Drag.hotSpot.y
    }
    function finish() {
        if (dragging)
            Drag.drop()
        dragging = false
    }
}
