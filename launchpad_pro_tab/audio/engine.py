"""Low-Latency-Audio-Engine (Mixer).

Design für minimale Latenz und Robustheit:

* Alle Kacheln liegen bereits dekodiert (int16-memmap) vor – beim Antippen wird nichts
  mehr geladen oder dekodiert, sondern nur eine "Stimme" (Voice) angelegt.
* Die UI kommuniziert ausschließlich über eine lock-freie Befehlswarteschlange
  (``collections.deque``); der Audio-Thread arbeitet sie zu Beginn jedes Blocks ab.
* Rückmeldungen (Positionen, Pegel) veröffentlicht der Audio-Thread als unveränderliche
  Schnappschüsse, die die UI mit ~30 Hz abfragt.
* Master-Bus mit Spitzenbegrenzer (Limiter) gegen Übersteuerung, wenn mehrere Kacheln
  gleichzeitig laufen, plus Peak-Meter.
* Ein Prefetch-Thread liest die memmap-Seiten laufender Stimmen voraus, damit der
  Audio-Callback nie auf die Festplatte warten muss.
"""

from __future__ import annotations

import logging
import math
import threading
import time
from collections import deque
from typing import Any, Hashable

import numpy as np

from ..core.constants import STOP_FADE_MS_DEFAULT
from .cache import warm
from .output import NullBackend, OutputBackend, SoundDeviceBackend, list_output_devices, pick_device
from .timestretch import WsolaStretcher

log = logging.getLogger(__name__)

MAX_BLOCK = 16384
LIMIT_CEILING = 0.98


class _TileVoice:
    __slots__ = ("key", "data", "pos", "end", "loop", "env", "env_step", "stopping", "scale")

    def __init__(self, key: Hashable, data: np.ndarray, loop: bool):
        self.key = key
        self.data = data
        self.pos = 0
        self.end = int(data.shape[0])
        self.loop = loop
        self.env = 1.0
        self.env_step = 0.0
        self.stopping = False
        self.scale = np.float32(1.0 / 32768.0) if data.dtype == np.int16 else np.float32(1.0)

    def fade_out(self, frames: int) -> None:
        self.stopping = True
        self.env_step = -self.env / max(1, frames)

    def render(self, out: np.ndarray, frames: int) -> bool:
        """Mischt in ``out``; liefert False, wenn die Stimme beendet ist."""
        o = 0
        while o < frames:
            avail = self.end - self.pos
            if avail <= 0:
                if self.loop and self.end > 0:
                    self.pos = 0
                    continue
                return False
            n = min(frames - o, avail)
            chunk = self.data[self.pos: self.pos + n]
            if self.env_step != 0.0:
                ramp = self.env + self.env_step * np.arange(1, n + 1, dtype=np.float32)
                np.clip(ramp, 0.0, 1.0, out=ramp)
                out[o: o + n] += chunk * (ramp * self.scale)[:, None]
                self.env = float(ramp[-1])
                if self.env <= 0.0:
                    return False
                if self.env >= 1.0:
                    self.env_step = 0.0
            else:
                out[o: o + n] += chunk * np.float32(self.scale * self.env)
            self.pos += n
            o += n
        return True


class _PreviewVoice:
    """Vorschau im Bereich "Bearbeiten & Schneiden" (Time-Stretch + Lautstärke in Echtzeit)."""

    FADE_MS = 6.0

    def __init__(self, data: np.ndarray, samplerate: int):
        self.data = data
        self.samplerate = samplerate
        self.stretcher = WsolaStretcher(data, samplerate)
        self.playing = False       # logischer Zustand (für die UI)
        self.env = 0.0             # Anti-Klick-Hüllkurve
        self.env_target = 0.0
        self.gain = 1.0
        self.gain_target = 1.0
        self.pending_seek: int | None = None
        self.ended = False
        self._fade_frames = max(1, int(samplerate * self.FADE_MS / 1000.0))

    def _apply_pending_seek(self) -> None:
        self.stretcher.seek(self.pending_seek)
        self.pending_seek = None
        if self.playing:
            self.env_target = 1.0  # nach dem Springen wieder einblenden

    def render(self, out: np.ndarray, frames: int) -> None:
        if self.env <= 0.0 and self.env_target <= 0.0:
            if self.pending_seek is None:
                return  # pausiert: nichts lesen, Position bleibt stehen
            self._apply_pending_seek()
            if self.env_target <= 0.0:
                return
        data, filled = self.stretcher.read(frames)

        # Anti-Klick-Hüllkurve (Ein-/Ausblenden bei Play/Pause/Springen)
        env: np.ndarray | None = None
        if self.env != self.env_target:
            step = np.float32(1.0 / self._fade_frames)
            idx = np.arange(1, frames + 1, dtype=np.float32)
            if self.env_target > self.env:
                env = np.minimum(np.float32(self.env_target), np.float32(self.env) + step * idx)
            else:
                env = np.maximum(np.float32(self.env_target), np.float32(self.env) - step * idx)
            self.env = float(env[-1])

        # Lautstärke (Fader) weich nachführen
        if self.gain != self.gain_target:
            gain = np.linspace(self.gain, self.gain_target, frames, dtype=np.float32)
            self.gain = self.gain_target
            factor = gain if env is None else env * gain
            out[:frames] += data * factor[:, None]
        elif env is not None:
            out[:frames] += data * (env * np.float32(self.gain))[:, None]
        else:
            out[:frames] += data * np.float32(self.gain * self.env)

        if filled < frames or self.stretcher.finished:
            # Ende der Auswahl erreicht -> Pause und zurück an den Auswahlanfang
            self.playing = False
            self.env = 0.0
            self.env_target = 0.0
            self.pending_seek = None
            self.stretcher.seek(self.stretcher.start)
            self.ended = True
        elif self.env <= 0.0 and self.env_target <= 0.0 and self.pending_seek is not None:
            self._apply_pending_seek()


class AudioEngine:
    """Mixer + Ausgabe. Alle öffentlichen Methoden sind aus dem UI-Thread aufrufbar."""

    def __init__(self) -> None:
        self.backend: OutputBackend | None = None
        self.samplerate = 48000
        self.error: str | None = None
        self.stop_fade_ms = STOP_FADE_MS_DEFAULT
        self._cmds: deque[tuple] = deque()
        self._voices: list[_TileVoice] = []
        self._preview: _PreviewVoice | None = None
        self._mix = np.zeros((MAX_BLOCK, 2), dtype=np.float32)
        self._lim_gain = 1.0
        self._peak = np.zeros(2, dtype=np.float32)
        self._limiting = False
        self._callback_error_logged = False
        # Schnappschüsse für die UI (werden als Ganzes ersetzt -> threadsicher lesbar)
        self.snapshot: dict[Hashable, tuple[int, int]] = {}
        self.preview_state: tuple[bool, float] = (False, 0.0)
        self.events: deque[tuple[str, Any]] = deque()
        self._prefetch_run = False
        self._prefetch_thread: threading.Thread | None = None
        self.cpu_load = 0.0

    # ------------------------------------------------------------------
    # Start / Stopp
    # ------------------------------------------------------------------
    def start(self, device_name: str | None = None, hostapi: str | None = None, blocksize: int = 0,
              allow_null: bool = True) -> None:
        self.shutdown_output()
        self._reset_voices()
        self.error = None
        errors: list[str] = []
        # Fallback-Kette: gewähltes/WASAPI-Gerät -> Systemstandard -> großer Puffer -> stumm
        attempts: list[tuple[int | None, int]] = []
        try:
            attempts.append((pick_device(device_name, hostapi), blocksize))
        except Exception as exc:
            errors.append(str(exc) or exc.__class__.__name__)
        attempts.append((None, blocksize))
        attempts.append((None, 2048))
        backend: OutputBackend | None = None
        tried: set[tuple[int | None, int]] = set()
        for device, frames in attempts:
            if (device, frames) in tried:
                continue
            tried.add((device, frames))
            candidate = None
            try:
                candidate = SoundDeviceBackend(device, frames)
                candidate.start(self._render)
                backend = candidate
                break
            except Exception as exc:
                errors.append(str(exc) or exc.__class__.__name__)
                log.warning("Audio-Ausgabe (Gerät %s, Puffer %s) nicht verfügbar: %s", device, frames, exc)
                if candidate is not None:
                    try:
                        candidate.stop()
                    except Exception:
                        pass
        if backend is None:
            if not list_output_devices():
                self.error = "Kein Audio-Ausgabegerät gefunden (Lautsprecher/Kopfhörer angeschlossen?)"
            else:
                self.error = errors[-1] if errors else "unbekannter Fehler"
            if not allow_null:
                raise RuntimeError(self.error)
            backend = NullBackend(self.samplerate)
            backend.start(self._render)
        elif errors:
            log.warning("Audio läuft über ein Ersatzgerät: %s", backend.name)
        self.backend = backend
        self.samplerate = backend.samplerate
        self._start_prefetch()

    def _reset_voices(self) -> None:
        # Stimmen gehören zur alten Samplerate/zum alten Gerät -> verwerfen
        self._cmds.clear()
        self._voices = []
        self._preview = None
        self.snapshot = {}
        self.preview_state = (False, 0.0)

    def start_null(self, samplerate: int = 48000) -> None:
        """Startet ohne Soundkarte (Tests/Screenshots)."""
        self.shutdown_output()
        self._reset_voices()
        self.samplerate = samplerate
        self.backend = NullBackend(samplerate)
        self.backend.start(self._render)
        self._start_prefetch()

    def shutdown_output(self) -> None:
        if self.backend is not None:
            self.backend.stop()
            self.backend = None

    def shutdown(self) -> None:
        self._prefetch_run = False
        self.shutdown_output()
        if self._prefetch_thread is not None:
            self._prefetch_thread.join(timeout=1.0)
            self._prefetch_thread = None
        self._voices = []
        self._preview = None
        self.snapshot = {}

    @property
    def device_name(self) -> str:
        return self.backend.name if self.backend else "–"

    @property
    def latency_ms(self) -> float:
        return self.backend.latency_ms if self.backend else 0.0

    @property
    def is_null(self) -> bool:
        return bool(self.backend is None or self.backend.is_null)

    # ------------------------------------------------------------------
    # Befehle (UI-Thread)
    # ------------------------------------------------------------------
    def toggle(self, key: Hashable, pcm: np.ndarray, loop: bool = False) -> None:
        """Start/Stopp-Umschalter einer Kachel (Entscheidung fällt atomar im Audio-Thread)."""
        self._cmds.append(("toggle", key, pcm, loop))

    def play(self, key: Hashable, pcm: np.ndarray, loop: bool = False) -> None:
        self._cmds.append(("play", key, pcm, loop))

    def stop(self, key: Hashable) -> None:
        self._cmds.append(("stop", key))

    def stop_all(self) -> None:
        self._cmds.append(("stop_all",))

    def set_loop(self, key: Hashable, loop: bool) -> None:
        self._cmds.append(("loop", key, loop))

    def kill(self, key: Hashable) -> None:
        """Sofort entfernen (z. B. Kachel gelöscht) – mit minimaler Blende."""
        self._cmds.append(("kill", key))

    def is_active(self, key: Hashable) -> bool:
        return key in self.snapshot

    # Vorschau ---------------------------------------------------------
    def preview_load(self, pcm: np.ndarray | None) -> None:
        self._cmds.append(("pv_load", pcm))
        self.preview_state = (False, 0.0)

    def preview_play(self) -> None:
        self._cmds.append(("pv_play",))

    def preview_pause(self) -> None:
        self._cmds.append(("pv_pause",))

    def preview_seek(self, frame: int) -> None:
        self._cmds.append(("pv_seek", int(frame)))

    def preview_region(self, start: int, end: int) -> None:
        self._cmds.append(("pv_region", int(start), int(end)))

    def preview_speed(self, speed: float) -> None:
        self._cmds.append(("pv_speed", float(speed)))

    def preview_gain(self, gain: float) -> None:
        self._cmds.append(("pv_gain", float(gain)))

    # Pegel ------------------------------------------------------------
    def take_levels(self) -> tuple[float, float, bool]:
        """Spitzenpegel seit dem letzten Abruf (L, R) und ob der Limiter arbeitet."""
        l, r = float(self._peak[0]), float(self._peak[1])
        self._peak[:] = 0.0
        return l, r, self._limiting

    # ------------------------------------------------------------------
    # Audio-Thread
    # ------------------------------------------------------------------
    def _fade_frames(self) -> int:
        return max(1, int(self.samplerate * self.stop_fade_ms / 1000.0))

    def _handle_commands(self) -> None:
        cmds = self._cmds
        while cmds:
            try:
                cmd = cmds.popleft()
            except IndexError:
                break
            op = cmd[0]
            if op == "toggle":
                _, key, pcm, loop = cmd
                active = next((v for v in self._voices if v.key == key and not v.stopping), None)
                if active is not None:
                    active.fade_out(self._fade_frames())
                elif pcm is not None and pcm.shape[0] > 0:
                    self._voices.append(_TileVoice(key, pcm, loop))
            elif op == "play":
                _, key, pcm, loop = cmd
                for v in self._voices:
                    if v.key == key and not v.stopping:
                        v.fade_out(self._fade_frames())
                if pcm is not None and pcm.shape[0] > 0:
                    self._voices.append(_TileVoice(key, pcm, loop))
            elif op == "stop":
                for v in self._voices:
                    if v.key == cmd[1] and not v.stopping:
                        v.fade_out(self._fade_frames())
            elif op == "stop_all":
                for v in self._voices:
                    if not v.stopping:
                        v.fade_out(self._fade_frames())
                pv = self._preview
                if pv is not None and pv.playing:
                    pv.playing = False
                    pv.env_target = 0.0
            elif op == "kill":
                for v in self._voices:
                    if v.key == cmd[1]:
                        v.fade_out(max(1, int(self.samplerate * 0.004)))
            elif op == "loop":
                for v in self._voices:
                    if v.key == cmd[1] and not v.stopping:
                        v.loop = bool(cmd[2])
            elif op == "pv_load":
                pcm = cmd[1]
                self._preview = _PreviewVoice(pcm, self.samplerate) if pcm is not None and pcm.shape[0] > 0 else None
            elif self._preview is not None:
                pv = self._preview
                if op == "pv_play":
                    if pv.stretcher.finished:
                        pv.stretcher.seek(pv.stretcher.start)
                    pv.playing = True
                    pv.ended = False
                    pv.env_target = 1.0
                elif op == "pv_pause":
                    pv.playing = False
                    pv.env_target = 0.0
                elif op == "pv_seek":
                    if pv.env > 0.0 or pv.env_target > 0.0:
                        pv.pending_seek = cmd[1]
                        pv.env_target = 0.0
                    else:
                        pv.stretcher.seek(cmd[1])
                elif op == "pv_region":
                    st = pv.stretcher
                    pos = int(st.position)
                    st.set_region(cmd[1], cmd[2])
                    target = min(max(pos, st.start), st.end)
                    if pos < st.start or pos >= st.end:
                        target = st.start
                    if pv.env > 0.0 or pv.env_target > 0.0:
                        pv.pending_seek = target
                        pv.env_target = 0.0
                    else:
                        st.seek(target)
                elif op == "pv_speed":
                    pv.stretcher.speed = cmd[1]
                elif op == "pv_gain":
                    pv.gain_target = cmd[1]

    def _render(self, outdata: np.ndarray, frames: int) -> None:
        t0 = time.perf_counter()
        try:
            out = self._mix[:frames] if frames <= MAX_BLOCK else np.zeros((frames, 2), dtype=np.float32)
            out.fill(0.0)
            self._handle_commands()
            voices = self._voices
            if voices:
                alive = [v for v in voices if v.render(out, frames)]
                if len(alive) != len(voices):
                    self._voices = alive
            pv = self._preview
            if pv is not None:
                pv.render(out, frames)
                if pv.ended:
                    pv.ended = False
                    self.events.append(("preview_end", None))
                self.preview_state = (pv.playing, pv.stretcher.position)
            self._master(out, frames)
            outdata[:frames] = out
            # Schnappschuss für die UI
            snap: dict[Hashable, tuple[int, int]] = {}
            for v in self._voices:
                if not v.stopping:
                    snap[v.key] = (v.pos, v.end)
            self.snapshot = snap
        except Exception:  # der Audio-Thread darf niemals abbrechen
            outdata.fill(0.0)
            if not self._callback_error_logged:
                self._callback_error_logged = True
                log.exception("Fehler im Audio-Callback")
        dt = time.perf_counter() - t0
        budget = frames / float(self.samplerate or 48000)
        self.cpu_load = 0.9 * self.cpu_load + 0.1 * (dt / budget if budget else 0.0)

    def _master(self, out: np.ndarray, frames: int) -> None:
        if frames == 0:
            return
        peak = float(np.max(np.abs(out)))
        target = 1.0 if peak <= LIMIT_CEILING else LIMIT_CEILING / peak
        g0 = self._lim_gain
        if target < g0:
            g1 = target
            out *= np.float32(g1)
        else:
            rel = math.exp(-frames / (self.samplerate * 0.15))
            g1 = target + (g0 - target) * rel
            if g0 < 0.9999 or g1 < 0.9999:
                out *= np.linspace(g0, g1, frames, dtype=np.float32)[:, None]
        if g1 > 0.9999:
            g1 = 1.0
        self._lim_gain = g1
        self._limiting = g1 < 0.995
        np.clip(out, -1.0, 1.0, out=out)
        np.maximum(self._peak, np.max(np.abs(out), axis=0), out=self._peak)

    # ------------------------------------------------------------------
    # Prefetch (memmap-Seiten vorlesen)
    # ------------------------------------------------------------------
    def _start_prefetch(self) -> None:
        if self._prefetch_thread is not None:
            return
        self._prefetch_run = True
        self._prefetch_thread = threading.Thread(target=self._prefetch_loop, name="AudioPrefetch", daemon=True)
        self._prefetch_thread.start()

    def _prefetch_loop(self) -> None:
        while self._prefetch_run:
            ahead = int(self.samplerate * 4)
            for v in list(self._voices):
                try:
                    warm(v.data, v.pos, ahead)
                    if v.loop:
                        warm(v.data, 0, ahead)
                except Exception:
                    pass
            pv = self._preview
            if pv is not None and pv.playing:
                try:
                    warm(pv.data, int(pv.stretcher.position), ahead)
                except Exception:
                    pass
            time.sleep(0.2)

    # ------------------------------------------------------------------
    # Offline-Mixdown (für Tests)
    # ------------------------------------------------------------------
    def render_offline(self, frames: int, block: int = 512) -> np.ndarray:
        out = np.zeros((frames, 2), dtype=np.float32)
        pos = 0
        while pos < frames:
            n = min(block, frames - pos)
            self._render(out[pos: pos + n], n)
            pos += n
        return out
