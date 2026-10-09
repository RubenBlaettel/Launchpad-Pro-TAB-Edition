"""Zentrale QML-Schnittstelle ("Backend").

Die Oberfläche spricht ausschließlich mit diesem Objekt (plus ``editor`` und ``master``).
Es verbindet Projektverwaltung, Audio-Engine, Hintergrundaufgaben und Einstellungen.

Mehrere Projekte können gleichzeitig in Registerkarten geöffnet sein (``tabs``, siehe
``bridge/tabs.py``). Alle Kachel-Befehle aus QML beziehen sich auf die aktive Karte; Kacheln
in Hintergrund-Karten spielen weiter und laden weiter.
"""

from __future__ import annotations

import gc
import itertools
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import Property, QObject, QTimer, QUrl, Signal, Slot

from .. import __version__
from ..audio import cache, tasks
from ..audio.cache import CacheEntry
from ..audio.engine import AudioEngine
from ..audio.output import list_output_devices
from ..core import purge
from ..core.constants import (
    AUDIO_EXTENSIONS,
    AUTOSAVE_DEBOUNCE_MS,
    AUTOSAVE_INTERVAL_MS,
    COVER_DIR,
    EDITED_DIR,
    GRID_DEFAULT,
    GRID_MAX,
    GRID_MIN,
    IMAGE_EXTENSIONS,
    PROJECT_FILE_NAME,
    TILE_COLORS,
)
from ..core.models import EditParams, TileData, clamp_grid
from ..core.paths import default_projects_dir
from ..core.project import Project, ProjectError
from ..core.settings import THEME_MODES, AppSettings
from ..core.util import format_time
from ..update.version import is_newer
from . import appearance
from .covers import import_cover
from .editor import EditorController
from .models import RecentAudioModel, RecentProjectsModel, TileModel
from .qtutil import PropertyObject, move_to_trash, rprop, to_local_path
from .tabs import EngineKey, Key, ProjectTab, TabsModel
from .tasks import TaskRunner
from .updater import UpdateController
from .volume import MasterVolumeController

log = logging.getLogger(__name__)

BUFFER_OPTIONS = (0, 128, 256, 512, 1024, 2048)
TRASH_RETRY_MS = 200          # Projekt löschen: Wartezeit zwischen zwei Versuchen …
TRASH_RETRIES = 25            # … und Anzahl der Wiederholungen (≈ 5 s)


class Backend(PropertyObject):
    # Ereignisse an QML
    toast = Signal(str, str, str, arguments=["message", "kind", "action"])
    errorDialog = Signal(str, str, arguments=["title", "message"])

    projectChanged = Signal()
    gridChanged = Signal()
    saveStateChanged = Signal()
    busyChanged = Signal()
    activeCountChanged = Signal()
    levelsChanged = Signal()
    audioChanged = Signal()
    showModeChanged = Signal()
    recentChanged = Signal()
    themeChanged = Signal()
    fullscreenChanged = Signal()
    tabsChanged = Signal()

    def __init__(self, engine: AudioEngine, runner: TaskRunner, settings: AppSettings,
                 documents_dir: Path | None = None, volume: MasterVolumeController | None = None,
                 parent: QObject | None = None):
        super().__init__(parent)
        self.engine = engine
        self.runner = runner
        self.settings = settings
        self._documents_dir = documents_dir
        self._tiles = TileModel(self)
        self._tab_model = TabsModel(self)
        self._recent_audio = RecentAudioModel(self)
        self._recent_projects = RecentProjectsModel(self)
        self._master = volume or MasterVolumeController(self)
        self._editor = EditorController(self, self)
        self._updater = UpdateController(runner, settings, self)
        self._updater.prepare_hook = self.prepare_for_update
        self._updater.resume_hook = self.runner.resume_processes
        self._updater.project_hook = lambda: str(self.project.root) if self.project is not None else None
        self._updater.busy_hook = self._set_busy
        self._uids = itertools.count(1)
        self._tab = ProjectTab(uid=next(self._uids))     # Start: eine leere Karte (Startseite)
        self._tabs: list[ProjectTab] = [self._tab]
        self._tab_model.set_tabs(self._tabs, self._tab)
        self._playing_keys: set = set()                  # Engine-Schlüssel, die beim letzten Takt liefen
        self._undo: tuple[ProjectTab, Project, Key, TileData] | None = None
        self._closing = False
        self.move_to_trash = move_to_trash               # Papierkorb (austauschbar, z. B. in Tests)

        self._busy = ""
        self._active_count = 0
        self._level_l = 0.0
        self._level_r = 0.0
        self._limiting = False
        self._show_mode = False
        self._theme_mode = settings.theme
        self._dark = appearance.apply_color_scheme(self._theme_mode)
        self._fullscreen = settings.fullscreen
        hints = appearance.style_hints()
        if hints is not None:
            hints.colorSchemeChanged.connect(self._on_system_scheme)

        self._ui_timer = QTimer(self)
        self._ui_timer.setInterval(33)
        self._ui_timer.timeout.connect(self._tick)
        self._autosave_timer = QTimer(self)
        self._autosave_timer.setInterval(AUTOSAVE_INTERVAL_MS)
        self._autosave_timer.timeout.connect(self._autosave)
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(AUTOSAVE_DEBOUNCE_MS)
        self._debounce.timeout.connect(self._autosave)
        self._clock = QTimer(self)
        self._clock.setInterval(15_000)
        self._clock.timeout.connect(self._update_save_text)

        self._refresh_recent_audio()
        self._refresh_recent_projects()

    def start(self, check_updates: bool = False) -> None:
        self._ui_timer.start()
        self._autosave_timer.start()
        self._clock.start()
        self._announce_version()
        if check_updates:
            self._updater.start()
            self.runner.submit_thread(self._updater.cleanup)

    def _announce_version(self) -> None:
        """Nach einem Update einmalig die neue Version melden."""
        previous = self.settings.last_version
        if previous == __version__:
            return
        if previous and is_newer(__version__, previous):
            self.notify(f"TAB Soundboard wurde auf Version {__version__} aktualisiert.", "success")
        self.settings.last_version = __version__
        self.settings.save()

    # ------------------------------------------------------------------
    # Properties für QML
    # ------------------------------------------------------------------
    @property
    def project(self) -> Project | None:
        """Projekt der aktiven Registerkarte (None = Startseite)."""
        return self._tab.project

    def _save_state_text(self) -> str:
        tab = self._tab
        if tab.project is None:
            return ""
        if tab.dirty:
            return "Ungespeicherte Änderungen"
        return f"Gespeichert um {tab.last_saved:%H:%M:%S}" if tab.last_saved else "Gespeichert"

    tiles = Property(QObject, lambda self: self._tiles, constant=True)
    tabs = Property(QObject, lambda self: self._tab_model, constant=True)
    recentAudio = Property(QObject, lambda self: self._recent_audio, constant=True)
    recentProjects = Property(QObject, lambda self: self._recent_projects, constant=True)
    editor = Property(QObject, lambda self: self._editor, constant=True)
    master = Property(QObject, lambda self: self._master, constant=True)
    updater = Property(QObject, lambda self: self._updater, constant=True)

    hasProject = Property(bool, lambda self: self._tab.project is not None, notify=projectChanged)
    projectName = Property(str, lambda self: self._tab.project.name if self._tab.project else "",
                           notify=projectChanged)
    projectPath = Property(str, lambda self: str(self._tab.project.root) if self._tab.project else "",
                           notify=projectChanged)
    gridSize = Property(int, lambda self: self._tab.project.data.grid if self._tab.project else GRID_DEFAULT,
                        notify=gridChanged)
    def _active_index(self) -> int:
        try:
            return self._tabs.index(self._tab)
        except ValueError:  # nur kurz während des Schließens der aktiven Karte
            return -1

    dirty = Property(bool, lambda self: self._tab.dirty, notify=saveStateChanged)
    saveStateText = Property(str, _save_state_text, notify=saveStateChanged)
    activeTab = Property(int, _active_index, notify=tabsChanged)
    busyText = rprop(str, "_busy", busyChanged)
    activeCount = rprop(int, "_active_count", activeCountChanged)
    levelL = rprop(float, "_level_l", levelsChanged)
    levelR = rprop(float, "_level_r", levelsChanged)
    limiting = rprop(bool, "_limiting", levelsChanged)
    showMode = rprop(bool, "_show_mode", showModeChanged)
    themeMode = rprop(str, "_theme_mode", themeChanged)
    darkTheme = rprop(bool, "_dark", themeChanged)
    fullscreen = rprop(bool, "_fullscreen", fullscreenChanged)

    gridOptions = Property(list, lambda self: list(range(GRID_MIN, GRID_MAX + 1)), constant=True)
    tileColors = Property(list, lambda self: list(TILE_COLORS), constant=True)
    audioExtensions = Property(list, lambda self: sorted(e.lstrip(".") for e in AUDIO_EXTENSIONS), constant=True)

    def _audio_device(self) -> str:
        return self.engine.device_name

    def _audio_info(self) -> str:
        if self.engine.is_null:
            return "Keine Soundkarte – Wiedergabe stumm" if self.engine.error else "Keine Audioausgabe"
        return f"{self.engine.samplerate / 1000:.1f} kHz · {self.engine.latency_ms:.0f} ms Latenz"

    audioDevice = Property(str, _audio_device, notify=audioChanged)
    audioInfo = Property(str, _audio_info, notify=audioChanged)
    audioOk = Property(bool, lambda self: not self.engine.is_null, notify=audioChanged)

    def _devices(self) -> list[str]:
        return ["Automatisch (Standardgerät)"] + [d.label for d in list_output_devices()]

    def _device_index(self) -> int:
        if not self.settings.audio_device:
            return 0
        for i, d in enumerate(list_output_devices()):
            if d.name == self.settings.audio_device and (
                not self.settings.audio_hostapi or d.hostapi == self.settings.audio_hostapi
            ):
                return i + 1
        return 0

    outputDevices = Property(list, _devices, notify=audioChanged)
    outputDeviceIndex = Property(int, _device_index, notify=audioChanged)
    bufferOptions = Property(list, lambda self: list(BUFFER_OPTIONS), constant=True)
    bufferFrames = Property(int, lambda self: int(self.settings.buffer_frames), notify=audioChanged)

    def _projects_dir(self) -> str:
        return self.settings.projects_dir or str(default_projects_dir(self._documents_dir))

    defaultProjectsDir = Property(str, _projects_dir, notify=projectChanged)

    # ------------------------------------------------------------------
    # Meldungen
    # ------------------------------------------------------------------
    @Slot(str, str)
    def notify(self, message: str, kind: str = "info", action: str = "") -> None:
        self.toast.emit(message, kind, action)

    def _error(self, title: str, message: str) -> None:
        log.warning("%s: %s", title, message)
        self.errorDialog.emit(title, message)

    def _set_busy(self, text: str) -> None:
        self._set("_busy", text, "busyChanged")

    # ------------------------------------------------------------------
    # Registerkarten
    # ------------------------------------------------------------------
    @Slot(int)
    def activateTab(self, index: int) -> None:  # noqa: N802
        if not self._busy and 0 <= index < len(self._tabs):
            self._switch_to(self._tabs[index])

    @Slot()
    def newTab(self) -> None:  # noqa: N802
        """Neue leere Registerkarte (Startseite) – höchstens eine leere Karte gleichzeitig."""
        if self._busy:
            return
        empty = next((t for t in self._tabs if t.project is None), None)
        if empty is None:
            empty = ProjectTab(uid=next(self._uids))
            self._tabs.append(empty)
            self._tab_model.set_tabs(self._tabs, self._tab)
            self.tabsChanged.emit()
        self._switch_to(empty)

    @Slot(int)
    def closeTab(self, index: int) -> None:  # noqa: N802
        """Registerkarte schließen: Projekt speichern, seine laufenden Kacheln ausblenden."""
        if not self._busy and 0 <= index < len(self._tabs):
            self._close_tab(self._tabs[index])

    def _close_tab(self, tab: ProjectTab) -> bool:
        """Schließt ``tab`` (speichert vorher). ``False``, wenn die Karte offen bleiben musste."""
        index = self._tabs.index(tab)
        was_active = tab is self._tab
        if tab.project is not None:
            if was_active and self._editor.saving:
                self.notify("Die Bearbeitung wird noch gespeichert – bitte einen Moment warten.", "warning")
                return False
            if was_active:
                self._park_editor()
            if tab.dirty and not self._save_tab(tab, silent=False):
                return False  # nicht gespeichert -> Karte bleibt offen
            self.engine.stop_group(tab.uid)
        if self._undo is not None and self._undo[0] is tab:
            self._undo = None
        self._tabs.remove(tab)
        if not self._tabs:
            self._tabs.append(ProjectTab(uid=next(self._uids)))  # immer mindestens eine (leere) Karte
        if was_active:
            self._tab_model.set_tabs(self._tabs, None)
            self._show(self._tabs[min(index, len(self._tabs) - 1)])
        else:
            self._tab_model.set_tabs(self._tabs, self._tab)
            self.tabsChanged.emit()
            self._refresh_recent_projects()
            self._persist_tabs()
        return True

    def restore_tabs(self, requested: str | None = None) -> None:
        """Programmstart: zuletzt offene Registerkarten wieder öffnen (+ ggf. ``requested``)."""
        active = self.settings.last_project
        for path in self.settings.projects_to_restore():
            if Path(path).exists():
                self.openProject(path)
        tab = self._find_tab(Path(active)) if active else None
        if tab is not None:
            self._switch_to(tab)
        if requested:
            self.openProject(requested)

    def _find_tab(self, path: Path) -> ProjectTab | None:
        try:
            target = Path(path).resolve()
        except OSError:
            return None
        return next((t for t in self._tabs
                     if t.project is not None and target in (t.project.root, t.project.file)), None)

    def _current(self, tab: ProjectTab, project: Project, key: Key | None = None, token: int | None = None) -> bool:
        """Gehört ein asynchrones Ergebnis noch zu dieser (offenen) Karte und ihrem Projekt?"""
        if tab.project is not project or tab not in self._tabs:
            return False
        return token is None or tab.tokens.get(key) == token

    def _refresh(self, tab: ProjectTab, key: Key, *roles: str) -> None:
        """Kachel neu anzeigen – nur, wenn ihre Karte gerade sichtbar ist."""
        if tab is self._tab:
            self._tiles.refresh(key, *roles)

    def _park_editor(self) -> None:
        """Bearbeitung der aktiven Karte als Zwischenstand sichern und schließen."""
        if self._editor.key is not None:
            self._editor.close(keep_session=True)

    def _leave(self) -> None:
        """Vor dem Wechsel weg von der aktiven Karte: Bearbeitung parken, Stand sichern."""
        if self._tab.project is not None:
            self._park_editor()
            if self._tab.dirty:
                self._save_tab(self._tab, silent=True)

    def _switch_to(self, tab: ProjectTab) -> None:
        if tab is not self._tab:
            self._leave()
            self._show(tab)

    def _show(self, tab: ProjectTab, announce_restore: bool = False) -> None:
        """Macht ``tab`` zur aktiven Karte und zeigt ihr Raster an."""
        self._tab = tab
        project = tab.project
        self._tiles.set_project(project.data if project else None, project.root if project else None, tab.runtime)
        self._tab_model.set_active(tab)
        self.projectChanged.emit()
        self.gridChanged.emit()
        self.saveStateChanged.emit()
        self.tabsChanged.emit()
        self._refresh_recent_projects()
        self._persist_tabs()
        if project is not None:
            state = project.read_edit_session()
            if state and self._editor.restore_session(state) and announce_restore:
                self.notify("Die letzte ungespeicherte Bearbeitung wurde wiederhergestellt.", "info")

    def _attach(self, tab: ProjectTab, project: Project) -> None:
        """Legt ``project`` in die Karte ``tab``, zeigt sie an und lädt die Kacheln."""
        tab.reset(project)
        if self._undo is not None and self._undo[0] is tab:
            self._undo = None
        self._tab_model.set_tabs(self._tabs, tab)
        self.settings.remember_project(project.root, project.name)
        self._show(tab, announce_restore=True)
        self._load_all_tiles(tab)
        self._schedule_cleanup(project)

    def _open_in_tab(self, project: Project) -> None:
        """Öffnet ``project`` in einer neuen Registerkarte (eine leere aktive Karte wird genutzt)."""
        if self._tab.project is None:
            tab = self._tab
        else:
            self._leave()
            tab = ProjectTab(uid=next(self._uids))
            self._tabs.append(tab)
        self._attach(tab, project)

    def _activate(self, project: Project) -> None:
        """Ersetzt das Projekt der aktiven Karte (das bisherige wird vorher sicher gespeichert)."""
        if self._tab.project is not None:
            self._leave()
            self.engine.stop_group(self._tab.uid)
        self._attach(self._tab, project)

    def _persist_tabs(self) -> None:
        """Offene Registerkarten merken (Wiederherstellung beim nächsten Start)."""
        self.settings.open_projects = [str(t.project.root) for t in self._tabs if t.project is not None]
        if self._tab.project is not None:
            self.settings.last_project = str(self._tab.project.root)
        self.settings.save()

    # ------------------------------------------------------------------
    # Projekte
    # ------------------------------------------------------------------
    @Slot(result=str)
    def suggestProjectName(self) -> str:  # noqa: N802
        return f"Neues Projekt {datetime.now():%Y-%m-%d}"

    @Slot(str, str, int, result=bool)
    def newProject(self, name: str, location: str, grid: int) -> bool:  # noqa: N802
        location = to_local_path(location) or self._projects_dir()
        try:
            project = Project.create(name, Path(location), clamp_grid(grid))
        except ProjectError as exc:
            self._error("Projekt konnte nicht erstellt werden", str(exc))
            return False
        self.settings.projects_dir = str(Path(location))
        self._open_in_tab(project)
        self.notify(f"Projekt „{project.name}“ wurde angelegt.", "success")
        return True

    @Slot(str, result=bool)
    def openProject(self, path: str) -> bool:  # noqa: N802
        """Öffnet ein Projekt in einer neuen Registerkarte – ist es schon offen, wird dorthin gewechselt."""
        path = to_local_path(path)
        if not path:
            return False
        p = Path(path)
        try:
            if p.suffix.lower() == ".zip":
                target = Project.import_zip(p, Path(self._projects_dir()))
                project = Project.open(target)
                self.notify(f"Projekt importiert nach: {target}", "success")
            else:
                tab = self._find_tab(p)
                if tab is not None:
                    if tab is self._tab:
                        self.notify("Dieses Projekt ist bereits geöffnet.", "info")
                    else:
                        self._switch_to(tab)
                    return True
                project = Project.open(p)
        except ProjectError as exc:
            self._error("Projekt konnte nicht geöffnet werden", str(exc))
            if not p.exists():
                self.settings.forget_project(str(p))
                self._refresh_recent_projects()
            return False
        except Exception as exc:  # unerwartet
            log.exception("Fehler beim Öffnen")
            self._error("Projekt konnte nicht geöffnet werden", str(exc))
            return False
        self._open_in_tab(project)
        return True

    @Slot(str)
    def forgetProject(self, path: str) -> None:  # noqa: N802
        self.settings.forget_project(path)
        self._persist_tabs()  # offene Karten bleiben gemerkt
        self._refresh_recent_projects()

    @Slot(str, result=bool)
    def deleteProject(self, path: str) -> bool:  # noqa: N802
        """Projekt in den Papierkorb verschieben (Projektauswahl). Ein offenes Projekt wird vorher
        gespeichert und seine Karte geschlossen; ein nicht mehr vorhandenes verschwindet nur aus
        der Liste. Gelöscht wird nur ein echter Projektordner, nie ein geschützter Ort."""
        raw = to_local_path(path)
        if not raw or self._busy or self._show_mode:
            return False
        p = Path(raw)
        root = p.parent if p.name == PROJECT_FILE_NAME else p
        name = next((e.get("name") for e in self.settings.recent_projects if e.get("path") == raw), None) or root.name
        if not root.exists():
            self.forgetProject(raw)
            self.notify(f"„{name}“ wurde nicht gefunden und aus der Liste entfernt.", "info")
            return True
        root = root.resolve()
        guard = purge.protected_dirs([self._documents_dir] if self._documents_dir else None)
        if root in guard or root.parent == root or not purge.is_project_dir(root):
            self.notify(f"„{root}“ ist kein Projektordner von TAB Soundboard – es wird nichts gelöscht.", "error")
            return False
        tab = self._find_tab(root)
        if tab is not None:
            if not self._close_tab(tab):
                return False
            tab.pcm.clear()     # gemappte Audiodaten freigeben – Windows sperrt den Ordner sonst
        self._trash_project(root, name, raw)
        return True

    def _trash_project(self, root: Path, name: str, listed: str, attempt: int = 0) -> None:
        """Verschiebt ``root`` in den Papierkorb. Direkt nach dem Schließen blenden Stimmen der Karte
        noch aus bzw. schreiben Worker in ihren Cache – dann kurz warten und erneut versuchen."""
        gc.collect()
        try:
            ok = self.move_to_trash(root)
        except OSError:
            ok = False
        if ok:
            for key in {listed, str(root)}:
                self.settings.forget_project(key)
            self._persist_tabs()
            self._refresh_recent_projects()
            self.notify(f"Projekt „{name}“ wurde in den Papierkorb verschoben.", "success")
        elif attempt < TRASH_RETRIES and root.exists():
            QTimer.singleShot(TRASH_RETRY_MS, lambda: self._trash_project(root, name, listed, attempt + 1))
        else:
            self._error("Projekt konnte nicht gelöscht werden",
                        f"„{name}“ ließ sich nicht in den Papierkorb verschieben. Möglicherweise ist eine "
                        f"Datei darin noch in einem anderen Programm geöffnet, oder das Laufwerk hat keinen "
                        f"Papierkorb.\n\nOrdner: {root}")

    def _schedule_cleanup(self, project: Project) -> None:
        """Unbenutzte Cache-Dateien und verwaiste Bearbeitungen entfernen.

        Alle Projektdaten werden hier im UI-Thread ausgewertet; der Hintergrund-Thread
        löscht nur noch die fertig berechnete Liste (keine gleichzeitigen Zugriffe).
        """
        sr = self.engine.samplerate
        refs = project.data.referenced_files()
        keep: set[str] = set()
        for rel in refs:
            path = project.abs(rel)
            try:
                if path is not None and path.exists():
                    keep.add(cache.cache_key(path, sr))
            except OSError:
                pass
        edited_dir = project.root / EDITED_DIR
        orphans: list[Path] = []
        if edited_dir.is_dir():
            orphans = [f for f in edited_dir.iterdir()
                       if f.is_file() and project.rel(f) not in refs and ".tmp" not in f.name]

        def work() -> None:
            cache.cleanup(project.cache_dir, keep)
            for f in orphans:
                try:
                    f.unlink()
                except OSError:
                    pass

        self.runner.submit_thread(work)

    @Slot()
    def saveProject(self) -> None:  # noqa: N802
        if self.project is None:
            return
        if self._save_now(silent=False):
            self.notify("Projekt gespeichert.", "success")

    def _save_now(self, silent: bool = True) -> bool:
        return self._save_tab(self._tab, silent)

    def _save_tab(self, tab: ProjectTab, silent: bool = True) -> bool:
        project = tab.project
        if project is None:
            return False
        try:
            project.save()
        except ProjectError as exc:
            if silent:
                self.notify(str(exc), "error")
            else:
                self._error("Speichern fehlgeschlagen", str(exc))
            return False
        if tab is self._tab:
            self._editor.write_session()
        tab.dirty = False
        tab.last_saved = datetime.now()
        self._tab_model.refresh(tab, "dirty")
        if tab is self._tab:
            self.saveStateChanged.emit()
        return True

    def _update_save_text(self) -> None:
        self.saveStateChanged.emit()

    def _mark_dirty(self, tab: ProjectTab | None = None) -> None:
        tab = tab or self._tab
        if tab.project is None:
            return
        if not tab.dirty:
            tab.dirty = True
            self._tab_model.refresh(tab, "dirty")
            if tab is self._tab:
                self.saveStateChanged.emit()
        self._debounce.start()

    def _autosave(self) -> None:
        for tab in list(self._tabs):
            if tab.project is not None and tab.dirty:
                self._save_tab(tab, silent=True)

    @Slot(str)
    def saveProjectAs(self, folder: str) -> None:  # noqa: N802
        tab, project = self._tab, self._tab.project
        if project is None:
            return
        target = to_local_path(folder)
        if not target:
            return
        self._save_tab(tab, silent=True)
        self._set_busy("Projekt wird kopiert …")

        def done(new_project: Project) -> None:
            self._set_busy("")
            if self._current(tab, project):
                self._switch_to(tab)
                self._activate(new_project)      # die Karte zeigt nun die Kopie
            else:
                self._open_in_tab(new_project)
            self.notify(f"Projekt gespeichert unter: {new_project.root}", "success")

        def failed(msg: str) -> None:
            self._set_busy("")
            self._error("Speichern unter fehlgeschlagen", msg)

        self.runner.submit_thread(project.save_as, Path(target), None, False, on_done=done, on_error=failed)

    @Slot(str)
    def exportProject(self, file_url: str) -> None:  # noqa: N802
        project = self.project
        if project is None:
            return
        target = to_local_path(file_url)
        if not target:
            return
        self._save_now(silent=True)
        self._set_busy("Projekt wird exportiert …")

        def done(path: Path) -> None:
            self._set_busy("")
            self.notify(f"Export erstellt: {path}", "success")

        def failed(msg: str) -> None:
            self._set_busy("")
            self._error("Export fehlgeschlagen", msg)

        self.runner.submit_thread(project.export_zip, Path(target), False, on_done=done, on_error=failed)

    @Slot(result=str)
    def suggestedExportName(self) -> str:  # noqa: N802
        if self.project is None:
            return "Projekt.zip"
        return f"{self.project.root.name}_{datetime.now():%Y-%m-%d}.zip"

    @Slot(result=str)
    def projectFileName(self) -> str:  # noqa: N802
        return PROJECT_FILE_NAME

    @Slot(str, result=str)
    def localPath(self, url: str) -> str:  # noqa: N802
        """file:///-URL (aus Datei-/Ordnerdialogen) in einen lesbaren lokalen Pfad umwandeln."""
        path = to_local_path(url)
        return str(Path(path)) if path else ""

    # ------------------------------------------------------------------
    # Raster
    # ------------------------------------------------------------------
    @Slot(int, result=int)
    def tilesLostOnResize(self, n: int) -> int:  # noqa: N802
        if self.project is None:
            return 0
        return len(self.project.data.tiles_outside(clamp_grid(n)))

    @Slot(int)
    def setGridSize(self, n: int) -> None:  # noqa: N802
        tab, project = self._tab, self._tab.project
        if project is None:
            return
        n = clamp_grid(n)
        old = project.data.grid
        if n == old:
            return
        for key in [k for k in list(tab.pcm) if k[0] >= n or k[1] >= n]:
            self.engine.kill(tab.engine_key(key))
            tab.pcm.pop(key, None)
        editor_key = self._editor.key
        if editor_key is not None and (editor_key[0] >= n or editor_key[1] >= n):
            self._editor.close(keep_session=False)
        removed = project.data.resize(n)
        self._tiles.reset()
        self.gridChanged.emit()
        self._mark_dirty(tab)
        if n < old and removed:
            self.notify(f"Raster auf {n}×{n} verkleinert – {len(removed)} Kachel(n) verworfen.", "warning")
        else:
            self.notify(f"Raster auf {n}×{n} geändert.", "info")

    # ------------------------------------------------------------------
    # Kacheln: Laden
    # ------------------------------------------------------------------
    def _key(self, index: int) -> Key | None:
        project = self._tab.project
        if project is None:
            return None
        n = project.data.grid
        if not 0 <= index < n * n:
            return None
        return divmod(int(index), n)

    def engine_key(self, index: int) -> EngineKey | None:
        """Schlüssel der Kachel ``index`` (aktive Karte) in der Audio-Engine."""
        key = self._key(index)
        return self._tab.engine_key(key) if key is not None else None

    def _load_all_tiles(self, tab: ProjectTab) -> None:
        assert tab.project is not None
        for key, tile in list(tab.project.data.tiles.items()):
            if tile.audio:
                self._load_tile(tab, key)

    def _load_tile(self, tab: ProjectTab, key: Key) -> None:
        project = tab.project
        tile = project.data.peek(*key) if project else None
        if project is None or tile is None or not tile.audio:
            return
        path = project.abs(tile.audio)
        rt = tab.rt(key)
        if path is None or not path.exists():
            rt.missing = True
            rt.loading = False
            self._refresh(tab, key, "missing", "loading")
            return
        rt.missing = False
        token = tab.next_token(key)
        entry = cache.lookup(project.cache_dir, path, self.engine.samplerate)
        if entry is not None:
            self._tile_ready(tab, project, key, token, entry)
            return
        rt.loading = True
        self._refresh(tab, key, "loading", "missing")
        self.runner.submit_process(
            tasks.prepare, str(path), str(project.cache_dir), self.engine.samplerate,
            on_done=lambda d: self._tile_ready(tab, project, key, token, CacheEntry.from_dict(d)),
            on_error=lambda msg: self._tile_failed(tab, project, key, token, msg),
        )

    def _tile_ready(self, tab: ProjectTab, project: Project, key: Key, token: int, entry: CacheEntry) -> None:
        if not self._current(tab, project, key, token):
            return
        tile = project.data.peek(*key)
        if tile is None or tile.is_empty:
            return
        pcm = cache.open_pcm(entry)
        cache.warm(pcm, 0, int(entry.samplerate * 2))  # Anfang vorladen -> sofortiger Start
        tab.pcm[key] = pcm
        if abs(tile.duration - entry.duration) > 0.01:
            tile.duration = entry.duration
        rt = tab.rt(key)
        rt.loading = False
        rt.missing = False
        rt.error = ""
        self._refresh(tab, key)

    def _tile_failed(self, tab: ProjectTab, project: Project, key: Key, token: int, message: str) -> None:
        if not self._current(tab, project, key, token):
            return
        rt = tab.rt(key)
        rt.loading = False
        rt.error = message
        self._refresh(tab, key, "loading", "errorText")
        where = "" if tab is self._tab else f"{project.name}: "
        self.notify(f"{where}Audiodatei kann nicht geladen werden: {message}", "error")

    # ------------------------------------------------------------------
    # Kacheln: Wiedergabe
    # ------------------------------------------------------------------
    @Slot(int, result=bool)
    def triggerTile(self, index: int) -> bool:  # noqa: N802
        """Start/Stopp-Umschalter; liefert True, wenn die Kachel dadurch startet."""
        tab = self._tab
        key = self._key(index)
        if key is None:
            return False
        tile = tab.project.data.peek(*key)
        if tile is None or tile.is_empty:
            return False
        pcm = tab.pcm.get(key)
        rt = tab.rt(key)
        if pcm is None:
            if rt.missing:
                self.notify(f"Audiodatei fehlt: {tile.audio}", "error")
            elif rt.loading:
                self.notify("Die Audiodatei wird noch vorbereitet …", "info")
            elif rt.error:
                self.notify(f"Audiodatei fehlerhaft: {rt.error}", "error")
            return False
        ekey = tab.engine_key(key)
        self.engine.toggle(ekey, pcm, tile.loop)
        # Sofortiges optisches Feedback; der UI-Timer gleicht danach mit der Engine ab.
        started = ekey not in self.engine.snapshot
        rt.playing = started
        rt.progress = 0.0
        if started:
            rt.remaining = tile.duration
        self._tiles.refresh(key, "playing", "progress", "remainingText")
        return started

    @Slot(int)
    def stopTile(self, index: int) -> None:  # noqa: N802
        """Kachel ausblenden – z. B. wenn ein Klick in ein Verschieben übergeht."""
        key = self._key(index)
        if key is None:
            return
        self.engine.stop(self._tab.engine_key(key))
        rt = self._tab.runtime.get(key)
        if rt is not None and rt.playing:
            rt.playing = False
            rt.progress = 0.0
            self._tiles.refresh(key, "playing", "progress", "remainingText")

    @Slot()
    def stopAll(self) -> None:  # noqa: N802
        """Panik-Taste: stoppt die Kacheln ALLER Registerkarten."""
        self.engine.stop_all()
        self._editor.pause()

    def _tick(self) -> None:
        engine = self.engine
        snap = engine.snapshot
        sr = float(engine.samplerate or 48000)
        keys = set(snap)
        tabs = {t.uid: t for t in self._tabs}
        counts: dict[int, int] = {}
        for ekey in keys | self._playing_keys:
            if type(ekey) is not tuple or len(ekey) != 3:
                continue
            tab = tabs.get(ekey[0])
            if tab is None:
                continue
            key = (ekey[1], ekey[2])
            rt = tab.rt(key)
            if ekey in snap:
                counts[tab.uid] = counts.get(tab.uid, 0) + 1
                pos, total = snap[ekey]
                progress = pos / total if total else 0.0
                remaining = (total - pos) / sr
                changed = (not rt.playing) or abs(progress - rt.progress) > 0.0005
                rt.playing = True
                rt.progress = progress
                if int(remaining) != int(rt.remaining) or changed:
                    rt.remaining = remaining
                    self._refresh(tab, key, "playing", "progress", "remainingText")
            elif rt.playing:
                rt.playing = False
                rt.progress = 0.0
                self._refresh(tab, key, "playing", "progress", "remainingText")
        self._playing_keys = keys
        for tab in self._tabs:
            n = counts.get(tab.uid, 0)
            if n != tab.playing:
                tab.playing = n
                self._tab_model.refresh(tab, "playing")
        count = sum(counts.values())
        if count != self._active_count:
            self._active_count = count
            self.activeCountChanged.emit()
        l, r, lim = engine.take_levels()
        if l != self._level_l or r != self._level_r or lim != self._limiting:
            self._level_l, self._level_r, self._limiting = l, r, lim
            self.levelsChanged.emit()
        while engine.events:
            try:
                ev, _ = engine.events.popleft()
            except IndexError:
                break
            if ev == "preview_end":
                self._editor.on_preview_end()
        self._editor.tick()

    # ------------------------------------------------------------------
    # Kacheln: Belegen / Bearbeiten
    # ------------------------------------------------------------------
    @Slot(int, result="QVariantMap")
    def tileInfo(self, index: int) -> dict[str, Any]:  # noqa: N802
        key = self._key(index)
        tile = self.project.data.peek(*key) if key else None
        if tile is None:
            return {"index": index, "number": index + 1, "empty": True, "title": "", "customTitle": "",
                    "color": TILE_COLORS[0], "cover": "", "loop": False, "sourceName": "", "duration": "",
                    "edited": False}
        cover = str(self.project.abs(tile.cover)) if tile.cover else ""
        return {
            "index": index,
            "number": index + 1,
            "empty": tile.is_empty,
            "title": tile.display_title,
            "customTitle": tile.title,
            "color": tile.color,
            "cover": QUrl.fromLocalFile(cover).toString() if cover else "",
            "loop": tile.loop,
            "sourceName": tile.source_name,
            "duration": format_time(tile.duration) if tile.duration else "",
            "edited": tile.is_edited,
        }

    @Slot(int, str)
    def assignAudio(self, index: int, path: str) -> None:  # noqa: N802
        key = self._key(index)
        if key is None:
            return
        self._assign_audio(self._tab, key, Path(to_local_path(path)))

    def _assign_audio(self, tab: ProjectTab, key: Key, src: Path) -> bool:
        project = tab.project
        if project is None:
            self.notify("Bitte zuerst ein Projekt anlegen oder öffnen.", "warning")
            return False
        if src.suffix.lower() not in AUDIO_EXTENSIONS:
            self.notify(f"„{src.name}“ ist kein unterstütztes Audioformat.", "warning")
            return False
        if not src.is_file():
            self.notify(f"Datei nicht gefunden: {src}", "error")
            return False
        if tab is self._tab and self._editor.key == key:
            self._editor.close(keep_session=False)
        self.engine.kill(tab.engine_key(key))
        tab.pcm.pop(key, None)
        project.data.tile(*key)
        rt = tab.rt(key)
        rt.loading = True
        rt.missing = False
        rt.error = ""
        self._refresh(tab, key, "loading", "missing", "errorText")
        token = tab.next_token(key)
        sr = self.engine.samplerate

        def copied(rel: str) -> None:
            if not self._current(tab, project, key, token):
                return
            abs_path = project.abs(rel)
            entry = cache.lookup(project.cache_dir, abs_path, sr)
            if entry is not None:
                finish(rel, entry)
            else:
                self.runner.submit_process(
                    tasks.prepare, str(abs_path), str(project.cache_dir), sr,
                    on_done=lambda d: finish(rel, CacheEntry.from_dict(d)),
                    on_error=failed,
                )

        def finish(rel: str, entry: CacheEntry) -> None:
            if not self._current(tab, project, key, token):
                return
            t = project.data.tile(*key)
            t.audio = rel
            t.original = rel
            t.edit = None
            t.title = ""
            t.duration = entry.duration
            t.source_name = src.name
            self._tile_ready(tab, project, key, token, entry)
            self.settings.remember_audio(src, entry.duration)
            self.settings.save()
            self._refresh_recent_audio()
            self._mark_dirty(tab)

        def failed(msg: str) -> None:
            if not self._current(tab, project, key, token):
                return
            tab.rt(key).loading = False
            self._refresh(tab, key)
            self.notify(f"„{src.name}“ kann nicht geladen werden: {msg}", "error")

        self.runner.submit_thread(project.import_audio, src, on_done=copied, on_error=failed)
        return True

    @Slot(int, str)
    def assignCover(self, index: int, path: str) -> None:  # noqa: N802
        key = self._key(index)
        if key is None:
            return
        self._assign_cover(self._tab, key, Path(to_local_path(path)))

    def _assign_cover(self, tab: ProjectTab, key: Key, src: Path, allow_pending: bool = False) -> bool:
        project = tab.project
        if project is None:
            return False
        tile = project.data.peek(*key)
        loading = tab.rt(key).loading
        if (tile is None or tile.is_empty) and not (allow_pending and loading):
            self.notify("Bitte zuerst eine Audio-Datei auf die Kachel legen – dann das Coverbild.", "warning")
            return False
        if src.suffix.lower() not in IMAGE_EXTENSIONS:
            self.notify("Coverbilder müssen JPG, PNG oder ICO sein.", "warning")
            return False

        def done(target: Path) -> None:
            if not self._current(tab, project):
                return
            t = project.data.tile(*key)
            t.cover = project.rel(target)
            self._refresh(tab, key, "coverUrl")
            self._mark_dirty(tab)

        def failed(msg: str) -> None:
            self.notify(f"Coverbild kann nicht verwendet werden: {msg}", "error")

        self.runner.submit_thread(import_cover, src, project.root / COVER_DIR, on_done=done, on_error=failed)
        return True

    @Slot(int)
    def removeCover(self, index: int) -> None:  # noqa: N802
        key = self._key(index)
        tile = self.project.data.peek(*key) if key else None
        if tile is not None and tile.cover:
            tile.cover = None
            self._tiles.refresh(key, "coverUrl")
            self._mark_dirty()

    @Slot(int, "QVariantList")
    def dropOnTile(self, index: int, urls: list) -> None:  # noqa: N802
        """Drag & Drop: Audiodateien belegen die Kachel (weitere -> nächste freie Kacheln),
        Bilder werden zum Coverbild."""
        tab, project = self._tab, self._tab.project
        key = self._key(index)
        if key is None or project is None:
            if project is None:
                self.notify("Bitte zuerst ein Projekt anlegen oder öffnen.", "warning")
            return
        paths = [Path(to_local_path(u)) for u in urls if to_local_path(u)]
        audio = [p for p in paths if p.suffix.lower() in AUDIO_EXTENSIONS]
        images = [p for p in paths if p.suffix.lower() in IMAGE_EXTENSIONS]
        if not audio and not images:
            self.notify("Nicht unterstützt – bitte Audiodateien oder JPG/PNG/ICO-Bilder ablegen.", "warning")
            return
        if audio:
            self._assign_audio(tab, key, audio[0])
            n = project.data.grid
            free = [divmod(i, n) for i in range(index + 1, n * n)
                    if (t := project.data.peek(*divmod(i, n))) is None or t.is_empty]
            skipped = 0
            for extra in audio[1:]:
                if not free:
                    skipped += 1
                    continue
                self._assign_audio(tab, free.pop(0), extra)
            if skipped:
                self.notify(f"{skipped} Datei(en) übersprungen – keine freien Kacheln mehr.", "warning")
        if images:
            self._assign_cover(tab, key, images[0], allow_pending=bool(audio))

    @Slot(int, int)
    def moveTile(self, source: int, target: int) -> None:  # noqa: N802
        """Drag & Drop im Raster: Kachel ``source`` auf ``target`` legen – belegte Kacheln tauschen.

        Laufende Kacheln spielen am neuen Platz weiter, eine offene Bearbeitung zieht mit um."""
        tab, project = self._tab, self._tab.project
        a, b = self._key(source), self._key(target)
        if project is None or a is None or b is None or a == b or self._show_mode:
            return
        tile = project.data.peek(*a)
        if tile is None or not tile.has_content:
            return
        if self._editor.saving:
            self.notify("Die Bearbeitung wird noch gespeichert – bitte einen Moment warten.", "warning")
            return
        if tab.rt(a).loading or tab.rt(b).loading:
            self.notify("Die Kachel wird noch geladen – bitte gleich noch einmal versuchen.", "info")
            return
        project.data.swap(a, b)
        for store in (tab.pcm, tab.runtime):
            va, vb = store.pop(a, None), store.pop(b, None)
            if va is not None:
                store[b] = va
            if vb is not None:
                store[a] = vb
        ea, eb = tab.engine_key(a), tab.engine_key(b)
        self.engine.rekey({ea: eb, eb: ea})
        self._playing_keys = {eb if k == ea else ea if k == eb else k for k in self._playing_keys}
        mapping = {a: b, b: a}
        self._editor.move_key(mapping)
        if self._undo is not None and self._undo[0] is tab and self._undo[2] in mapping:
            u_tab, u_project, u_key, u_data = self._undo
            self._undo = (u_tab, u_project, mapping[u_key], u_data)  # der leere Platz ist mitgewandert
        self._tiles.refresh(a)
        self._tiles.refresh(b)
        self._mark_dirty(tab)

    @Slot(int)
    def clearTile(self, index: int) -> None:  # noqa: N802
        tab, project = self._tab, self._tab.project
        key = self._key(index)
        if key is None:
            return
        tile = project.data.peek(*key)
        if tile is None:
            return
        self._undo = (tab, project, key, tile.copy())
        tab.next_token(key)
        self.engine.kill(tab.engine_key(key))
        if self._editor.key == key:
            self._editor.close(keep_session=False)
        tab.pcm.pop(key, None)
        project.data.tiles.pop(key, None)
        self._tiles.clear_runtime(key)
        self._tiles.refresh(key)
        self._mark_dirty(tab)
        self.notify(f"Kachel {index + 1} wurde geleert.", "info", "undo")

    @Slot()
    def undoClear(self) -> None:  # noqa: N802
        """Stellt die zuletzt geleerte Kachel wieder her (auch wenn inzwischen die Karte gewechselt wurde)."""
        if self._undo is None:
            return
        tab, project, key, data = self._undo
        self._undo = None
        if not self._current(tab, project):
            return
        if key[0] >= project.data.grid or key[1] >= project.data.grid:
            return
        data.row, data.col = key
        project.data.tiles[key] = data
        self._refresh(tab, key)
        self._load_tile(tab, key)
        self._mark_dirty(tab)
        self.notify("Kachel wiederhergestellt.", "success")

    @Slot(int, str)
    def setTileColor(self, index: int, color: str) -> None:  # noqa: N802
        key = self._key(index)
        if key is None:
            return
        tile = self.project.data.tile(*key)
        if tile.color != color:
            tile.color = color
            self._tiles.refresh(key, "tileColor")
            self._mark_dirty()

    @Slot(int, str)
    def setTileTitle(self, index: int, title: str) -> None:  # noqa: N802
        key = self._key(index)
        if key is None:
            return
        tile = self.project.data.tile(*key)
        title = title.strip()
        if title == tile.display_title and not tile.title:
            return  # unverändert (Dateiname)
        if tile.title != title:
            tile.title = title
            self._tiles.refresh(key, "title")
            self._mark_dirty()

    @Slot(int, bool)
    def setTileLoop(self, index: int, loop: bool) -> None:  # noqa: N802
        key = self._key(index)
        if key is None:
            return
        tile = self.project.data.tile(*key)
        if tile.loop != loop:
            tile.loop = bool(loop)
            self.engine.set_loop(self._tab.engine_key(key), tile.loop)
            self._tiles.refresh(key, "loop")
            self._mark_dirty()

    @Slot(int)
    def editTile(self, index: int) -> None:  # noqa: N802
        key = self._key(index)
        if key is not None:
            self._editor.open_tile(key)

    def apply_edit(self, project: Project, key: Key, params: EditParams | None, rel: str | None,
                   entry: CacheEntry | None) -> None:
        """Legt eine gerenderte Bearbeitung (oder das Original, ``params=None``) auf die Kachel.

        ``project`` ist das Projekt, in dem bearbeitet wurde – die Karte muss nicht mehr aktiv sein."""
        tab = next((t for t in self._tabs if t.project is project), None)
        if tab is None:
            return
        tile = project.data.peek(*key)
        if tile is None or tile.is_empty:
            return
        self.engine.kill(tab.engine_key(key))
        if params is None or rel is None:
            tile.audio = tile.original
            tile.edit = None
            tab.pcm.pop(key, None)
            self._load_tile(tab, key)
        else:
            tile.audio = rel
            tile.edit = params
            tile.duration = entry.duration if entry else tile.duration
            if entry is not None:
                self._tile_ready(tab, project, key, tab.next_token(key), entry)
        self._refresh(tab, key)
        self._mark_dirty(tab)
        self._save_tab(tab, silent=True)

    # ------------------------------------------------------------------
    # Zuletzt verwendete Audiodateien / Projekte
    # ------------------------------------------------------------------
    def _refresh_recent_audio(self) -> None:
        self._recent_audio.set_items(self.settings.recent_audio)
        self.recentChanged.emit()

    def _refresh_recent_projects(self) -> None:
        current = str(self.project.root) if self.project else ""
        open_paths = {str(t.project.root) for t in self._tabs if t.project is not None}
        self._recent_projects.set_items(self.settings.recent_projects, current, open_paths)
        self.recentChanged.emit()

    @Slot("QVariantList")
    def addRecentFiles(self, urls: list) -> None:  # noqa: N802
        added = 0
        for u in urls:
            p = Path(to_local_path(u))
            if p.suffix.lower() in AUDIO_EXTENSIONS and p.is_file():
                self.settings.remember_audio(p)
                added += 1
                self.runner.submit_thread(tasks.probe_file, str(p), on_done=lambda info, p=p: self._probed(p, info))
        if added:
            self.settings.save()
            self._refresh_recent_audio()
        else:
            self.notify("Keine unterstützten Audiodateien gefunden.", "warning")

    def _probed(self, path: Path, info: dict) -> None:
        if self.settings.update_audio_duration(path, float(info.get("duration") or 0.0)):
            self.settings.save()
            self._refresh_recent_audio()

    @Slot(str)
    def removeRecent(self, path: str) -> None:  # noqa: N802
        self.settings.forget_audio(path)
        self.settings.save()
        self._refresh_recent_audio()

    @Slot(result=str)
    def audioFilterString(self) -> str:  # noqa: N802
        exts = " ".join(f"*{e}" for e in sorted(AUDIO_EXTENSIONS))
        return f"Audiodateien ({exts})"

    # ------------------------------------------------------------------
    # Show-Modus & Audio-Einstellungen
    # ------------------------------------------------------------------
    @Slot(bool)
    def setShowMode(self, enabled: bool) -> None:  # noqa: N802
        self._set("_show_mode", bool(enabled), "showModeChanged")

    # ------------------------------------------------------------------
    # Darstellung (Dunkel / Hell / wie System)
    # ------------------------------------------------------------------
    @Slot(str)
    def setThemeMode(self, mode: str) -> None:  # noqa: N802
        if mode not in THEME_MODES:
            return
        if self.settings.theme != mode:
            self.settings.theme = mode
            self.settings.save()
        self._theme_mode = mode
        self._dark = appearance.apply_color_scheme(mode)
        self.themeChanged.emit()

    @Slot()
    def toggleTheme(self) -> None:  # noqa: N802
        """Schnellumschalter in der Kopfleiste: wechselt zwischen Dunkel und Hell."""
        self.setThemeMode("light" if self._dark else "dark")

    @Slot(bool)
    def setFullscreen(self, enabled: bool) -> None:  # noqa: N802
        """Vollbild ein/aus (Schalter, F11 oder Fenstersystem) – wird für den nächsten Start gemerkt."""
        enabled = bool(enabled)
        if enabled == self._fullscreen:
            return
        self._fullscreen = enabled
        self.settings.fullscreen = enabled
        self.settings.save()
        self.fullscreenChanged.emit()

    def start_fullscreen(self) -> None:
        """``--fullscreen``: diesmal im Vollbild starten, ohne die gespeicherte Einstellung zu ändern."""
        self._set("_fullscreen", True, "fullscreenChanged")

    def _on_system_scheme(self, *_args) -> None:
        if self._theme_mode == "system":
            dark = appearance.system_prefers_dark()
            if dark != self._dark:
                self._dark = dark
                self.themeChanged.emit()

    @Slot(int)
    def setOutputDevice(self, index: int) -> None:  # noqa: N802
        if index <= 0:
            self.settings.audio_device = None
            self.settings.audio_hostapi = None
        else:
            devices = list_output_devices()
            if index - 1 < len(devices):
                d = devices[index - 1]
                self.settings.audio_device = d.name
                self.settings.audio_hostapi = d.hostapi
        self.settings.save()
        self.restart_audio()

    @Slot(int)
    def setBufferFrames(self, frames: int) -> None:  # noqa: N802
        self.settings.buffer_frames = int(frames)
        self.settings.save()
        self.restart_audio()

    def restart_audio(self) -> None:
        old_sr = self.engine.samplerate
        self._editor.close(keep_session=True)
        self.engine.start(self.settings.audio_device, self.settings.audio_hostapi, self.settings.buffer_frames)
        self.engine.stop_fade_ms = self.settings.stop_fade_ms
        self.audioChanged.emit()
        if self.engine.samplerate != old_sr:
            for tab in self._tabs:
                if tab.project is not None:
                    tab.pcm.clear()
                    self._load_all_tiles(tab)
        if self.engine.error:
            self.notify(f"Audiogerät nicht verfügbar: {self.engine.error}", "error")
        else:
            self.notify(f"Audioausgabe: {self.engine.device_name}", "info")

    # ------------------------------------------------------------------
    # Beenden
    # ------------------------------------------------------------------
    def prepare_for_update(self) -> bool:
        """Vor dem Installieren eines Updates: Wiedergabe stoppen, alles speichern,
        Worker-Prozesse beenden (damit der Installer alle Programmdateien ersetzen kann)."""
        self.engine.stop_all()
        ok = self.saveBeforeClose()
        if ok:
            self.runner.stop_processes()
        return ok

    @Slot(result=bool)
    def saveBeforeClose(self) -> bool:  # noqa: N802
        """Wird beim Schließen des Fensters aufgerufen: alle offenen Projekte sicher speichern."""
        ok = True
        for tab in self._tabs:
            if tab.project is not None:
                ok = self._save_tab(tab, silent=False) and ok
        if self.project is not None:
            self._editor.write_session(force=True)
        self._persist_tabs()
        return ok

    @Slot()
    def shutdown(self) -> None:
        if self._closing:
            return
        self._closing = True
        self._ui_timer.stop()
        self._autosave_timer.stop()
        self._debounce.stop()
        for tab in self._tabs:
            try:
                if tab.project is not None and tab.dirty:
                    tab.project.save()
            except Exception:
                log.exception("Speichern beim Beenden fehlgeschlagen")
        try:
            self._editor.write_session(force=True)
        except Exception:
            log.exception("Zwischenstand beim Beenden nicht gespeichert")
        self.settings.save()
        self._updater.shutdown()
        self.engine.shutdown()
        self._master.shutdown()
        self.runner.shutdown()
