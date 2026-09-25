import QtQuick
import QtQuick.Templates as T
import QtQuick.Controls.impl

// Media-Taste mit typischem Symbol und kleiner Beschriftung darunter (touch-freundlich).
T.AbstractButton {
    id: control
    property string iconName: ""
    property bool highlighted: false
    property color highlightColor: Theme.accent
    property bool accent: false
    implicitWidth: 56
    implicitHeight: 52
    focusPolicy: Qt.NoFocus
    hoverEnabled: true
    opacity: enabled ? 1 : 0.38

    background: Rectangle {
        radius: Theme.radiusSmall
        color: control.accent ? (control.pressed ? Theme.accentStrong : (control.hovered ? Qt.lighter(Theme.accent, 1.08) : Theme.accent))
             : control.highlighted ? Theme.alpha(control.highlightColor, control.pressed ? 0.35 : 0.2)
             : control.pressed ? Theme.cardPressed : (control.hovered ? Theme.cardHover : Theme.card)
        border.color: control.accent ? "transparent" : (control.highlighted ? Theme.alpha(control.highlightColor, 0.8) : Theme.border)
    }
    contentItem: Column {
        spacing: 3
        topPadding: 6
        IconImage {
            anchors.horizontalCenter: parent.horizontalCenter
            source: Theme.icon(control.iconName)
            sourceSize: Qt.size(22, 22)
            width: 22; height: 22
            color: control.accent ? Theme.onAccent : (control.highlighted ? control.highlightColor : Theme.text)
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: control.text
            color: control.accent ? Theme.onAccent : (control.highlighted ? control.highlightColor : Theme.textDim)
            font.family: Theme.fontFamily
            font.pixelSize: 9
            font.weight: Font.DemiBold
        }
    }
    scale: pressed ? 0.95 : 1.0
    Behavior on scale { NumberAnimation { duration: 70 } }
}
