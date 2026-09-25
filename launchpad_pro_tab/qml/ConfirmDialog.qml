import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Rückfrage mit "Abbrechen" (links) und Bestätigung (rechts).
AppDialog {
    id: dlg
    property string message: ""
    property string detail: ""
    property string confirmText: "Fortfahren"
    property string cancelText: "Abbrechen"
    property string confirmVariant: "danger"
    signal confirmed()
    signal cancelled()

    iconName: "warning"
    iconColor: Theme.warning
    dialogWidth: 520
    closePolicy: Popup.CloseOnEscape

    property bool _accepted: false
    onOpened: _accepted = false
    onClosed: if (!_accepted) cancelled()

    ColumnLayout {
        width: parent.width
        spacing: 10
        Text {
            Layout.fillWidth: true
            text: dlg.message
            color: Theme.text
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontLarge
            wrapMode: Text.Wrap
            lineHeight: 1.2
        }
        Text {
            Layout.fillWidth: true
            visible: dlg.detail !== ""
            text: dlg.detail
            color: Theme.textDim
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontBody
            wrapMode: Text.Wrap
            lineHeight: 1.2
        }
    }

    buttons: [
        AppButton {
            text: dlg.cancelText
            variant: "solid"
            Layout.preferredWidth: 150
            onClicked: dlg.close()
        },
        Item { Layout.fillWidth: true },
        AppButton {
            text: dlg.confirmText
            variant: dlg.confirmVariant
            Layout.preferredWidth: 190
            onClicked: { dlg._accepted = true; dlg.close(); dlg.confirmed() }
        }
    ]
}
