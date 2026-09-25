import QtQuick

// Horizontale Stereo-Pegelanzeige (grün/gelb/rot) mit Spitzenwert-Haltung
// und "LIMIT"-Anzeige (leuchtet, wenn der Master-Limiter eingreift).
Item {
    id: meter
    property real levelL: 0      // linear 0..1
    property real levelR: 0
    property bool limiting: false
    property real floorDb: -60
    implicitHeight: 26

    function toFrac(v) {
        if (v <= 0.00001) return 0
        const d = 20 * Math.log(v) / Math.LN10
        return Math.max(0, Math.min(1, (d - floorDb) / -floorDb))
    }

    property real shownL: 0
    property real shownR: 0
    property real holdL: 0
    property real holdR: 0
    onLevelLChanged: { const f = toFrac(levelL); shownL = Math.max(f, shownL - 0.035); if (f > holdL) { holdL = f; holdTimer.restart() } }
    onLevelRChanged: { const f = toFrac(levelR); shownR = Math.max(f, shownR - 0.035); if (f > holdR) { holdR = f; holdTimer.restart() } }
    Timer { id: holdTimer; interval: 1200; onTriggered: { meter.holdL = meter.shownL; meter.holdR = meter.shownR } }
    Timer {
        // Ausklingen, auch wenn keine neuen Werte kommen
        interval: 50; repeat: true; running: meter.shownL > 0 || meter.shownR > 0
        onTriggered: { meter.shownL = Math.max(meter.toFrac(meter.levelL), meter.shownL - 0.03); meter.shownR = Math.max(meter.toFrac(meter.levelR), meter.shownR - 0.03) }
    }

    Row {
        anchors.fill: parent
        spacing: 8
        Column {
            width: parent.width - limitLed.width - 8
            anchors.verticalCenter: parent.verticalCenter
            spacing: 3
            Repeater {
                model: 2
                Row {
                    required property int index
                    spacing: 6
                    Text {
                        width: 10
                        text: index === 0 ? "L" : "R"
                        color: Theme.textMute
                        font.family: Theme.fontFamily
                        font.pixelSize: 9
                        font.weight: Font.Bold
                        anchors.verticalCenter: parent.verticalCenter
                    }
                    Rectangle {
                        id: bar
                        width: parent.parent.width - 16
                        height: 8
                        radius: 2
                        color: "#0B0C0F"
                        border.color: "#1E2128"
                        readonly property real frac: index === 0 ? meter.shownL : meter.shownR
                        readonly property real hold: index === 0 ? meter.holdL : meter.holdR
                        Rectangle {
                            x: 1; y: 1
                            height: parent.height - 2
                            width: (parent.width - 2) * bar.frac
                            radius: 1
                            gradient: Gradient {
                                orientation: Gradient.Horizontal
                                GradientStop { position: 0.0; color: Theme.meterGreen }
                                GradientStop { position: 0.72; color: Theme.meterGreen }
                                GradientStop { position: 0.86; color: Theme.meterYellow }
                                GradientStop { position: 1.0; color: Theme.meterRed }
                            }
                        }
                        Rectangle {
                            visible: bar.hold > 0.01
                            x: 1 + (parent.width - 4) * bar.hold
                            y: 1
                            width: 2
                            height: parent.height - 2
                            color: bar.hold > 0.95 ? Theme.meterRed : "#FFFFFF"
                        }
                    }
                }
            }
        }
        Rectangle {
            id: limitLed
            width: 46
            height: 20
            radius: 4
            anchors.verticalCenter: parent.verticalCenter
            color: meter.limiting ? Theme.meterRed : "#15171C"
            border.color: meter.limiting ? "#FF8A8A" : Theme.border
            Text {
                anchors.centerIn: parent
                text: "LIMIT"
                color: meter.limiting ? "#FFFFFF" : Theme.textMute
                font.family: Theme.fontFamily
                font.pixelSize: 9
                font.weight: Font.Bold
                font.letterSpacing: 0.8
            }
        }
    }
}
