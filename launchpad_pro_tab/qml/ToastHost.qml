import QtQuick
import QtQuick.Layouts

// Kurze Meldungen unten in der Mitte (optional mit "Rückgängig").
Item {
    id: host
    property int maxToasts: 3

    function show(message, kind, action) {
        if (toastModel.count >= maxToasts) toastModel.remove(0)
        toastModel.append({ message: message, kind: kind || "info", action: action || "" })
    }

    ListModel { id: toastModel }

    Column {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 18
        spacing: 8
        Repeater {
            model: toastModel
            delegate: Rectangle {
                id: toast
                required property int index
                required property string message
                required property string kind
                required property string action
                readonly property color accentColor: kind === "error" ? Theme.danger
                                                    : kind === "warning" ? Theme.warning
                                                    : kind === "success" ? Theme.accent : Theme.info
                anchors.horizontalCenter: parent ? parent.horizontalCenter : undefined
                width: Math.min(host.width - 40, row.implicitWidth + 36)
                height: Math.max(52, msg.implicitHeight + 24)
                radius: 12
                color: "#F21A1D25"
                border.color: Theme.alpha(accentColor, 0.65)
                opacity: 0
                Component.onCompleted: opacity = 1
                Behavior on opacity { NumberAnimation { duration: 160 } }

                RowLayout {
                    id: row
                    anchors.fill: parent
                    anchors.leftMargin: 16
                    anchors.rightMargin: 10
                    spacing: 12
                    Icon {
                        name: toast.kind === "error" || toast.kind === "warning" ? "warning" : (toast.kind === "success" ? "check" : "info")
                        size: 20
                        color: toast.accentColor
                    }
                    Text {
                        id: msg
                        Layout.maximumWidth: host.width - 220
                        text: toast.message
                        color: Theme.text
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBody
                        wrapMode: Text.Wrap
                    }
                    AppButton {
                        visible: toast.action === "undo"
                        implicitHeight: 38
                        text: "Rückgängig"
                        iconName: "undo"
                        iconSize: 16
                        font.pixelSize: Theme.fontSmall
                        onClicked: { backend.undoClear(); toastModel.remove(toast.index) }
                    }
                    AppButton {
                        width: 36; implicitHeight: 36
                        iconName: "close"
                        iconSize: 12
                        variant: "flat"
                        tint: Theme.textMute
                        onClicked: toastModel.remove(toast.index)
                    }
                }
                Timer {
                    running: true
                    interval: toast.action === "undo" ? 8000 : (toast.kind === "error" ? 7000 : 4000)
                    onTriggered: if (toast.index >= 0 && toast.index < toastModel.count) toastModel.remove(toast.index)
                }
            }
        }
    }
}
