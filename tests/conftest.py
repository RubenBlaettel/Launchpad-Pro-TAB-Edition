"""Gemeinsame Test-Hilfen.

Alle Tests laufen ohne Soundkarte und ohne Bildschirm (``QT_QPA_PLATFORM=offscreen``)
und schreiben Einstellungen/Projekte ausschließlich in temporäre Ordner.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
_CFG = Path(tempfile.mkdtemp(prefix="lptab-test-cfg-"))
os.environ["LPTAB_CONFIG_DIR"] = str(_CFG)
os.environ["LPTAB_PROJECTS_DIR"] = str(_CFG / "Projekte")

SR = 48000


def sine(freq: float = 440.0, seconds: float = 1.0, sr: int = SR, amp: float = 0.5, channels: int = 2) -> np.ndarray:
    t = np.arange(int(sr * seconds)) / sr
    x = (np.sin(2 * np.pi * freq * t) * amp).astype(np.float32)
    return np.stack([x] * channels, axis=1) if channels > 1 else x


@pytest.fixture(scope="session")
def qapp():
    """Eine QGuiApplication für alle Qt-Tests (es darf nur eine pro Prozess geben)."""
    from PySide6.QtGui import QGuiApplication

    app = QGuiApplication.instance() or QGuiApplication([sys.argv[0]])
    yield app


def wait_until(app, cond, timeout: float = 20.0) -> bool:
    import time

    from PySide6.QtCore import QEventLoop

    end = time.monotonic() + timeout
    while time.monotonic() < end:
        app.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 20)
        if cond():
            return True
        time.sleep(0.005)
    return False


@pytest.fixture
def wav_file(tmp_path: Path):
    """Erzeugt eine WAV-Datei: ``wav_file(name, seconds, freq, sr)``."""
    import soundfile as sf

    def make(name: str = "ton.wav", seconds: float = 1.0, freq: float = 440.0, sr: int = SR, amp: float = 0.5) -> Path:
        path = tmp_path / name
        sf.write(path, sine(freq, seconds, sr, amp), sr)
        return path

    return make


def dominant_frequency(x: np.ndarray, sr: int) -> float:
    mono = x[:, 0] if x.ndim == 2 else x
    spec = np.abs(np.fft.rfft(mono * np.hanning(len(mono))))
    return float(np.argmax(spec) * sr / len(mono))
