import QtQuick
import QtQuick.Layouts
import QtQuick.Templates as T

// Registerkarten über dem Kachel-Raster (wie im Browser): eine Karte je geöffnetem Projekt,
// "+" öffnet eine leere Karte (Startseite). Kacheln im Hintergrund spielen weiter – die Karte
// zeigt dann ein Wiedergabe-Symbol. Im Show-Modus nur Umschalten (kein Öffnen/Schließen).
Item {
    id: strip
    implicitHeight: Theme.touch

    RowLayout {
        anchors.fill: parent
        spacing: 8

        ListView {
            id: list
            Layout.fillWidth: true
            Layout.fillHeight: true
            orientation: ListView.Horizontal
            spacing: 6
            clip: true
            model: backend.tabs
            boundsBehavior: Flickable.StopAtBounds
            interactive: contentWidth > width
            currentIndex: backend.activeTab
            highlightFollowsCurrentItem: false
            onCurrentIndexChanged: if (currentIndex >= 0) positionViewAtIndex(currentIndex, ListView.Contain)

            delegate: T.AbstractButton {
                id: tab
                required property int index
                required property string title
                required property string path
                required property bool hasProject
                required property bool dirty
                required property int playing
                required property bool active
                objectName: "tab_" + index
                width: Math.max(150, Math.min(280, content.implicitWidth + 24))
                height: ListView.view.height
                hoverEnabled: true
                focusPolicy: Qt.NoFocus
                leftPadding: 14
                rightPadding: 6
                onClicked: backend.activateTab(index)

                background: Rectangle {
                    radius: Theme.radiusSmall
                    color: tab.active ? Theme.panel
                         : tab.pressed ? Theme.cardPressed
                         : tab.hovered ? Theme.cardHover : Theme.card
                    border.width: tab.active ? 2 : 1
                    border.color: tab.active ? Theme.alpha(Theme.accent, 0.8) : Theme.border
                }

                contentItem: RowLayout {
                    id: content
                    spacing: 8
                    Rectangle {  // gespeichert (grün) / ungespeichert (gelb) / leer
                        implicitWidth: 9; implicitHeight: 9; radius: 5
                        color: !tab.hasProject ? Theme.textMute : (tab.dirty ? Theme.warning : Theme.accent)
                    }
                    Text {
                        Layout.fillWidth: true
                        Layout.maximumWidth: 170
                        text: tab.title
                        color: tab.active ? Theme.text : Theme.textDim
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontBody
                        font.weight: tab.active ? Font.Bold : Font.DemiBold
                        elide: Text.ElideRight
                    }
                    // läuft etwas in dieser Karte? (auch im Hintergrund)
                    Rectangle {
                        visible: tab.playing > 0
                        implicitWidth: playRow.implicitWidth + 12
                        implicitHeight: 22
                        radius: 11
                        color: Theme.alpha(Theme.accent, 0.16)
                        Row {
                            id: playRow
                            anchors.centerIn: parent
                            spacing: 3
                            Icon { anchors.verticalCenter: parent.verticalCenter; name: "play"; size: 11; color: Theme.accent }
                            Text {
                                anchors.verticalCenter: parent.verticalCenter
                                text: tab.playing
                                color: Theme.accent
                                font.family: Theme.fontFamily
                                font.pixelSize: 11
                                font.weight: Font.Bold
                            }
                        }
                        SequentialAnimation on opacity {
                            running: tab.playing > 0 && !tab.active
                            loops: Animation.Infinite
                            alwaysRunToEnd: true
                            NumberAnimation { to: 0.45; duration: 650; easing.type: Easing.InOutSine }
                            NumberAnimation { to: 1.0; duration: 650; easing.type: Easing.InOutSine }
                        }
                    }
                    AppButton {
                        objectName: "closeTab_" + tab.index
                        visible: !backend.showMode
                        implicitWidth: 36
                        implicitHeight: 36
                        iconName: "close"
                        iconSize: 12
                        variant: "flat"
                        tint: Theme.textMute
                        onClicked: backend.closeTab(tab.index)
                    }
                }

                // Mittlere Maustaste schließt (wie im Browser). Nur echte Maus: acceptedButtons filtert
                // Touch nicht – ohne acceptedDevices schloss jedes Antippen der Karte das Projekt.
                TapHandler {
                    acceptedDevices: PointerDevice.Mouse
                    acceptedButtons: Qt.MiddleButton
                    gesturePolicy: TapHandler.ReleaseWithinBounds
                    onTapped: if (!backend.showMode) backend.closeTab(tab.index)
                }
            }
        }

        AppButton {
            objectName: "newTabButton"
            visible: !backend.showMode
            Layout.preferredWidth: Theme.touch
            iconName: "plus"
            variant: "ghost"
            toolTipText: "Neue Registerkarte  [Strg+T]"
            onClicked: backend.newTab()
        }
    }
}
