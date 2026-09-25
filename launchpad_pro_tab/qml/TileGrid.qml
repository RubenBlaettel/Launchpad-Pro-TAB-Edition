import QtQuick

// Das Kachel-Raster (3×3 bis 7×7), quadratische Kacheln, zentriert.
Item {
    id: area
    signal menuRequested(int index)

    readonly property int n: Math.max(1, backend.gridSize)
    readonly property real gap: n >= 6 ? 10 : 14
    readonly property real cell: Math.floor(Math.min((width - (n - 1) * gap) / n, (height - (n - 1) * gap) / n))

    Grid {
        id: grid
        anchors.centerIn: parent
        columns: area.n
        spacing: area.gap
        visible: backend.hasProject

        Repeater {
            model: backend.tiles
            delegate: Tile {
                objectName: "tile_" + index
                width: area.cell
                height: area.cell
                onMenuRequested: (i) => area.menuRequested(i)
            }
        }
    }
}
