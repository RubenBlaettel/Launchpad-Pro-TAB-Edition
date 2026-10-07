pragma Singleton
import QtQuick

// Oberflächenzustand, den mehrere Komponenten teilen.
QtObject {
    // Anzahl sichtbarer modaler Fenster (AppDialog, Projektauswahl). Solange eines offen ist,
    // reagieren Kacheln nicht: Qt reicht Mausklicks auf TapHandler (Standard-gesturePolicy)
    // in einem Pop-up sonst an die Kachel dahinter weiter.
    property int modalCount: 0
    readonly property bool modalOpen: modalCount > 0
}
