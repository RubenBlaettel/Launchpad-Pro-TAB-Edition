import QtQuick
import QtQuick.Layouts

// Audio-Einstellungen: Ausgabegerät, Puffergröße (Latenz), Infos.
AppDialog {
    id: dlg
    title: "Einstellungen"
    iconName: "settings"
    dialogWidth: 640

    function labelFor(frames) {
        return frames === 0 ? "Automatisch (niedrige Latenz)" : frames + " Samples"
    }

    ColumnLayout {
        width: parent.width
        spacing: 8

        FieldLabel { text: "Audio-Ausgabe" }
        AppComboBox {
            id: deviceBox
            Layout.fillWidth: true
            model: backend.outputDevices
            currentIndex: backend.outputDeviceIndex
            onActivated: (i) => backend.setOutputDevice(i)
        }
        Text {
            Layout.fillWidth: true
            text: "Aktiv: " + backend.audioDevice + "  ·  " + backend.audioInfo
            color: backend.audioOk ? Theme.textDim : Theme.danger
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontSmall
            wrapMode: Text.Wrap
        }

        FieldLabel { text: "Puffergröße (kleiner = geringere Latenz, größer = robuster)"; Layout.topMargin: 10 }
        AppComboBox {
            Layout.preferredWidth: 320
            model: backend.bufferOptions.map(f => dlg.labelFor(f))
            currentIndex: Math.max(0, backend.bufferOptions.indexOf(backend.bufferFrames))
            onActivated: (i) => backend.setBufferFrames(backend.bufferOptions[i])
        }
        Text {
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            text: "Unter Windows wird automatisch WASAPI verwendet (geringe Latenz). Bei Knacksern die Puffergröße erhöhen."
            color: Theme.textMute
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontSmall
            lineHeight: 1.2
        }

        Rectangle { Layout.fillWidth: true; Layout.topMargin: 12; height: 1; color: Theme.border }

        GridLayout {
            Layout.fillWidth: true
            Layout.topMargin: 6
            columns: 2
            columnSpacing: 16
            rowSpacing: 6
            FieldLabel { text: "Version" }
            Text { text: "Launchpad Pro TAB Edition " + appVersion; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: Theme.fontBody }
            FieldLabel { text: "Systemlautstärke" }
            Text { text: master.backendName; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: Theme.fontBody; Layout.fillWidth: true; elide: Text.ElideRight }
            FieldLabel { text: "Protokoll" }
            Text { text: logFile; color: Theme.textDim; font.family: Theme.fontFamily; font.pixelSize: Theme.fontSmall; Layout.fillWidth: true; elide: Text.ElideMiddle }
        }
    }

    buttons: [
        Item { Layout.fillWidth: true },
        AppButton {
            text: "Schließen"
            variant: "accent"
            Layout.preferredWidth: 150
            onClicked: dlg.close()
        }
    ]
}
