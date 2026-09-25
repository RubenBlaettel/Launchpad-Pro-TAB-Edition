import QtQuick

// Miniatur der Oberfläche für die Auswahl des Farbschemas (Einstellungen › Darstellung).
// Zeigt bewusst die Farben BEIDER Modi unabhängig vom aktuell aktiven Theme.
Item {
    id: preview
    property bool dark: true
    implicitWidth: 156
    implicitHeight: 88

    readonly property color cBg: dark ? "#0A0B0F" : "#E8EBF0"
    readonly property color cBar: dark ? "#0F1116" : "#F4F5F8"
    readonly property color cPanel: dark ? "#14161C" : "#FFFFFF"
    readonly property color cLine: dark ? "#2A2F3D" : "#D8DEE7"
    readonly property color cBorder: dark ? "#262B36" : "#CBD1DA"
    readonly property color cEmpty: dark ? "#1A1D25" : "#DCE1E8"
    readonly property var pads: ["#D64DFF", "#1FD6FF", cEmpty, "#FFC61A", "#14D9A0", "#FF5252"]

    Rectangle {
        anchors.fill: parent
        radius: 10
        color: preview.cBg
        border.color: preview.cBorder
        clip: true

        Rectangle { x: 1; y: 1; width: parent.width - 2; height: 12; radius: 9; color: preview.cBar }
        Rectangle { x: 8; y: 5; width: 22; height: 4; radius: 2; color: preview.cLine }
        Rectangle { x: parent.width - 20; y: 4; width: 12; height: 6; radius: 3; color: "#E5243A" }

        Rectangle {
            x: 7; y: 19
            width: 44; height: 62
            radius: 5
            color: preview.cPanel
            Column {
                x: 6; y: 7
                spacing: 6
                Repeater {
                    model: [30, 22, 26, 18]
                    Rectangle { required property int modelData; width: modelData; height: 4; radius: 2; color: preview.cLine }
                }
            }
        }
        Grid {
            x: 58; y: 19
            columns: 3
            spacing: 4
            Repeater {
                model: preview.pads
                Rectangle {
                    required property color modelData
                    width: 27; height: 29
                    radius: 5
                    color: modelData
                }
            }
        }
    }
}
