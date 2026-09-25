import QtQuick

// Schlanker Tooltip (nur für Maus-Bedienung relevant, erscheint verzögert).
Item {
    id: tip
    property string text: ""
    property bool shown: false
    anchors.fill: parent
    z: 1000

    Rectangle {
        id: bubble
        visible: opacity > 0
        opacity: 0
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.top
        anchors.bottomMargin: 6
        width: label.implicitWidth + 16
        height: label.implicitHeight + 10
        radius: 6
        color: "#E6000000"
        border.color: Theme.border
        Text {
            id: label
            anchors.centerIn: parent
            text: tip.text
            color: Theme.text
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontSmall
        }
        states: State {
            name: "on"; when: tip.shown
            PropertyChanges { bubble.opacity: 1 }
        }
        transitions: [
            Transition { to: "on"; SequentialAnimation { PauseAnimation { duration: 600 } NumberAnimation { property: "opacity"; duration: 120 } } },
            Transition { from: "on"; NumberAnimation { property: "opacity"; duration: 80 } }
        ]
    }
}
