"""Erzeugt Demo-Material (synthetische Klänge + Coverbilder) für Screenshots und Tests.

Alle Klänge werden mathematisch erzeugt – keine urheberrechtlich geschützten Inhalte.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np

SR = 44100


def _env(n: int, attack: float, release: float) -> np.ndarray:
    t = np.arange(n) / SR
    a = np.clip(t / max(attack, 1e-3), 0, 1)
    r = np.clip((n / SR - t) / max(release, 1e-3), 0, 1)
    return (a * r).astype(np.float32)


def _tone(freq: float, dur: float, harmonics=(1.0, 0.5, 0.25), decay: float = 0.0) -> np.ndarray:
    t = np.arange(int(dur * SR)) / SR
    x = sum(a * np.sin(2 * np.pi * freq * (i + 1) * t) for i, a in enumerate(harmonics))
    if decay:
        x = x * np.exp(-t / decay)
    return x.astype(np.float32)


def _stereo(x: np.ndarray, width: float = 0.15) -> np.ndarray:
    d = int(SR * 0.004)
    right = np.concatenate([np.zeros(d, np.float32), x[:-d]]) if d else x
    return np.stack([x, (1 - width) * x + width * right], axis=1)


def _norm(x: np.ndarray, peak: float = 0.85) -> np.ndarray:
    m = float(np.max(np.abs(x))) or 1.0
    return (x / m * peak).astype(np.float32)


def _lowpass(x: np.ndarray, alpha: float) -> np.ndarray:
    """Einpoliger Tiefpass, per FFT vektorisiert."""
    n = len(x)
    size = 1 << int(2 * n - 1).bit_length()
    w = 2 * np.pi * np.fft.rfftfreq(size)
    h = alpha / (1 - (1 - alpha) * np.exp(-1j * w))
    return np.fft.irfft(np.fft.rfft(x, size) * h, size)[:n].astype(np.float32)


def overture(dur: float = 42.0) -> np.ndarray:
    chords = [(261.6, 329.6, 392.0), (220.0, 261.6, 329.6), (174.6, 220.0, 261.6), (196.0, 246.9, 293.7)]
    seg = dur / 8
    parts = []
    rng = np.random.default_rng(1)
    for k in range(8):
        c = chords[k % 4]
        x = sum(_tone(f, seg, (1, 0.45, 0.3, 0.12)) for f in c) / 3
        beat = np.zeros_like(x)
        for b in range(int(seg * 2)):
            s = int(b * SR / 2)
            hit = _tone(c[0] / 2, 0.35, (1, 0.3), decay=0.12)
            beat[s:s + len(hit)] += hit[: len(beat) - s]
        swell = 0.55 + 0.45 * np.sin(np.linspace(0, np.pi, len(x)))
        noise = rng.normal(0, 0.03, len(x)).astype(np.float32)
        parts.append((x * swell + beat * 0.6 + noise) * _env(len(x), 0.05, 0.05))
    return _stereo(_norm(np.concatenate(parts)))


def rain(dur: float = 20.0) -> np.ndarray:
    rng = np.random.default_rng(2)
    n = int(dur * SR)
    x = rng.normal(0, 1, n).astype(np.float32)
    x = x - _lowpass(x, 0.02) * 0.9
    drops = np.zeros(n, np.float32)
    for pos in rng.integers(0, n - 2000, 900):
        drops[pos:pos + 600] += _tone(rng.uniform(1800, 4200), 600 / SR, (1,), decay=0.004)[:600] * rng.uniform(0.2, 0.8)
    mod = 0.75 + 0.25 * np.sin(np.linspace(0, 6 * np.pi, n))
    return _stereo(_norm(x * 0.25 * mod + drops, 0.6), 0.6)


def thunder(dur: float = 7.0) -> np.ndarray:
    rng = np.random.default_rng(3)
    n = int(dur * SR)
    x = rng.normal(0, 1, n).astype(np.float32)
    x = _lowpass(x, 0.035)
    t = np.arange(n) / SR
    env = np.exp(-t / 1.6) * (1 + 1.5 * np.exp(-((t - 0.3) ** 2) / 0.01) + 0.8 * np.exp(-((t - 1.4) ** 2) / 0.05))
    return _stereo(_norm(x * env.astype(np.float32)), 0.4)


def bell(dur: float = 8.0) -> np.ndarray:
    partials = [(1.0, 1.0), (2.76, 0.6), (5.4, 0.35), (8.93, 0.2), (0.5, 0.5)]
    t = np.arange(int(dur * SR)) / SR
    x = sum(a * np.sin(2 * np.pi * 330 * r * t) * np.exp(-t / (2.8 / r ** 0.5)) for r, a in partials)
    return _stereo(_norm(x.astype(np.float32)))


def doorbell() -> np.ndarray:
    a = _tone(659.3, 0.9, (1, 0.2), decay=0.35)
    b = _tone(523.3, 1.4, (1, 0.2), decay=0.5)
    return _stereo(_norm(np.concatenate([a, b])))


def applause(dur: float = 14.0) -> np.ndarray:
    rng = np.random.default_rng(4)
    n = int(dur * SR)
    x = np.zeros(n, np.float32)
    for pos in rng.integers(0, n - 3000, 5200):
        clap = rng.normal(0, 1, 800).astype(np.float32) * np.exp(-np.arange(800) / 90)
        x[pos:pos + 800] += clap * rng.uniform(0.2, 1.0)
    env = np.clip(np.minimum(np.arange(n) / (SR * 1.5), (n - np.arange(n)) / (SR * 3)), 0, 1)
    return _stereo(_norm(x * env.astype(np.float32)), 0.7)


def waltz(dur: float = 36.0) -> np.ndarray:
    beat = 60 / 150
    n = int(dur * SR)
    x = np.zeros(n, np.float32)
    bass = [146.8, 110.0, 130.8, 98.0]
    for i in range(int(dur / beat)):
        s = int(i * beat * SR)
        bar = (i // 3) % 4
        if i % 3 == 0:
            h = _tone(bass[bar], beat * 0.9, (1, 0.5, 0.2), decay=0.3)
        else:
            f = bass[bar] * 2
            h = (_tone(f * 1.26, beat * 0.5, (1, 0.3), decay=0.12) + _tone(f * 1.5, beat * 0.5, (1, 0.3), decay=0.12)) * 0.6
        x[s:s + len(h)] += h[: n - s]
    melody = [587.3, 659.3, 698.5, 659.3, 587.3, 523.3, 587.3, 440.0]
    for i in range(int(dur / (beat * 3))):
        s = int(i * beat * 3 * SR)
        h = _tone(melody[i % len(melody)], beat * 2.8, (1, 0.35, 0.15), decay=1.2) * 0.7
        x[s:s + len(h)] += h[: n - s]
    return _stereo(_norm(x * _env(n, 0.3, 2.0)))


def gong() -> np.ndarray:
    return _stereo(_norm(np.concatenate([_tone(f, 1.1, (1, 0.4, 0.2), decay=0.6) for f in (523.3, 659.3, 784.0)])))


def phone(dur: float = 6.0) -> np.ndarray:
    n = int(dur * SR)
    t = np.arange(n) / SR
    ring = (np.sin(2 * np.pi * 440 * t) + np.sin(2 * np.pi * 480 * t)) * ((t % 3.0) < 1.8) * (0.6 + 0.4 * np.sign(np.sin(2 * np.pi * 20 * t)))
    return _stereo(_norm(ring.astype(np.float32), 0.7))


def wind(dur: float = 24.0) -> np.ndarray:
    rng = np.random.default_rng(5)
    n = int(dur * SR)
    x = _lowpass(rng.normal(0, 1, n).astype(np.float32), 0.01)
    mod = 0.5 + 0.5 * np.sin(np.linspace(0, 5 * np.pi, n)) ** 2
    return _stereo(_norm(x * mod.astype(np.float32), 0.7), 0.8)


SOUNDS = {
    "Ouvertüre.flac": overture,
    "Regen (Loop).ogg": rain,
    "Donner.wav": thunder,
    "Kirchenglocke.mp3": bell,
    "Türklingel.wav": doorbell,
    "Applaus.mp3": applause,
    "Walzer.flac": waltz,
    "Pausengong.wav": gong,
    "Telefon.ogg": phone,
    "Wind.mp3": wind,
}


def write_sounds(target: Path) -> dict[str, Path]:
    import soundfile as sf

    target.mkdir(parents=True, exist_ok=True)
    out = {}
    for name, fn in SOUNDS.items():
        path = target / name
        if not path.exists():
            data = fn()
            ext = path.suffix.lower()
            if ext == ".mp3":
                sf.write(path, data, SR, format="MP3", subtype="MPEG_LAYER_III")
            elif ext == ".ogg":
                sf.write(path, data, SR, format="OGG", subtype="VORBIS")
            else:
                sf.write(path, data, SR)
        out[name] = path
    return out


def write_covers(target: Path) -> dict[str, Path]:
    """Einfache, generierte Coverbilder (benötigt eine laufende QGuiApplication)."""
    from PySide6.QtCore import QPointF, QRectF, Qt
    from PySide6.QtGui import QBrush, QColor, QImage, QLinearGradient, QPainter, QPainterPath, QPen, QRadialGradient

    target.mkdir(parents=True, exist_ok=True)
    S = 512

    def canvas(c1: str, c2: str) -> tuple[QImage, QPainter]:
        img = QImage(S, S, QImage.Format.Format_RGB32)
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        g = QLinearGradient(0, 0, S, S)
        g.setColorAt(0, QColor(c1))
        g.setColorAt(1, QColor(c2))
        p.fillRect(0, 0, S, S, QBrush(g))
        return img, p

    covers = {}

    img, p = canvas("#1B2A4A", "#0B1020")  # Donner
    for i in range(3):
        rg = QRadialGradient(QPointF(120 + i * 140, 140 + 20 * i), 170)
        rg.setColorAt(0, QColor(90, 100, 130, 200))
        rg.setColorAt(1, QColor(90, 100, 130, 0))
        p.setBrush(QBrush(rg))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(120 + i * 140, 140 + 20 * i), 170, 120)
    bolt = QPainterPath()
    for i, (x, y) in enumerate([(290, 150), (210, 300), (262, 300), (205, 440), (330, 260), (272, 260), (320, 150)]):
        bolt.moveTo(x, y) if i == 0 else bolt.lineTo(x, y)
    bolt.closeSubpath()
    p.setBrush(QColor("#FFE066"))
    p.setPen(QPen(QColor("#FFF6C8"), 4))
    p.drawPath(bolt)
    p.end()
    covers["Donner"] = target / "donner.png"
    img.save(str(covers["Donner"]))

    img, p = canvas("#0E3B5C", "#06131F")  # Regen
    p.setPen(QPen(QColor(150, 210, 255, 170), 5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    rng = np.random.default_rng(7)
    for _ in range(70):
        x, y = rng.uniform(0, S), rng.uniform(0, S)
        p.drawLine(QPointF(x, y), QPointF(x - 14, y + 38))
    p.end()
    covers["Regen"] = target / "regen.jpg"
    img.save(str(covers["Regen"]), "JPG", 90)

    img, p = canvas("#5B1A7A", "#1C0B2E")  # Walzer
    p.setBrush(QColor("#FFD6FF"))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(QRectF(150, 320, 110, 80))
    p.drawEllipse(QRectF(290, 290, 110, 80))
    p.drawRect(QRectF(242, 120, 16, 240))
    p.drawRect(QRectF(382, 90, 16, 240))
    beam = QPainterPath()
    beam.moveTo(242, 120)
    beam.lineTo(398, 90)
    beam.lineTo(398, 140)
    beam.lineTo(242, 170)
    beam.closeSubpath()
    p.drawPath(beam)
    p.end()
    covers["Walzer"] = target / "walzer.png"
    img.save(str(covers["Walzer"]))

    img, p = canvas("#6B3E00", "#1E1100")  # Glocke
    rg = QRadialGradient(QPointF(256, 240), 200)
    rg.setColorAt(0, QColor("#FFD27A"))
    rg.setColorAt(1, QColor("#A8651A"))
    p.setBrush(QBrush(rg))
    p.setPen(Qt.PenStyle.NoPen)
    bellp = QPainterPath()
    bellp.moveTo(256, 90)
    bellp.cubicTo(150, 95, 150, 300, 100, 380)
    bellp.lineTo(412, 380)
    bellp.cubicTo(362, 300, 362, 95, 256, 90)
    p.drawPath(bellp)
    p.drawEllipse(QPointF(256, 405), 34, 34)
    p.end()
    covers["Glocke"] = target / "glocke.png"
    img.save(str(covers["Glocke"]))

    img, p = canvas("#0F4D3A", "#04140F")  # Applaus
    p.setPen(QPen(QColor("#7CFFCB"), 10, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    for i in range(7):
        a = -math.pi / 2 + (i - 3) * 0.32
        p.drawLine(QPointF(256 + 150 * math.cos(a), 300 + 150 * math.sin(a)), QPointF(256 + 220 * math.cos(a), 300 + 220 * math.sin(a)))
    p.setBrush(QColor("#E9FFF6"))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(QPointF(256, 330), 90, 90)
    p.end()
    covers["Applaus"] = target / "applaus.jpg"
    img.save(str(covers["Applaus"]), "JPG", 90)
    return covers
