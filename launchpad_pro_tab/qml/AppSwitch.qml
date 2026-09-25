import QtQuick
import QtQuick.Templates as T

// Großer Umschalter (touch-freundlich) mit Beschriftung.
T.AbstractButton {
    id: control
    checkable: true
    property string subText: ""
    implicitHeight: Theme.touch
    implicitWidth: 260
    focusPolicy: Qt.NoFocus
    opacity: enabled ? 1 : 0.4

    background: Rectangle {
        radius: Theme.radiusSmall
        color: control.pressed ? Theme.cardPressed : Theme.card
        border.color: control.checked ? Theme.alpha(Theme.accent, 0.6) : Theme.border
    }
    contentItem: Item {
        Column {
            anchors.left: parent.left
            anchors.leftMargin: 14
            anchors.verticalCenter: parent.verticalCenter
            anchors.right: knobTrack.left
            anchors.rightMargin: 10
            spacing: 1
            Text {
                width: parent.width
                text: control.text
                color: Theme.text
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontBody
                font.weight: Font.DemiBold
                elide: Text.ElideRight
            }
            Text {
                width: parent.width
                visible: control.subText !== ""
                text: control.subText
                color: Theme.textMute
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontTiny
                elide: Text.ElideRight
            }
        }
        Rectangle {
            id: knobTrack
            anchors.right: parent.right
            anchors.rightMargin: 12
            anchors.verticalCenter: parent.verticalCenter
            width: 50; height: 28; radius: 14
            color: control.checked ? Theme.accent : Theme.switchOff
            Behavior on color { ColorAnimation { duration: 120 } }
            Rectangle {
                width: 22; height: 22; radius: 11
                y: 3
                x: control.checked ? parent.width - width - 3 : 3
                color: "#FFFFFF"
                Behavior on x { NumberAnimation { duration: 120; easing.type: Easing.OutCubic } }
            }
        }
    }
}
