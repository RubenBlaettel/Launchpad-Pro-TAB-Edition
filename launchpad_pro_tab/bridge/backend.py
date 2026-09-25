"""Zentrale QML-Schnittstelle ("Backend").

Die Oberfläche spricht ausschließlich mit diesem Objekt (plus ``editor`` und ``master``).
Es verbindet Projektverwaltung, Audio-Engine, Hintergrundaufgaben und Einstellungen.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
from PySide6.QtCore import Property, QObject, QTimer, QUrl, Signal, Slot

from ..audio import cache, tasks
from ..audio.cache import CacheEntry
from ..audio.engine import AudioEngine
from ..audio.output import list_output_devices
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
from ..core.settings import AppSettings
from ..core.util import format_time
from .covers import import_cover
from .editor import EditorController
from .models import RecentAudioModel, RecentProjectsModel, TileModel
from .qtutil import PropertyObject, rprop, to_local_path
from .tasks import TaskRunner
from .volume import MasterVolumeController

log = logging.getLogger(__name__)

Key = tuple[int, int]
BUFFER_OPTIONS = (0, 128, 256, 512, 1024, 2048)


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

    def __init__(self, engine: AudioEngine, runner: TaskRunner, settings: AppSettings,
                 documents_dir: Path | None = None, volume: MasterVolumeController | None = None,
                 parent: QObject | None = None):
        super().__init__(parent)
        self.engine = engine
        self.runner = runner
        self.settings = settings
        self.project: Project | None = None
        self._documents_dir = documents_dir
        self._tiles = TileModel(self)
        self._recent_audio = RecentAudioModel(self)
        self._recent_projects = RecentProjectsModel(self)
        self._master = volume or MasterVolumeController(self)
        self._editor = EditorController(self, self)
        self._pcm: dict[Key, np.ndarray] = {}
        self._tokens: dict[Key, int] = {}
        self._playing_keys: set[Key] = set()
        self._undo: tuple[Key, TileData] | None = None
        self._closing = False

        self._has_project = False
        self._project_name = ""
        self._project_path = ""
        self._grid = GRID_DEFAULT
        self._dirty = False
        self._save_text = ""
        self._busy = ""
        self._active_count = 0
        self._level_l = 0.0
        self._level_r = 0.0
        self._limiting = False
        self._show_mode = False

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

    def start(self) -> None:
        self._ui_timer.start()
        self._autosave_timer.start()
        self._clock.start()

    # ------------------------------------------------------------------
    # Properties für QML
    # ------------------------------------------------------------------
    tiles = Property(QObject, lambda self: self._tiles, constant=True)
    recentAudio = Property(QObject, lambda self: self._recent_audio, constant=True)
    recentProjects = Property(QObject, lambda self: self._recent_projects, constant=True)
    editor = Property(QObject, lambda self: self._editor, constant=True)
    master = Property(QObject, lambda self: self._master, constant=True)

    hasProject = rprop(bool, "_has_project", projectChanged)
    projectName = rprop(str, "_project_name", projectChanged)
    projectPath = rprop(str, "_project_path", projectChanged)
    gridSize = rprop(int, "_grid", gridChanged)
    dirty = rprop(bool, "_dirty", saveStateChanged)
    saveStateText = rprop(str, "_save_text", saveStateChanged)
    busyText = rprop(str, "_busy", busyChanged)
    activeCount = rprop(int, "_active_count", activeCountChanged)
    levelL = rprop(float, "_level_l", levelsChanged)
    levelR = rprop(float, "_level_r", levelsChanged)
    limiting = rprop(bool, "_limiting", levelsChanged)
    showMode = rprop(bool, "_show_mode", showModeChanged)

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
        self._activate(project)
        self.notify(f"Projekt „{project.name}“ wurde angelegt.", "success")
        return True

    @Slot(str, result=bool)
    def openProject(self, path: str) -> bool:  # noqa: N802
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
                if self.project is not None and p.resolve() in (self.project.root, self.project.file):
                    self.notify("Dieses Projekt ist bereits geöffnet.", "info")
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
        self._activate(project)
        return True

    @Slot(str)
    def forgetProject(self, path: str) -> None:  # noqa: N802
        self.settings.forget_project(path)
        self.settings.save()
        self._refresh_recent_projects()

    def _activate(self, project: Project) -> None:
        """Wechselt auf ``project`` (das bisherige wird vorher sicher gespeichert)."""
        if self.project is not None:
            self._save_now(silent=True)
            self._editor.close(keep_session=True)
            self.engine.stop_all()
        self._pcm.clear()
        self._tokens.clear()
        self._playing_keys.clear()
        self._undo = None
        self.project = project
        self._tiles.set_project(project.data, project.root)
        self._has_project = True
        self._project_name = project.name
        self._project_path = str(project.root)
        self._grid = project.data.grid
        self._dirty = False
        self.projectChanged.emit()
        self.gridChanged.emit()
        self.settings.remember_project(project.root, project.name)
        self.settings.save()
        self._refresh_recent_projects()
        self._update_save_text()
        self._load_all_tiles()
        self._schedule_cleanup(project)
        state = project.read_edit_session()
        if state:
            if self._editor.restore_session(state):
                self.notify("Die letzte ungespeicherte Bearbeitung wurde wiederhergestellt.", "info")

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
        if self.project is None:
            return False
        try:
            self.project.save()
        except ProjectError as exc:
            if silent:
                self.notify(str(exc), "error")
            else:
                self._error("Speichern fehlgeschlagen", str(exc))
            return False
        self._editor.write_session()
        self._dirty = False
        self._last_saved = datetime.now()
        self._update_save_text()
        return True

    def _update_save_text(self) -> None:
        if self.project is None:
            text = ""
        elif self._dirty:
            text = "Ungespeicherte Änderungen"
        else:
            last = getattr(self, "_last_saved", None)
            text = f"Gespeichert um {last:%H:%M:%S}" if last else "Gespeichert"
        self._save_text = text
        self.saveStateChanged.emit()

    def _mark_dirty(self) -> None:
        if not self._dirty:
            self._dirty = True
            self._update_save_text()
        self._debounce.start()

    def _autosave(self) -> None:
        if self.project is not None and self._dirty:
            self._save_now(silent=True)

    @Slot(str)
    def saveProjectAs(self, folder: str) -> None:  # noqa: N802
        if self.project is None:
            return
        target = to_local_path(folder)
        if not target:
            return
        project = self.project
        self._save_now(silent=True)
        self._set_busy("Projekt wird kopiert …")

        def done(new_project: Project) -> None:
            self._set_busy("")
            self._activate(new_project)
            self.notify(f"Projekt gespeichert unter: {new_project.root}", "success")

        def failed(msg: str) -> None:
            self._set_busy("")
            self._error("Speichern unter fehlgeschlagen", msg)

        self.runner.submit_thread(project.save_as, Path(target), None, False, on_done=done, on_error=failed)

    @Slot(str)
    def exportProject(self, file_url: str) -> None:  # noqa: N802
        if self.project is None:
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

        self.runner.submit_thread(self.project.export_zip, Path(target), False, on_done=done, on_error=failed)

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
        if self.project is None:
            return
        n = clamp_grid(n)
        old = self.project.data.grid
        if n == old:
            return
        for key in [k for k in list(self._pcm) if k[0] >= n or k[1] >= n]:
            self.engine.kill(key)
            self._pcm.pop(key, None)
        editor_key = self._editor.key
        if editor_key is not None and (editor_key[0] >= n or editor_key[1] >= n):
            self._editor.close(keep_session=False)
        removed = self.project.data.resize(n)
        self._grid = n
        self._tiles.reset()
        self.gridChanged.emit()
        self._mark_dirty()
        if n < old and removed:
            self.notify(f"Raster auf {n}×{n} verkleinert – {len(removed)} Kachel(n) verworfen.", "warning")
        else:
            self.notify(f"Raster auf {n}×{n} geändert.", "info")

    # ------------------------------------------------------------------
    # Kacheln: Laden
    # ------------------------------------------------------------------
    def _key(self, index: int) -> Key | None:
        if self.project is None:
            return None
        n = self.project.data.grid
        if not 0 <= index < n * n:
            return None
        return divmod(int(index), n)

    def _next_token(self, key: Key) -> int:
        token = self._tokens.get(key, 0) + 1
        self._tokens[key] = token
        return token

    def _load_all_tiles(self) -> None:
        assert self.project is not None
        for key, tile in list(self.project.data.tiles.items()):
            if tile.audio:
                self._load_tile(key)

    def _load_tile(self, key: Key) -> None:
        project = self.project
        tile = project.data.peek(*key) if project else None
        if project is None or tile is None or not tile.audio:
            return
        path = project.abs(tile.audio)
        rt = self._tiles.runtime(key)
        if path is None or not path.exists():
            rt.missing = True
            rt.loading = False
            self._tiles.refresh(key, "missing", "loading")
            return
        rt.missing = False
        token = self._next_token(key)
        entry = cache.lookup(project.cache_dir, path, self.engine.samplerate)
        if entry is not None:
            self._tile_ready(project, key, token, entry)
            return
        rt.loading = True
        self._tiles.refresh(key, "loading", "missing")
        self.runner.submit_process(
            tasks.prepare, str(path), str(project.cache_dir), self.engine.samplerate,
            on_done=lambda d: self._tile_ready(project, key, token, CacheEntry.from_dict(d)),
            on_error=lambda msg: self._tile_failed(project, key, token, msg),
        )

    def _tile_ready(self, project: Project, key: Key, token: int, entry: CacheEntry) -> None:
        if project is not self.project or self._tokens.get(key) != token:
            return
        tile = project.data.peek(*key)
        if tile is None or tile.is_empty:
            return
        pcm = cache.open_pcm(entry)
        cache.warm(pcm, 0, int(entry.samplerate * 2))  # Anfang vorladen -> sofortiger Start
        self._pcm[key] = pcm
        if abs(tile.duration - entry.duration) > 0.01:
            tile.duration = entry.duration
        rt = self._tiles.runtime(key)
        rt.loading = False
        rt.missing = False
        rt.error = ""
        self._tiles.refresh(key)

    def _tile_failed(self, project: Project, key: Key, token: int, message: str) -> None:
        if project is not self.project or self._tokens.get(key) != token:
            return
        rt = self._tiles.runtime(key)
        rt.loading = False
        rt.error = message
        self._tiles.refresh(key, "loading", "errorText")
        self.notify(f"Audiodatei kann nicht geladen werden: {message}", "error")

    # ------------------------------------------------------------------
    # Kacheln: Wiedergabe
    # ------------------------------------------------------------------
    @Slot(int)
    def triggerTile(self, index: int) -> None:  # noqa: N802
        key = self._key(index)
        if key is None:
            return
        tile = self.project.data.peek(*key)
        if tile is None or tile.is_empty:
            return
        pcm = self._pcm.get(key)
        rt = self._tiles.runtime(key)
        if pcm is None:
            if rt.missing:
                self.notify(f"Audiodatei fehlt: {tile.audio}", "error")
            elif rt.loading:
                self.notify("Die Audiodatei wird noch vorbereitet …", "info")
            elif rt.error:
                self.notify(f"Audiodatei fehlerhaft: {rt.error}", "error")
            return
        self.engine.toggle(key, pcm, tile.loop)
        # Sofortiges optisches Feedback; der UI-Timer gleicht danach mit der Engine ab.
        if key in self.engine.snapshot:
            rt.playing = False
            rt.progress = 0.0
        else:
            rt.playing = True
            rt.progress = 0.0
            rt.remaining = tile.duration
        self._tiles.refresh(key, "playing", "progress", "remainingText")

    @Slot()
    def stopAll(self) -> None:  # noqa: N802
        self.engine.stop_all()
        self._editor.pause()

    def _tick(self) -> None:
        engine = self.engine
        snap = engine.snapshot
        sr = float(engine.samplerate or 48000)
        keys = set(snap)
        for key in keys | self._playing_keys:
            rt = self._tiles.runtime(key)
            if key in snap:
                pos, total = snap[key]
                progress = pos / total if total else 0.0
                remaining = (total - pos) / sr
                changed = (not rt.playing) or abs(progress - rt.progress) > 0.0005
                rt.playing = True
                rt.progress = progress
                if int(remaining) != int(rt.remaining) or changed:
                    rt.remaining = remaining
                    self._tiles.refresh(key, "playing", "progress", "remainingText")
            elif rt.playing:
                rt.playing = False
                rt.progress = 0.0
                self._tiles.refresh(key, "playing", "progress", "remainingText")
        self._playing_keys = keys
        count = len(keys)
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
        self._assign_audio(key, Path(to_local_path(path)))

    def _assign_audio(self, key: Key, src: Path) -> bool:
        project = self.project
        if project is None:
            self.notify("Bitte zuerst ein Projekt anlegen oder öffnen.", "warning")
            return False
        if src.suffix.lower() not in AUDIO_EXTENSIONS:
            self.notify(f"„{src.name}“ ist kein unterstütztes Audioformat.", "warning")
            return False
        if not src.is_file():
            self.notify(f"Datei nicht gefunden: {src}", "error")
            return False
        if self._editor.key == key:
            self._editor.close(keep_session=False)
        self.engine.kill(key)
        self._pcm.pop(key, None)
        tile = project.data.tile(*key)
        rt = self._tiles.runtime(key)
        rt.loading = True
        rt.missing = False
        rt.error = ""
        self._tiles.refresh(key, "loading", "missing", "errorText")
        token = self._next_token(key)
        sr = self.engine.samplerate

        def copied(rel: str) -> None:
            if project is not self.project or self._tokens.get(key) != token:
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
            if project is not self.project or self._tokens.get(key) != token:
                return
            t = project.data.tile(*key)
            t.audio = rel
            t.original = rel
            t.edit = None
            t.title = ""
            t.duration = entry.duration
            t.source_name = src.name
            self._tile_ready(project, key, token, entry)
            self.settings.remember_audio(src, entry.duration)
            self.settings.save()
            self._refresh_recent_audio()
            self._mark_dirty()

        def failed(msg: str) -> None:
            if project is not self.project or self._tokens.get(key) != token:
                return
            rt2 = self._tiles.runtime(key)
            rt2.loading = False
            self._tiles.refresh(key)
            self.notify(f"„{src.name}“ kann nicht geladen werden: {msg}", "error")

        del tile
        self.runner.submit_thread(project.import_audio, src, on_done=copied, on_error=failed)
        return True

    @Slot(int, str)
    def assignCover(self, index: int, path: str) -> None:  # noqa: N802
        key = self._key(index)
        if key is None:
            return
        self._assign_cover(key, Path(to_local_path(path)))

    def _assign_cover(self, key: Key, src: Path, allow_pending: bool = False) -> bool:
        project = self.project
        if project is None:
            return False
        tile = project.data.peek(*key)
        loading = self._tiles.runtime(key).loading
        if (tile is None or tile.is_empty) and not (allow_pending and loading):
            self.notify("Bitte zuerst eine Audio-Datei auf die Kachel legen – dann das Coverbild.", "warning")
            return False
        if src.suffix.lower() not in IMAGE_EXTENSIONS:
            self.notify("Coverbilder müssen JPG, PNG oder ICO sein.", "warning")
            return False

        def done(target: Path) -> None:
            if project is not self.project:
                return
            t = project.data.tile(*key)
            t.cover = project.rel(target)
            self._tiles.refresh(key, "coverUrl")
            self._mark_dirty()

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
        key = self._key(index)
        if key is None or self.project is None:
            if self.project is None:
                self.notify("Bitte zuerst ein Projekt anlegen oder öffnen.", "warning")
            return
        paths = [Path(to_local_path(u)) for u in urls if to_local_path(u)]
        audio = [p for p in paths if p.suffix.lower() in AUDIO_EXTENSIONS]
        images = [p for p in paths if p.suffix.lower() in IMAGE_EXTENSIONS]
        if not audio and not images:
            self.notify("Nicht unterstützt – bitte Audiodateien oder JPG/PNG/ICO-Bilder ablegen.", "warning")
            return
        if audio:
            self._assign_audio(key, audio[0])
            n = self.project.data.grid
            free = [divmod(i, n) for i in range(index + 1, n * n)
                    if (t := self.project.data.peek(*divmod(i, n))) is None or t.is_empty]
            skipped = 0
            for extra in audio[1:]:
                if not free:
                    skipped += 1
                    continue
                self._assign_audio(free.pop(0), extra)
            if skipped:
                self.notify(f"{skipped} Datei(en) übersprungen – keine freien Kacheln mehr.", "warning")
        if images:
            self._assign_cover(key, images[0], allow_pending=bool(audio))

    @Slot(int)
    def clearTile(self, index: int) -> None:  # noqa: N802
        key = self._key(index)
        if key is None:
            return
        tile = self.project.data.peek(*key)
        if tile is None:
            return
        self._undo = (key, tile.copy())
        self._next_token(key)
        self.engine.kill(key)
        if self._editor.key == key:
            self._editor.close(keep_session=False)
        self._pcm.pop(key, None)
        self.project.data.tiles.pop(key, None)
        self._tiles.clear_runtime(key)
        self._tiles.refresh(key)
        self._mark_dirty()
        self.notify(f"Kachel {index + 1} wurde geleert.", "info", "undo")

    @Slot()
    def undoClear(self) -> None:  # noqa: N802
        if self._undo is None or self.project is None:
            return
        key, data = self._undo
        self._undo = None
        if key[0] >= self.project.data.grid or key[1] >= self.project.data.grid:
            return
        self.project.data.tiles[key] = data
        self._tiles.refresh(key)
        self._load_tile(key)
        self._mark_dirty()
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
            self.engine.set_loop(key, tile.loop)
            self._tiles.refresh(key, "loop")
            self._mark_dirty()

    @Slot(int)
    def editTile(self, index: int) -> None:  # noqa: N802
        key = self._key(index)
        if key is not None:
            self._editor.open_tile(key)

    def apply_edit(self, key: Key, params: EditParams | None, rel: str | None, entry: CacheEntry | None) -> None:
        """Legt eine gerenderte Bearbeitung (oder das Original, ``params=None``) auf die Kachel."""
        project = self.project
        if project is None:
            return
        tile = project.data.peek(*key)
        if tile is None or tile.is_empty:
            return
        self.engine.kill(key)
        if params is None or rel is None:
            tile.audio = tile.original
            tile.edit = None
            self._pcm.pop(key, None)
            self._load_tile(key)
        else:
            tile.audio = rel
            tile.edit = params
            tile.duration = entry.duration if entry else tile.duration
            if entry is not None:
                self._tile_ready(project, key, self._next_token(key), entry)
        self._tiles.refresh(key)
        self._mark_dirty()
        self._save_now(silent=True)

    # ------------------------------------------------------------------
    # Zuletzt verwendete Audiodateien
    # ------------------------------------------------------------------
    def _refresh_recent_audio(self) -> None:
        self._recent_audio.set_items(self.settings.recent_audio)
        self.recentChanged.emit()

    def _refresh_recent_projects(self) -> None:
        current = str(self.project.root) if self.project else ""
        self._recent_projects.set_items(self.settings.recent_projects, current)
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
        if self.engine.samplerate != old_sr and self.project is not None:
            self._pcm.clear()
            self._load_all_tiles()
        if self.engine.error:
            self.notify(f"Audiogerät nicht verfügbar: {self.engine.error}", "error")
        else:
            self.notify(f"Audioausgabe: {self.engine.device_name}", "info")

    # ------------------------------------------------------------------
    # Beenden
    # ------------------------------------------------------------------
    @Slot(result=bool)
    def saveBeforeClose(self) -> bool:  # noqa: N802
        """Wird beim Schließen des Fensters aufgerufen: Projekt sicher speichern."""
        if self.project is None:
            self.settings.save()
            return True
        ok = self._save_now(silent=False)
        self._editor.write_session(force=True)
        self.settings.save()
        return ok

    @Slot()
    def shutdown(self) -> None:
        if self._closing:
            return
        self._closing = True
        self._ui_timer.stop()
        self._autosave_timer.stop()
        self._debounce.stop()
        try:
            if self.project is not None and self._dirty:
                self.project.save()
            self._editor.write_session(force=True)
        except Exception:
            log.exception("Speichern beim Beenden fehlgeschlagen")
        self.settings.save()
        self.engine.shutdown()
        self._master.shutdown()
        self.runner.shutdown()
