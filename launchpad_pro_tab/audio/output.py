"""Audio-Ausgabe-Backends (Schnittstelle ``OutputBackend``).

* ``SoundDeviceBackend`` – PortAudio über ``sounddevice``. Unter Windows wird bevorzugt
  WASAPI (geringe Latenz) verwendet, sonst der Systemstandard.
* ``NullBackend`` – taktet den Mixer ohne Soundkarte (Tests, Screenshots, Notbetrieb).
"""

from __future__ import annotations

import logging
import sys
import threading
import time
from dataclasses import dataclass
from typing import Callable, Protocol

import numpy as np

log = logging.getLogger(__name__)

RenderFn = Callable[[np.ndarray, int], None]


@dataclass
class DeviceInfo:
    index: int
    name: str
    hostapi: str
    samplerate: int
    is_default: bool

    @property
    def label(self) -> str:
        return f"{self.name}  ({self.hostapi})"


class OutputBackend(Protocol):
    name: str
    samplerate: int
    latency_ms: float
    is_null: bool

    def start(self, render: RenderFn) -> None: ...
    def stop(self) -> None: ...


def _sd():
    import sounddevice as sd  # noqa: WPS433 – lazy import (PortAudio evtl. nicht vorhanden)

    return sd


def list_output_devices() -> list[DeviceInfo]:
    try:
        sd = _sd()
        hostapis = sd.query_hostapis()
        default_out = sd.default.device[1] if isinstance(sd.default.device, (list, tuple)) else sd.default.device
        devices = []
        for i, d in enumerate(sd.query_devices()):
            if d.get("max_output_channels", 0) < 1:
                continue
            devices.append(
                DeviceInfo(i, d["name"], hostapis[d["hostapi"]]["name"], int(d["default_samplerate"]), i == default_out)
            )
        return devices
    except Exception as exc:  # PortAudio fehlt / keine Geräte
        log.warning("Audiogeräte können nicht abgefragt werden: %s", exc)
        return []


def pick_device(name: str | None, hostapi: str | None) -> int | None:
    """Wählt das Ausgabegerät: gespeicherte Auswahl > WASAPI-Standard (Windows) > Standard."""
    sd = _sd()
    devices = list_output_devices()
    if name:
        for d in devices:
            if d.name == name and (not hostapi or d.hostapi == hostapi):
                return d.index
        for d in devices:
            if d.name == name:
                return d.index
    if sys.platform == "win32":
        for api in sd.query_hostapis():
            if "WASAPI" in api["name"] and api.get("default_output_device", -1) >= 0:
                return int(api["default_output_device"])
    default = sd.default.device[1] if isinstance(sd.default.device, (list, tuple)) else sd.default.device
    if default is not None and default >= 0:
        return int(default)
    return devices[0].index if devices else None


class SoundDeviceBackend:
    is_null = False

    def __init__(self, device: int | None, blocksize: int = 0):
        sd = _sd()
        self._sd = sd
        info = sd.query_devices(device, "output") if device is not None else sd.query_devices(kind="output")
        self.device = device
        self.hostapi = sd.query_hostapis(info["hostapi"])["name"]
        self.name = f"{info['name']} ({self.hostapi})"
        self.samplerate = int(info["default_samplerate"])
        self.channels = 2 if info["max_output_channels"] >= 2 else 1
        self.blocksize = int(blocksize)
        self.latency_ms = 0.0
        self._stream = None

    def start(self, render: RenderFn) -> None:
        sd = self._sd
        channels = self.channels
        mono_buf = np.zeros((8192, 2), dtype=np.float32)

        def callback(outdata, frames, _time, status):  # PortAudio-Thread
            if channels == 2:
                render(outdata, frames)
            else:
                buf = mono_buf[:frames] if frames <= mono_buf.shape[0] else np.zeros((frames, 2), np.float32)
                render(buf, frames)
                outdata[:, 0] = (buf[:, 0] + buf[:, 1]) * 0.5

        extra = None
        if "WASAPI" in self.hostapi:
            try:
                extra = sd.WasapiSettings(exclusive=False, auto_convert=True)
            except TypeError:
                extra = sd.WasapiSettings(exclusive=False)
        latency = "low" if self.blocksize == 0 else max(self.blocksize / self.samplerate, 0.003)
        self._stream = sd.OutputStream(
            device=self.device,
            samplerate=self.samplerate,
            channels=channels,
            dtype="float32",
            blocksize=self.blocksize,
            latency=latency,
            callback=callback,
            extra_settings=extra,
            prime_output_buffers_using_stream_callback=True,
        )
        self._stream.start()
        self.latency_ms = float(self._stream.latency) * 1000.0
        log.info("Audio-Ausgabe: %s, %d Hz, Latenz %.1f ms", self.name, self.samplerate, self.latency_ms)

    def stop(self) -> None:
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as exc:
                log.warning("Fehler beim Schließen des Audio-Streams: %s", exc)
            self._stream = None


class NullBackend:
    """Taktet den Mixer in Echtzeit, ohne Audio auszugeben."""

    is_null = True

    def __init__(self, samplerate: int = 48000, blocksize: int = 512):
        self.name = "Keine Audioausgabe"
        self.samplerate = int(samplerate)
        self.blocksize = int(blocksize)
        self.latency_ms = blocksize / samplerate * 1000.0
        self._running = False
        self._thread: threading.Thread | None = None

    def start(self, render: RenderFn) -> None:
        self._running = True
        buf = np.zeros((self.blocksize, 2), dtype=np.float32)

        def run():
            period = self.blocksize / self.samplerate
            next_t = time.perf_counter()
            while self._running:
                render(buf, self.blocksize)
                next_t += period
                delay = next_t - time.perf_counter()
                if delay > 0:
                    time.sleep(delay)
                elif delay < -0.5:  # zu weit zurück (z. B. Standby) -> neu synchronisieren
                    next_t = time.perf_counter()

        self._thread = threading.Thread(target=run, name="NullAudioOutput", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None
