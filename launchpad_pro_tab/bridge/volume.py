"""QML-Controller für den roten Master-Fader (System-Master-Lautstärke).

Alle Zugriffe auf das Betriebssystem laufen in einem eigenen Thread (COM-Apartment unter
Windows, ``pactl`` & Co. unter Linux), damit der Fader nie ruckelt. Beim Ziehen wird nur
der jeweils neueste Wert gesetzt (Throttling); externe Änderungen (z. B. Lautstärketasten
der Tastatur) werden jede Sekunde übernommen.
"""

from __future__ import annotations

import logging
import queue
import threading
import time

from PySide6.QtCore import QObject, Signal, Slot

from ..system.volume import DummyVolume, SystemVolume, create_system_volume
from .qtutil import PropertyObject, rprop

log = logging.getLogger(__name__)


class MasterVolumeController(PropertyObject):
    volumeChanged = Signal()
    mutedChanged = Signal()
    backendChanged = Signal()
    _polled = Signal(float, bool)
    _ready = Signal(str, bool)

    def __init__(self, parent: QObject | None = None, backend_factory=create_system_volume):
        super().__init__(parent)
        self._volume = 0.75
        self._muted = False
        self._name = "…"
        self._real = False
        self._factory = backend_factory
        self._q: queue.Queue = queue.Queue()
        self._pending_volume: float | None = None
        self._last_user_change = 0.0
        self._lock = threading.Lock()
        self._running = True
        self._polled.connect(self._on_polled)
        self._ready.connect(self._on_ready)
        self._thread = threading.Thread(target=self._run, name="SystemVolume", daemon=True)
        self._thread.start()

    volume = rprop(float, "_volume", volumeChanged)
    muted = rprop(bool, "_muted", mutedChanged)
    backendName = rprop(str, "_name", backendChanged)
    isReal = rprop(bool, "_real", backendChanged)

    # ------------------------------------------------------------------
    @Slot(float)
    def setVolume(self, value: float) -> None:  # noqa: N802
        value = min(1.0, max(0.0, float(value)))
        self._last_user_change = time.monotonic()
        self._set("_volume", value, "volumeChanged")
        with self._lock:
            first = self._pending_volume is None
            self._pending_volume = value
        if first:
            self._q.put(("volume",))

    @Slot(bool)
    def setMuted(self, muted: bool) -> None:  # noqa: N802
        self._last_user_change = time.monotonic()
        self._set("_muted", bool(muted), "mutedChanged")
        self._q.put(("mute", bool(muted)))

    @Slot()
    def toggleMute(self) -> None:  # noqa: N802
        self.setMuted(not self._muted)

    def shutdown(self) -> None:
        self._running = False
        self._q.put(("quit",))
        self._thread.join(timeout=1.5)

    # ------------------------------------------------------------------
    def _run(self) -> None:
        try:
            backend: SystemVolume = self._factory()
        except Exception as exc:  # pragma: no cover – Fabrik fängt bereits ab
            log.warning("Systemlautstärke nicht verfügbar: %s", exc)
            backend = DummyVolume()
        self._ready.emit(backend.name, bool(backend.is_real))
        last_poll = 0.0
        last_refresh = time.monotonic()
        while self._running:
            try:
                cmd = self._q.get(timeout=0.25)
            except queue.Empty:
                cmd = None
            try:
                if cmd is not None:
                    if cmd[0] == "quit":
                        break
                    if cmd[0] == "volume":
                        with self._lock:
                            value, self._pending_volume = self._pending_volume, None
                        if value is not None:
                            backend.set_volume(value)
                            time.sleep(0.02)  # max. ~50 Aktualisierungen/s
                    elif cmd[0] == "mute":
                        backend.set_mute(cmd[1])
                now = time.monotonic()
                if now - last_refresh > 5.0:
                    backend.refresh()  # Standardgerät gewechselt?
                    last_refresh = now
                if now - last_poll >= 1.0 and self._pending_volume is None:
                    last_poll = now
                    v, m = backend.get()
                    self._polled.emit(float(v), bool(m))
            except Exception as exc:
                log.debug("Systemlautstärke: %s", exc)
                time.sleep(0.5)

    @Slot(float, bool)
    def _on_polled(self, volume: float, muted: bool) -> None:
        # Kurz nach einer Bedienung nicht zurückspringen (Polling hinkt hinterher)
        if time.monotonic() - self._last_user_change < 1.5:
            return
        if abs(volume - self._volume) > 0.004:
            self._set("_volume", volume, "volumeChanged")
        self._set("_muted", muted, "mutedChanged")

    @Slot(str, bool)
    def _on_ready(self, name: str, real: bool) -> None:
        self._name = name
        self._real = real
        self.backendChanged.emit()
