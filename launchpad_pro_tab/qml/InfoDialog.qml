import QtQuick
import QtQuick.Layouts

// Einfache Meldung (Fehler/Hinweis) mit einer Schaltfläche.
AppDialog {
    id: dlg
    property string message: ""
    iconName: "warning"
    iconColor: Theme.danger
    dialogWidth: 540

    function show(t, m) {
        title = t
        message = m
        open()
    }

    Text {
        width: parent.width
        text: dlg.message
        color: Theme.text
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fontBody
        wrapMode: Text.Wrap
        lineHeight: 1.25
    }

    buttons: [
        Item { Layout.fillWidth: true },
        AppButton {
            text: "OK"
            variant: "accent"
            Layout.preferredWidth: 140
            onClicked: dlg.close()
        }
    ]
}
