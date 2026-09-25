"""Bedient die echte Anwendung automatisch und erzeugt die Screenshots für die README.

Aufruf (Linux ohne Bildschirm):

    xvfb-run -a -s "-screen 0 1920x1080x24" python tools/make_screenshots.py

Unter Windows/macOS einfach ``python tools/make_screenshots.py``. Die Bilder landen in
``docs/images/``. Es wird ein temporäres Demo-Projekt mit synthetischen Klängen angelegt;
eigene Projekte und Einstellungen bleiben unberührt.
"""

from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

OUT = ROOT / "docs" / "images"


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="lptab-shots-"))
    os.environ["LPTAB_CONFIG_DIR"] = str(tmp / "config")
    os.environ["LPTAB_PROJECTS_DIR"] = str(tmp / "Projekte")
    OUT.mkdir(parents=True, exist_ok=True)

    from PySide6.QtCore import Q_ARG, QEventLoop, QMetaObject, QObject, QPointF, QRect, QTimer

    import demo_assets
    from launchpad_pro_tab.app import create_app

    ctx = create_app([sys.argv[0]], no_audio=True)
    app, backend, win = ctx.app, ctx.backend, ctx.window
    editor = backend.editor
    win.showNormal()
    win.setWidth(1920)
    win.setHeight(1080)
    win.setX(0)
    win.setY(0)

    def wait(ms: int) -> None:
        end = time.monotonic() + ms / 1000
        while time.monotonic() < end:
            app.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 20)
            time.sleep(0.005)

    def wait_until(cond, timeout: float = 30.0) -> bool:
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            app.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 20)
            if cond():
                return True
            time.sleep(0.01)
        return False

    def grab(name: str, crop: str | None = None, margin: int = 0) -> None:
        wait(350)
        img = win.grabWindow()
        if crop:
            item = win.findChild(QObject, crop)
            p = item.mapToScene(QPointF(0, 0))
            r = QRect(int(p.x()) - margin, int(p.y()) - margin, int(item.width()) + 2 * margin, int(item.height()) + 2 * margin)
            img = img.copy(r)
        img.save(str(OUT / name))
        print("gespeichert:", OUT / name, img.width(), "x", img.height())

    def call(obj_name: str, method: str, *args) -> None:
        obj = win.findChild(QObject, obj_name)
        qargs = [Q_ARG("QVariant", a) for a in args]
        QMetaObject.invokeMethod(obj, method, *qargs)

    wait(800)
    grab("01_start.png")

    # ------------------------------------------------------------------ Demo-Projekt
    media = tmp / "Medien"
    sounds = demo_assets.write_sounds(media)
    covers = demo_assets.write_covers(media / "Cover")
    backend.newProject("Sommerstück 2026", str(tmp / "Projekte"), 5)
    wait(300)
    layout = [
        # index, datei, farbe, titel, schleife, cover
        (0, "Ouvertüre.flac", "#D64DFF", "Ouvertüre", False, None),
        (1, "Regen (Loop).ogg", "#1FD6FF", "Regen", True, "Regen"),
        (2, "Donner.wav", "#3D8BFF", "Donner", False, "Donner"),
        (3, "Wind.mp3", "#14D9A0", "Wind", True, None),
        (5, "Türklingel.wav", "#FFC61A", "Türklingel", False, None),
        (6, "Telefon.ogg", "#FF8A1F", "Telefon Akt 2", False, None),
        (7, "Kirchenglocke.mp3", "#FF8A1F", "Kirchenglocke", False, "Glocke"),
        (10, "Walzer.flac", "#7A5CFF", "Walzer (Ballszene)", False, "Walzer"),
        (11, "Applaus.mp3", "#2EE66E", "Applaus", False, "Applaus"),
        (12, "Pausengong.wav", "#E6E9F0", "Pausengong", False, None),
        (15, "Donner.wav", "#FF5252", "Donnerschlag laut", False, None),
        (16, "Ouvertüre.flac", "#FF4FA3", "Finale", False, None),
    ]
    backend.addRecentFiles([str(p) for p in sounds.values()])
    for idx, fname, color, title, loop, cover in layout:
        backend.assignAudio(idx, str(sounds[fname]))
    wait_until(lambda: backend.runner.pending == 0, 60)
    wait(300)
    for idx, fname, color, title, loop, cover in layout:
        backend.setTileColor(idx, color)
        backend.setTileTitle(idx, title)
        if loop:
            backend.setTileLoop(idx, True)
        if cover:
            backend.assignCover(idx, str(covers[cover]))
    wait_until(lambda: backend.runner.pending == 0, 30)
    wait(500)

    # Bearbeitung vorbereiten (Ouvertüre gekürzt, schneller, lauter) und speichern
    backend.editTile(16)
    wait_until(lambda: editor.active, 20)
    editor.setSelStart(6.0)
    editor.setSelEnd(34.0)
    editor.setSpeed(1.12)
    editor.setGain(1.25)
    editor.save()
    wait_until(lambda: not editor.active, 30)
    wait(500)

    # Laufende Kacheln + aktiver Editor für die Hauptansicht
    backend.triggerTile(1)
    backend.triggerTile(10)
    wait(2600)
    backend.editTile(0)
    wait_until(lambda: editor.active, 20)
    editor.setSelStart(3.4)
    editor.setSelEnd(36.8)
    editor.setSpeed(1.25)
    editor.setGain(1.41)
    editor.seek(9.0)
    editor.play()
    wait(1500)
    grab("02_hauptansicht.png")
    grab("06_bearbeiten.png", crop="editorSection", margin=6)
    grab("07_master.png", crop="masterSection", margin=6)
    grab("08_raster.png", crop="tileGrid", margin=10)

    # Heller Modus (gleiche Situation)
    backend.setThemeMode("light")
    wait(600)
    grab("12_hauptansicht_hell.png")
    grab("13_bearbeiten_hell.png", crop="editorSection", margin=6)
    call("tileMenu", "openFor", 10)
    grab("14_kachelmenue_hell.png")
    call("tileMenu", "close")
    wait(300)
    backend.setThemeMode("dark")
    wait(300)
    editor.pause()

    call("tileMenu", "openFor", 10)
    grab("03_kachelmenue.png")
    call("tileMenu", "close")
    wait(300)

    call("newDialog", "openFresh")
    grab("04_neues_projekt.png")
    call("newDialog", "close")
    wait(300)

    call("openDialog", "open")
    grab("10_projekt_oeffnen.png")
    call("openDialog", "close")
    wait(300)

    call("settingsDialog", "openPage", 0)
    grab("11_einstellungen.png")
    call("settingsDialog", "close")
    wait(300)

    QMetaObject.invokeMethod(win, "requestGridSize", Q_ARG("QVariant", 3))
    grab("05_raster_verkleinern.png")
    call("shrinkDialog", "close")
    wait(300)

    backend.setShowMode(True)
    backend.stopAll()
    wait(400)
    backend.triggerTile(2)
    backend.triggerTile(12)
    wait(1200)
    grab("09_show_modus.png")
    backend.setShowMode(False)

    # ------------------------------------------------------------------ Update-Hinweis
    # Simuliertes Release 1.2.0 (keine Netzwerkverbindung nötig), Darstellung wie unter Windows
    from datetime import datetime, timezone

    from launchpad_pro_tab.update.install import InstallKind
    from launchpad_pro_tab.update.releases import Asset, Release
    from launchpad_pro_tab.update.version import parse_version

    notes = (
        "## Neu in 1.2.0\n\n"
        "- **Cue-Liste:** Kacheln in eine feste Reihenfolge bringen und mit der Leertaste weiterschalten\n"
        "- **Fade-in/Fade-out** je Kachel einstellbar\n"
        "- Exklusiv-Gruppen: eine Kachel stoppt automatisch die anderen der Gruppe\n\n"
        "## Verbesserungen\n\n"
        "- Schnelleres Laden großer Projekte\n"
        "- Behoben: Coverbild wurde nach dem Umbenennen nicht aktualisiert\n"
    )
    release = Release(
        version=parse_version("1.2.0"), tag="v1.2.0", title="Launchpad Pro TAB Edition 1.2.0", notes=notes,
        html_url="https://github.com/RubenBlaettel/Launchpad-Pro-TAB-Edition/releases/tag/v1.2.0",
        published=datetime(2026, 10, 12, 18, 0, tzinfo=timezone.utc), prerelease=False,
        assets=[Asset("LaunchpadProTAB-Setup-1.2.0.exe", "https://example.invalid/setup.exe", 118_400_000, "0" * 64)],
    )
    # Einmalige Frage beim ersten Start (automatische Update-Suche nur mit Zustimmung)
    call("updateConsentDialog", "open")
    grab("18_update_frage.png")
    call("updateConsentDialog", "close")
    wait(300)

    updater = backend.updater
    updater._kind = InstallKind.WINDOWS_INSTALLER
    updater._manual = False
    updater._checked([release])
    wait(700)
    grab("15_update_hinweis.png")
    call("updateDialog", "open")
    grab("16_update_dialog.png")
    call("updateDialog", "close")
    wait(300)
    updater.setAutoCheck(True)                          # Zustand nach „Ja, automatisch suchen“
    call("settingsDialog", "openPage", 2)
    grab("17_einstellungen_updates.png")
    call("settingsDialog", "close")
    wait(300)

    editor.cancel()
    backend.stopAll()
    wait(300)
    ctx.dispose()
    QTimer.singleShot(0, app.quit)
    app.exec()
    print("Fertig. Temporäre Daten:", tmp)
    return 0


if __name__ == "__main__":
    sys.exit(main())
