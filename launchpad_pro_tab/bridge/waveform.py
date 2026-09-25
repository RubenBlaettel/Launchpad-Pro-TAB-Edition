"""QML-Element ``WaveformView``: Wellenform-Darstellung im Stil eines Oszilloskops.

Grün auf Schwarz mit Raster (angelehnt an Bild 1); im hellen Modus (``dark: false``)
dunkelgrün auf hellem Grund. Gezeichnet wird nur bei Zoom-, Größen-, Farb- oder
Auswahländerungen; der Abspielkopf ist ein separates QML-Element und bewegt sich daher
ohne Neuzeichnen der Wellenform (GPU-schonend).
"""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import Property, QLineF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtQml import QmlElement
from PySide6.QtQuick import QQuickPaintedItem

from ..audio.dsp import PEAK_BUCKET, aggregate_peaks, columns_from_pcm

QML_IMPORT_NAME = "LaunchpadPro"
QML_IMPORT_MAJOR_VERSION = 1

_STEPS = (0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10, 15, 30, 60, 120, 300, 600)

class Palette:
    """Farben der Wellenform – je eine Palette für den dunklen und den hellen Modus."""

    def __init__(self, bg: QColor, grid: QColor, grid_major: QColor, label: QColor, wave: QColor,
                 wave_core: QColor, wave_dim: QColor, wave_dim_core: QColor, center: QColor):
        self.bg = bg
        self.grid = grid
        self.grid_major = grid_major
        self.label = label
        self.wave = wave
        self.wave_core = wave_core
        self.wave_dim = wave_dim
        self.wave_dim_core = wave_dim_core
        self.center = center


DARK = Palette(
    bg=QColor("#000000"),
    grid=QColor(24, 92, 52, 150),
    grid_major=QColor(30, 120, 66, 200),
    label=QColor(46, 170, 100),
    wave=QColor("#14D992"),
    wave_core=QColor("#6BF5C3"),
    wave_dim=QColor(20, 217, 146, 70),
    wave_dim_core=QColor(107, 245, 195, 60),
    center=QColor(20, 217, 146, 90),
)
LIGHT = Palette(
    bg=QColor("#F3F7F5"),
    grid=QColor(9, 138, 94, 38),
    grid_major=QColor(9, 138, 94, 70),
    label=QColor(40, 110, 82),
    wave=QColor("#12A872"),
    wave_core=QColor("#07714D"),
    wave_dim=QColor(18, 168, 114, 70),
    wave_dim_core=QColor(7, 113, 77, 60),
    center=QColor(9, 138, 94, 90),
)


def _fmt(t: float, step: float) -> str:
    m, s = divmod(t, 60.0)
    if step < 1:
        return f"{int(m)}:{s:04.1f}".replace(".", ",")
    return f"{int(m)}:{int(round(s)) % 60:02d}"


@QmlElement
class WaveformView(QQuickPaintedItem):
    viewChanged = Signal()
    selectionChanged = Signal()
    activeChanged = Signal()
    durationChanged = Signal()
    darkChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAntialiasing(False)
        self.setOpaquePainting(True)
        self._pal = DARK
        self.setFillColor(self._pal.bg)
        self._peaks: np.ndarray | None = None
        self._pcm: np.ndarray | None = None
        self._sr = 48000
        self._duration = 0.0
        self._view_start = 0.0
        self._view_end = 1.0
        self._sel_start = 0.0
        self._sel_end = 1.0
        self._active = False
        self._font = QFont()
        self._font.setPixelSize(10)
        self.widthChanged.connect(self.update)
        self.heightChanged.connect(self.update)

    # ------------------------------------------------------------------
    # Daten (aus Python gesetzt)
    # ------------------------------------------------------------------
    def set_source(self, peaks: np.ndarray | None, pcm: np.ndarray | None, samplerate: int, duration: float) -> None:
        self._peaks = peaks
        self._pcm = pcm
        self._sr = int(samplerate)
        if self._duration != duration:
            self._duration = float(duration)
            self.durationChanged.emit()
        self.update()

    def clear_source(self) -> None:
        self.set_source(None, None, self._sr, 0.0)

    # ------------------------------------------------------------------
    # QML-Properties
    # ------------------------------------------------------------------
    def _get_view_start(self) -> float:
        return self._view_start

    def _set_view_start(self, v: float) -> None:
        if v != self._view_start:
            self._view_start = float(v)
            self.viewChanged.emit()
            self.update()

    def _get_view_end(self) -> float:
        return self._view_end

    def _set_view_end(self, v: float) -> None:
        if v != self._view_end:
            self._view_end = float(v)
            self.viewChanged.emit()
            self.update()

    def _get_sel_start(self) -> float:
        return self._sel_start

    def _set_sel_start(self, v: float) -> None:
        if v != self._sel_start:
            self._sel_start = float(v)
            self.selectionChanged.emit()
            self.update()

    def _get_sel_end(self) -> float:
        return self._sel_end

    def _set_sel_end(self, v: float) -> None:
        if v != self._sel_end:
            self._sel_end = float(v)
            self.selectionChanged.emit()
            self.update()

    def _get_active(self) -> bool:
        return self._active

    def _set_active(self, v: bool) -> None:
        if v != self._active:
            self._active = bool(v)
            self.activeChanged.emit()
            self.update()

    def _get_dark(self) -> bool:
        return self._pal is DARK

    def _set_dark(self, v: bool) -> None:
        pal = DARK if v else LIGHT
        if pal is not self._pal:
            self._pal = pal
            self.setFillColor(pal.bg)
            self.darkChanged.emit()
            self.update()

    viewStart = Property(float, _get_view_start, _set_view_start, notify=viewChanged)
    viewEnd = Property(float, _get_view_end, _set_view_end, notify=viewChanged)
    selStart = Property(float, _get_sel_start, _set_sel_start, notify=selectionChanged)
    selEnd = Property(float, _get_sel_end, _set_sel_end, notify=selectionChanged)
    active = Property(bool, _get_active, _set_active, notify=activeChanged)
    dark = Property(bool, _get_dark, _set_dark, notify=darkChanged)
    duration = Property(float, lambda self: self._duration, notify=durationChanged)

    # ------------------------------------------------------------------
    # Zeichnen
    # ------------------------------------------------------------------
    def paint(self, painter: QPainter) -> None:
        w = max(1, int(self.width()))
        h = max(1.0, float(self.height()))
        pal = self._pal
        painter.fillRect(QRectF(0, 0, w, h), pal.bg)
        v0, v1 = self._view_start, self._view_end
        span = max(1e-6, v1 - v0)
        mid = h / 2.0

        # Raster: horizontale Linien (Viertel) + Zeitraster mit Beschriftung
        pen = QPen(pal.grid, 1)
        painter.setPen(pen)
        for frac in (0.125, 0.25, 0.375, 0.625, 0.75, 0.875):
            y = round(h * frac) + 0.5
            painter.drawLine(QLineF(0, y, w, y))
        step = next((s for s in _STEPS if s / span * w >= 72), _STEPS[-1])
        t = np.ceil(v0 / step) * step
        painter.setFont(self._font)
        while t <= v1 + 1e-9:
            x = round((t - v0) / span * w) + 0.5
            painter.setPen(QPen(pal.grid_major, 1))
            painter.drawLine(QLineF(x, 0, x, h))
            if self._active:
                painter.setPen(pal.label)
                painter.drawText(QRectF(x + 3, 2, 60, 12), Qt.AlignmentFlag.AlignLeft, _fmt(t, step))
            t += step

        painter.setPen(QPen(pal.center, 1))
        painter.drawLine(QLineF(0, mid, w, mid))
        if not self._active or self._peaks is None or self._duration <= 0:
            return

        # Spalten berechnen (Peaks oder bei starkem Zoom direkt aus PCM)
        frames_per_col = span * self._sr / w
        if frames_per_col < PEAK_BUCKET and self._pcm is not None:
            cols = columns_from_pcm(self._pcm, int(v0 * self._sr), int(np.ceil(v1 * self._sr)), w)
        else:
            b0 = v0 * self._sr / PEAK_BUCKET
            b1 = v1 * self._sr / PEAK_BUCKET
            cols = aggregate_peaks(self._peaks, b0, b1, w)
        amp = mid * 0.94
        top = mid - np.clip(cols[:, 1], -1, 1) * amp
        bot = mid - np.clip(cols[:, 0], -1, 1) * amp
        bot = np.maximum(bot, top + 1.0)
        rms = np.clip(cols[:, 2], 0, 1) * amp
        rt, rb = mid - rms, mid + rms
        xs = np.arange(w) + 0.5
        col_t = v0 + (xs / w) * span
        inside = (col_t >= self._sel_start) & (col_t <= self._sel_end)
        has_data = col_t <= self._duration

        for mask, c_peak, c_core in ((~inside & has_data, pal.wave_dim, pal.wave_dim_core),
                                     (inside & has_data, pal.wave, pal.wave_core)):
            idx = np.nonzero(mask)[0]
            if idx.size == 0:
                continue
            painter.setPen(QPen(c_peak, 1))
            painter.drawLines([QLineF(xs[i], top[i], xs[i], bot[i]) for i in idx])
            core = idx[(rb[idx] - rt[idx]) > 1.0]
            if core.size:
                painter.setPen(QPen(c_core, 1))
                painter.drawLines([QLineF(xs[i], rt[i], xs[i], rb[i]) for i in core])
