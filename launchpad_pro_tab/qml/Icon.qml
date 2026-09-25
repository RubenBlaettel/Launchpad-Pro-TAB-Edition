import QtQuick
import QtQuick.Controls.impl

// Einfärbbares SVG-Icon aus qml/icons/<name>.svg
Item {
    id: root
    property string name: ""
    property int size: 20
    property color color: Theme.text
    implicitWidth: size
    implicitHeight: size
    width: size
    height: size

    IconImage {
        anchors.fill: parent
        source: root.name !== "" ? Theme.icon(root.name) : ""
        sourceSize: Qt.size(root.size, root.size)
        color: root.color
        fillMode: Image.PreserveAspectFit
    }
}
