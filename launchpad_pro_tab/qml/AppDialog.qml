import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Modales Dialogfenster im App-Design (zentriert, abgedunkelter Hintergrund).
Popup {
    id: dialog
    property string title: ""
    property string iconName: ""
    property color iconColor: Theme.accent
    default property alias content: body.data
    property alias buttons: footerRow.data
    property int dialogWidth: 560

    parent: Overlay.overlay
    anchors.centerIn: parent
    width: Math.min(dialogWidth, (parent ? parent.width : 800) - 48)
    height: Math.min(implicitHeight, (parent ? parent.height : 600) - 48)
    modal: true
    focus: true
    padding: 0
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

    Overlay.modal: Rectangle { color: "#B3000000" }

    enter: Transition {
        ParallelAnimation {
            NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 140; easing.type: Easing.OutCubic }
            NumberAnimation { property: "scale"; from: 0.96; to: 1; duration: 160; easing.type: Easing.OutCubic }
        }
    }
    exit: Transition { NumberAnimation { property: "opacity"; from: 1; to: 0; duration: 100 } }

    background: Rectangle {
        radius: 18
        color: Theme.panel
        border.color: Theme.borderStrong
    }

    contentItem: ColumnLayout {
        spacing: 0
        RowLayout {
            Layout.fillWidth: true
            Layout.margins: 22
            Layout.bottomMargin: 8
            spacing: 12
            Rectangle {
                visible: dialog.iconName !== ""
                width: 40; height: 40; radius: 12
                color: Theme.alpha(dialog.iconColor, 0.14)
                Icon { anchors.centerIn: parent; name: dialog.iconName; size: 22; color: dialog.iconColor }
            }
            Text {
                Layout.fillWidth: true
                text: dialog.title
                color: Theme.text
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontTitle
                font.weight: Font.Bold
                elide: Text.ElideRight
            }
            AppButton {
                width: 44; implicitHeight: 44
                iconName: "close"
                variant: "flat"
                tint: Theme.textDim
                onClicked: dialog.close()
            }
        }
        Item {
            id: body
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.leftMargin: 22
            Layout.rightMargin: 22
            implicitHeight: childrenRect.height
        }
        RowLayout {
            id: footerRow
            Layout.fillWidth: true
            Layout.margins: 22
            Layout.topMargin: 18
            spacing: 10
        }
    }
}
