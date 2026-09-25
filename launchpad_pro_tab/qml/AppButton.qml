import QtQuick
import QtQuick.Templates as T
import QtQuick.Controls.impl

// Touch-freundlicher Button (min. 48 px) mit Icon und Text.
// variant: "ghost" | "solid" | "accent" | "danger" | "flat"
T.AbstractButton {
    id: control
    property string iconName: ""
    property string variant: "solid"
    property int iconSize: 20
    property color tint: variant === "accent" ? Theme.onAccent : (variant === "danger" ? "#FFFFFF" : Theme.text)
    property bool active: false          // z. B. für Umschalter
    property color activeColor: Theme.accent
    property string toolTipText: ""

    implicitHeight: Theme.touch
    implicitWidth: Math.max(implicitHeight, content.implicitWidth + (text !== "" ? 32 : 16))
    hoverEnabled: true
    focusPolicy: Qt.NoFocus
    font.family: Theme.fontFamily
    font.pixelSize: Theme.fontBody
    font.weight: Font.DemiBold

    readonly property color _fg: active ? activeColor : tint

    background: Rectangle {
        radius: Theme.radiusSmall
        color: {
            const v = control.variant
            if (v === "accent") return control.pressed ? Theme.accentStrong : (control.hovered ? Qt.lighter(Theme.accent, 1.08) : Theme.accent)
            if (v === "danger") return control.pressed ? Qt.darker(Theme.dangerStrong, 1.15) : (control.hovered ? Qt.lighter(Theme.dangerStrong, 1.1) : Theme.dangerStrong)
            if (v === "flat") return control.pressed ? Theme.cardPressed : (control.hovered ? Theme.cardHover : "transparent")
            if (v === "ghost") return control.pressed ? Theme.cardPressed : (control.hovered ? Theme.cardHover : "transparent")
            return control.pressed ? Theme.cardPressed : (control.hovered ? Theme.cardHover : Theme.card)
        }
        border.width: (control.variant === "flat" || control.variant === "accent" || control.variant === "danger") ? 0 : 1
        border.color: control.active ? Theme.alpha(control.activeColor, 0.7) : Theme.border
        Behavior on color { ColorAnimation { duration: 90 } }
    }

    contentItem: Item {
        implicitWidth: content.implicitWidth
        implicitHeight: content.implicitHeight
        Row {
            id: content
            anchors.centerIn: parent
            spacing: 8
            IconImage {
                visible: control.iconName !== ""
                anchors.verticalCenter: parent.verticalCenter
                source: control.iconName !== "" ? Theme.icon(control.iconName) : ""
                sourceSize: Qt.size(control.iconSize, control.iconSize)
                width: control.iconSize
                height: control.iconSize
                color: control._fg
            }
            Text {
                visible: control.text !== ""
                anchors.verticalCenter: parent.verticalCenter
                text: control.text
                font: control.font
                color: control._fg
                elide: Text.ElideRight
            }
        }
    }

    scale: pressed ? 0.965 : 1.0
    Behavior on scale { NumberAnimation { duration: 80; easing.type: Easing.OutCubic } }
    opacity: enabled ? 1.0 : 0.38

    ToolTipLite {
        text: control.toolTipText
        shown: control.toolTipText !== "" && control.hovered && !control.pressed
    }
}
