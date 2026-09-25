import QtQuick
import QtQuick.Shapes

// Kleiner Lade-Kreisel.
Item {
    id: spinner
    property int size: 28
    property bool running: true
    property color color: Theme.accent
    width: size
    height: size
    visible: running

    Shape {
        anchors.fill: parent
        preferredRendererType: Shape.CurveRenderer
        RotationAnimator on rotation {
            running: spinner.running && spinner.visible
            from: 0; to: 360
            duration: 900
            loops: Animation.Infinite
        }
        ShapePath {
            strokeColor: spinner.color
            strokeWidth: Math.max(2, spinner.size / 9)
            fillColor: "transparent"
            capStyle: ShapePath.RoundCap
            PathAngleArc {
                centerX: spinner.size / 2; centerY: spinner.size / 2
                radiusX: spinner.size / 2 - 3; radiusY: radiusX
                startAngle: 0; sweepAngle: 270
            }
        }
    }
}
