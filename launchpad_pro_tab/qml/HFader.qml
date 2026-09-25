import QtQuick

// Horizontaler Fader mit rotem Knopf (Master, angelehnt an Bild 3).
// ``value`` 0..1 (Systemlautstärke), Skala 0–100 %.
Item {
    id: fader
    property real value: 0.5
    property color capTop: "#FF6A5C"
    property color capBottom: "#B3141C"
    signal moved(real value)

    implicitHeight: 64
    opacity: enabled ? 1 : 0.45

    // Skala oberhalb der Bahn
    Item {
        id: scaleRow
        anchors.left: track.left
        anchors.right: track.right
        anchors.leftMargin: track.capW / 2 + 6
        anchors.rightMargin: track.capW / 2 + 6
        anchors.top: parent.top
        height: 18
        Repeater {
            model: 11
            Item {
                required property int index
                x: scaleRow.width * index / 10
                width: 1
                height: scaleRow.height
                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.top: parent.top
                    visible: index % 2 === 0
                    text: index * 10
                    color: Theme.textMute
                    font.family: Theme.fontFamily
                    font.pixelSize: 10
                    font.features: { "tnum": 1 }
                }
                Rectangle {
                    anchors.bottom: parent.bottom
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: 1
                    height: index % 5 === 0 ? 6 : 3
                    color: Theme.textMute
                }
            }
        }
    }

    Rectangle {
        id: track
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: scaleRow.bottom
        anchors.topMargin: 3
        anchors.bottom: parent.bottom
        radius: 6
        color: Theme.faderTrack
        border.color: "#23252B"

        readonly property real capW: 30
        readonly property real travel: width - capW - 12
        readonly property real capX: 6 + fader.value * travel

        // Schlitz + Füllung in Rot bis zum Knopf
        Rectangle {
            anchors.verticalCenter: parent.verticalCenter
            x: 6 + track.capW / 2
            width: track.width - 12 - track.capW
            height: 4
            radius: 2
            color: "#26282E"
        }
        Rectangle {
            anchors.verticalCenter: parent.verticalCenter
            x: 6 + track.capW / 2
            width: Math.max(0, track.capX - 6)
            height: 4
            radius: 2
            color: Theme.alpha(Theme.master, 0.75)
        }
        // Knopf
        Rectangle {
            id: cap
            x: track.capX
            anchors.verticalCenter: parent.verticalCenter
            width: track.capW
            height: track.height - 8
            radius: 5
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.0; color: fader.capTop }
                GradientStop { position: 0.48; color: Qt.darker(fader.capTop, 1.08) }
                GradientStop { position: 0.52; color: Qt.darker(fader.capBottom, 1.05) }
                GradientStop { position: 1.0; color: fader.capBottom }
            }
            border.color: drag.active ? "#FFFFFF" : "#5A0B10"
            border.width: drag.active ? 2 : 1
            Rectangle { anchors.centerIn: parent; width: 2; height: parent.height - 10; color: "#FFFFFF"; opacity: 0.85 }
            Behavior on x { enabled: !drag.active; NumberAnimation { duration: 90 } }
        }

        property real startValue: 0
        DragHandler {
            id: drag
            target: null
            yAxis.enabled: false
            enabled: fader.enabled
            onActiveChanged: if (active) track.startValue = fader.value
            onTranslationChanged: fader.moved(Math.max(0, Math.min(1, track.startValue + translation.x / track.travel)))
        }
        TapHandler {
            enabled: fader.enabled
            // Antippen neben den Knopf bewegt schrittweise (kein Sprung auf volle Lautstärke)
            onTapped: (pt) => {
                const x = pt.position.x
                if (x < track.capX) fader.moved(Math.max(0, fader.value - 0.05))
                else if (x > track.capX + track.capW) fader.moved(Math.min(1, fader.value + 0.05))
            }
        }
        WheelHandler {
            enabled: fader.enabled
            onWheel: (ev) => fader.moved(Math.max(0, Math.min(1, fader.value + (ev.angleDelta.y > 0 ? 0.02 : -0.02))))
        }
    }
}
