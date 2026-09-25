import QtQuick
import QtQuick.Layouts

// Überschrift eines Bereichs, z. B. "PROJEKT" – optional mit Inhalten rechts.
RowLayout {
    id: header
    property string text: ""
    property string iconName: ""
    property color iconColor: Theme.accent
    default property alias trailing: trailingRow.data
    spacing: 10
    Layout.fillWidth: true

    Icon {
        visible: header.iconName !== ""
        name: header.iconName
        size: 18
        color: header.iconColor
    }
    Text {
        text: header.text.toUpperCase()
        color: Theme.textDim
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fontSmall
        font.weight: Font.Bold
        font.letterSpacing: 1.4
        Layout.fillWidth: true
        elide: Text.ElideRight
    }
    Row {
        id: trailingRow
        spacing: 8
        Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
    }
}
