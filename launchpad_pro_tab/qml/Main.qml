import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import QtQuick.Window

// Hauptfenster: links Verlauf + Optionen, rechts das Kachel-Raster.
ApplicationWindow {
    id: win
    width: Math.min(1720, Screen.desktopAvailableWidth)
    height: Math.min(1000, Screen.desktopAvailableHeight)
    minimumWidth: 1180
    minimumHeight: 700
    visible: true
    visibility: (typeof startFullscreen !== "undefined" && startFullscreen) ? Window.FullScreen : Window.Maximized
    color: Theme.bg
    title: "Launchpad Pro TAB Edition" + (backend.hasProject ? "  –  " + backend.projectName : "")
    font.family: Theme.fontFamily

    property bool forceQuit: false
    readonly property bool dialogOpen: tileMenu.opened || newDialog.opened || openDialog.opened || settingsDialog.opened
                                       || infoDialog.opened || shrinkDialog.opened || closeFailed.opened
                                       || updateDialog.opened

    // Vor dem endgültigen Schließen das Projekt sicher speichern
    onClosing: (close) => {
        if (win.forceQuit) return
        if (!backend.saveBeforeClose()) {
            close.accepted = false
            closeFailed.open()
        }
    }

    header: TopBar {
        onGridSizeRequested: (n) => win.requestGridSize(n)
        onSettingsRequested: settingsDialog.openPage(0)
        onUpdateRequested: updateDialog.open()
    }

    function requestGridSize(n) {
        if (n === backend.gridSize) return
        if (n < backend.gridSize) {
            const lost = backend.tilesLostOnResize(n)
            shrinkDialog.targetSize = n
            shrinkDialog.message = "Das Raster wird von " + backend.gridSize + " × " + backend.gridSize + " auf " + n + " × " + n + " verkleinert."
            shrinkDialog.detail = lost > 0
                ? "Achtung, möglicher Datenverlust: " + lost + (lost === 1 ? " belegte Kachel liegt" : " belegte Kacheln liegen") + " außerhalb des neuen Rasters. Ihre Inhalte werden verworfen."
                : "Die wegfallenden Kacheln sind leer – es gehen keine Inhalte verloren."
            shrinkDialog.open()
        } else {
            backend.setGridSize(n)
        }
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 16

        // ------------------------------------------------ linke Spalte
        Flickable {
            id: leftScroll
            Layout.preferredWidth: Math.round(Math.max(480, Math.min(700, win.width * 0.36)))
            Layout.fillHeight: true
            contentWidth: width
            contentHeight: leftCol.implicitHeight
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            interactive: contentHeight > height
            ScrollBar.vertical: ScrollBar { policy: leftScroll.interactive ? ScrollBar.AsNeeded : ScrollBar.AlwaysOff }

            ColumnLayout {
                id: leftCol
                width: leftScroll.width
                height: Math.max(implicitHeight, leftScroll.height)
                spacing: 12

                RecentList {
                    objectName: "recentList"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumHeight: 150
                    dragProxy: dragProxy
                }
                ProjectSection {
                    id: projectSection
                    objectName: "projectSection"
                    Layout.fillWidth: true
                    onOpenRequested: openDialog.open()
                    onNewRequested: newDialog.openFresh()
                }
                EditorSection {
                    objectName: "editorSection"
                    Layout.fillWidth: true
                }
                MasterSection {
                    objectName: "masterSection"
                    Layout.fillWidth: true
                }
            }
        }

        // ------------------------------------------------ Kachel-Raster
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: Theme.radius
            color: Theme.bgRaised
            border.color: Theme.border

            TileGrid {
                id: tileGrid
                objectName: "tileGrid"
                anchors.fill: parent
                anchors.margins: 20
                onMenuRequested: (i) => tileMenu.openFor(i)
            }
            WelcomeOverlay {
                anchors.fill: parent
                visible: !backend.hasProject
                onNewRequested: newDialog.openFresh()
                onOpenRequested: openDialog.open()
            }
            // Hinweisleiste im Show-Modus
            Rectangle {
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.top: parent.top
                anchors.topMargin: -1
                visible: backend.showMode
                width: showRow.implicitWidth + 28
                height: 30
                radius: 8
                color: Theme.alpha(Theme.warning, 0.16)
                border.color: Theme.alpha(Theme.warning, 0.6)
                Row {
                    id: showRow
                    anchors.centerIn: parent
                    spacing: 8
                    Icon { name: "lock"; size: 14; color: Theme.warning; anchors.verticalCenter: parent.verticalCenter }
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: "Show-Modus: Kacheln lösen beim Berühren aus · Bearbeiten gesperrt"
                        color: Theme.warning
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSmall
                        font.weight: Font.DemiBold
                    }
                }
            }
            ToastHost {
                id: toasts
                anchors.fill: parent
                z: 50
                onActionTriggered: (action) => { if (action === "update") updateDialog.open() }
            }
        }
    }

    DragProxy { id: dragProxy; parent: Overlay.overlay }

    // Laufende Hintergrundaktion (Export, Kopieren …) – sperrt das ganze Fenster
    Rectangle {
        parent: Overlay.overlay
        anchors.fill: parent
        visible: backend.busyText !== ""
        color: Theme.scrimStrong
        z: 900
        Column {
            anchors.centerIn: parent
            spacing: 14
            Spinner { anchors.horizontalCenter: parent.horizontalCenter; size: 46; running: parent.parent.visible }
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: backend.busyText
                color: Theme.text
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontLarge
            }
        }
        MouseArea { anchors.fill: parent; acceptedButtons: Qt.AllButtons; hoverEnabled: true; preventStealing: true }
    }

    // ------------------------------------------------ Dialoge
    TileMenu { id: tileMenu; objectName: "tileMenu" }
    NewProjectDialog { id: newDialog; objectName: "newDialog" }
    OpenProjectDialog { id: openDialog; objectName: "openDialog" }
    SettingsDialog {
        id: settingsDialog
        objectName: "settingsDialog"
        onShowUpdateRequested: updateDialog.open()
    }
    UpdateDialog { id: updateDialog; objectName: "updateDialog" }
    InfoDialog { id: infoDialog }
    ConfirmDialog {
        id: shrinkDialog
        objectName: "shrinkDialog"
        property int targetSize: 0
        title: "Raster verkleinern?"
        confirmText: "Fortfahren"
        onConfirmed: backend.setGridSize(targetSize)
    }
    ConfirmDialog {
        id: closeFailed
        title: "Projekt konnte nicht gespeichert werden"
        message: "Beim Speichern ist ein Fehler aufgetreten. Trotzdem beenden?"
        detail: "Nicht gespeicherte Änderungen gehen dann verloren."
        confirmText: "Ohne Speichern beenden"
        onConfirmed: { win.forceQuit = true; Qt.quit() }
    }

    Connections {
        target: backend
        function onToast(message, kind, action) { toasts.show(message, kind, action) }
        function onErrorDialog(title, message) { infoDialog.show(title, message) }
    }
    Connections {
        target: updater
        // Neue Version: kurzer Hinweis (nicht während einer Vorstellung) + dauerhaft der Knopf oben
        function onUpdateFound(version) {
            if (!backend.showMode)
                toasts.show("Neue Version " + version + " von Launchpad Pro ist verfügbar.", "info", "update")
        }
        // Installer/Neustart übernimmt – Projekt ist bereits gespeichert
        function onQuitRequested() { win.forceQuit = true; Qt.quit() }
    }

    // ------------------------------------------------ Tastenkürzel
    Shortcut { sequences: [StandardKey.Save]; onActivated: backend.saveProject() }
    Shortcut { sequences: ["Ctrl+Shift+S"]; enabled: backend.hasProject && !backend.showMode; onActivated: projectSaveAs() }
    Shortcut { sequences: ["Ctrl+E"]; enabled: backend.hasProject && !backend.showMode; onActivated: projectSection.exportZip() }
    Shortcut { sequences: ["Ctrl+O"]; enabled: !backend.showMode; onActivated: openDialog.open() }
    Shortcut { sequences: ["Ctrl+N"]; enabled: !backend.showMode; onActivated: newDialog.openFresh() }
    Shortcut { sequences: ["Escape"]; enabled: !win.dialogOpen; onActivated: backend.stopAll() }
    Shortcut { sequences: ["F11"]; onActivated: win.visibility = (win.visibility === Window.FullScreen ? Window.Windowed : Window.FullScreen) }
    Shortcut { sequences: ["Space"]; enabled: editor.active && !win.dialogOpen; onActivated: editor.togglePlay() }

    function projectSaveAs() { projectSection.saveAs() }
}
