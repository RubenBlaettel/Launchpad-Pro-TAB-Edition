import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Einmalige Frage beim ersten Start: Darf Launchpad Pro automatisch nach Updates suchen?
// Ohne Antwort (Fenster geschlossen) wird beim nächsten Start erneut gefragt.
AppDialog {
    id: dlg
    title: "Automatisch nach Updates suchen?"
    iconName: "refresh"
    dialogWidth: 600
    closePolicy: Popup.CloseOnEscape

    ColumnLayout {
        width: parent.width
        spacing: 10
        Text {
            Layout.fillWidth: true
            text: "Launchpad Pro kann beim Start prüfen, ob eine neue Version veröffentlicht wurde, und Sie darauf hinweisen."
            color: Theme.text
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontLarge
            wrapMode: Text.Wrap
            lineHeight: 1.2
        }
        Text {
            Layout.fillWidth: true
            text: "Dafür fragt das Programm die öffentliche Projektseite auf GitHub ab. Übertragen werden nur die "
                  + "üblichen Verbindungsdaten (z. B. die IP-Adresse) – keine Projekte, Audiodateien oder Einstellungen. "
                  + "Installiert wird ein Update immer erst nach Ihrer Bestätigung."
            color: Theme.textDim
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontBody
            wrapMode: Text.Wrap
            lineHeight: 1.2
        }
        Text {
            Layout.fillWidth: true
            text: "Ändern lässt sich das jederzeit unter Einstellungen › Updates."
            color: Theme.textMute
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontSmall
            wrapMode: Text.Wrap
        }
    }

    buttons: [
        AppButton {
            objectName: "consentNoButton"
            text: "Nein, nicht suchen"
            variant: "solid"
            Layout.preferredWidth: 190
            onClicked: { updater.answerConsent(false); dlg.close() }
        },
        Item { Layout.fillWidth: true },
        AppButton {
            objectName: "consentYesButton"
            text: "Ja, automatisch suchen"
            iconName: "check"
            variant: "accent"
            Layout.preferredWidth: 240
            onClicked: { updater.answerConsent(true); dlg.close() }
        }
    ]
}
