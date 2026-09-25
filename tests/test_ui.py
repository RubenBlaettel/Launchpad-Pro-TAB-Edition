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
    assert wait_until(app, lambda: (0, 0) in engine.snapshot and backend.activeCount == 1)
    backend.triggerTile(0)
    assert wait_until(app, lambda: (0, 0) not in engine.snapshot and backend.activeCount == 0)
    backend.triggerTile(2)  # Schleife
    assert wait_until(app, lambda: (0, 2) in engine.snapshot)
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
    assert wait_until(app, lambda: (0, 0) in engine.snapshot, 3)
    QTest.mouseClick(win, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, pos)
    assert wait_until(app, lambda: (0, 0) not in engine.snapshot, 3)

    # Rechtsklick: Auswahlliste öffnet sich
    QTest.mouseClick(win, Qt.MouseButton.RightButton, Qt.KeyboardModifier.NoModifier, pos)
    assert wait_until(app, lambda: menu.property("opened"), 3)
    assert menu.property("tileIndex") == 0
    menu.close()
    assert wait_until(app, lambda: not menu.property("visible"), 3)
    assert (0, 0) not in engine.snapshot  # Rechtsklick spielt nicht ab

    # Touch: kurzes Tippen spielt ab
    touch = QTest.createTouchDevice()
    QTest.touchEvent(win, touch).press(0, pos, win).commit()
    wait_until(app, lambda: False, 0.08)
    QTest.touchEvent(win, touch).release(0, pos, win).commit()
    assert wait_until(app, lambda: (0, 0) in engine.snapshot, 3)
    backend.stopAll()
    assert wait_until(app, lambda: engine.snapshot == {}, 3)

    # Touch: lange drücken öffnet die Auswahlliste (und spielt nicht ab)
    QTest.touchEvent(win, touch).press(0, pos, win).commit()
    assert wait_until(app, lambda: menu.property("opened"), 3)
    QTest.touchEvent(win, touch).release(0, pos, win).commit()
    wait_until(app, lambda: False, 0.2)
    assert (0, 0) not in engine.snapshot
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
    assert wait_until(app, lambda: (0, 0) in engine.snapshot, 3)
    wait_until(app, lambda: False, 0.8)
    assert not menu.property("opened")
    QTest.touchEvent(win, touch).release(0, pos, win).commit()
    backend.setShowMode(False)
    backend.stopAll()
    assert wait_until(app, lambda: engine.snapshot == {}, 3)
    assert QML_ERRORS == []
