import QtQuick

// Schwebende "Karte", die beim Ziehen aus der Liste unter dem Finger/der Maus hängt.
// Tiles erkennen sie über ihre DropArea (keys: text/uri-list) und lesen ``filePath``.
Rectangle {
    id: proxy
    property string filePath: ""
    property string label: ""
    property bool dragging: false

    width: Math.min(300, labelText.implicitWidth + 56)
    height: 46
    radius: 10
    color: Theme.popup
    border.color: Theme.accent
    border.width: 2
    visible: dragging
    z: 10000

    Drag.active: dragging
    Drag.keys: ["text/uri-list"]
    Drag.dragType: Drag.Internal
    Drag.supportedActions: Qt.CopyAction
    Drag.hotSpot.x: 20
    Drag.hotSpot.y: height / 2

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

    function begin(path, name, scenePos) {
        filePath = path
        label = name
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
