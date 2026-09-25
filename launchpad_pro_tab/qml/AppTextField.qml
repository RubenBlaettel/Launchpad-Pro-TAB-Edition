import QtQuick
import QtQuick.Controls.Basic

// Eingabefeld im App-Design (48 px hoch, touch-freundlich).
TextField {
    id: field
    implicitHeight: Theme.touch
    color: Theme.text
    placeholderTextColor: Theme.textMute
    selectionColor: Theme.alpha(Theme.accent, 0.4)
    selectedTextColor: Theme.text
    font.family: Theme.fontFamily
    font.pixelSize: Theme.fontLarge
    leftPadding: 14
    rightPadding: 14
    verticalAlignment: TextInput.AlignVCenter
    background: Rectangle {
        radius: Theme.radiusSmall
        color: Theme.field
        border.width: field.activeFocus ? 2 : 1
        border.color: field.activeFocus ? Theme.accent : Theme.border
    }
}
