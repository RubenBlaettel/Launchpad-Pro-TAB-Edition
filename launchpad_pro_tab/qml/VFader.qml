import QtQuick

// Vertikaler Fader im Mischpult-Stil (angelehnt an Bild 3):
// schwarze Fader-Bahn mit Skala, heller Fader-Knopf, Wertanzeige und Beschriftung.
// Arbeitet in dB, liefert/erwartet aber einen linearen Faktor (1.0 = 100 %).
// Rastpunkt bei ``detentDb`` (Normalstellung), Doppeltippen setzt darauf zurück.
Rectangle {
    id: fader
    property real value: 1.0            // linearer Faktor
    property real minDb: -20            // 10 %
    property real maxDb: 6.0206         // 200 %
    property real detentDb: 0
    property real snapDb: 0.8
    property string label: "LAUTSTÄRKE"
    property color capTop: "#F4F5F7"
    property color capBottom: "#B9BDC4"
    property var ticks: [
        { db: 6.0206, text: "200" }, { db: 3.52, text: "150" }, { db: 0, text: "100" },
        { db: -2.5, text: "75" }, { db: -6.02, text: "50" }, { db: -12.04, text: "25" }, { db: -20, text: "10" }
    ]
    signal moved(real value)

    readonly property real db: value > 0 ? 20 * Math.log(value) / Math.LN10 : minDb
    readonly property real frac: Math.max(0, Math.min(1, (db - minDb) / (maxDb - minDb)))

    implicitWidth: 92
    radius: 10
    gradient: Gradient {
        GradientStop { position: 0; color: Theme.faderStripLight }
        GradientStop { position: 1; color: Theme.faderStrip }
    }
    border.color: Theme.faderBorder
    opacity: enabled ? 1 : 0.45

    function dbToGain(d) { return Math.pow(10, d / 20) }

    // ------------------------------------------------------ Fader-Bahn
    Rectangle {
        id: track
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: readout.top
        anchors.margins: 8
        anchors.bottomMargin: 6
        radius: 4
        color: Theme.faderTrack
        border.color: Theme.faderTrackBorder

        readonly property real capH: 26
        readonly property real travel: height - capH - 12
        readonly property real capY: 6 + (1 - fader.frac) * travel

        // Skala
        Repeater {
            model: fader.ticks
            Item {
                required property var modelData
                readonly property real f: (modelData.db - fader.minDb) / (fader.maxDb - fader.minDb)
                width: track.width
                height: 12
                y: 6 + (1 - f) * track.travel + track.capH / 2 - height / 2
                Text {
                    anchors.right: tickLine.left
                    anchors.rightMargin: 4
                    anchors.verticalCenter: parent.verticalCenter
                    text: modelData.text
                    color: Math.abs(modelData.db - fader.detentDb) < 0.01 ? "#FFFFFF" : Theme.faderScale
                    font.family: Theme.fontFamily
                    font.pixelSize: 10
                    font.weight: Math.abs(modelData.db - fader.detentDb) < 0.01 ? Font.Bold : Font.Normal
                }
                Rectangle {
                    id: tickLine
                    x: track.width * 0.44
                    anchors.verticalCenter: parent.verticalCenter
                    width: Math.abs(modelData.db - fader.detentDb) < 0.01 ? 12 : 7
                    height: Math.abs(modelData.db - fader.detentDb) < 0.01 ? 2 : 1
                    color: Theme.faderScale
                }
            }
        }
        // Schlitz
        Rectangle {
            x: track.width * 0.72
            y: 8
            width: 3
            height: track.height - 16
            radius: 1.5
            color: "#2B2D33"
            border.color: "#000000"
        }
        // Fader-Knopf
        Rectangle {
            id: cap
            x: track.width * 0.44 - 6
            y: track.capY
            width: track.width - x - 6
            height: track.capH
            radius: 4
            gradient: Gradient {
                GradientStop { position: 0.0; color: fader.capTop }
                GradientStop { position: 0.48; color: Qt.darker(fader.capTop, 1.05) }
                GradientStop { position: 0.52; color: Qt.darker(fader.capBottom, 1.1) }
                GradientStop { position: 1.0; color: fader.capBottom }
            }
            border.color: drag.active ? Theme.accent : "#2A2C31"
            border.width: drag.active ? 2 : 1
            Rectangle { anchors.centerIn: parent; width: parent.width - 8; height: 2; color: "#1E2024"; opacity: 0.8 }
            Behavior on y { enabled: !drag.active; NumberAnimation { duration: 90 } }
        }

        // Ziehen: relativ (kein Springen beim Antippen), Rastpunkt bei 0 dB
        property real startFrac: 0
        DragHandler {
            id: drag
            target: null
            xAxis.enabled: false
            enabled: fader.enabled
            onActiveChanged: if (active) track.startFrac = fader.frac
            onTranslationChanged: {
                let f = track.startFrac - translation.y / track.travel
                f = Math.max(0, Math.min(1, f))
                let d = fader.minDb + f * (fader.maxDb - fader.minDb)
                if (Math.abs(d - fader.detentDb) < fader.snapDb) d = fader.detentDb
                fader.moved(fader.dbToGain(d))
            }
        }
        TapHandler {
            enabled: fader.enabled
            onDoubleTapped: fader.moved(fader.dbToGain(fader.detentDb))
        }
        WheelHandler {
            enabled: fader.enabled
            onWheel: (ev) => {
                let d = fader.db + (ev.angleDelta.y > 0 ? 0.5 : -0.5)
                d = Math.max(fader.minDb, Math.min(fader.maxDb, d))
                if (Math.abs(d - fader.detentDb) < 0.25) d = fader.detentDb
                fader.moved(fader.dbToGain(d))
            }
        }
    }

    // ------------------------------------------------------ Anzeige
    Column {
        id: readout
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 8
        anchors.horizontalCenter: parent.horizontalCenter
        spacing: 1
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: Math.round(fader.value * 100) + " %"
            color: Theme.faderText
            font.family: Theme.fontFamily
            font.pixelSize: 15
            font.weight: Font.Bold
            font.features: { "tnum": 1 }
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: (fader.db >= 0 ? "+" : "") + fader.db.toFixed(1).replace(".", ",") + " dB"
            color: Theme.faderTextDim
            font.family: Theme.fontFamily
            font.pixelSize: 10
            font.features: { "tnum": 1 }
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            topPadding: 3
            text: fader.label
            color: Theme.faderLabel
            font.family: Theme.fontFamily
            font.pixelSize: 10
            font.weight: Font.Bold
            font.letterSpacing: 1.2
        }
    }
}
