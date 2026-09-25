pragma Singleton
import QtQuick

// Zentrales Design-System: Farben, Abstände, Schriftgrößen.
// Dunkles Bühnen-Design (blendfrei im abgedunkelten Theatersaal).
QtObject {
    // Flächen
    readonly property color bg: "#0A0B0F"
    readonly property color bgRaised: "#0F1116"
    readonly property color panel: "#14161C"
    readonly property color card: "#1A1D25"
    readonly property color cardHover: "#222632"
    readonly property color cardPressed: "#2A2F3D"
    readonly property color field: "#0F1116"
    readonly property color border: "#262B36"
    readonly property color borderStrong: "#363D4C"

    // Text
    readonly property color text: "#EEF1F7"
    readonly property color textDim: "#A6AEBD"
    readonly property color textMute: "#6C7485"

    // Akzente
    readonly property color accent: "#14D992"       // Wellenform-Grün (Bild 1)
    readonly property color accentStrong: "#0FBF80"
    readonly property color accentSoft: "#1A14D992"
    readonly property color magenta: "#D64DFF"      // Pad-Leuchten (Bild 2)
    readonly property color danger: "#FF4D5E"
    readonly property color dangerStrong: "#E5243A"
    readonly property color warning: "#FFB547"
    readonly property color info: "#4DA3FF"
    readonly property color master: "#E8262F"       // roter Master-Fader (Bild 3)

    // Fader-Optik (angelehnt an Bild 3)
    readonly property color faderStrip: "#3B3F47"
    readonly property color faderStripLight: "#4A4F59"
    readonly property color faderTrack: "#050506"
    readonly property color faderScale: "#C9CDD4"
    readonly property color meterGreen: "#2BD96B"
    readonly property color meterYellow: "#F2C94C"
    readonly property color meterRed: "#FF3B3B"

    // Maße
    readonly property int radius: 14
    readonly property int radiusSmall: 9
    readonly property int touch: 48          // minimale Touch-Zielgröße
    readonly property int gap: 12
    readonly property int pad: 16

    // Schrift
    readonly property string fontFamily: typeof appFontFamily !== "undefined" ? appFontFamily : "Inter"
    readonly property int fontTiny: 11
    readonly property int fontSmall: 12
    readonly property int fontBody: 14
    readonly property int fontLarge: 16
    readonly property int fontTitle: 20

    function alpha(c, a) { return Qt.rgba(c.r, c.g, c.b, a) }
    function icon(name) { return Qt.resolvedUrl("icons/" + name + ".svg") }
}
