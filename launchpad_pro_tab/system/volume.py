"""Schnittstelle zur System-Master-Lautstärke.

``SystemVolume`` ist das gemeinsame Interface; die konkrete Implementierung wird zur
Laufzeit gewählt:

* Windows  – Core Audio ``IAudioEndpointVolume`` (über ``pycaw``/``comtypes``)
* Linux    – PulseAudio/PipeWire (``pactl`` bzw. ``wpctl``) oder ALSA (``amixer``)
* macOS    – ``osascript``
* Fallback – ``DummyVolume`` (nur intern, damit die Oberfläche bedienbar bleibt)

Alle Methoden sind blockierend und werden von ``bridge.volume`` in einem eigenen
Thread ausgeführt (COM-Objekte bleiben dadurch in *einem* Thread).
"""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
import sys
from typing import Protocol

log = logging.getLogger(__name__)


class SystemVolume(Protocol):
    name: str
    is_real: bool

    def get(self) -> tuple[float, bool]:
        """(Lautstärke 0..1, stumm)"""
        ...

    def set_volume(self, value: float) -> None: ...

    def set_mute(self, muted: bool) -> None: ...

    def refresh(self) -> None:
        """Standardgerät neu ermitteln (z. B. nach Kopfhörer-Wechsel)."""
        ...


def _clamp01(v: float) -> float:
    return 0.0 if v < 0 else 1.0 if v > 1 else float(v)


class DummyVolume:
    name = "Simuliert (keine Systemlautstärke verfügbar)"
    is_real = False

    def __init__(self) -> None:
        self._v = 0.75
        self._m = False

    def get(self) -> tuple[float, bool]:
        return self._v, self._m

    def set_volume(self, value: float) -> None:
        self._v = _clamp01(value)

    def set_mute(self, muted: bool) -> None:
        self._m = bool(muted)

    def refresh(self) -> None:
        pass


class WindowsVolume:
    """Windows-Master-Lautstärke des Standard-Wiedergabegeräts."""

    is_real = True

    def __init__(self) -> None:
        import comtypes

        try:
            comtypes.CoInitialize()
        except OSError:
            pass  # bereits initialisiert
        self._ev = None
        self.name = "Windows-Systemlautstärke"
        self._endpoint()

    def _endpoint(self):
        if self._ev is None:
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

            dev = AudioUtilities.GetSpeakers()
            ev = getattr(dev, "EndpointVolume", None)  # pycaw >= 2024
            if ev is None:  # ältere pycaw-Versionen liefern das rohe IMMDevice
                from ctypes import POINTER, cast

                from comtypes import CLSCTX_ALL

                iface = dev.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                ev = cast(iface, POINTER(IAudioEndpointVolume))
            try:
                friendly = getattr(dev, "FriendlyName", None)
                if friendly:
                    self.name = f"Windows: {friendly}"
            except Exception:
                pass
            self._ev = ev
        return self._ev

    def get(self) -> tuple[float, bool]:
        try:
            ev = self._endpoint()
            return float(ev.GetMasterVolumeLevelScalar()), bool(ev.GetMute())
        except Exception:
            self._ev = None
            raise

    def set_volume(self, value: float) -> None:
        try:
            self._endpoint().SetMasterVolumeLevelScalar(_clamp01(value), None)
        except Exception:
            self._ev = None
            raise

    def set_mute(self, muted: bool) -> None:
        try:
            self._endpoint().SetMute(1 if muted else 0, None)
        except Exception:
            self._ev = None
            raise

    def refresh(self) -> None:
        self._ev = None


def _run(args: list[str], timeout: float = 2.0) -> str:
    kwargs = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
    res = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=True, **kwargs)
    return res.stdout


class PulseVolume:
    """PulseAudio/PipeWire über ``pactl``."""

    is_real = True
    name = "PulseAudio/PipeWire (Standardausgabe)"

    def __init__(self) -> None:
        self.get()  # wirft, wenn kein Server erreichbar ist

    def get(self) -> tuple[float, bool]:
        out = _run(["pactl", "get-sink-volume", "@DEFAULT_SINK@"])
        m = re.search(r"(\d+)%", out)
        vol = int(m.group(1)) / 100.0 if m else 0.0
        mute = "yes" in _run(["pactl", "get-sink-mute", "@DEFAULT_SINK@"]).lower()
        return _clamp01(vol), mute

    def set_volume(self, value: float) -> None:
        _run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{int(round(_clamp01(value) * 100))}%"])

    def set_mute(self, muted: bool) -> None:
        _run(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "1" if muted else "0"])

    def refresh(self) -> None:
        pass


class WirePlumberVolume:
    is_real = True
    name = "PipeWire (Standardausgabe)"

    def __init__(self) -> None:
        self.get()

    def get(self) -> tuple[float, bool]:
        out = _run(["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"])
        m = re.search(r"([\d.]+)", out)
        return _clamp01(float(m.group(1)) if m else 0.0), "MUTED" in out

    def set_volume(self, value: float) -> None:
        _run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"{_clamp01(value):.3f}"])

    def set_mute(self, muted: bool) -> None:
        _run(["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "1" if muted else "0"])

    def refresh(self) -> None:
        pass


class AlsaVolume:
    is_real = True
    name = "ALSA Master"

    def __init__(self) -> None:
        self.get()

    def get(self) -> tuple[float, bool]:
        out = _run(["amixer", "get", "Master"])
        m = re.search(r"\[(\d+)%\]", out)
        return _clamp01(int(m.group(1)) / 100.0 if m else 0.0), "[off]" in out

    def set_volume(self, value: float) -> None:
        _run(["amixer", "-q", "set", "Master", f"{int(round(_clamp01(value) * 100))}%"])

    def set_mute(self, muted: bool) -> None:
        _run(["amixer", "-q", "set", "Master", "mute" if muted else "unmute"])

    def refresh(self) -> None:
        pass


class MacVolume:
    is_real = True
    name = "macOS-Systemlautstärke"

    def __init__(self) -> None:
        self.get()

    def get(self) -> tuple[float, bool]:
        v = _run(["osascript", "-e", "output volume of (get volume settings)"]).strip()
        m = _run(["osascript", "-e", "output muted of (get volume settings)"]).strip()
        return _clamp01(float(v) / 100.0 if v and v != "missing value" else 0.0), m == "true"

    def set_volume(self, value: float) -> None:
        _run(["osascript", "-e", f"set volume output volume {int(round(_clamp01(value) * 100))}"])

    def set_mute(self, muted: bool) -> None:
        _run(["osascript", "-e", f"set volume output muted {'true' if muted else 'false'}"])

    def refresh(self) -> None:
        pass


def create_system_volume() -> SystemVolume:
    """Wählt die passende Implementierung für das laufende Betriebssystem."""
    candidates: list[type] = []
    if sys.platform == "win32":
        candidates = [WindowsVolume]
    elif sys.platform == "darwin":
        candidates = [MacVolume]
    else:
        if shutil.which("pactl"):
            candidates.append(PulseVolume)
        if shutil.which("wpctl"):
            candidates.append(WirePlumberVolume)
        if shutil.which("amixer"):
            candidates.append(AlsaVolume)
    for cls in candidates:
        try:
            backend = cls()
            log.info("Systemlautstärke: %s", backend.name)
            return backend
        except Exception as exc:
            log.info("Systemlautstärke via %s nicht verfügbar: %s", cls.__name__, exc)
    return DummyVolume()
