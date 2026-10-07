"""Integrationstest: echte QML-Oberfläche + Backend + Engine (ohne Soundkarte).

Spielt die wichtigsten Abläufe durch: Projekt anlegen, Kacheln belegen (Datei,
Drag & Drop, Cover inkl. ICO), abspielen, bearbeiten/schneiden/speichern,
Zwischenstand nach "Absturz" wiederherstellen, Raster verkleinern, Löschen/Rückgängig,
Speichern beim Beenden und Export.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from conftest import wait_until

QML_ERRORS: list[str] = []


def _handler(mode, context, message):
    # Nur echte QML-Fehler/Warnungen aus unseren Dateien sammeln
    if "/qml/" in (context.file or "") or ".qml" in message:
        QML_ERRORS.append(message)


@pytest.fixture(scope="module")
def ctx(qapp, tmp_path_factory):
    from PySide6.QtCore import qInstallMessageHandler

    from launchpad_pro_tab.app import create_app

    qInstallMessageHandler(_handler)
    context = create_app([sys.argv[0]], no_audio=True, use_processes=True)
    # Offscreen-Bildschirm ist nur 800×800 (kleiner als die Mindestgröße des Fensters):
    # auf eine realistische Größe bringen, sonst überdecken Meldungen die halbe Kachelfläche.
    win = context.window
    win.setProperty("visibility", 2)  # Window.Windowed
    win.setWidth(1440)
    win.setHeight(900)
    yield context
    context.dispose()
    qapp.processEvents()
    qInstallMessageHandler(None)


def _png(path: Path, color: str = "#FF00FF", size: int = 64, fmt: str | None = None) -> Path:
    from PySide6.QtGui import QColor, QImage

    img = QImage(size, size, QImage.Format.Format_ARGB32)
    img.fill(QColor(color))
    assert img.save(str(path), fmt)
    return path


def test_qml_loaded_without_errors(ctx):
    assert ctx.window is not None
    wait_until(ctx.app, lambda: False, 0.3)
    assert QML_ERRORS == []


def test_full_workflow(ctx, tmp_path, wav_file):
    app, backend = ctx.app, ctx.backend
    editor = backend.editor
    engine = backend.engine

    # --- Projekt anlegen ---------------------------------------------------
    assert backend.newProject("UI Test", str(tmp_path / "projekte"), 4)
    assert backend.hasProject and backend.gridSize == 4
    assert backend.tiles.rowCount() == 16
    root = Path(backend.projectPath)
    assert ctx.settings.last_project == str(root)

    # --- Audio zuweisen ------------------------------------------------------
    a = wav_file("eins.wav", 1.0, 440)
    b = wav_file("zwei.wav", 0.5, 550)
    c = wav_file("drei.wav", 0.5, 660)
    backend.assignAudio(0, str(a))
    assert wait_until(app, lambda: backend.tileInfo(0)["empty"] is False and not backend.runner.pending)
    assert (root / "audio" / "eins.wav").exists()
    assert backend.recentAudio.rowCount() >= 1

    # Drag & Drop mehrerer Dateien: Kachel 2 + nächste freie Kachel
    backend.dropOnTile(1, [str(b), str(c)])
    assert wait_until(app, lambda: not backend.tileInfo(1)["empty"] and not backend.tileInfo(2)["empty"])

    # Cover (PNG und ICO)
    backend.assignCover(0, str(_png(tmp_path / "cover.png")))
    backend.assignCover(1, str(_png(tmp_path / "icon.ico", "#00FFAA", 48, "ICO")))
    assert wait_until(app, lambda: backend.tileInfo(0)["cover"] and backend.tileInfo(1)["cover"])
    assert backend.tileInfo(1)["cover"].endswith(".png")
    # Cover auf leere Kachel wird abgelehnt
    backend.assignCover(5, str(tmp_path / "cover.png"))
    wait_until(app, lambda: False, 0.2)
    assert backend.tileInfo(5)["cover"] == ""

    backend.setTileColor(0, "#FF5252")
    backend.setTileTitle(0, "Donner")
    backend.setTileLoop(2, True)
    info = backend.tileInfo(0)
    assert info["color"] == "#FF5252" and info["title"] == "Donner"
    assert backend.tileInfo(2)["loop"]

    # --- Abspielen (Start/Stopp) --------------------------------------------
    backend.triggerTile(0)
    assert wait_until(app, lambda: backend.engine_key(0) in engine.snapshot and backend.activeCount == 1)
    backend.triggerTile(0)
    assert wait_until(app, lambda: backend.engine_key(0) not in engine.snapshot and backend.activeCount == 0)
    backend.triggerTile(2)  # Schleife
    assert wait_until(app, lambda: backend.engine_key(2) in engine.snapshot)
    backend.stopAll()
    assert wait_until(app, lambda: engine.snapshot == {})

    # --- Bearbeiten & Schneiden --------------------------------------------
    backend.editTile(0)
    assert wait_until(app, lambda: editor.active)
    assert editor.duration == pytest.approx(1.0, abs=0.01)
    editor.setSelStart(0.2)
    editor.setSelEnd(0.8)
    editor.setSpeed(1.25)
    editor.setGain(1.5)
    editor.play()
    assert wait_until(app, lambda: editor.position > 0.25)
    editor.pause()
    editor.save()
    assert wait_until(app, lambda: not editor.active, 30)
    tile = backend.project.data.peek(0, 0)
    assert tile.is_edited and tile.audio.startswith("audio/bearbeitet/")
    assert tile.duration == pytest.approx(0.48, abs=0.01)
    assert (root / tile.audio).exists() and (root / tile.original).exists()
    assert editor.speed == 1.0 and editor.gain == 1.0  # zurückgesetzt

    # Erneut öffnen: Parameter sind wieder da (nachträglich änderbar)
    backend.editTile(0)
    assert wait_until(app, lambda: editor.active)
    assert editor.selStart == pytest.approx(0.2, abs=1e-3)
    assert editor.speed == pytest.approx(1.25)

    # --- Absturz simulieren: Zwischenstand wird wiederhergestellt -----------
    editor.setSelEnd(0.7)
    editor.write_session(force=True)
    project_path = backend.projectPath
    from launchpad_pro_tab.core.project import Project

    backend._activate(Project.open(project_path))  # wie ein Neustart
    assert wait_until(app, lambda: editor.active)
    assert editor.selEnd == pytest.approx(0.7, abs=1e-3)
    editor.cancel()
    assert not (root / ".autosave" / "bearbeitung.json").exists()

    # --- Löschen + Rückgängig ----------------------------------------------
    backend.clearTile(1)
    assert backend.tileInfo(1)["empty"]
    backend.undoClear()
    assert wait_until(app, lambda: not backend.tileInfo(1)["empty"])

    # --- Raster verkleinern ---------------------------------------------------
    backend.assignAudio(15, str(a))  # (3,3) fällt bei 3×3 weg
    assert wait_until(app, lambda: not backend.tileInfo(15)["empty"] and not backend.runner.pending)
    assert backend.tilesLostOnResize(3) == 1
    backend.setGridSize(3)
    assert backend.gridSize == 3 and backend.tiles.rowCount() == 9
    assert backend.project.data.peek(3, 3) is None
    backend.setGridSize(5)
    assert backend.tiles.rowCount() == 25

    # --- Speichern beim Beenden -------------------------------------------
    assert backend.saveBeforeClose()
    reopened = Project.open(project_path)
    assert reopened.data.grid == 5
    assert reopened.data.peek(0, 0).title == "Donner"
    assert reopened.data.peek(0, 0).edit.speed == pytest.approx(1.25)

    # --- Export -----------------------------------------------------------
    backend.exportProject(str(tmp_path / "export.zip"))
    assert wait_until(app, lambda: (tmp_path / "export.zip").exists() and backend.busyText == "", 30)

    assert QML_ERRORS == []


# ---------------------------------------------------------------------------
# Echte Eingabeereignisse: Maus und Touch auf den Kacheln
# ---------------------------------------------------------------------------
def _find_item(root, name: str):
    """Sucht im visuellen Baum (Repeater-Delegates sind keine QObject-Kinder)."""
    if root.objectName() == name:
        return root
    for child in root.childItems():
        found = _find_item(child, name)
        if found is not None:
            return found
    return None


def _tile_center(win, index: int):
    from PySide6.QtCore import QPoint, QPointF

    item = _find_item(win.contentItem(), f"tile_{index}")
    assert item is not None
    p = item.mapToScene(QPointF(item.width() / 2, item.height() / 2))
    return QPoint(int(p.x()), int(p.y()))


def test_mouse_and_touch_interaction(ctx, tmp_path, wav_file):
    from PySide6.QtCore import QObject, Qt
    from PySide6.QtTest import QTest

    app, backend, win = ctx.app, ctx.backend, ctx.window
    engine = backend.engine
    menu = win.findChild(QObject, "tileMenu")
    assert backend.newProject("Touch Test", str(tmp_path / "projekte"), 4)
    backend.assignAudio(0, str(wav_file("t.wav", 3.0)))
    assert wait_until(app, lambda: not backend.tileInfo(0)["empty"] and not backend.runner.pending)
    wait_until(app, lambda: False, 0.3)
    pos = _tile_center(win, 0)

    # Linksklick: startet sofort, zweiter Klick stoppt
    QTest.mouseClick(win, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, pos)
    assert wait_until(app, lambda: backend.engine_key(0) in engine.snapshot, 3)
    QTest.mouseClick(win, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, pos)
    assert wait_until(app, lambda: backend.engine_key(0) not in engine.snapshot, 3)

    # Rechtsklick: Auswahlliste öffnet sich
    QTest.mouseClick(win, Qt.MouseButton.RightButton, Qt.KeyboardModifier.NoModifier, pos)
    assert wait_until(app, lambda: menu.property("opened"), 3)
    assert menu.property("tileIndex") == 0
    menu.close()
    assert wait_until(app, lambda: not menu.property("visible"), 3)
    assert backend.engine_key(0) not in engine.snapshot  # Rechtsklick spielt nicht ab

    # Touch: kurzes Tippen spielt ab
    touch = QTest.createTouchDevice()
    QTest.touchEvent(win, touch).press(0, pos, win).commit()
    wait_until(app, lambda: False, 0.08)
    QTest.touchEvent(win, touch).release(0, pos, win).commit()
    assert wait_until(app, lambda: backend.engine_key(0) in engine.snapshot, 3)
    backend.stopAll()
    assert wait_until(app, lambda: engine.snapshot == {}, 3)

    # Touch: lange drücken öffnet die Auswahlliste (und spielt nicht ab)
    QTest.touchEvent(win, touch).press(0, pos, win).commit()
    assert wait_until(app, lambda: menu.property("opened"), 3)
    QTest.touchEvent(win, touch).release(0, pos, win).commit()
    wait_until(app, lambda: False, 0.2)
    assert backend.engine_key(0) not in engine.snapshot
    menu.close()
    assert wait_until(app, lambda: not menu.property("visible"), 3)

    # Leere Kachel antippen öffnet die Auswahlliste zum Belegen
    empty_pos = _tile_center(win, 5)
    QTest.touchEvent(win, touch).press(0, empty_pos, win).commit()
    wait_until(app, lambda: False, 0.08)
    QTest.touchEvent(win, touch).release(0, empty_pos, win).commit()
    assert wait_until(app, lambda: menu.property("opened") and menu.property("tileIndex") == 5, 3)
    menu.close()
    assert wait_until(app, lambda: not menu.property("visible"), 3)

    # Show-Modus: Berühren löst sofort aus (noch vor dem Loslassen), kein Menü
    backend.setShowMode(True)
    QTest.touchEvent(win, touch).press(0, pos, win).commit()
    assert wait_until(app, lambda: backend.engine_key(0) in engine.snapshot, 3)
    wait_until(app, lambda: False, 0.8)
    assert not menu.property("opened")
    QTest.touchEvent(win, touch).release(0, pos, win).commit()
    backend.setShowMode(False)
    backend.stopAll()
    assert wait_until(app, lambda: engine.snapshot == {}, 3)
    assert QML_ERRORS == []


def test_long_press_menu_survives_system_right_click(ctx, tmp_path, wav_file):
    """Windows macht aus „Gedrückt halten“ beim Loslassen einen Rechtsklick an der Fingerposition –
    das per langem Drücken geöffnete Kachel-Menü darf davon nicht wieder zugehen."""
    from PySide6.QtCore import QEvent, QObject, QPointF, Qt
    from PySide6.QtGui import QMouseEvent
    from PySide6.QtTest import QTest

    from launchpad_pro_tab.system import integration

    app, backend, win = ctx.app, ctx.backend, ctx.window
    menu = win.findChild(QObject, "tileMenu")
    assert backend.newProject("Gedrückt halten", str(tmp_path / "projekte"), 4)
    backend.assignAudio(15, str(wav_file("halten.wav", 1.0)))
    assert wait_until(app, lambda: not backend.tileInfo(15)["empty"] and not backend.runner.pending)
    wait_until(app, lambda: False, 0.3)
    pos = _tile_center(win, 15)                         # rechts unten – liegt neben dem Menü
    touch = QTest.createTouchDevice()

    def right_click(source, *device):
        for typ, buttons in ((QEvent.Type.MouseButtonPress, Qt.MouseButton.RightButton),
                             (QEvent.Type.MouseButtonRelease, Qt.MouseButton.NoButton)):
            app.sendEvent(win, QMouseEvent(typ, QPointF(pos), QPointF(pos), QPointF(win.mapToGlobal(pos)),
                                           Qt.MouseButton.RightButton, buttons, Qt.KeyboardModifier.NoModifier,
                                           source, *device))
        wait_until(app, lambda: False, 0.3)

    QTest.touchEvent(win, touch).press(0, pos, win).commit()
    assert wait_until(app, lambda: menu.property("opened"), 3)
    wait_until(app, lambda: False, 1.0)                 # Finger bleibt noch liegen
    QTest.touchEvent(win, touch).release(0, pos, win).commit()
    right_click(Qt.MouseEventSource.MouseEventSynthesizedBySystem)            # wie Windows
    right_click(Qt.MouseEventSource.MouseEventNotSynthesized, touch)          # vom Touch-Gerät
    assert menu.property("visible") and menu.property("tileIndex") == 15

    # Ein echter Rechtsklick mit der Maus neben das Menü schließt es weiterhin
    QTest.mouseClick(win, Qt.MouseButton.RightButton, Qt.KeyboardModifier.NoModifier, pos)
    assert wait_until(app, lambda: not menu.property("visible"), 3)
    assert backend.engine_key(15) not in backend.engine.snapshot
    assert integration.disable_press_and_hold(0) is False  # ohne Fenster: nichts zu tun
    assert QML_ERRORS == []


def _center(win, name):
    from PySide6.QtCore import QPoint, QPointF

    item = _find_item(win.contentItem(), name)
    assert item is not None, name
    p = item.mapToScene(QPointF(item.width() / 2, item.height() / 2))
    return QPoint(int(p.x()), int(p.y()))


def test_theme_switching(ctx):
    from PySide6.QtCore import QObject, Qt
    from PySide6.QtGui import QColor
    from PySide6.QtTest import QTest

    from launchpad_pro_tab.bridge import appearance

    app, backend, win = ctx.app, ctx.backend, ctx.window
    assert backend.themeMode == "dark" and backend.darkTheme
    assert win.property("color") == QColor("#0A0B0F")

    backend.setThemeMode("light")
    wait_until(app, lambda: False, 0.2)
    assert not backend.darkTheme and ctx.settings.theme == "light"
    assert win.property("color") == QColor("#E8EBF0")
    backend.toggleTheme()
    assert backend.darkTheme and backend.themeMode == "dark"
    backend.setThemeMode("unsinn")                      # wird ignoriert
    assert backend.themeMode == "dark"
    backend.setThemeMode("system")
    assert backend.darkTheme == appearance.system_prefers_dark()

    # Umschalten per Klick in den Einstellungen (Reiter „Darstellung“)
    dlg = win.findChild(QObject, "settingsDialog")
    dlg.setProperty("page", 0)
    dlg.open()
    assert wait_until(app, lambda: dlg.property("opened"), 3)
    wait_until(app, lambda: False, 0.3)
    QTest.mouseClick(win, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, _center(win, "themeCard_light"))
    assert wait_until(app, lambda: backend.themeMode == "light", 3)
    QTest.mouseClick(win, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, _center(win, "themeCard_dark"))
    assert wait_until(app, lambda: backend.themeMode == "dark", 3)
    for page in range(4):                               # alle Reiter ohne QML-Fehler
        dlg.setProperty("page", page)
        wait_until(app, lambda: False, 0.1)
    dlg.close()
    assert wait_until(app, lambda: not dlg.property("visible"), 3)
    assert QML_ERRORS == []


def test_update_notice_and_dialog(ctx):
    from datetime import datetime, timezone

    from PySide6.QtCore import QObject

    from launchpad_pro_tab.update.install import InstallKind
    from launchpad_pro_tab.update.releases import Asset, Release
    from launchpad_pro_tab.update.version import parse_version

    app, backend, win = ctx.app, ctx.backend, ctx.window
    updater = backend.updater
    pill = _find_item(win.contentItem(), "updatePill")
    assert pill is not None and not pill.isVisible()

    release = Release(parse_version("99.0.0"), "v99.0.0", "Launchpad Pro 99", "## Neu\n\n- Alles besser",
                      "https://example.invalid/v99", datetime(2026, 10, 1, tzinfo=timezone.utc), False,
                      [Asset("LaunchpadProTAB-Setup-99.0.0.exe", "https://example.invalid/s.exe", 1000, "0" * 64)])
    updater._kind = InstallKind.WINDOWS_INSTALLER
    updater._manual = False
    updater._checked([release])
    wait_until(app, lambda: False, 0.3)
    assert updater.available and updater.canInstall and updater.latestVersion == "99.0.0"
    assert pill.isVisible()

    dlg = win.findChild(QObject, "updateDialog")
    dlg.open()
    assert wait_until(app, lambda: dlg.property("opened"), 3)
    button = _find_item(win.contentItem(), "installUpdateButton")
    assert button is not None and button.isEnabled()
    backend.setShowMode(True)                           # während der Vorstellung gesperrt
    wait_until(app, lambda: False, 0.1)
    assert not button.isEnabled()
    backend.setShowMode(False)
    dlg.close()
    assert wait_until(app, lambda: not dlg.property("visible"), 3)

    updater.skipVersion()
    wait_until(app, lambda: False, 0.2)
    assert not updater.available and not pill.isVisible()
    assert QML_ERRORS == []


# ---------------------------------------------------------------------------
# Registerkarten, Projektauswahl, Kacheln verschieben, Durchklick-Schutz
# ---------------------------------------------------------------------------
def _role(model, row: int, name: str):
    roles = {bytes(v).decode(): k for k, v in model.roleNames().items()}
    return model.data(model.index(row, 0), roles[name])


def _items(root, cls_prefix: str, out=None):
    """Alle sichtbaren Items, deren QML-Typ mit ``cls_prefix`` beginnt (inkl. Pop-up-Inhalte)."""
    out = [] if out is None else out
    if root.metaObject().className().startswith(cls_prefix) and root.isVisible():
        out.append(root)
    for child in root.childItems():
        _items(child, cls_prefix, out)
    return out


def _center_of(item):
    from PySide6.QtCore import QPoint, QPointF

    p = item.mapToScene(QPointF(item.width() / 2, item.height() / 2))
    return QPoint(int(p.x()), int(p.y()))


def _tile_under(win, pt, count: int):
    from PySide6.QtCore import QPointF

    for i in range(count):
        item = _find_item(win.contentItem(), f"tile_{i}")
        p0 = item.mapToScene(QPointF(0, 0))
        if p0.x() <= pt.x() <= p0.x() + item.width() and p0.y() <= pt.y() <= p0.y() + item.height():
            return i
    return None


def _glide(app, move, start, end, steps: int = 24):
    """Zeiger/Finger in kleinen Schritten von ``start`` nach ``end`` bewegen."""
    from PySide6.QtCore import QPoint

    for i in range(1, steps + 1):
        move(QPoint(start.x() + (end.x() - start.x()) * i // steps, start.y() + (end.y() - start.y()) * i // steps))
        wait_until(app, lambda: False, 0.012)


def test_project_tabs(ctx, tmp_path, wav_file):
    from launchpad_pro_tab.core.project import Project

    app, backend, settings = ctx.app, ctx.backend, ctx.settings
    engine, tabs = backend.engine, backend.tabs
    root = tmp_path / "projekte"
    assert backend.newProject("Tab A", str(root), 4)
    path_a, index_a = backend.projectPath, backend.activeTab
    backend.assignAudio(0, str(wav_file("a.wav", 3.0)))
    assert wait_until(app, lambda: not backend.tileInfo(0)["empty"] and not backend.runner.pending)
    backend.setTileLoop(0, True)
    count = tabs.rowCount()

    # Neues Projekt öffnet sich in einer eigenen Registerkarte
    assert backend.newProject("Tab B", str(root), 3)
    assert tabs.rowCount() == count + 1 and backend.activeTab == index_a + 1
    assert backend.projectName == "Tab B" and backend.gridSize == 3 and backend.tiles.rowCount() == 9

    # Kachel in A läuft weiter, während B sichtbar ist (wie ein Browser-Tab)
    backend.activateTab(index_a)
    assert backend.projectName == "Tab A" and backend.gridSize == 4
    backend.triggerTile(0)
    key_a = backend.engine_key(0)
    assert wait_until(app, lambda: key_a in engine.snapshot, 3)
    backend.activateTab(index_a + 1)
    wait_until(app, lambda: False, 0.3)
    assert key_a in engine.snapshot and backend.activeCount == 1
    assert _role(tabs, index_a, "playing") == 1 and not _role(tabs, index_a, "active")

    # Schon offenes Projekt öffnen -> nur zu seiner Karte wechseln
    assert backend.openProject(path_a)
    assert backend.activeTab == index_a and tabs.rowCount() == count + 1
    recent = backend.recentProjects
    rows = {_role(recent, i, "name"): i for i in range(recent.rowCount())}
    assert _role(recent, rows["Tab A"], "current") and _role(recent, rows["Tab A"], "open")
    assert _role(recent, rows["Tab B"], "open") and not _role(recent, rows["Tab B"], "current")
    assert path_a in settings.open_projects and settings.last_project == path_a

    # Karte schließen: speichert, blendet ihre Kacheln aus
    backend.closeTab(index_a)
    assert wait_until(app, lambda: key_a not in engine.snapshot, 3)
    assert tabs.rowCount() == count and path_a not in settings.open_projects
    assert Project.open(path_a).data.peek(0, 0).loop

    # Leere Karte (Startseite) – es gibt höchstens eine
    backend.newTab()
    assert not backend.hasProject and backend.tiles.rowCount() == 0
    n = tabs.rowCount()
    backend.newTab()
    assert tabs.rowCount() == n

    # Alle Karten schließen -> eine leere bleibt
    for _ in range(20):
        if tabs.rowCount() == 1 and not backend.hasProject:
            break
        backend.closeTab(0)
    assert tabs.rowCount() == 1 and not backend.hasProject and settings.open_projects == []

    # Beim nächsten Start werden die Karten wiederhergestellt
    path_b = str((root / "Tab B").resolve())
    settings.open_projects = [path_a, path_b]
    settings.last_project = path_a
    backend.restore_tabs()
    assert tabs.rowCount() == 2 and backend.projectPath == path_a
    assert [_role(tabs, i, "title") for i in range(2)] == ["Tab A", "Tab B"]
    assert QML_ERRORS == []


def test_tabs_by_touch(ctx, tmp_path):
    """Touchmonitor: Antippen einer Karte holt sie nach vorne – schließen nur über das X."""
    from PySide6.QtCore import QPoint, QPointF, Qt
    from PySide6.QtTest import QTest

    app, backend, win = ctx.app, ctx.backend, ctx.window
    tabs = backend.tabs
    assert backend.newProject("Touch A", str(tmp_path), 3)
    a = backend.activeTab
    assert backend.newProject("Touch B", str(tmp_path), 3)
    b = backend.activeTab
    count = tabs.rowCount()
    touch = QTest.createTouchDevice()

    def tap(pt):
        QTest.touchEvent(win, touch).press(0, pt, win).commit()
        wait_until(app, lambda: False, 0.05)
        QTest.touchEvent(win, touch).release(0, pt, win).commit()
        wait_until(app, lambda: False, 0.3)

    def spots():
        tab = _find_item(win.contentItem(), f"tab_{a}")
        close = _find_item(win.contentItem(), f"closeTab_{a}")
        p0 = tab.mapToScene(QPointF(0, 0))
        x0 = close.mapToScene(QPointF(0, 0)).x()
        y = int(p0.y() + tab.height() / 2)
        return {"Titel": QPoint(int(p0.x() + 40), y), "Mitte": _center_of(tab), "neben dem X": QPoint(int(x0 - 6), y)}

    for name in spots():
        backend.activateTab(b)
        wait_until(app, lambda: False, 0.3)
        tap(spots()[name])
        assert tabs.rowCount() == count, f"Antippen „{name}“ hat die Karte geschlossen"
        assert backend.activeTab == a and backend.projectName == "Touch A", name

    # Das X schließt weiterhin – per Touch und die mittlere Maustaste wie im Browser
    tap(_center_of(_find_item(win.contentItem(), f"closeTab_{a}")))
    assert tabs.rowCount() == count - 1 and backend.projectName != "Touch A"
    b = next(i for i in range(tabs.rowCount()) if _role(tabs, i, "title") == "Touch B")
    wait_until(app, lambda: False, 0.3)
    QTest.mouseClick(win, Qt.MouseButton.MiddleButton, Qt.KeyboardModifier.NoModifier,
                     _center_of(_find_item(win.contentItem(), f"tab_{b}")))
    wait_until(app, lambda: False, 0.3)                   # (zuletzt bleibt eine leere Karte)
    assert all(_role(tabs, i, "title") != "Touch B" for i in range(tabs.rowCount()))
    assert QML_ERRORS == []


def test_project_picker(ctx, tmp_path):
    from PySide6.QtCore import QObject, Qt
    from PySide6.QtTest import QTest

    app, backend, win = ctx.app, ctx.backend, ctx.window
    assert backend.newProject("Auswahl 1", str(tmp_path), 3)
    first = backend.projectPath
    assert backend.newProject("Auswahl 2", str(tmp_path), 3)
    picker = win.findChild(QObject, "projectPicker")
    QTest.mouseClick(win, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, _center(win, "projectField"))
    assert wait_until(app, lambda: picker.property("opened"), 3)
    rows = [r for r in _items(win.contentItem(), "ProjectRow") if r.property("path") == first]
    assert rows and rows[0].property("open") and not rows[0].property("current")
    QTest.mouseClick(win, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, _center_of(rows[0]))
    assert wait_until(app, lambda: backend.projectPath == first and not picker.property("visible"), 3)
    assert QML_ERRORS == []


def test_delete_project(ctx, tmp_path, wav_file):
    """Projektauswahl: Papierkorb mit Rückfrage; offene Projekte werden vorher geschlossen."""
    import shutil

    from PySide6.QtCore import QObject, Qt
    from PySide6.QtTest import QTest

    app, backend, win, settings = ctx.app, ctx.backend, ctx.window, ctx.settings
    engine = backend.engine
    trash = tmp_path / "Papierkorb"
    trash.mkdir()
    trashed: list[str] = []

    def fake_trash(path):
        # wie der echte Papierkorb: scheitert (Windows), solange Dateien darin gemappt/geöffnet sind
        try:
            shutil.move(str(path), str(trash / path.name))
        except OSError:
            return False
        trashed.append(path.name)
        return True

    real_trash, backend.move_to_trash = backend.move_to_trash, fake_trash
    try:
        root = tmp_path / "projekte"
        assert backend.newProject("Weg damit", str(root), 3)
        path_a = backend.projectPath
        backend.assignAudio(0, str(wav_file("a.wav", 3.0)))
        assert wait_until(app, lambda: not backend.tileInfo(0)["empty"] and not backend.runner.pending)
        backend.setTileLoop(0, True)
        backend.triggerTile(0)
        key_a = backend.engine_key(0)
        assert wait_until(app, lambda: key_a in engine.snapshot, 3)
        backend.editTile(0)
        assert wait_until(app, lambda: backend.editor.active)
        assert backend.newProject("Bleibt", str(root), 3)
        path_b = backend.projectPath
        tabs = backend.tabs.rowCount()

        # Offenes, spielendes Projekt (Hintergrund-Karte, geparkte Bearbeitung) löschen
        assert backend.deleteProject(path_a)
        assert wait_until(app, lambda: not Path(path_a).exists(), 10)
        assert trashed == ["Weg damit"] and (trash / "Weg damit" / "projekt.lptab").exists()
        assert key_a not in engine.snapshot and backend.tabs.rowCount() == tabs - 1
        assert backend.projectPath == path_b
        assert path_a not in [p["path"] for p in settings.recent_projects]
        assert path_a not in settings.open_projects

        # Kein Projektordner / geschützter Ort: es wird nichts angefasst
        stranger = tmp_path / "Fremd"
        stranger.mkdir()
        (stranger / "brief.txt").write_text("privat", encoding="utf-8")
        assert not backend.deleteProject(str(stranger))
        assert not backend.deleteProject(str(Path.home()))
        assert (stranger / "brief.txt").exists() and trashed == ["Weg damit"]

        # Nicht mehr vorhandenes Projekt verschwindet nur aus der Liste
        gone = tmp_path / "Verschwunden"
        settings.remember_project(gone, "Verschwunden")
        backend.forgetProject("")                       # Liste neu aufbauen
        assert backend.deleteProject(str(gone.resolve()))
        assert str(gone.resolve()) not in [p["path"] for p in settings.recent_projects]

        # Show-Modus: gesperrt
        backend.setShowMode(True)
        assert not backend.deleteProject(path_b) and Path(path_b).exists()
        backend.setShowMode(False)

        # Oberfläche: Papierkorb in der Projektauswahl -> Rückfrage -> „In den Papierkorb“
        wait_until(app, lambda: False, 0.3)
        picker = win.findChild(QObject, "projectPicker")
        dialog = win.findChild(QObject, "deleteProjectDialog")
        QTest.mouseClick(win, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, _center(win, "projectField"))
        assert wait_until(app, lambda: picker.property("opened"), 3)
        row = next(r for r in _items(win.contentItem(), "ProjectRow") if r.property("path") == path_b)
        button = next(b for b in _items(row, "AppButton") if b.objectName() == "deleteProjectButton")
        QTest.mouseClick(win, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, _center_of(button))
        assert wait_until(app, lambda: dialog.property("opened") and not picker.property("visible"), 3)
        assert backend.projectPath == path_b and Path(path_b).exists()   # erst nach Bestätigung
        confirm = next(b for b in _items(win.contentItem(), "AppButton") if b.property("text") == "In den Papierkorb")
        QTest.mouseClick(win, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, _center_of(confirm))
        assert wait_until(app, lambda: not Path(path_b).exists(), 10)
        assert trashed == ["Weg damit", "Bleibt"] and backend.projectPath != path_b
        assert all(_role(backend.tabs, i, "path") != path_b for i in range(backend.tabs.rowCount()))
        assert wait_until(app, lambda: not dialog.property("visible"), 3)
    finally:
        backend.move_to_trash = real_trash
    assert QML_ERRORS == []


def test_drag_tiles_to_swap(ctx, tmp_path, wav_file):
    from PySide6.QtCore import QObject, Qt
    from PySide6.QtTest import QTest

    app, backend, win = ctx.app, ctx.backend, ctx.window
    engine = backend.engine
    menu = win.findChild(QObject, "tileMenu")
    assert backend.newProject("Verschieben", str(tmp_path / "projekte"), 4)
    backend.assignAudio(0, str(wav_file("eins.wav", 3.0, 440)))
    backend.assignAudio(1, str(wav_file("zwei.wav", 3.0, 550)))
    assert wait_until(app, lambda: not backend.tileInfo(0)["empty"] and not backend.tileInfo(1)["empty"]
                      and not backend.runner.pending)
    backend.setTileLoop(0, True)

    # Eine laufende Kachel tauschen: sie spielt am neuen Platz weiter
    backend.triggerTile(0)
    assert wait_until(app, lambda: backend.engine_key(0) in engine.snapshot, 3)
    backend.moveTile(0, 1)
    assert backend.tileInfo(0)["sourceName"] == "zwei.wav" and backend.tileInfo(1)["sourceName"] == "eins.wav"
    assert wait_until(app, lambda: backend.engine_key(1) in engine.snapshot
                      and backend.engine_key(0) not in engine.snapshot, 3)
    assert wait_until(app, lambda: _role(backend.tiles, 1, "playing") and not _role(backend.tiles, 0, "playing"), 3)
    backend.stopAll()
    assert wait_until(app, lambda: engine.snapshot == {}, 3)

    # Auf einen leeren Platz verschieben
    backend.moveTile(1, 5)
    assert backend.tileInfo(1)["empty"] and backend.tileInfo(5)["sourceName"] == "eins.wav"
    moved = backend.project.data.peek(1, 1)
    assert (moved.row, moved.col) == (1, 1) and backend.dirty
    wait_until(app, lambda: False, 0.3)

    # Echte Maus: Drücken startet sofort – beim Ziehen bricht der Ton ab, die Kacheln tauschen
    start, target = _tile_center(win, 0), _tile_center(win, 5)
    QTest.mousePress(win, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
    assert wait_until(app, lambda: backend.engine_key(0) in engine.snapshot, 3)
    _glide(app, lambda p: QTest.mouseMove(win, p), start, target)
    QTest.mouseRelease(win, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, target)
    assert wait_until(app, lambda: backend.tileInfo(5)["sourceName"] == "zwei.wav", 3)
    assert backend.tileInfo(0)["sourceName"] == "eins.wav"
    assert wait_until(app, lambda: engine.snapshot == {}, 3)

    # Touch: Ziehen verschiebt, ohne abzuspielen oder das Menü zu öffnen
    touch = QTest.createTouchDevice()
    start, target = _tile_center(win, 5), _tile_center(win, 10)
    QTest.touchEvent(win, touch).press(0, start, win).commit()
    _glide(app, lambda p: QTest.touchEvent(win, touch).move(0, p, win).commit(), start, target)
    QTest.touchEvent(win, touch).release(0, target, win).commit()
    assert wait_until(app, lambda: backend.tileInfo(10)["sourceName"] == "zwei.wav", 3)
    assert backend.tileInfo(5)["empty"] and engine.snapshot == {} and not menu.property("visible")

    # Show-Modus: Verschieben gesperrt
    backend.setShowMode(True)
    start, target = _tile_center(win, 10), _tile_center(win, 15)
    QTest.mousePress(win, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
    _glide(app, lambda p: QTest.mouseMove(win, p), start, target)
    QTest.mouseRelease(win, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, target)
    wait_until(app, lambda: False, 0.3)
    assert backend.tileInfo(10)["sourceName"] == "zwei.wav" and backend.tileInfo(15)["empty"]
    backend.setShowMode(False)
    backend.stopAll()
    assert wait_until(app, lambda: engine.snapshot == {}, 3)

    # Kartenwechsel mitten im Ziehen bricht ab – nichts wird im falschen Projekt getauscht
    here = backend.activeTab
    assert backend.newProject("Nebenkarte", str(tmp_path / "projekte"), 4)
    other = backend.activeTab
    backend.assignAudio(0, str(wav_file("neben.wav", 1.0, 700)))
    assert wait_until(app, lambda: not backend.tileInfo(0)["empty"] and not backend.runner.pending)
    backend.activateTab(here)
    wait_until(app, lambda: False, 0.3)
    start, target = _tile_center(win, 0), _tile_center(win, 1)
    QTest.mousePress(win, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
    _glide(app, lambda p: QTest.mouseMove(win, p), start, target)
    proxy = _find_item(win.contentItem(), "dragProxy")
    assert proxy.property("dragging")
    backend.activateTab(other)
    QTest.mouseRelease(win, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, target)
    wait_until(app, lambda: False, 0.3)
    assert not proxy.property("dragging") and not proxy.isVisible()           # keine hängende Miniatur
    assert backend.tileInfo(0)["sourceName"] == "neben.wav" and backend.tileInfo(1)["empty"]  # unberührt
    backend.activateTab(here)
    assert backend.tileInfo(0)["sourceName"] == "eins.wav" and backend.tileInfo(1)["empty"]
    backend.stopAll()
    assert wait_until(app, lambda: engine.snapshot == {}, 3)
    assert QML_ERRORS == []


def test_drag_tile_into_editor(ctx, tmp_path, wav_file):
    """Kachel auf „Bearbeiten & Schneiden“ ziehen öffnet sie dort (Maus und Touch)."""
    from PySide6.QtCore import QPoint, QPointF, Qt
    from PySide6.QtTest import QTest

    app, backend, win = ctx.app, ctx.backend, ctx.window
    editor, engine = backend.editor, backend.engine
    assert backend.newProject("Ziehen zum Bearbeiten", str(tmp_path / "projekte"), 4)
    backend.assignAudio(0, str(wav_file("eins.wav", 2.0, 440)))
    backend.assignAudio(1, str(wav_file("zwei.wav", 1.0, 550)))
    assert wait_until(app, lambda: not backend.tileInfo(0)["empty"] and not backend.tileInfo(1)["empty"]
                      and not backend.runner.pending)
    wait_until(app, lambda: False, 0.3)
    section = _find_item(win.contentItem(), "editorSection")
    frame = _find_item(win.contentItem(), "editorDropFrame")
    p0 = frame.mapToScene(QPointF(0, 0))
    target = QPoint(int(p0.x() + frame.width() / 2), int(p0.y() + 100))  # Wellenform (sicher im Fenster)
    assert target.y() < win.height() - 20
    touch = QTest.createTouchDevice()

    def touch_drag(index):
        start = _tile_center(win, index)
        QTest.touchEvent(win, touch).press(0, start, win).commit()
        _glide(app, lambda p: QTest.touchEvent(win, touch).move(0, p, win).commit(), start, target)
        hint = section.property("dropHint")
        QTest.touchEvent(win, touch).release(0, target, win).commit()
        wait_until(app, lambda: False, 0.3)
        return hint

    # Maus: Drücken startet die Kachel, Ziehen bricht den Ton ab, Loslassen öffnet die Bearbeitung
    start = _tile_center(win, 0)
    QTest.mousePress(win, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
    assert wait_until(app, lambda: backend.engine_key(0) in engine.snapshot, 3)
    _glide(app, lambda p: QTest.mouseMove(win, p), start, target)
    assert frame.isVisible() and section.property("dropOk")
    assert section.property("dropHint") == "Zum Bearbeiten loslassen"
    pill = _find_item(win.contentItem(), "editorDropHint")
    assert pill.isVisible() and pill.y() > frame.height() / 2      # Zeiger oben -> Hinweis unten
    QTest.mouseRelease(win, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, target)
    assert wait_until(app, lambda: editor.active, 10)
    assert editor.editsTile(0) and editor.tileLabel.startswith("Kachel 1 ")
    assert wait_until(app, lambda: backend.engine_key(0) not in engine.snapshot, 3)
    assert not frame.isVisible() and section.property("dropHint") == ""
    assert backend.tileInfo(0)["sourceName"] == "eins.wav"      # nichts verschoben

    # Dieselbe Kachel noch einmal: bleibt offen, Änderungen bleiben erhalten
    editor.setSelStart(0.5)
    assert touch_drag(0) == "Wird bereits bearbeitet"
    assert editor.active and editor.editsTile(0) and editor.selStart == pytest.approx(0.5, abs=1e-3)

    # Touch: andere Kachel ersetzt die offene Bearbeitung (Hinweis warnt davor)
    assert touch_drag(1) == "Stattdessen diese Kachel bearbeiten"
    assert wait_until(app, lambda: editor.active and editor.editsTile(1), 10)
    assert editor.tileLabel.startswith("Kachel 2 ") and editor.duration == pytest.approx(1.0, abs=0.01)
    assert backend.tileInfo(0)["sourceName"] == "eins.wav" and backend.tileInfo(1)["sourceName"] == "zwei.wav"
    assert engine.snapshot == {}
    editor.cancel()
    assert wait_until(app, lambda: not editor.active, 3)
    assert QML_ERRORS == []


def test_clicks_do_not_reach_tiles_behind_popups(ctx, tmp_path, wav_file):
    from PySide6.QtCore import Q_ARG, QMetaObject, QObject, Qt
    from PySide6.QtTest import QTest

    app, backend, win = ctx.app, ctx.backend, ctx.window
    engine = backend.engine
    assert backend.newProject("Durchklicken", str(tmp_path / "projekte"), 4)
    backend.dropOnTile(0, [str(wav_file(f"k{i}.wav", 2.0, 300 + 20 * i)) for i in range(16)])
    assert wait_until(app, lambda: all(not backend.tileInfo(i)["empty"] for i in range(16))
                      and not backend.runner.pending, 30)
    wait_until(app, lambda: False, 0.3)

    # Farbkreise im Kachel-Menü liegen über Kacheln: Klick färbt nur, startet nichts dahinter
    menu = win.findChild(QObject, "tileMenu")
    QMetaObject.invokeMethod(menu, "openFor", Q_ARG("QVariant", 0))
    assert wait_until(app, lambda: menu.property("opened"), 3)
    swatches = [s for s in _items(win.contentItem(), "QQuickRectangle")
                if abs(s.width() - 40) < 0.5 and abs(s.height() - 40) < 0.5 and s.property("radius") == 20]
    over = [s for s in swatches if _tile_under(win, _center_of(s), 16) is not None]
    assert len(over) >= 2
    QTest.mouseClick(win, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, _center_of(over[0]))
    wait_until(app, lambda: False, 0.3)
    assert engine.snapshot == {}
    assert backend.tileInfo(0)["color"].upper() == over[0].property("color").name().upper()
    touch = QTest.createTouchDevice()
    QTest.touchEvent(win, touch).press(0, _center_of(over[1]), win).commit()
    wait_until(app, lambda: False, 0.6)                   # länger als "lange drücken"
    QTest.touchEvent(win, touch).release(0, _center_of(over[1]), win).commit()
    wait_until(app, lambda: False, 0.3)
    assert engine.snapshot == {} and menu.property("tileIndex") == 0
    menu.close()
    assert wait_until(app, lambda: not menu.property("visible"), 3)

    # Hinweis-Meldungen über den Kacheln: Antippen schließt sie, die Kachel darunter bleibt stumm
    note = "Hinweis über den Kacheln"
    backend.notify(note, "info")
    wait_until(app, lambda: False, 0.3)
    texts = [t for t in _items(win.contentItem(), "QQuickText") if t.property("text") == note]
    assert texts and _tile_under(win, _center_of(texts[0]), 16) is not None
    QTest.mouseClick(win, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, _center_of(texts[0]))
    wait_until(app, lambda: False, 0.3)
    assert engine.snapshot == {}
    assert not [t for t in _items(win.contentItem(), "QQuickText") if t.property("text") == note]
    assert QML_ERRORS == []


def test_fader_tracks_follow_theme(ctx):
    from PySide6.QtGui import QColor

    app, backend, win = ctx.app, ctx.backend, ctx.window
    tracks = [_find_item(_find_item(win.contentItem(), name), "faderTrack")
              for name in ("masterSection", "editorSection")]
    assert all(t is not None for t in tracks)
    backend.setThemeMode("light")
    wait_until(app, lambda: False, 0.1)
    assert [t.property("color") for t in tracks] == [QColor("#DDE2E9")] * 2   # hellgrau im hellen Modus
    backend.setThemeMode("dark")
    wait_until(app, lambda: False, 0.1)
    assert [t.property("color") for t in tracks] == [QColor("#050506")] * 2


def test_fullscreen_switch(ctx):
    from PySide6.QtCore import QObject, Qt
    from PySide6.QtGui import QWindow
    from PySide6.QtTest import QTest

    from launchpad_pro_tab.core.settings import AppSettings

    app, backend, win = ctx.app, ctx.backend, ctx.window
    full, windowed = QWindow.Visibility.FullScreen, QWindow.Visibility.Windowed
    size = (win.width(), win.height())
    assert win.visibility() == windowed and not backend.fullscreen

    # Schalter in Einstellungen → Darstellung
    dlg = win.findChild(QObject, "settingsDialog")
    dlg.setProperty("page", 0)
    dlg.open()
    assert wait_until(app, lambda: dlg.property("opened"), 3)
    wait_until(app, lambda: False, 0.3)
    switch = _find_item(win.contentItem(), "fullscreenSwitch")
    assert switch is not None and switch.isVisible() and not switch.property("checked")
    QTest.mouseClick(win, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, _center_of(switch))
    assert wait_until(app, lambda: win.visibility() == full, 3)
    assert backend.fullscreen and switch.property("checked")
    assert AppSettings.load(ctx.settings._path).fullscreen is True           # für den nächsten Start gemerkt
    wait_until(app, lambda: False, 0.3)                                     # Dialog neu zentriert
    QTest.mouseClick(win, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, _center_of(switch))
    assert wait_until(app, lambda: win.visibility() == windowed, 3)         # vorheriger Fensterzustand
    assert not backend.fullscreen and not switch.property("checked") and not ctx.settings.fullscreen
    dlg.close()
    assert wait_until(app, lambda: not dlg.property("visible"), 3)

    # F11 und das Fenstersystem schalten mit – der Schalter zeigt immer den echten Zustand
    QTest.keyClick(win, Qt.Key.Key_F11)
    assert wait_until(app, lambda: win.visibility() == full, 3)
    assert backend.fullscreen and switch.property("checked")
    win.showNormal()
    assert wait_until(app, lambda: not backend.fullscreen, 3) and not switch.property("checked")
    win.showMinimized()                                                     # Minimieren ändert nichts
    wait_until(app, lambda: False, 0.2)
    assert not backend.fullscreen
    win.showNormal()
    wait_until(app, lambda: False, 0.2)                                     # Fenstersystem meldet nach

    # --fullscreen gilt nur für diesen Start, die gespeicherte Einstellung bleibt
    backend.start_fullscreen()
    assert wait_until(app, lambda: win.visibility() == full, 3)
    assert not ctx.settings.fullscreen
    backend.setFullscreen(False)
    assert wait_until(app, lambda: win.visibility() == windowed, 3)
    win.setWidth(size[0])
    win.setHeight(size[1])
    wait_until(app, lambda: False, 0.2)
    assert (win.width(), win.height()) == size
    assert QML_ERRORS == []


def test_update_consent_question(ctx):
    """Beim ersten Start fragt das Programm, ob es nach Updates suchen darf (nie im Show-Modus)."""
    from PySide6.QtCore import QObject, Qt
    from PySide6.QtTest import QTest

    app, backend, win = ctx.app, ctx.backend, ctx.window
    updater = backend.updater
    dlg = win.findChild(QObject, "updateConsentDialog")
    assert ctx.settings.update_check is None and not updater.consentPending

    backend.setShowMode(True)
    updater.start(delay_ms=10)
    assert wait_until(app, lambda: updater.consentPending, 3)
    wait_until(app, lambda: False, 1.2)
    assert not dlg.property("visible")                  # nicht während der Vorstellung
    backend.setShowMode(False)
    assert wait_until(app, lambda: dlg.property("opened"), 5)
    wait_until(app, lambda: False, 0.3)
    QTest.mouseClick(win, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, _center(win, "consentYesButton"))
    assert wait_until(app, lambda: ctx.settings.update_check is True, 3)
    assert wait_until(app, lambda: not dlg.property("visible"), 3)
    assert not updater.consentPending and updater.autoCheck
    wait_until(app, lambda: updater.state in ("idle", "uptodate", "available"), 5)   # Test-URL: kein Netz
    assert QML_ERRORS == []


def test_settings_in_store_version(ctx, monkeypatch):
    """Store-Fassung: Updates-Reiter zeigt den Store statt der eigenen Update-Suche."""
    from PySide6.QtCore import QObject, Qt
    from PySide6.QtTest import QTest

    from launchpad_pro_tab.update.install import InstallKind

    app, backend, win = ctx.app, ctx.backend, ctx.window
    updater = backend.updater
    original = InstallKind(updater.installKind)
    opened = []
    monkeypatch.setattr("launchpad_pro_tab.bridge.updater.QDesktopServices.openUrl",
                        lambda url: opened.append(url.toString()) or True)
    dlg = win.findChild(QObject, "settingsDialog")
    try:
        updater.set_install_kind(InstallKind.MS_STORE)
        dlg.setProperty("page", 2)
        dlg.open()
        assert wait_until(app, lambda: dlg.property("opened"), 3)
        wait_until(app, lambda: False, 0.3)
        root = win.contentItem()
        assert _find_item(root, "storeUpdateText").isVisible()
        assert not _find_item(root, "checkUpdatesButton").isVisible()
        assert not _find_item(root, "autoCheckSwitch").isVisible()
        QTest.mouseClick(win, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
                         _center(win, "storeUpdatesButton"))
        assert wait_until(app, lambda: opened == ["ms-windows-store://downloadsandupdates"], 3)

        updater.set_install_kind(original)               # zurück: eigene Update-Suche sichtbar
        wait_until(app, lambda: False, 0.2)
        assert _find_item(root, "checkUpdatesButton").isVisible()
        assert not _find_item(root, "storeUpdateText").isVisible()
    finally:
        updater.set_install_kind(original)
        dlg.close()
        assert wait_until(app, lambda: not dlg.property("visible"), 3)
    assert QML_ERRORS == []
