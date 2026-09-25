import QtQuick

// Abgerundete Fläche mit Rahmen für die Bereiche der linken Spalte.
Rectangle {
    id: card
    default property alias content: inner.data
    property int padding: Theme.pad
    color: Theme.panel
    radius: Theme.radius
    border.color: Theme.border
    border.width: 1

    Item {
        id: inner
        anchors.fill: parent
        anchors.margins: card.padding
    }
}
