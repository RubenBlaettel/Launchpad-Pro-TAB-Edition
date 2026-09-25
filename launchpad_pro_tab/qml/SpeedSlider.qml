import QtQuick

// Schieberegler "Schnelligkeit" 0,5× … 2,0× (logarithmisch, 1,0× in der Mitte)
// mit spürbarem Rastpunkt bei "normal" (1,0×). Doppeltippen = zurück auf 1,0×.
Item {
    id: slider
    property real value: 1.0
    signal moved(real value)

    readonly property real pos: Math.log(Math.max(0.5, Math.min(2.0, value))) / Math.LN2   // -1 … +1
    readonly property real knob: 30
    implicitHeight: 52
    opacity: enabled ? 1 : 0.45

    function posToX(p) { return knob / 2 + (p + 1) / 2 * (width - knob) }

    // Beschriftung
    Repeater {
        model: [ { v: 0.5, t: "0,5×" }, { v: 0.75, t: "0,75×" }, { v: 1.0, t: "normal" }, { v: 1.5, t: "1,5×" }, { v: 2.0, t: "2×" } ]
        Text {
            required property var modelData
            readonly property real p: Math.log(modelData.v) / Math.LN2
            x: Math.max(0, Math.min(slider.width - width, slider.posToX(p) - width / 2))
            y: slider.height - height
            text: modelData.t
            color: modelData.v === 1.0 ? Theme.accent : Theme.textMute
            font.family: Theme.fontFamily
            font.pixelSize: 10
            font.weight: modelData.v === 1.0 ? Font.Bold : Font.Normal
        }
    }

    Item {
        id: rail
        anchors.left: parent.left
        anchors.right: parent.right
        y: 4
        height: slider.knob

        Rectangle {
            anchors.verticalCenter: parent.verticalCenter
            x: slider.knob / 2
            width: parent.width - slider.knob
            height: 6
            radius: 3
            color: "#0B0C10"
            border.color: Theme.border
        }
        // Füllung von der Mitte (1,0×) zum Knopf
        Rectangle {
            anchors.verticalCenter: parent.verticalCenter
            readonly property real cx: slider.posToX(0)
            readonly property real kx: slider.posToX(slider.pos)
            x: Math.min(cx, kx)
            width: Math.abs(kx - cx)
            height: 6
            radius: 3
            color: Theme.accent
            opacity: 0.8
        }
        // Rastpunkt-Markierung
        Rectangle {
            x: slider.posToX(0) - 1.5
            anchors.verticalCenter: parent.verticalCenter
            width: 3
            height: 18
            radius: 1.5
            color: Theme.accent
        }
        // Knopf
        Rectangle {
            id: knobItem
            x: slider.posToX(slider.pos) - width / 2
            anchors.verticalCenter: parent.verticalCenter
            width: slider.knob
            height: slider.knob
            radius: width / 2
            color: drag.active ? Qt.lighter(Theme.accent, 1.1) : "#F2F4F7"
            border.color: Math.abs(slider.pos) < 0.001 ? Theme.accent : "#8B93A3"
            border.width: 3
            Behavior on x { enabled: !drag.active; NumberAnimation { duration: 90 } }
        }

        property real startPos: 0
        DragHandler {
            id: drag
            target: null
            yAxis.enabled: false
            enabled: slider.enabled
            onActiveChanged: if (active) rail.startPos = slider.pos
            onTranslationChanged: {
                let p = rail.startPos + translation.x / (rail.width - slider.knob) * 2
                p = Math.max(-1, Math.min(1, p))
                if (Math.abs(p) < 0.06) p = 0            // Rastpunkt "normal"
                slider.moved(Math.pow(2, p))
            }
        }
        TapHandler {
            enabled: slider.enabled
            onDoubleTapped: slider.moved(1.0)
            onTapped: (pt) => {
                // Antippen der Bahn: in Richtung des Fingers in 0,05er-Schritten
                const kx = slider.posToX(slider.pos)
                if (Math.abs(pt.position.x - kx) < slider.knob) return
                let v = slider.value + (pt.position.x > kx ? 0.05 : -0.05)
                v = Math.max(0.5, Math.min(2.0, Math.round(v * 100) / 100))
                slider.moved(v)
            }
        }
        WheelHandler {
            enabled: slider.enabled
            onWheel: (ev) => slider.moved(Math.max(0.5, Math.min(2.0, Math.round((slider.value + (ev.angleDelta.y > 0 ? 0.01 : -0.01)) * 100) / 100)))
        }
    }
}
