import QtQuick
import QtQuick.Layouts

// Einstellungen: Darstellung (Dunkel/Hell/System), Audio, Updates, Info.
AppDialog {
    id: dlg
    title: "Einstellungen"
    iconName: "settings"
    dialogWidth: 720
    property int page: 0

    function openPage(p) { page = p; open() }

    function labelFor(frames) {
        return frames === 0 ? "Automatisch (niedrige Latenz)" : frames + " Samples"
    }
    readonly property bool isWindows: Qt.platform.os === "windows"
    readonly property var kindText: ({
        "windows-installer": "Installiert (Windows-Installer)",
        "windows-portable": "Portable Version (ohne Installer)",
        "linux-bundle": "Linux-Programmpaket",
        "source": "Python-Quellcode",
        "unsupported": "–"
    })

    ColumnLayout {
        width: parent.width
        spacing: 14

        // ------------------------------------------------ Reiter
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 52
            radius: Theme.radiusSmall + 2
            color: Theme.field
            border.color: Theme.border
            RowLayout {
                anchors.fill: parent
                anchors.margins: 4
                spacing: 4
                Repeater {
                    model: [ { t: "Darstellung", i: "sun" }, { t: "Audio", i: "headphones" },
                             { t: "Updates", i: "refresh" }, { t: "Info", i: "info" } ]
                    AppButton {
                        required property var modelData
                        required property int index
                        objectName: "settingsTab_" + index
                        Layout.fillWidth: true
                        implicitHeight: 44
                        text: modelData.t
                        iconName: modelData.i
                        iconSize: 18
                        variant: dlg.page === index ? "solid" : "flat"
                        active: dlg.page === index
                        onClicked: dlg.page = index
                        // Hinweis-Punkt, wenn ein Update bereitsteht
                        Rectangle {
                            visible: index === 2 && updater.available
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.margins: 8
                            width: 9; height: 9; radius: 5
                            color: Theme.accent
                        }
                    }
                }
            }
        }

        StackLayout {
            Layout.fillWidth: true
            currentIndex: dlg.page

            // ================================================ Darstellung
            ColumnLayout {
                spacing: 10
                FieldLabel { text: "Farbschema" }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    Repeater {
                        model: [
                            { m: "dark", i: "moon", t: "Dunkel", s: "Blendfrei im dunklen Saal" },
                            { m: "light", i: "sun", t: "Hell", s: "Für helle Räume und Proben" },
                            { m: "system", i: "monitor", t: dlg.isWindows ? "Wie Windows" : "Wie System",
                              s: dlg.isWindows ? "Folgt der Windows-Einstellung" : "Folgt der Systemeinstellung" }
                        ]
                        Rectangle {
                            id: modeCard
                            required property var modelData
                            readonly property bool selected: backend.themeMode === modelData.m
                            objectName: "themeCard_" + modelData.m
                            Layout.fillWidth: true
                            implicitHeight: 196
                            radius: Theme.radius
                            color: mTap.pressed ? Theme.cardPressed : (mHover.hovered ? Theme.cardHover : Theme.card)
                            border.width: selected ? 2 : 1
                            border.color: selected ? Theme.accent : Theme.border
                            Column {
                                anchors.centerIn: parent
                                spacing: 7
                                // Vorschau: Dunkel, Hell oder beides (wie System)
                                Item {
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    width: 156; height: 88
                                    ThemePreview { anchors.fill: parent; dark: modeCard.modelData.m !== "light" }
                                    Item {
                                        visible: modeCard.modelData.m === "system"
                                        x: parent.width / 2; width: parent.width / 2; height: parent.height
                                        clip: true
                                        ThemePreview { x: -parent.x; width: 156; height: 88; dark: false }
                                    }
                                }
                                Row {
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    spacing: 7
                                    Icon { anchors.verticalCenter: parent.verticalCenter; name: modeCard.modelData.i; size: 18
                                           color: modeCard.selected ? Theme.accent : Theme.textDim }
                                    Text {
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: modeCard.modelData.t
                                        color: Theme.text
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fontLarge
                                        font.weight: Font.Bold
                                    }
                                }
                                Text {
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    text: modeCard.modelData.s
                                    color: Theme.textMute
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fontSmall
                                }
                            }
                            Icon {
                                visible: modeCard.selected
                                anchors.right: parent.right
                                anchors.top: parent.top
                                anchors.margins: 10
                                name: "check"
                                size: 18
                                color: Theme.accent
                            }
                            HoverHandler { id: mHover }
                            TapHandler { id: mTap; onTapped: backend.setThemeMode(modeCard.modelData.m) }
                        }
                    }
                }
                Text {
                    Layout.fillWidth: true
                    Layout.topMargin: 4
                    wrapMode: Text.Wrap
                    text: "Tipp: Mit dem Sonnen- bzw. Mond-Symbol oben rechts wechseln Sie jederzeit schnell zwischen Hell und Dunkel."
                    color: Theme.textMute
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSmall
                    lineHeight: 1.2
                }
            }

            // ================================================ Audio
            ColumnLayout {
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
            }

            // ================================================ Updates
            ColumnLayout {
                spacing: 10
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: statusRow.implicitHeight + 28
                    radius: Theme.radius
                    color: Theme.card
                    border.color: updater.available ? Theme.alpha(Theme.accent, 0.6)
                                 : updater.state === "error" ? Theme.alpha(Theme.danger, 0.5) : Theme.border
                    RowLayout {
                        id: statusRow
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 14
                        Rectangle {
                            Layout.alignment: Qt.AlignTop
                            width: 44; height: 44; radius: 12
                            color: Theme.alpha(updater.state === "error" ? Theme.danger : Theme.accent, 0.14)
                            Icon {
                                anchors.centerIn: parent
                                visible: updater.state !== "checking"
                                name: updater.available ? "sparkle" : (updater.state === "error" ? "warning" : "check")
                                size: 22
                                color: updater.state === "error" ? Theme.danger : Theme.accent
                            }
                            Spinner { anchors.centerIn: parent; size: 24; running: updater.state === "checking" }
                        }
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 3
                            Text {
                                Layout.fillWidth: true
                                text: "Installierte Version " + updater.currentVersion
                                color: Theme.text
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontLarge
                                font.weight: Font.Bold
                            }
                            Text {
                                objectName: "updateStatusText"
                                Layout.fillWidth: true
                                visible: text !== ""
                                text: updater.message
                                color: updater.state === "error" ? Theme.danger : (updater.available ? Theme.accent : Theme.textDim)
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontBody
                                font.weight: updater.available ? Font.DemiBold : Font.Normal
                                wrapMode: Text.Wrap
                            }
                            Text {
                                Layout.fillWidth: true
                                text: updater.lastCheckText
                                color: Theme.textMute
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSmall
                            }
                        }
                    }
                }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    AppButton {
                        objectName: "checkUpdatesButton"
                        text: updater.state === "checking" ? "Suche läuft …" : "Jetzt nach Updates suchen"
                        iconName: "refresh"
                        enabled: updater.state !== "checking" && updater.state !== "downloading" && updater.state !== "installing"
                        onClicked: updater.checkNow()
                    }
                    AppButton {
                        visible: updater.available
                        text: "Update anzeigen"
                        iconName: "download"
                        variant: "accent"
                        onClicked: { dlg.close(); dlg.showUpdateRequested() }
                    }
                    Item { Layout.fillWidth: true }
                }
                AppSwitch {
                    objectName: "autoCheckSwitch"
                    Layout.fillWidth: true
                    Layout.topMargin: 4
                    text: "Beim Start automatisch nach Updates suchen"
                    subText: "Nur ein Hinweis – installiert wird erst nach Ihrer Bestätigung"
                    checked: updater.autoCheck
                    onToggled: updater.setAutoCheck(checked)
                }
                AppSwitch {
                    Layout.fillWidth: true
                    text: "Vorabversionen (Beta) anbieten"
                    subText: "Neue Funktionen testen, bevor sie für alle freigegeben werden"
                    checked: updater.includePrereleases
                    onToggled: updater.setIncludePrereleases(checked)
                }
                Text {
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                    text: "Updates werden aus den Releases auf GitHub geladen und vor der Installation per SHA-256-Prüfsumme geprüft."
                    color: Theme.textMute
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSmall
                    lineHeight: 1.2
                }
            }

            // ================================================ Info
            GridLayout {
                columns: 2
                columnSpacing: 18
                rowSpacing: 10
                FieldLabel { text: "Version" }
                Text { text: "Launchpad Pro TAB Edition " + appVersion; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: Theme.fontBody }
                FieldLabel { text: "Installation" }
                Text { text: dlg.kindText[updater.installKind] || updater.installKind; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: Theme.fontBody }
                FieldLabel { text: "Systemlautstärke" }
                Text { text: master.backendName; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: Theme.fontBody; Layout.fillWidth: true; elide: Text.ElideRight }
                FieldLabel { text: "Protokoll" }
                Text { text: logFile; color: Theme.textDim; font.family: Theme.fontFamily; font.pixelSize: Theme.fontSmall; Layout.fillWidth: true; elide: Text.ElideMiddle }
                FieldLabel { text: "Projekt-Standardordner" }
                Text { text: backend.defaultProjectsDir; color: Theme.textDim; font.family: Theme.fontFamily; font.pixelSize: Theme.fontSmall; Layout.fillWidth: true; elide: Text.ElideMiddle }
                FieldLabel { text: "Quellcode & Updates" }
                Text {
                    Layout.fillWidth: true
                    text: "<a href=\"" + updater.releaseUrl + "\">" + updater.releaseUrl.replace("https://", "") + "</a>"
                    textFormat: Text.StyledText
                    linkColor: Theme.accent
                    color: Theme.textDim
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSmall
                    elide: Text.ElideRight
                    onLinkActivated: (link) => Qt.openUrlExternally(link)
                    HoverHandler { cursorShape: Qt.PointingHandCursor }
                }
            }
        }
    }

    signal showUpdateRequested()

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
