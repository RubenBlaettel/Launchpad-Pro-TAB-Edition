import QtQuick
import QtQuick.Effects
import QtQuick.Shapes

// Eine Launchpad-Kachel.
//  • Linksklick / kurzes Tippen  -> Start/Stopp (Maus: sofort beim Drücken)
//  • Rechtsklick / lang drücken   -> Auswahlliste (Belegen, Cover, Farbe, Bearbeiten, Löschen)
//  • Drag & Drop: Audiodatei belegt die Kachel, Bild wird Coverbild
//  • Show-Modus: Touch löst bereits beim Berühren aus, Bearbeiten ist gesperrt
Item {
    id: tile

    // Rollen aus backend.tiles
    required property int index
    required property bool empty
    required property string title
    required property color tileColor
    required property string coverUrl
    required property string durationText
    required property bool loop
    required property bool playing
    required property real progress
    required property string remainingText
    required property bool loading
    required property bool edited
    required property bool missing
    required property string errorText

    signal menuRequested(int index)

    readonly property bool locked: backend.showMode
    readonly property bool hasCover: coverUrl !== "" && !empty
    readonly property real radius: Math.max(8, Math.min(18, width * 0.09))
    readonly property real lum: 0.2126 * tileColor.r + 0.7152 * tileColor.g + 0.0722 * tileColor.b
    readonly property color ink: (!hasCover && lum > 0.62) ? "#11131A" : "#FFFFFF"
    readonly property real fs: Math.max(11, Math.min(20, width * 0.085))
    property string dropHint: ""
    property real lpProgress: 0

    function trigger() {
        if (!tile.empty)
            backend.triggerTile(tile.index)
    }

    // ---------------------------------------------------------------- Leuchten
    Rectangle {
        id: glowSource
        anchors.fill: pad
        radius: tile.radius
        color: tile.tileColor
        visible: false
    }
    MultiEffect {
        id: glow
        source: glowSource
        anchors.fill: glowSource
        visible: tile.playing && !tile.empty
        autoPaddingEnabled: true
        shadowEnabled: true
        shadowColor: tile.tileColor
        shadowBlur: 1.0
        blurMax: 56
        shadowScale: 1.07
        shadowOpacity: 1.0
        SequentialAnimation on opacity {
            running: glow.visible
            loops: Animation.Infinite
            NumberAnimation { from: 1.0; to: 0.55; duration: 700; easing.type: Easing.InOutSine }
            NumberAnimation { from: 0.55; to: 1.0; duration: 700; easing.type: Easing.InOutSine }
        }
    }

    // ---------------------------------------------------------------- Pad
    Item {
        id: pad
        anchors.fill: parent
        scale: tap.pressed ? 0.955 : 1.0
        Behavior on scale { NumberAnimation { duration: 90; easing.type: Easing.OutCubic } }

        // Leere Kachel
        Rectangle {
            anchors.fill: parent
            visible: tile.empty
            radius: tile.radius
            color: hover.hovered && !tile.locked ? Theme.cardHover : "#15181F"
            border.width: 1
            border.color: tile.dropHint !== "" ? Theme.accent : Theme.border
            Column {
                anchors.centerIn: parent
                spacing: 6
                opacity: tile.locked ? 0.25 : 0.55
                Icon {
                    anchors.horizontalCenter: parent.horizontalCenter
                    name: "plus"
                    size: Math.max(16, Math.min(34, tile.width * 0.2))
                    color: Theme.textDim
                }
                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    visible: tile.width > 90
                    text: tile.locked ? "leer" : "Belegen"
                    color: Theme.textDim
                    font.family: Theme.fontFamily
                    font.pixelSize: Math.max(10, tile.fs * 0.75)
                }
            }
        }

        // Belegte Kachel: Pad-Farbe mit LED-Schimmer (Bild 2)
        Rectangle {
            id: base
            anchors.fill: parent
            visible: !tile.empty
            radius: tile.radius
            gradient: Gradient {
                GradientStop { position: 0.0; color: Qt.lighter(tile.tileColor, tile.playing ? 1.28 : 1.06) }
                GradientStop { position: 1.0; color: Qt.darker(tile.tileColor, tile.playing ? 1.05 : 1.45) }
            }
        }
        Shape {
            anchors.fill: parent
            visible: !tile.empty && !tile.hasCover
            opacity: tile.playing ? 0.75 : 0.42
            preferredRendererType: Shape.CurveRenderer
            ShapePath {
                strokeWidth: 0
                strokeColor: "transparent"
                fillGradient: RadialGradient {
                    centerX: pad.width / 2; centerY: pad.height * 0.46
                    centerRadius: pad.width * 0.62
                    focalX: centerX; focalY: centerY
                    GradientStop { position: 0.0; color: Qt.rgba(1, 1, 1, 0.55) }
                    GradientStop { position: 0.55; color: Qt.rgba(1, 1, 1, 0.08) }
                    GradientStop { position: 1.0; color: Qt.rgba(1, 1, 1, 0.0) }
                }
                PathRectangle { x: 0; y: 0; width: pad.width; height: pad.height; radius: tile.radius }
            }
        }

        // Coverbild (kachelfüllend, abgerundet maskiert)
        Image {
            id: coverImg
            anchors.fill: parent
            anchors.margins: 3
            visible: false
            source: tile.hasCover ? tile.coverUrl : ""
            fillMode: Image.PreserveAspectCrop
            asynchronous: true
            cache: true
            sourceSize: Qt.size(Math.ceil(width * 2), Math.ceil(height * 2))
        }
        Item {
            id: coverMask
            anchors.fill: coverImg
            layer.enabled: true
            visible: false
            Rectangle { anchors.fill: parent; radius: Math.max(4, tile.radius - 3); color: "black" }
        }
        MultiEffect {
            anchors.fill: coverImg
            source: coverImg
            visible: tile.hasCover && coverImg.status === Image.Ready
            maskEnabled: true
            maskSource: coverMask
            maskThresholdMin: 0.5
            maskSpreadAtMin: 1.0
            brightness: tile.playing ? 0.06 : -0.08
        }

        // Abdunklung unten für lesbare Beschriftung
        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.margins: tile.hasCover ? 3 : 0
            height: parent.height * 0.55
            radius: tile.radius
            visible: !tile.empty
            gradient: Gradient {
                GradientStop { position: 0.0; color: "transparent" }
                GradientStop { position: 1.0; color: tile.hasCover ? "#D0000000" : Qt.rgba(0, 0, 0, 0.28) }
            }
        }

        // Nummer
        Rectangle {
            x: Math.max(5, tile.width * 0.05)
            y: x
            height: Math.max(16, tile.fs * 1.15)
            width: Math.max(height, numText.implicitWidth + 10)
            radius: height / 2
            color: tile.empty ? "transparent" : Qt.rgba(0, 0, 0, 0.28)
            visible: tile.width > 64
            Text {
                id: numText
                anchors.centerIn: parent
                text: tile.index + 1
                color: tile.empty ? Theme.textMute : (tile.hasCover ? "#FFFFFF" : Qt.rgba(tile.ink.r, tile.ink.g, tile.ink.b, 0.85))
                font.family: Theme.fontFamily
                font.pixelSize: Math.max(9, tile.fs * 0.66)
                font.weight: Font.Bold
            }
        }

        // Status-Symbole oben rechts
        Row {
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.margins: Math.max(5, tile.width * 0.05)
            spacing: 4
            visible: !tile.empty
            Icon { visible: tile.loop; name: "loop"; size: Math.max(12, tile.fs * 0.9); color: tile.ink; opacity: 0.9 }
            Icon { visible: tile.edited; name: "scissors"; size: Math.max(12, tile.fs * 0.9); color: tile.ink; opacity: 0.9 }
            Icon { visible: tile.missing || tile.errorText !== ""; name: "warning"; size: Math.max(12, tile.fs * 0.95); color: Theme.warning }
        }

        // Titel + Dauer / Restzeit
        Column {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.margins: Math.max(6, tile.width * 0.07)
            anchors.bottomMargin: Math.max(10, tile.width * 0.09)
            spacing: 2
            visible: !tile.empty
            Text {
                width: parent.width
                text: tile.playing ? tile.remainingText : tile.durationText
                visible: text !== "" && tile.height > 70
                color: tile.ink
                opacity: tile.playing ? 1.0 : 0.8
                font.family: Theme.fontFamily
                font.pixelSize: tile.playing ? tile.fs * 1.05 : tile.fs * 0.72
                font.weight: tile.playing ? Font.Bold : Font.Medium
                font.features: { "tnum": 1 }
            }
            Text {
                width: parent.width
                text: tile.missing ? "Datei fehlt" : tile.title
                color: tile.ink
                font.family: Theme.fontFamily
                font.pixelSize: tile.fs
                font.weight: Font.Bold
                wrapMode: Text.Wrap
                maximumLineCount: tile.height > 110 ? 2 : 1
                elide: Text.ElideRight
                lineHeight: 0.95
                style: Qt.colorEqual(tile.ink, "#FFFFFF") ? Text.Raised : Text.Normal
                styleColor: Qt.rgba(0, 0, 0, 0.25)
            }
        }

        // Fortschrittsbalken
        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.leftMargin: tile.radius * 0.7
            anchors.rightMargin: tile.radius * 0.7
            anchors.bottomMargin: Math.max(4, tile.width * 0.035)
            height: Math.max(3, tile.width * 0.028)
            radius: height / 2
            visible: tile.playing
            color: Qt.rgba(0, 0, 0, 0.35)
            Rectangle {
                width: parent.width * Math.max(0, Math.min(1, tile.progress))
                height: parent.height
                radius: parent.radius
                color: tile.hasCover ? tile.tileColor : tile.ink
            }
        }

        // Rahmen: spielend (weiß), Cover (Kachelfarbe), Drop-Ziel (Akzent)
        Rectangle {
            anchors.fill: parent
            radius: tile.radius
            color: "transparent"
            visible: !tile.empty || tile.dropHint !== ""
            border.width: tile.dropHint !== "" ? 3 : (tile.playing ? 3 : (tile.hasCover ? 3 : 1))
            border.color: tile.dropHint !== "" ? Theme.accent
                        : tile.playing ? "#FFFFFF"
                        : tile.hasCover ? tile.tileColor
                        : Qt.rgba(1, 1, 1, 0.14)
        }

        // Laden
        Rectangle {
            anchors.fill: parent
            radius: tile.radius
            visible: tile.loading
            color: "#99000000"
            Spinner { anchors.centerIn: parent; size: Math.min(36, tile.width * 0.3); running: tile.loading }
        }

        // Drop-Hinweis
        Rectangle {
            anchors.centerIn: parent
            visible: tile.dropHint !== ""
            width: Math.min(parent.width - 12, dropText.implicitWidth + 16)
            height: dropText.implicitHeight + 10
            radius: 6
            color: "#E6000000"
            Text {
                id: dropText
                anchors.centerIn: parent
                width: Math.min(implicitWidth, tile.width - 28)
                text: tile.dropHint
                color: Theme.accent
                font.family: Theme.fontFamily
                font.pixelSize: Math.max(10, tile.fs * 0.7)
                font.weight: Font.DemiBold
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.Wrap
            }
        }

        // Hover (nur Maus)
        Rectangle {
            anchors.fill: parent
            radius: tile.radius
            visible: hover.hovered && !tile.empty
            color: Qt.rgba(1, 1, 1, 0.06)
        }
    }

    // Fortschrittsring für "lange drücken" (Touch)
    Shape {
        anchors.centerIn: parent
        width: Math.min(tile.width, tile.height) * 0.56
        height: width
        visible: tile.lpProgress > 0.25
        opacity: Math.min(1, (tile.lpProgress - 0.25) * 4)
        preferredRendererType: Shape.CurveRenderer
        ShapePath {
            strokeColor: Qt.rgba(1, 1, 1, 0.25)
            strokeWidth: 5
            fillColor: Qt.rgba(0, 0, 0, 0.35)
            PathAngleArc { centerX: width / 2; centerY: height / 2; radiusX: width / 2 - 4; radiusY: radiusX; startAngle: 0; sweepAngle: 360 }
        }
        ShapePath {
            strokeColor: "#FFFFFF"
            strokeWidth: 5
            fillColor: "transparent"
            capStyle: ShapePath.RoundCap
            PathAngleArc { centerX: width / 2; centerY: height / 2; radiusX: width / 2 - 4; radiusY: radiusX; startAngle: -90; sweepAngle: 360 * tile.lpProgress }
        }
    }
    NumberAnimation {
        id: lpAnim
        target: tile
        property: "lpProgress"
        from: 0; to: 1
        duration: 520
    }

    // ---------------------------------------------------------------- Eingabe
    HoverHandler { id: hover }

    TapHandler {
        id: tap
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        longPressThreshold: 0.5
        onPressedChanged: {
            if (pressed) {
                const isMouse = point.device.type === PointerDevice.Mouse
                if (isMouse) {
                    if (point.pressedButtons & Qt.RightButton) {
                        if (!tile.locked) tile.menuRequested(tile.index)
                    } else if (!tile.empty) {
                        tile.trigger()                        // Maus: sofort beim Drücken
                    } else if (!tile.locked) {
                        tile.menuRequested(tile.index)
                    }
                } else if (tile.locked) {
                    tile.trigger()                            // Show-Modus: sofort beim Berühren
                } else {
                    lpAnim.restart()
                }
            } else {
                lpAnim.stop()
                tile.lpProgress = 0
            }
        }
        onTapped: (eventPoint, button) => {
            if (eventPoint.device.type === PointerDevice.Mouse || tile.locked)
                return
            if (tile.empty) tile.menuRequested(tile.index)
            else tile.trigger()
        }
        onLongPressed: {
            if (point.device.type === PointerDevice.Mouse || tile.locked)
                return
            lpAnim.stop()
            tile.lpProgress = 0
            tile.menuRequested(tile.index)
        }
    }

    DropArea {
        anchors.fill: parent
        enabled: !tile.locked
        keys: ["text/uri-list"]
        function hintFor(drag) {
            let urls = drag.hasUrls ? drag.urls : []
            if (!drag.hasUrls && drag.source && drag.source.filePath)
                urls = [drag.source.filePath]
            let audio = 0, image = 0
            for (let i = 0; i < urls.length; ++i) {
                const u = String(urls[i]).toLowerCase()
                if (/\.(jpe?g|png|ico)$/.test(u)) image++
                else audio++
            }
            if (audio > 0)
                return tile.empty ? (audio > 1 ? audio + " Dateien belegen" : "Audio zuweisen") : "Audio ersetzen"
            if (image > 0)
                return tile.empty ? "Erst Audio zuweisen" : "Als Coverbild"
            return ""
        }
        onEntered: (drag) => { tile.dropHint = hintFor(drag); drag.accept(Qt.CopyAction) }
        onExited: tile.dropHint = ""
        onDropped: (drop) => {
            let urls = []
            if (drop.hasUrls) urls = drop.urls
            else if (drop.source && drop.source.filePath) urls = [drop.source.filePath]
            tile.dropHint = ""
            if (urls.length > 0) {
                backend.dropOnTile(tile.index, urls)
                drop.accept(Qt.CopyAction)
            }
        }
    }
}
