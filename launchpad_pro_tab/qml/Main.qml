import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import QtQuick.Window

// Hauptfenster: links Verlauf + Optionen, rechts Registerkarten + Kachel-Raster.
ApplicationWindow {
    id: win
    width: Math.min(1720, Screen.desktopAvailableWidth)
    height: Math.min(1000, Screen.desktopAvailableHeight)
    minimumWidth: 1180
    minimumHeight: 700
    visible: true
    // nur beim Start ausgewertet; danach schaltet setFullscreen()
    visibility: (typeof startFullscreen !== "undefined" && startFullscreen) ? Window.FullScreen : Window.Maximized
    color: Theme.bg
    title: "TAB Soundboard" + (backend.hasProject ? "  –  " + backend.projectName : "")
    font.family: Theme.fontFamily

    property bool forceQuit: false
    property bool consentAsked: false
    readonly property bool dialogOpen: UiState.modalOpen   // irgendein Dialog / die Projektauswahl offen

    // Vollbild (Einstellungen → Darstellung, F11): Fenster und gespeicherte Einstellung gleich halten
    property int windowedVisibility: Window.Maximized      // Zustand vor dem Vollbild
    function setFullscreen(on) {
        if (on === (win.visibility === Window.FullScreen)) return
        if (on) {
            win.windowedVisibility = win.visibility === Window.Windowed ? Window.Windowed : Window.Maximized
            win.visibility = Window.FullScreen
        } else {
            win.visibility = win.windowedVisibility
        }
    }
    onVisibilityChanged: {
        // Minimieren/Ausblenden ändert nichts an der Einstellung
        const v = win.visibility
        if (v === Window.FullScreen || v === Window.Maximized || v === Window.Windowed)
            backend.setFullscreen(v === Window.FullScreen)
    }

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

    // Projekt löschen (Papierkorb in der Projektauswahl / auf der Startseite): immer mit Rückfrage;
    // ein nicht mehr vorhandenes Projekt verschwindet ohne Rückfrage aus der Liste.
    function requestDeleteProject(path, name, exists, open) {
        if (backend.showMode) return
        if (!exists) { backend.deleteProject(path); return }
        deleteProjectDialog.path = path
        deleteProjectDialog.message = "„" + name + "“ wird mit allen Audio-Kopien, Coverbildern und Bearbeitungen in den Papierkorb verschoben."
        deleteProjectDialog.detail = (open ? "Das Projekt ist gerade geöffnet: Es wird gespeichert, seine Kacheln werden gestoppt und die Registerkarte wird geschlossen.\n\n" : "")
            + "Wiederherstellen lässt es sich bei Bedarf über den Papierkorb.\n" + path
        deleteProjectDialog.open()
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
                    onDeleteRequested: (path, name, exists, open) => win.requestDeleteProject(path, name, exists, open)
                }
                EditorSection {
                    objectName: "editorSection"
                    Layout.fillWidth: true
                    dragProxy: dragProxy
                }
                MasterSection {
                    objectName: "masterSection"
                    Layout.fillWidth: true
                }
            }
        }

        // ------------------------------------------------ Registerkarten + Kachel-Raster
        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 10

            TabStrip {
                objectName: "tabStrip"
                Layout.fillWidth: true
            }

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
                    dragProxy: dragProxy
                    onMenuRequested: (i) => tileMenu.openFor(i)
                }
                WelcomeOverlay {
                    anchors.fill: parent
                    visible: !backend.hasProject
                    onNewRequested: newDialog.openFresh()
                    onOpenRequested: openDialog.open()
                    onDeleteRequested: (path, name, exists, open) => win.requestDeleteProject(path, name, exists, open)
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
                    MouseArea { anchors.fill: parent; acceptedButtons: Qt.AllButtons; hoverEnabled: true }  // nicht zur Kachel durchreichen
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
    }

    DragProxy { id: dragProxy; objectName: "dragProxy"; parent: Overlay.overlay }

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
    UpdateConsentDialog { id: consentDialog; objectName: "updateConsentDialog" }
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
        id: deleteProjectDialog
        objectName: "deleteProjectDialog"
        property string path: ""
        title: "Projekt löschen?"
        iconName: "trash"
        iconColor: Theme.danger
        confirmText: "In den Papierkorb"
        onConfirmed: backend.deleteProject(path)
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
        function onFullscreenChanged() { win.setFullscreen(backend.fullscreen) }
    }
    Connections {
        target: updater
        // Neue Version: kurzer Hinweis (nicht während einer Vorstellung) + dauerhaft der Knopf oben
        function onUpdateFound(version) {
            if (!backend.showMode)
                toasts.show("Neue Version " + version + " von TAB Soundboard ist verfügbar.", "info", "update")
        }
        // Installer/Neustart übernimmt – Projekt ist bereits gespeichert
        function onQuitRequested() { win.forceQuit = true; Qt.quit() }
    }
    // Einmalige Frage zur Update-Suche – nicht während einer Vorstellung und nicht über anderen Dialogen
    Timer {
        interval: 700
        repeat: true
        running: updater.consentPending && !win.consentAsked
        onTriggered: {
            if (!backend.showMode && !win.dialogOpen) {
                win.consentAsked = true
                consentDialog.open()
            }
        }
    }

    // ------------------------------------------------ Tastenkürzel
    Shortcut { sequences: [StandardKey.Save]; onActivated: backend.saveProject() }
    Shortcut { sequences: ["Ctrl+Shift+S"]; enabled: backend.hasProject && !backend.showMode; onActivated: projectSaveAs() }
    Shortcut { sequences: ["Ctrl+E"]; enabled: backend.hasProject && !backend.showMode; onActivated: projectSection.exportZip() }
    Shortcut { sequences: ["Ctrl+O"]; enabled: !backend.showMode; onActivated: openDialog.open() }
    Shortcut { sequences: ["Ctrl+N"]; enabled: !backend.showMode; onActivated: newDialog.openFresh() }
    Shortcut { sequences: ["Escape"]; enabled: !win.dialogOpen; onActivated: backend.stopAll() }
    Shortcut { sequences: ["F11"]; onActivated: win.setFullscreen(win.visibility !== Window.FullScreen) }
    Shortcut { sequences: ["Space"]; enabled: editor.active && !win.dialogOpen; onActivated: editor.togglePlay() }
    // Registerkarten (wie im Browser); Umschalten ist auch im Show-Modus erlaubt
    Shortcut {
        sequences: ["Ctrl+Tab", "Ctrl+PgDown"]
        enabled: !win.dialogOpen && backend.tabs.count > 1
        onActivated: backend.activateTab((backend.activeTab + 1) % backend.tabs.count)
    }
    Shortcut {
        sequences: ["Ctrl+Shift+Tab", "Ctrl+Shift+Backtab", "Ctrl+PgUp"]
        enabled: !win.dialogOpen && backend.tabs.count > 1
        onActivated: backend.activateTab((backend.activeTab - 1 + backend.tabs.count) % backend.tabs.count)
    }
    Shortcut { sequences: ["Ctrl+T"]; enabled: !backend.showMode && !win.dialogOpen; onActivated: backend.newTab() }
    Shortcut { sequences: ["Ctrl+W"]; enabled: !backend.showMode && !win.dialogOpen; onActivated: backend.closeTab(backend.activeTab) }

    function projectSaveAs() { projectSection.saveAs() }
}
