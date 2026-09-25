pragma Singleton
import QtQuick

// Zentrales Design-System: Farben, Abstände, Schriftgrößen.
// Zwei Farbwelten:
//  • Dunkel – blendfreies Bühnen-Design für den abgedunkelten Theatersaal (Standard)
//  • Hell   – für helle Räume (Proben, Vorbereitung am Schreibtisch)
// Umschalten über ``backend.setThemeMode("dark" | "light" | "system")``.
// Neue Farben immer hier für BEIDE Modi anlegen – nie feste Farbwerte in Komponenten.
QtObject {
    readonly property bool dark: typeof backend === "undefined" || !backend ? true : backend.darkTheme

    // Flächen
    readonly property color bg: dark ? "#0A0B0F" : "#E8EBF0"
    readonly property color bgRaised: dark ? "#0F1116" : "#F4F5F8"
    readonly property color panel: dark ? "#14161C" : "#FFFFFF"
    readonly property color card: dark ? "#1A1D25" : "#EEF1F5"
    readonly property color cardHover: dark ? "#222632" : "#E4E8EE"
    readonly property color cardPressed: dark ? "#2A2F3D" : "#D8DEE7"
    readonly property color field: dark ? "#0F1116" : "#F6F7FA"
    readonly property color border: dark ? "#262B36" : "#D6DBE3"
    readonly property color borderStrong: dark ? "#363D4C" : "#BDC4D0"
    readonly property color tileEmpty: dark ? "#15181F" : "#E3E7ED"
    readonly property color popup: dark ? "#F21A1D25" : "#FAFFFFFF"      // Toasts, Tooltips, Drag-Karte
    readonly property color scrim: dark ? "#B3000000" : "#66101521"      // Hintergrund hinter Dialogen
    readonly property color scrimStrong: dark ? "#B8000000" : "#D9F4F5F8" // Sperr-Overlay mit Text
    readonly property color switchOff: dark ? "#2B303B" : "#C3CAD5"

    // Text
    readonly property color text: dark ? "#EEF1F7" : "#141821"
    readonly property color textDim: dark ? "#A6AEBD" : "#465063"
    readonly property color textMute: dark ? "#6C7485" : "#687184"

    // Akzente (im hellen Modus dunkler, damit Text/Symbole auf Weiß lesbar bleiben)
    readonly property color accent: dark ? "#14D992" : "#098A5E"       // Wellenform-Grün (Bild 1)
    readonly property color accentStrong: dark ? "#0FBF80" : "#07714D"
    readonly property color onAccent: dark ? "#05140E" : "#FFFFFF"     // Text auf Akzentfläche
    readonly property color magenta: dark ? "#D64DFF" : "#A51FD1"      // Pad-Leuchten (Bild 2)
    readonly property color danger: dark ? "#FF4D5E" : "#D42536"
    readonly property color dangerStrong: dark ? "#E5243A" : "#D11F33"
    readonly property color warning: dark ? "#FFB547" : "#A65F00"
    readonly property color onWarning: dark ? "#15120A" : "#FFFFFF"
    readonly property color info: dark ? "#4DA3FF" : "#1D6FD6"
    readonly property color master: dark ? "#E8262F" : "#E0232C"       // roter Master-Fader (Bild 3)

    // Fader-Optik (angelehnt an Bild 3): Bahn bleibt in beiden Modi schwarz wie am Mischpult
    readonly property color faderStrip: dark ? "#3B3F47" : "#CBD0D8"
    readonly property color faderStripLight: dark ? "#4A4F59" : "#DDE1E7"
    readonly property color faderBorder: dark ? "#555A64" : "#AAB1BC"
    readonly property color faderTrack: dark ? "#050506" : "#17191E"
    readonly property color faderTrackBorder: dark ? "#1B1C20" : "#0E0F12"
    readonly property color faderScale: "#C9CDD4"                      // Skala auf der Bahn
    readonly property color faderText: dark ? "#FFFFFF" : "#141821"   // Anzeige unter der Bahn
    readonly property color faderTextDim: dark ? "#C9CDD4" : "#4A5263"
    readonly property color faderLabel: dark ? "#E3E6EA" : "#2A303B"

    // Pegelanzeige
    readonly property color meterBg: dark ? "#0B0C0F" : "#DDE2E9"
    readonly property color meterBorder: dark ? "#1E2128" : "#C8CFD9"
    readonly property color meterHold: dark ? "#FFFFFF" : "#141821"
    readonly property color meterGreen: dark ? "#2BD96B" : "#1DB954"
    readonly property color meterYellow: dark ? "#F2C94C" : "#E0A800"
    readonly property color meterRed: dark ? "#FF3B3B" : "#E62E2E"
    readonly property color ledOff: dark ? "#15171C" : "#E6E9EF"

    // Wellenform / Bearbeiten (Hintergrund der Wellenform selbst zeichnet WaveformView)
    readonly property color waveBg: dark ? "#000000" : "#F3F7F5"
    readonly property color overviewBg: dark ? "#0D0F13" : "#E3EAE6"
    readonly property color playhead: dark ? "#FFFFFF" : "#141821"

    // Regler & Sonstiges
    readonly property color railBg: dark ? "#0B0C10" : "#D5DBE3"
    readonly property color knob: dark ? "#F2F4F7" : "#FFFFFF"
    readonly property color knobBorder: dark ? "#8B93A3" : "#98A1B0"
    readonly property color swatchRing: dark ? "#FFFFFF" : "#141821"
    readonly property color logoBg: "#191B22"                          // Mini-Launchpad bleibt dunkel
    readonly property color logoBorder: dark ? "#2C3140" : "#191B22"

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
