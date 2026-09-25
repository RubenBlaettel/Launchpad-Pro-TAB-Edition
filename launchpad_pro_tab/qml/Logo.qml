import QtQuick

// Mini-Launchpad als Logo (3×3 leuchtende Pads).
Item {
    id: logo
    property int size: 36
    width: size
    height: size
    readonly property var colors: ["#D64DFF", "#FF4FA3", "#7A5CFF",
                                   "#1FD6FF", "#14D9A0", "#D64DFF",
                                   "#FFC61A", "#D64DFF", "#FF5252"]
    Rectangle {
        anchors.fill: parent
        radius: logo.size * 0.22
        color: Theme.logoBg
        border.color: Theme.logoBorder
    }
    Grid {
        anchors.centerIn: parent
        columns: 3
        spacing: logo.size * 0.06
        Repeater {
            model: 9
            Rectangle {
                required property int index
                width: logo.size * 0.22
                height: width
                radius: width * 0.25
                gradient: Gradient {
                    GradientStop { position: 0; color: Qt.lighter(logo.colors[index], 1.25) }
                    GradientStop { position: 1; color: Qt.darker(logo.colors[index], 1.2) }
                }
            }
        }
    }
}
