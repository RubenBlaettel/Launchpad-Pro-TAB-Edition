"""Controller für den Bereich "Bearbeiten & Schneiden".

Arbeitet nicht-destruktiv: Es wird immer die *Originaldatei* der Kachel geladen; Schnitt,
Tempo und Lautstärke sind Parameter (``EditParams``). Beim Speichern wird daraus eine neue
Datei unter ``audio/bearbeitet/`` gerendert und auf die Kachel gelegt – das Original bleibt
erhalten, die Parameter werden im Projekt gespeichert. Dadurch kann eine Bearbeitung
später jederzeit wieder geöffnet und angepasst werden.

Während der Bearbeitung wird der Zwischenstand alle 5 s in ``.autosave/`` geschrieben und
nach einem Absturz automatisch wiederhergestellt.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np
from PySide6.QtCore import QObject, QTimer, Signal, Slot

from ..audio import cache, tasks
from ..audio.cache import CacheEntry
from ..core.constants import (
    EDIT_AUTOSAVE_INTERVAL_MS,
    GAIN_MAX,
    GAIN_MIN,
    MIN_SELECTION_S,
    SPEED_MAX,
    SPEED_MIN,
    STEP_SECONDS,
)
from ..core.models import EditParams, clamp
from ..core.util import format_time, now_iso
from .qtutil import PropertyObject, rprop

if TYPE_CHECKING:  # pragma: no cover
    from .backend import Backend

log = logging.getLogger(__name__)

MIN_VIEW_S = 0.05


class EditorController(PropertyObject):
    activeChanged = Signal()
    loadingChanged = Signal()
    savingChanged = Signal()
    infoChanged = Signal()
    positionChanged = Signal()
    playingChanged = Signal()
    selectionChanged = Signal()
    speedChanged = Signal()
    gainChanged = Signal()
    viewChanged = Signal()

    def __init__(self, backend: "Backend", parent: QObject | None = None):
        super().__init__(parent)
        self._backend = backend
        self._wave = None
        self._key: tuple[int, int] | None = None
        self._original_rel: str | None = None
        self._entry: CacheEntry | None = None
        self._pcm: np.ndarray | None = None
        self._peaks: np.ndarray | None = None
        self._sr = 48000
        self._token = 0
        self._seek_guard = 0.0
        self._session_dirty = False
        self._reset_values()
        self._autosave = QTimer(self)
        self._autosave.setInterval(EDIT_AUTOSAVE_INTERVAL_MS)
        self._autosave.timeout.connect(self.write_session)

    def _reset_values(self) -> None:
        self._active = False
        self._loading = False
        self._saving = False
        self._tile_label = ""
        self._file_name = ""
        self._duration = 0.0
        self._position = 0.0
        self._playing = False
        self._sel_start = 0.0
        self._sel_end = 0.0
        self._speed = 1.0
        self._gain = 1.0
        self._view_start = 0.0
        self._view_end = 1.0

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------
    active = rprop(bool, "_active", activeChanged)
    loading = rprop(bool, "_loading", loadingChanged)
    saving = rprop(bool, "_saving", savingChanged)
    tileLabel = rprop(str, "_tile_label", infoChanged)
    fileName = rprop(str, "_file_name", infoChanged)
    duration = rprop(float, "_duration", infoChanged)
    position = rprop(float, "_position", positionChanged)
    playing = rprop(bool, "_playing", playingChanged)
    selStart = rprop(float, "_sel_start", selectionChanged)
    selEnd = rprop(float, "_sel_end", selectionChanged)
    speed = rprop(float, "_speed", speedChanged)
    gain = rprop(float, "_gain", gainChanged)
    viewStart = rprop(float, "_view_start", viewChanged)
    viewEnd = rprop(float, "_view_end", viewChanged)

    @property
    def key(self) -> tuple[int, int] | None:
        return self._key if (self._active or self._loading) else None

    # ------------------------------------------------------------------
    # Formatierte Texte für die Oberfläche
    # ------------------------------------------------------------------
    @Slot(float, result=str)
    def fmt(self, seconds: float) -> str:
        return format_time(seconds, with_tenths=True)

    # ------------------------------------------------------------------
    # Öffnen / Schließen
    # ------------------------------------------------------------------
    @Slot(QObject)
    def attachWaveform(self, item: QObject) -> None:  # noqa: N802
        self._wave = item
        if self._active and self._peaks is not None:
            item.set_source(self._peaks, self._pcm, self._sr, self._duration)

    def open_tile(self, key: tuple[int, int], restore: dict[str, Any] | None = None) -> bool:
        backend = self._backend
        project = backend.project
        if project is None:
            return False
        tile = project.data.peek(*key)
        if tile is None or tile.is_empty:
            return False
        if self._active or self._loading:
            self.close(keep_session=False)
        original_rel = tile.original or tile.audio
        src = project.abs(original_rel)
        if src is None or not src.exists():
            backend.notify("Die Originaldatei der Kachel wurde nicht gefunden.", "error")
            return False
        self._key = key
        self._original_rel = original_rel
        self._token += 1
        token = self._token
        index = project.data.index_of(*key) + 1
        self._tile_label = f"Kachel {index} · {tile.display_title}"
        self._file_name = tile.source_name or src.name
        self.infoChanged.emit()
        self._set("_loading", True, "loadingChanged")
        params: EditParams | None = None
        if restore and restore.get("params"):
            params = EditParams.from_dict(restore["params"])
        elif tile.edit is not None and tile.is_edited:
            params = tile.edit
        sr = backend.engine.samplerate
        entry = cache.lookup(project.cache_dir, src, sr)
        if entry is not None:
            self._on_loaded(token, entry, params, restore)
        else:
            backend.runner.submit_process(
                tasks.prepare, str(src), str(project.cache_dir), sr,
                on_done=lambda d: self._on_loaded(token, CacheEntry.from_dict(d), params, restore),
                on_error=lambda msg: self._on_load_failed(token, msg),
            )
        return True

    def _on_load_failed(self, token: int, message: str) -> None:
        if token != self._token:
            return
        self._backend.notify(f"Audiodatei kann nicht bearbeitet werden: {message}", "error")
        self.close(keep_session=False)

    def _on_loaded(self, token: int, entry: CacheEntry, params: EditParams | None,
                   restore: dict[str, Any] | None) -> None:
        if token != self._token or self._key is None:
            return
        engine = self._backend.engine
        self._entry = entry
        self._pcm = cache.open_pcm(entry)
        self._peaks = cache.load_peaks(entry)
        self._sr = entry.samplerate
        dur = entry.duration
        p = (params or EditParams()).normalized(dur)
        self._duration = dur
        self.infoChanged.emit()
        self._sel_start, self._sel_end = p.start, float(p.end if p.end is not None else dur)
        self.selectionChanged.emit()
        self._set("_speed", p.speed, "speedChanged")
        self._set("_gain", p.gain, "gainChanged")
        v0, v1 = 0.0, dur
        if restore and isinstance(restore.get("view"), list) and len(restore["view"]) == 2:
            v0, v1 = self._clamp_view(float(restore["view"][0]), float(restore["view"][1]))
        self._view_start, self._view_end = v0, v1
        self.viewChanged.emit()
        pos = self._sel_start
        if restore and restore.get("position") is not None:
            pos = clamp(float(restore["position"]), self._sel_start, self._sel_end)
        engine.preview_load(self._pcm)
        engine.preview_region(self._frame(self._sel_start), self._frame(self._sel_end))
        engine.preview_speed(self._speed)
        engine.preview_gain(self._gain)
        engine.preview_seek(self._frame(pos))
        self._position = pos
        self._seek_guard = time.monotonic() + 0.25
        self.positionChanged.emit()
        if self._wave is not None:
            self._wave.set_source(self._peaks, self._pcm, self._sr, dur)
        self._set("_loading", False, "loadingChanged")
        self._set("_active", True, "activeChanged")
        self._session_dirty = True
        self.write_session()
        self._autosave.start()

    def close(self, keep_session: bool = False) -> None:
        """Beendet die Bearbeitung und setzt alles auf Standardwerte zurück (ausgegraut)."""
        self._token += 1
        self._autosave.stop()
        if keep_session and self._active:
            self.write_session(force=True)
        engine = self._backend.engine
        engine.preview_load(None)
        project = self._backend.project
        if not keep_session and project is not None:
            project.clear_edit_session()
        if self._wave is not None:
            self._wave.clear_source()
        self._key = None
        self._original_rel = None
        self._entry = None
        self._pcm = None
        self._peaks = None
        self._reset_values()
        for sig in (self.loadingChanged, self.savingChanged, self.infoChanged, self.positionChanged,
                    self.playingChanged, self.selectionChanged, self.speedChanged, self.gainChanged,
                    self.viewChanged, self.activeChanged):
            sig.emit()

    @Slot()
    def cancel(self) -> None:
        if self._active or self._loading:
            self.close(keep_session=False)
            self._backend.notify("Bearbeitung verworfen.", "info")

    # ------------------------------------------------------------------
    # Zwischenstand (Absturzsicherung)
    # ------------------------------------------------------------------
    def _touch(self) -> None:
        self._session_dirty = True

    def session_state(self) -> dict[str, Any] | None:
        if not self._active or self._key is None:
            return None
        return {
            "tile": list(self._key),
            "original": self._original_rel,
            "params": self._params().to_dict(),
            "position": round(self._position, 4),
            "view": [round(self._view_start, 4), round(self._view_end, 4)],
            "saved": now_iso(),
        }

    @Slot()
    def write_session(self, force: bool = False) -> None:
        if not (self._session_dirty or force):
            return
        state = self.session_state()
        project = self._backend.project
        if state is None or project is None:
            return
        project.write_edit_session(state)
        self._session_dirty = False

    def restore_session(self, state: dict[str, Any]) -> bool:
        project = self._backend.project
        try:
            key = (int(state["tile"][0]), int(state["tile"][1]))
        except (KeyError, TypeError, ValueError, IndexError):
            return False
        if project is None:
            return False
        tile = project.data.peek(*key)
        if tile is None or tile.is_empty or (tile.original or tile.audio) != state.get("original"):
            project.clear_edit_session()
            return False
        return self.open_tile(key, restore=state)

    # ------------------------------------------------------------------
    # Wiedergabe-Steuerung (Vorschau)
    # ------------------------------------------------------------------
    def _frame(self, seconds: float) -> int:
        return int(round(seconds * self._sr))

    def tick(self) -> None:
        """Wird vom UI-Timer (~30 Hz) aufgerufen."""
        if not self._active:
            return
        playing, frame = self._backend.engine.preview_state
        if time.monotonic() >= self._seek_guard:
            pos = frame / float(self._sr)
            if abs(pos - self._position) > 1e-4:
                self._position = pos
                self.positionChanged.emit()
            self._set("_playing", bool(playing), "playingChanged")

    def on_preview_end(self) -> None:
        self._set("_playing", False, "playingChanged")
        self._position = self._sel_start
        self._seek_guard = time.monotonic() + 0.15
        self.positionChanged.emit()

    @Slot()
    def play(self) -> None:
        if not self._active:
            return
        if self._position >= self._sel_end - 0.02 or self._position < self._sel_start:
            self.seek(self._sel_start)
        self._backend.engine.preview_play()
        self._seek_guard = time.monotonic() + 0.12
        self._set("_playing", True, "playingChanged")

    @Slot()
    def pause(self) -> None:
        if not self._active:
            return
        self._backend.engine.preview_pause()
        self._seek_guard = time.monotonic() + 0.12
        self._set("_playing", False, "playingChanged")

    @Slot()
    def togglePlay(self) -> None:  # noqa: N802
        self.pause() if self._playing else self.play()

    @Slot(float)
    def seek(self, seconds: float) -> None:
        if not self._active:
            return
        t = clamp(float(seconds), self._sel_start, max(self._sel_start, self._sel_end - 0.001))
        self._backend.engine.preview_seek(self._frame(t))
        self._position = t
        self._seek_guard = time.monotonic() + 0.15
        self.positionChanged.emit()
        self._touch()

    @Slot()
    def stepBack(self) -> None:  # noqa: N802
        self.seek(self._position - STEP_SECONDS)

    @Slot()
    def stepForward(self) -> None:  # noqa: N802
        self.seek(self._position + STEP_SECONDS)

    @Slot()
    def toStart(self) -> None:  # noqa: N802
        self.seek(self._sel_start)

    @Slot()
    def reset(self) -> None:
        """Alle Bearbeitungen auf Standard zurücksetzen (ganze Datei, 1,0×, 100 %)."""
        if not self._active:
            return
        self._sel_start, self._sel_end = 0.0, self._duration
        self.selectionChanged.emit()
        engine = self._backend.engine
        engine.preview_region(0, self._frame(self._duration))
        self.setSpeed(1.0)
        self.setGain(1.0)
        self.zoomFit()
        self.seek(0.0)

    # ------------------------------------------------------------------
    # Auswahl
    # ------------------------------------------------------------------
    def _apply_selection(self) -> None:
        self.selectionChanged.emit()
        self._backend.engine.preview_region(self._frame(self._sel_start), self._frame(self._sel_end))
        if not (self._sel_start <= self._position <= self._sel_end):
            self._position = clamp(self._position, self._sel_start, self._sel_end)
            self._seek_guard = time.monotonic() + 0.15
            self.positionChanged.emit()
        self._touch()

    @Slot(float)
    def setSelStart(self, seconds: float) -> None:  # noqa: N802
        if not self._active:
            return
        t = clamp(float(seconds), 0.0, max(0.0, self._sel_end - MIN_SELECTION_S))
        if t != self._sel_start:
            self._sel_start = t
            self._apply_selection()

    @Slot(float)
    def setSelEnd(self, seconds: float) -> None:  # noqa: N802
        if not self._active:
            return
        t = clamp(float(seconds), min(self._duration, self._sel_start + MIN_SELECTION_S), self._duration)
        if t != self._sel_end:
            self._sel_end = t
            self._apply_selection()

    @Slot()
    def markStart(self) -> None:  # noqa: N802
        self.setSelStart(self._position)

    @Slot()
    def markEnd(self) -> None:  # noqa: N802
        self.setSelEnd(self._position)

    # ------------------------------------------------------------------
    # Tempo & Lautstärke
    # ------------------------------------------------------------------
    @Slot(float)
    def setSpeed(self, speed: float) -> None:  # noqa: N802
        s = clamp(float(speed), SPEED_MIN, SPEED_MAX)
        if abs(s - 1.0) < 1e-3:
            s = 1.0
        if self._set("_speed", s, "speedChanged"):
            self._backend.engine.preview_speed(s)
            self.selectionChanged.emit()  # Ergebnislänge ändert sich
            self._touch()

    @Slot(float)
    def setGain(self, gain: float) -> None:  # noqa: N802
        g = clamp(float(gain), GAIN_MIN, GAIN_MAX)
        if abs(g - 1.0) < 1e-3:
            g = 1.0
        if self._set("_gain", g, "gainChanged"):
            self._backend.engine.preview_gain(g)
            self._touch()

    # ------------------------------------------------------------------
    # Zoom / Ausschnitt
    # ------------------------------------------------------------------
    def _clamp_view(self, v0: float, v1: float) -> tuple[float, float]:
        dur = max(self._duration, MIN_VIEW_S)
        span = clamp(v1 - v0, MIN_VIEW_S, dur)
        v0 = clamp(v0, 0.0, dur - span)
        return v0, v0 + span

    @Slot(float, float)
    def setView(self, v0: float, v1: float) -> None:  # noqa: N802
        if not self._active:
            return
        v0, v1 = self._clamp_view(float(v0), float(v1))
        if (v0, v1) != (self._view_start, self._view_end):
            self._view_start, self._view_end = v0, v1
            self.viewChanged.emit()
            self._touch()

    @Slot(float, float)
    def zoomAround(self, center: float, factor: float) -> None:  # noqa: N802
        span = self._view_end - self._view_start
        if span <= 0 or factor <= 0:
            return
        rel = (center - self._view_start) / span
        new_span = span / factor
        v0 = center - rel * new_span
        self.setView(v0, v0 + new_span)

    @Slot()
    def zoomIn(self) -> None:  # noqa: N802
        center = self._position if self._view_start <= self._position <= self._view_end else \
            (self._view_start + self._view_end) / 2
        self.zoomAround(center, 2.0)

    @Slot()
    def zoomOut(self) -> None:  # noqa: N802
        self.zoomAround((self._view_start + self._view_end) / 2, 0.5)

    @Slot()
    def zoomFit(self) -> None:  # noqa: N802
        self.setView(0.0, self._duration)

    @Slot(float)
    def panBy(self, seconds: float) -> None:  # noqa: N802
        self.setView(self._view_start + seconds, self._view_end + seconds)

    # ------------------------------------------------------------------
    # Speichern
    # ------------------------------------------------------------------
    def _params(self) -> EditParams:
        return EditParams(self._sel_start, self._sel_end, self._speed, self._gain)

    @Slot()
    def save(self) -> None:
        backend = self._backend
        project = backend.project
        if not self._active or self._saving or project is None or self._key is None:
            return
        self.pause()
        key = self._key
        params = self._params().normalized(self._duration)
        if params.is_identity(self._duration):
            tile = project.data.peek(*key)
            if tile is not None and tile.is_edited:
                backend.apply_edit(key, None, None, None)
                backend.notify("Bearbeitung entfernt – die Kachel spielt wieder das Original.", "success")
            else:
                backend.notify("Keine Änderungen – die Kachel bleibt unverändert.", "info")
            self.close(keep_session=False)
            return
        src = project.abs(self._original_rel)
        digest = hashlib.sha1(json.dumps(params.to_dict(), sort_keys=True).encode()).hexdigest()[:8]
        out = project.edited_target(Path(self._file_name).stem or "Audio", key[0], key[1], digest)
        self._set("_saving", True, "savingChanged")
        self.write_session(force=True)
        token = self._token
        backend.runner.submit_process(
            tasks.render_edit, str(src), str(project.cache_dir), self._sr, params.to_dict(), str(out),
            on_done=lambda res: self._on_rendered(token, key, params, out, res),
            on_error=lambda msg: self._on_render_failed(token, msg),
        )

    def _on_rendered(self, token: int, key: tuple[int, int], params: EditParams, out: Path, res: dict) -> None:
        backend = self._backend
        project = backend.project
        if project is None:
            return
        entry = CacheEntry.from_dict(res["cache"])
        backend.apply_edit(key, params, project.rel(out), entry)
        msg = f"Bearbeitung gespeichert ({format_time(res['duration'], True)})."
        if res.get("limited"):
            msg += " Der Limiter hat Übersteuerungen abgefangen."
        backend.notify(msg, "success")
        if token == self._token:
            self.close(keep_session=False)

    def _on_render_failed(self, token: int, message: str) -> None:
        if token == self._token:
            self._set("_saving", False, "savingChanged")
        self._backend.notify(f"Speichern der Bearbeitung fehlgeschlagen: {message}", "error")
