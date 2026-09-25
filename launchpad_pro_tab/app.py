"""Programmstart: Logging, Qt-Anwendung, Audio-Engine, QML-Oberfläche."""

from __future__ import annotations

import argparse
import faulthandler
import logging
import logging.handlers
import multiprocessing
import os
import sys
from pathlib import Path

from . import __app_id__, __app_name__, __organization__, __version__
from .core.paths import config_dir

PACKAGE_DIR = Path(__file__).resolve().parent
QML_DIR = PACKAGE_DIR / "qml"
FONT_DIR = PACKAGE_DIR / "assets" / "fonts"
ICON_FILE = PACKAGE_DIR / "assets" / "app_icon.png"

log = logging.getLogger("launchpad_pro_tab")
_fault_file = None


def setup_logging(verbose: bool = False) -> Path:
    global _fault_file
    log_path = config_dir() / "launchpad.log"
    root = logging.getLogger()
    root.setLevel(logging.DEBUG if verbose else logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    fh = logging.handlers.RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    fh.setFormatter(fmt)
    root.addHandler(fh)
    if sys.stderr is not None:
        sh = logging.StreamHandler()
        sh.setFormatter(fmt)
        root.addHandler(sh)
    # Native Abstürze (z. B. Treiber) ebenfalls protokollieren
    try:
        _fault_file = open(config_dir() / "absturz.log", "a", encoding="utf-8")  # noqa: SIM115
        faulthandler.enable(_fault_file)
    except OSError:
        pass

    def excepthook(exc_type, exc, tb):
        log.critical("Unbehandelter Fehler", exc_info=(exc_type, exc, tb))

    sys.excepthook = excepthook
    return log_path


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="launchpad-pro-tab", description=__app_name__)
    p.add_argument("path", nargs="?", help="Projektordner, projekt.lptab oder Export-ZIP (z. B. per Doppelklick)")
    p.add_argument("--project", help="Projektordner, projekt.lptab oder Export-ZIP öffnen")
    p.add_argument("--no-audio", action="store_true", help="ohne Soundkarte starten (stumm)")
    p.add_argument("--fullscreen", action="store_true", help="im Vollbild starten (Touch-Terminal)")
    p.add_argument("--verbose", action="store_true", help="ausführliches Protokoll")
    p.add_argument("--smoke-test", action="store_true",
                   help="Selbsttest: Oberfläche laden, kurz laufen lassen, beenden (Exit-Code 0 = OK)")
    p.add_argument("--no-update-check", action="store_true", help="beim Start nicht nach Updates suchen")
    p.add_argument("--wait-pid", type=int, default=0, help=argparse.SUPPRESS)   # nach einem Update
    p.add_argument("--purge-user-data", action="store_true",
                   help="alle Projekte und Einstellungen löschen (Deinstallation); ohne --yes nur anzeigen")
    p.add_argument("--yes", action="store_true", help="Rückfrage bei --purge-user-data überspringen")
    p.add_argument("--version", action="version", version=f"{__app_name__} {__version__}")
    args, _unknown = p.parse_known_args(argv[1:])
    return args


def load_fonts() -> str:
    from PySide6.QtGui import QFontDatabase

    family = ""
    for ttf in sorted(FONT_DIR.glob("*.ttf")):
        fid = QFontDatabase.addApplicationFont(str(ttf))
        if fid >= 0 and not family:
            fams = QFontDatabase.applicationFontFamilies(fid)
            family = fams[0] if fams else ""
    return family or "Segoe UI"


class AppContext:
    """Alle Bausteine einer laufenden Anwendung (auch für Tests/Screenshots)."""

    def __init__(self, app, qml, backend, engine, runner, settings):
        self.app = app
        self.qml = qml
        self.backend = backend
        self.engine = engine
        self.runner = runner
        self.settings = settings

    @property
    def window(self):
        roots = self.qml.rootObjects() if self.qml is not None else []
        return roots[0] if roots else None

    def handle_instance_message(self, payload: dict) -> None:
        """Zweiter Programmstart: Fenster nach vorne holen, ggf. Projekt öffnen."""
        win = self.window
        if win is not None:
            from PySide6.QtGui import QWindow

            if win.visibility() == QWindow.Visibility.Minimized:
                win.showMaximized()
            win.show()
            win.raise_()
            win.requestActivate()
        project = payload.get("project") if isinstance(payload, dict) else None
        if project and Path(project).exists():
            self.backend.openProject(project)

    def dispose(self) -> None:
        """Oberfläche vor dem Backend abbauen (sonst werten QML-Bindungen gelöschte Objekte aus)."""
        import shiboken6

        self.backend.shutdown()
        if self.qml is not None:
            win = self.window
            if win is not None:
                win.close()
            shiboken6.delete(self.qml)
            self.qml = None


def make_qapp(argv: list[str]):
    """Die (einzige) QGuiApplication anlegen bzw. die vorhandene liefern."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QGuiApplication

    app = QGuiApplication.instance()
    if app is None:
        QGuiApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
        app = QGuiApplication(argv)
    return app


def create_app(argv: list[str], *, no_audio: bool = False, fullscreen: bool = False,
               use_processes: bool = True, check_updates: bool = False) -> AppContext:
    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
    from PySide6.QtCore import QStandardPaths, QUrl
    from PySide6.QtGui import QFont, QIcon
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtQuick import QQuickWindow  # noqa: F401 – Typ für rootObjects()
    from PySide6.QtQuickControls2 import QQuickStyle

    app = make_qapp(argv)
    app.setApplicationName(__app_name__)
    app.setApplicationDisplayName(__app_name__)
    app.setOrganizationName(__organization__)
    app.setApplicationVersion(__version__)
    app.setDesktopFileName(__app_id__)
    if ICON_FILE.exists():
        app.setWindowIcon(QIcon(str(ICON_FILE)))
    QQuickStyle.setStyle("Basic")
    family = load_fonts()
    font = QFont(family)
    font.setPixelSize(14)
    font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    app.setFont(font)

    from .audio.engine import AudioEngine
    from .bridge import waveform  # noqa: F401 – registriert das QML-Element WaveformView
    from .bridge.backend import Backend
    from .bridge.tasks import TaskRunner
    from .core.settings import AppSettings

    settings = AppSettings.load()
    engine = AudioEngine()
    engine.stop_fade_ms = settings.stop_fade_ms
    if no_audio:
        engine.start_null()
    else:
        engine.start(settings.audio_device, settings.audio_hostapi, settings.buffer_frames)
    runner = TaskRunner(use_processes=use_processes)
    runner.warm_up()
    documents = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
    backend = Backend(engine, runner, settings, Path(documents) if documents else None)

    qml = QQmlApplicationEngine()
    ctx = qml.rootContext()
    ctx.setContextProperty("backend", backend)
    ctx.setContextProperty("editor", backend.editor)
    ctx.setContextProperty("master", backend.master)
    ctx.setContextProperty("updater", backend.updater)
    ctx.setContextProperty("appVersion", __version__)
    ctx.setContextProperty("appFontFamily", family)
    ctx.setContextProperty("logFile", str(config_dir() / "launchpad.log"))
    ctx.setContextProperty("startFullscreen", bool(fullscreen))
    qml.load(QUrl.fromLocalFile(str(QML_DIR / "Main.qml")))
    context = AppContext(app, qml, backend, engine, runner, settings)
    if not qml.rootObjects():
        backend.shutdown()
        raise RuntimeError("Die Oberfläche konnte nicht geladen werden (siehe Protokoll).")
    backend.start(check_updates=check_updates)
    app.aboutToQuit.connect(backend.shutdown)
    if engine.error:
        backend.notify(f"Keine Audioausgabe verfügbar: {engine.error}", "error")
    return context


def _requested_project(args: argparse.Namespace) -> str | None:
    """Projekt aus ``--project`` oder dem Dateipfad (Doppelklick auf eine .lptab-Datei)."""
    for raw in (args.project, args.path):
        if raw and Path(raw).exists():
            return str(Path(raw).resolve())
    return None


def main(argv: list[str] | None = None) -> int:
    multiprocessing.freeze_support()
    argv = list(sys.argv if argv is None else argv)
    if "--finish-update" in argv:
        return finish_update(argv)
    args = parse_args(argv)
    if args.purge_user_data:
        return purge_user_data(confirmed=args.yes)
    setup_logging(args.verbose)
    log.info("%s %s startet (Python %s, %s)", __app_name__, __version__, sys.version.split()[0], sys.platform)

    # Der Audio-Thread braucht den GIL zügig: häufigere Thread-Wechsel = weniger Aussetzer
    sys.setswitchinterval(0.001)

    if args.smoke_test:
        return smoke_test(argv)

    if args.wait_pid:
        from .update.install import wait_for_pid

        wait_for_pid(args.wait_pid, timeout=30)

    from .bridge.single_instance import SingleInstance
    from .system import integration

    integration.set_app_user_model_id()
    make_qapp(argv)
    requested = _requested_project(args)
    instance = SingleInstance()
    if instance.forward({"action": "activate", "project": requested or ""}):
        log.info("Launchpad Pro läuft bereits – Auftrag an die laufende Instanz übergeben.")
        return 0
    instance.listen()
    integration.create_instance_mutex()

    try:
        ctx = create_app(argv, no_audio=args.no_audio, fullscreen=args.fullscreen,
                         check_updates=not args.no_update_check)
    except RuntimeError as exc:
        log.critical("%s", exc)
        return 1
    instance.messageReceived.connect(ctx.handle_instance_message)

    project = requested or ctx.settings.last_project
    if project and Path(project).exists():
        ctx.backend.openProject(project)

    rc = ctx.app.exec()
    instance.close()
    ctx.dispose()
    log.info("Beendet (Code %s)", rc)
    return rc


def purge_user_data(confirmed: bool) -> int:
    """``--purge-user-data``: Projekte + Einstellungen löschen (vom Deinstaller aufgerufen).

    Läuft ohne Oberfläche. Ohne ``--yes`` wird nur angezeigt, was gelöscht würde.
    Ein Protokoll landet im Temp-Ordner (``launchpad-pro-tab-entfernen.log``).
    """
    import tempfile

    from .core.purge import execute_purge, plan_purge

    documents = None
    qt_dirs: list[Path] = []
    try:
        from PySide6.QtCore import QCoreApplication, QStandardPaths

        QCoreApplication.setOrganizationName(__organization__)
        QCoreApplication.setApplicationName(__app_name__)
        loc = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
        documents = Path(loc) if loc else None
        for kind in (QStandardPaths.StandardLocation.CacheLocation, QStandardPaths.StandardLocation.AppLocalDataLocation):
            loc = QStandardPaths.writableLocation(kind)
            if loc:
                qt_dirs.append(Path(loc))      # z. B. QML-Cache von Qt
    except Exception:  # noqa: BLE001
        pass
    plan = plan_purge(documents=documents, extra_dirs=qt_dirs)
    lines = plan.describe()
    if not confirmed:
        print("Folgende Daten würden gelöscht (mit --yes ausführen):")
        print("\n".join(f"  {line}" for line in lines) or "  (nichts gefunden)")
        return 0
    report = execute_purge(plan)
    try:
        log_file = Path(tempfile.gettempdir()) / "launchpad-pro-tab-entfernen.log"
        log_file.write_text(
            "Gelöscht:\n" + "\n".join(report.deleted)
            + "\n\nBehalten (enthielt fremde Dateien):\n" + "\n".join(report.kept)
            + "\n\nFehler:\n" + "\n".join(report.errors) + "\n",
            encoding="utf-8",
        )
    except OSError:
        pass
    if sys.stdout is not None:
        print(f"{len(report.deleted)} Einträge gelöscht, {len(report.kept)} behalten, {len(report.errors)} Fehler.")
    return 0 if not report.errors else 1


def finish_update(argv: list[str]) -> int:
    """Hilfsprozess der neuen Version nach einem Linux-Update (siehe ``update.install``)."""
    from .update.install import finish_linux_update

    try:
        i = argv.index("--finish-update")
        install_dir = Path(argv[i + 1])
        wait_pid = int(argv[argv.index("--wait-pid") + 1]) if "--wait-pid" in argv else 0
    except (ValueError, IndexError):
        return 2
    restart = argv[argv.index("--") + 1:] if "--" in argv else []
    logging.basicConfig(filename=str(config_dir() / "update.log"), level=logging.INFO,
                        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    return finish_linux_update(install_dir, wait_pid, restart)


def smoke_test(argv: list[str]) -> int:
    """Startet die komplette Oberfläche ohne Soundkarte, prüft auf QML-Fehler und beendet sich.

    Wird im CI gegen die fertige Windows-EXE ausgeführt, um fehlende QML-Module oder
    Bibliotheken im Paket zu erkennen. Ergebnis zusätzlich im Protokoll.
    """
    import tempfile

    from PySide6.QtCore import QTimer, qInstallMessageHandler

    tmp = tempfile.mkdtemp(prefix="lptab-smoke-")
    os.environ["LPTAB_CONFIG_DIR"] = tmp
    os.environ["LPTAB_PROJECTS_DIR"] = tmp
    problems: list[str] = []

    def handler(_mode, context, message):
        if ".qml" in (context.file or "") or ".qml" in message or "module" in message.lower():
            problems.append(message)

    qInstallMessageHandler(handler)
    try:
        ctx = create_app(argv, no_audio=True)
    except Exception as exc:  # noqa: BLE001
        log.critical("Smoke-Test fehlgeschlagen: %s", exc)
        for p in problems:
            log.critical("  %s", p)
        return 2
    ok_project = ctx.backend.newProject("Smoke-Test", tmp, 4)
    ok_audio = _smoke_audio(ctx, Path(tmp)) if ok_project else False
    QTimer.singleShot(500, ctx.app.quit)
    ctx.app.exec()
    ctx.dispose()
    if not ok_audio:
        problems.append("Audiodateien konnten nicht über die Worker-Prozesse dekodiert werden")
    qInstallMessageHandler(None)
    if problems or not ok_project:
        log.critical("Smoke-Test: %d Problem(e)", len(problems) + (0 if ok_project else 1))
        for p in problems:
            log.critical("  %s", p)
        return 3
    log.info("Smoke-Test erfolgreich")
    return 0


def _smoke_audio(ctx: AppContext, folder: Path) -> bool:
    """WAV (libsndfile) und MP3 (FFmpeg) über die Worker-Prozesse laden und abspielen."""
    import time

    import numpy as np
    import soundfile as sf
    from PySide6.QtCore import QEventLoop

    t = np.arange(24000) / 48000.0
    tone = np.stack([np.sin(2 * np.pi * 440 * t)] * 2, axis=1).astype(np.float32) * 0.3
    wav, mp3 = folder / "smoke.wav", folder / "smoke.mp3"
    sf.write(wav, tone, 48000)
    sf.write(mp3, tone, 48000, format="MP3", subtype="MPEG_LAYER_III")
    backend = ctx.backend
    backend.assignAudio(0, str(wav))
    backend.assignAudio(1, str(mp3))
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        ctx.app.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 50)
        if not backend.tileInfo(0)["empty"] and not backend.tileInfo(1)["empty"] and backend.runner.pending == 0:
            break
        time.sleep(0.02)
    else:
        return False
    backend.triggerTile(1)
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline and (0, 1) not in backend.engine.snapshot:
        ctx.app.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 20)
        time.sleep(0.01)
    playing = (0, 1) in backend.engine.snapshot
    backend.stopAll()
    return playing
