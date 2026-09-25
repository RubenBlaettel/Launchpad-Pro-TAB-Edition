import QtQuick
import QtQuick.Layouts
import LaunchpadPro

// Optionen › Bearbeiten & Schneiden.
// Ausgegraut, bis in der Auswahlliste einer Kachel "Bearbeiten" gewählt wird.
Card {
    id: card
    implicitHeight: col.implicitHeight + 2 * padding
    readonly property bool on: editor.active && !editor.saving && !backend.showMode

    function timeToX(t) { return (t - editor.viewStart) / Math.max(0.0001, editor.viewEnd - editor.viewStart) * wave.width }
    function xToTime(x) { return editor.viewStart + x / Math.max(1, wave.width) * (editor.viewEnd - editor.viewStart) }

    ColumnLayout {
        id: col
        anchors.left: parent.left
        anchors.right: parent.right
        spacing: 10

        SectionHeader {
            text: "Bearbeiten & Schneiden"
            iconName: "scissors"
            Rectangle {
                visible: editor.active || editor.loading
                height: 26
                width: Math.min(labelText.implicitWidth + 20, card.width * 0.42)
                radius: 13
                color: Theme.alpha(Theme.accent, 0.13)
                border.color: Theme.alpha(Theme.accent, 0.5)
                Text {
                    id: labelText
                    anchors.centerIn: parent
                    width: parent.width - 16
                    text: editor.tileLabel
                    color: Theme.accent
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSmall
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                    horizontalAlignment: Text.AlignHCenter
                }
            }
            AppButton {
                visible: editor.active || editor.loading
                enabled: !backend.showMode
                implicitHeight: 32
                height: 32
                text: "Verwerfen"
                iconName: "close"
                iconSize: 14
                variant: "flat"
                tint: Theme.textDim
                font.pixelSize: Theme.fontSmall
                toolTipText: "Bearbeitung ohne Speichern schließen"
                onClicked: editor.cancel()
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 12

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 8

                // ---------------------------------------------- Wellenform
                Rectangle {
                    id: waveFrame
                    Layout.fillWidth: true
                    Layout.preferredHeight: 124
                    radius: 8
                    color: "#000000"
                    border.color: Theme.border
                    clip: true

                    WaveformView {
                        id: wave
                        anchors.fill: parent
                        anchors.margins: 1
                        active: editor.active
                        viewStart: editor.viewStart
                        viewEnd: editor.viewEnd
                        selStart: editor.selStart
                        selEnd: editor.selEnd
                        Component.onCompleted: editor.attachWaveform(wave)
                    }

                    // Interaktion: Tippen = Abspielposition, Ziehen = verschieben, Pinch/Mausrad = Zoom
                    Item {
                        anchors.fill: wave
                        enabled: card.on
                        property real panStart: 0
                        property real lastScale: 1
                        TapHandler {
                            onTapped: (pt) => editor.seek(card.xToTime(pt.position.x))
                        }
                        DragHandler {
                            id: panDrag
                            target: null
                            yAxis.enabled: false
                            onActiveChanged: if (active) parent.panStart = editor.viewStart
                            onTranslationChanged: {
                                const span = editor.viewEnd - editor.viewStart
                                const v0 = parent.panStart - translation.x / wave.width * span
                                editor.setView(v0, v0 + span)
                            }
                        }
                        PinchHandler {
                            target: null
                            onActiveChanged: if (active) parent.lastScale = 1
                            onActiveScaleChanged: {
                                const f = activeScale / parent.lastScale
                                parent.lastScale = activeScale
                                editor.zoomAround(card.xToTime(centroid.position.x), f)
                            }
                        }
                        WheelHandler {
                            onWheel: (ev) => {
                                if (ev.modifiers & Qt.ShiftModifier || Math.abs(ev.angleDelta.x) > Math.abs(ev.angleDelta.y)) {
                                    const d = (ev.angleDelta.x !== 0 ? ev.angleDelta.x : ev.angleDelta.y) / 120
                                    editor.panBy(-d * (editor.viewEnd - editor.viewStart) * 0.1)
                                } else {
                                    editor.zoomAround(card.xToTime(ev.x), ev.angleDelta.y > 0 ? 1.25 : 0.8)
                                }
                            }
                        }
                    }

                    // Auswahl-Griffe (Anfang / Ende) – groß genug für Finger
                    Repeater {
                        model: 2
                        Item {
                            id: handle
                            required property int index
                            readonly property bool isStart: index === 0
                            readonly property real t: isStart ? editor.selStart : editor.selEnd
                            readonly property real hx: card.timeToX(t)
                            visible: editor.active && hx >= -20 && hx <= wave.width + 20
                            x: wave.x + hx - width / 2
                            y: 0
                            width: 44
                            height: waveFrame.height
                            z: 5
                            Rectangle {
                                anchors.horizontalCenter: parent.horizontalCenter
                                width: 2
                                height: parent.height
                                color: hDrag.active ? "#FFFFFF" : Theme.warning
                            }
                            Rectangle {
                                // Fahne mit Zeit
                                y: 4
                                x: handle.isStart ? parent.width / 2 : parent.width / 2 - width
                                width: flagText.implicitWidth + 12
                                height: 20
                                radius: 4
                                color: hDrag.active ? "#FFFFFF" : Theme.warning
                                Text {
                                    id: flagText
                                    anchors.centerIn: parent
                                    text: (handle.isStart ? "[ " : "") + editor.fmt(handle.t) + (handle.isStart ? "" : " ]")
                                    color: "#15120A"
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 10
                                    font.weight: Font.Bold
                                    font.features: { "tnum": 1 }
                                }
                            }
                            property real startX: 0
                            DragHandler {
                                id: hDrag
                                target: null
                                yAxis.enabled: false
                                enabled: card.on
                                onActiveChanged: if (active) handle.startX = handle.hx
                                onTranslationChanged: {
                                    const t = card.xToTime(handle.startX + translation.x)
                                    if (handle.isStart) editor.setSelStart(t)
                                    else editor.setSelEnd(t)
                                }
                            }
                        }
                    }

                    // Abspielkopf
                    Rectangle {
                        readonly property real px: card.timeToX(editor.position)
                        visible: editor.active && px >= 0 && px <= wave.width
                        x: wave.x + px - 1
                        y: 0
                        z: 6
                        width: 2
                        height: waveFrame.height
                        color: "#FFFFFF"
                        Rectangle {
                            anchors.horizontalCenter: parent.horizontalCenter
                            anchors.verticalCenter: parent.top
                            width: 10; height: 10; rotation: 45
                            color: "#FFFFFF"
                        }
                    }

                    // Zoom-Tasten (überlagert)
                    Row {
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        anchors.margins: 6
                        spacing: 4
                        z: 7
                        visible: editor.active
                        Repeater {
                            model: [ { i: "zoom-out", t: "Verkleinern" }, { i: "zoom-in", t: "Vergrößern" }, { i: "fit", t: "Alles zeigen" } ]
                            AppButton {
                                required property var modelData
                                width: 34; height: 30
                                implicitHeight: 30
                                iconName: modelData.i
                                iconSize: 16
                                variant: "solid"
                                opacity: 0.88
                                toolTipText: modelData.t
                                onClicked: {
                                    if (modelData.i === "zoom-out") editor.zoomOut()
                                    else if (modelData.i === "zoom-in") editor.zoomIn()
                                    else editor.zoomFit()
                                }
                            }
                        }
                    }

                    // Hinweis im ausgegrauten Zustand
                    Column {
                        anchors.centerIn: parent
                        spacing: 8
                        visible: !editor.active && !editor.loading
                        Icon { anchors.horizontalCenter: parent.horizontalCenter; name: "scissors"; size: 26; color: Theme.alpha(Theme.accent, 0.55) }
                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            horizontalAlignment: Text.AlignHCenter
                            text: "Kachel lange drücken oder rechtsklicken\n→ „Bearbeiten“ wählen"
                            color: Theme.alpha(Theme.accent, 0.7)
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSmall
                            lineHeight: 1.2
                        }
                    }
                    Rectangle {
                        anchors.fill: parent
                        visible: editor.loading || editor.saving
                        color: "#B0000000"
                        z: 8
                        Column {
                            anchors.centerIn: parent
                            spacing: 8
                            Spinner { anchors.horizontalCenter: parent.horizontalCenter; size: 30; running: parent.parent.visible }
                            Text {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: editor.saving ? "Bearbeitung wird gespeichert …" : "Audiospur wird geladen …"
                                color: Theme.text
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSmall
                            }
                        }
                    }
                }

                // Übersicht (ganze Datei, sichtbarer Ausschnitt)
                Rectangle {
                    id: overview
                    Layout.fillWidth: true
                    Layout.preferredHeight: 12
                    radius: 4
                    color: "#0D0F13"
                    border.color: Theme.border
                    opacity: editor.active ? 1 : 0.4
                    readonly property real dur: Math.max(0.001, editor.duration)
                    Rectangle {
                        x: overview.width * editor.selStart / overview.dur
                        width: Math.max(2, overview.width * (editor.selEnd - editor.selStart) / overview.dur)
                        height: parent.height
                        radius: 4
                        color: Theme.alpha(Theme.accent, 0.35)
                        visible: editor.active
                    }
                    Rectangle {
                        x: overview.width * editor.viewStart / overview.dur
                        width: Math.max(6, overview.width * (editor.viewEnd - editor.viewStart) / overview.dur)
                        height: parent.height
                        radius: 4
                        color: "transparent"
                        border.color: "#FFFFFF"
                        border.width: 1.5
                        visible: editor.active
                    }
                    Rectangle {
                        x: overview.width * editor.position / overview.dur - 1
                        width: 2
                        height: parent.height
                        color: "#FFFFFF"
                        visible: editor.active
                    }
                    DragHandler {
                        target: null
                        yAxis.enabled: false
                        enabled: card.on
                        onCentroidChanged: {
                            if (!active) return
                            const span = editor.viewEnd - editor.viewStart
                            const c = centroid.position.x / overview.width * editor.duration
                            editor.setView(c - span / 2, c + span / 2)
                        }
                    }
                }

                // Zeiten + Anfang/Ende an der Abspielposition setzen
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    enabled: card.on
                    Column {
                        Layout.fillWidth: true
                        spacing: 1
                        Text {
                            text: editor.fmt(editor.position) + "  /  " + editor.fmt(editor.duration)
                            color: editor.active ? Theme.text : Theme.textMute
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontBody
                            font.weight: Font.DemiBold
                            font.features: { "tnum": 1 }
                        }
                        Text {
                            readonly property real len: Math.max(0, editor.selEnd - editor.selStart)
                            text: "Auswahl " + editor.fmt(len) + (Math.abs(editor.speed - 1) > 0.001 ? "  →  " + editor.fmt(len / editor.speed) : "")
                            color: Theme.textMute
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fontSmall
                            font.features: { "tnum": 1 }
                        }
                    }
                    AppButton {
                        implicitHeight: 42
                        text: "Anfang hier"
                        iconName: "mark-start"
                        iconSize: 18
                        font.pixelSize: Theme.fontSmall
                        toolTipText: "Auswahl-Anfang auf die Abspielposition setzen"
                        onClicked: editor.markStart()
                    }
                    AppButton {
                        implicitHeight: 42
                        text: "Ende hier"
                        iconName: "mark-end"
                        iconSize: 18
                        font.pixelSize: Theme.fontSmall
                        toolTipText: "Auswahl-Ende auf die Abspielposition setzen"
                        onClicked: editor.markEnd()
                    }
                }

                // Schnelligkeit
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12
                    enabled: card.on
                    Column {
                        Layout.preferredWidth: 92
                        spacing: 2
                        Row {
                            spacing: 6
                            Icon { name: "speed"; size: 16; color: Theme.textDim; anchors.verticalCenter: parent.verticalCenter }
                            Text {
                                text: "Schnelligkeit"
                                color: Theme.textDim
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fontSmall
                                font.weight: Font.DemiBold
                            }
                        }
                        Text {
                            text: editor.speed.toFixed(2).replace(".", ",") + "×"
                            color: Math.abs(editor.speed - 1) < 0.001 ? Theme.text : Theme.accent
                            font.family: Theme.fontFamily
                            font.pixelSize: 18
                            font.weight: Font.Bold
                            font.features: { "tnum": 1 }
                        }
                    }
                    SpeedSlider {
                        Layout.fillWidth: true
                        value: editor.speed
                        onMoved: (v) => editor.setSpeed(v)
                    }
                }

                // Transport (typische Symbole, Beschriftung darunter)
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 5
                    enabled: card.on
                    TransportButton { Layout.fillWidth: true; Layout.minimumWidth: 46; text: "Von Anfang"; iconName: "to-start"; onClicked: editor.toStart() }
                    TransportButton {
                        Layout.fillWidth: true; Layout.minimumWidth: 46
                        text: "Schritt zurück"; iconName: "step-back"
                        autoRepeat: true; autoRepeatDelay: 350; autoRepeatInterval: 110
                        onClicked: editor.stepBack()
                    }
                    TransportButton { Layout.fillWidth: true; Layout.minimumWidth: 46; text: "Play"; iconName: "play"; highlighted: editor.playing; onClicked: editor.play() }
                    TransportButton { Layout.fillWidth: true; Layout.minimumWidth: 46; text: "Pause"; iconName: "pause"; highlighted: editor.active && !editor.playing; highlightColor: Theme.textDim; onClicked: editor.pause() }
                    TransportButton {
                        Layout.fillWidth: true; Layout.minimumWidth: 46
                        text: "Schritt vor"; iconName: "step-forward"
                        autoRepeat: true; autoRepeatDelay: 350; autoRepeatInterval: 110
                        onClicked: editor.stepForward()
                    }
                    TransportButton { Layout.fillWidth: true; Layout.minimumWidth: 46; text: "Zurücksetzen"; iconName: "reset"; onClicked: editor.reset() }
                    TransportButton { Layout.fillWidth: true; Layout.minimumWidth: 58; text: "Speichern"; iconName: "save"; accent: true; onClicked: editor.save() }
                }
            }

            VFader {
                Layout.fillHeight: true
                Layout.preferredWidth: 92
                enabled: card.on
                value: editor.gain
                label: "LAUTSTÄRKE"
                onMoved: (v) => editor.setGain(v)
            }
        }
    }
}
