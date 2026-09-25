import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Controls.impl

// Touch-freundliches Dropdown-Menü im App-Design.
ComboBox {
    id: control
    property string prefix: ""
    implicitHeight: Theme.touch
    font.family: Theme.fontFamily
    font.pixelSize: Theme.fontBody
    font.weight: Font.DemiBold
    focusPolicy: Qt.NoFocus

    background: Rectangle {
        radius: Theme.radiusSmall
        color: control.pressed ? Theme.cardPressed : (control.hovered ? Theme.cardHover : Theme.card)
        border.color: control.popup.visible ? Theme.accent : Theme.border
        border.width: 1
    }
    contentItem: Text {
        leftPadding: 14
        rightPadding: control.indicator.width + 8
        text: control.prefix + control.displayText
        font: control.font
        color: Theme.text
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }
    indicator: IconImage {
        x: control.width - width - 12
        y: (control.height - height) / 2
        width: 14; height: 14
        sourceSize: Qt.size(14, 14)
        source: Theme.icon("chevron-down")
        color: Theme.textDim
    }
    delegate: ItemDelegate {
        id: del
        required property int index
        required property var modelData
        width: ListView.view ? ListView.view.width : control.width
        height: Theme.touch
        highlighted: control.highlightedIndex === index
        contentItem: Text {
            text: del.modelData
            color: del.index === control.currentIndex ? Theme.accent : Theme.text
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontBody
            font.weight: del.index === control.currentIndex ? Font.Bold : Font.Normal
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
        background: Rectangle {
            radius: 6
            color: del.pressed ? Theme.cardPressed : (del.highlighted ? Theme.cardHover : "transparent")
        }
    }
    popup: Popup {
        y: control.height + 6
        width: Math.max(control.width, 200)
        implicitHeight: Math.min(contentItem.implicitHeight + 16, 420)
        padding: 8
        contentItem: ListView {
            clip: true
            implicitHeight: contentHeight
            model: control.popup.visible ? control.delegateModel : null
            currentIndex: control.highlightedIndex
            boundsBehavior: Flickable.StopAtBounds
        }
        background: Rectangle {
            radius: Theme.radiusSmall
            color: Theme.card
            border.color: Theme.borderStrong
        }
    }
}
