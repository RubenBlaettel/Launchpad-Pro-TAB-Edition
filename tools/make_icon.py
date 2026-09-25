"""Erzeugt das Programm-Icon (PNG + mehrstufiges Windows-ICO).

    python tools/make_icon.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "launchpad_pro_tab" / "assets"

COLORS = ["#D64DFF", "#FF4FA3", "#7A5CFF",
          "#1FD6FF", "#14D9A0", "#D64DFF",
          "#FFC61A", "#D64DFF", "#FF5252"]


def render(size: int):
    from PySide6.QtCore import QPointF, QRectF, Qt
    from PySide6.QtGui import QColor, QImage, QLinearGradient, QPainter, QRadialGradient

    img = QImage(size, size, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    s = float(size)
    bg = QLinearGradient(0, 0, 0, s)
    bg.setColorAt(0, QColor("#232733"))
    bg.setColorAt(1, QColor("#0D0F14"))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(bg)
    p.drawRoundedRect(QRectF(s * 0.02, s * 0.02, s * 0.96, s * 0.96), s * 0.22, s * 0.22)
    pad = s * 0.225
    gap = s * 0.055
    x0 = (s - 3 * pad - 2 * gap) / 2
    for i, c in enumerate(COLORS):
        r, col = divmod(i, 3)
        x = x0 + col * (pad + gap)
        y = x0 + r * (pad + gap)
        color = QColor(c)
        if size >= 48:  # Leuchten
            glow = QRadialGradient(QPointF(x + pad / 2, y + pad / 2), pad * 0.9)
            glow.setColorAt(0, QColor(color.red(), color.green(), color.blue(), 110))
            glow.setColorAt(1, QColor(color.red(), color.green(), color.blue(), 0))
            p.setBrush(glow)
            p.drawEllipse(QPointF(x + pad / 2, y + pad / 2), pad * 0.9, pad * 0.9)
        g = QLinearGradient(0, y, 0, y + pad)
        g.setColorAt(0, color.lighter(135))
        g.setColorAt(1, color.darker(125))
        p.setBrush(g)
        p.drawRoundedRect(QRectF(x, y, pad, pad), pad * 0.24, pad * 0.24)
        hl = QRadialGradient(QPointF(x + pad / 2, y + pad * 0.45), pad * 0.55)
        hl.setColorAt(0, QColor(255, 255, 255, 120))
        hl.setColorAt(1, QColor(255, 255, 255, 0))
        p.setBrush(hl)
        p.drawRoundedRect(QRectF(x, y, pad, pad), pad * 0.24, pad * 0.24)
    p.end()
    return img


def main() -> None:
    from PySide6.QtGui import QGuiApplication

    _app = QGuiApplication.instance() or QGuiApplication(sys.argv)  # muss leben, solange gezeichnet wird
    ASSETS.mkdir(parents=True, exist_ok=True)
    render(256).save(str(ASSETS / "app_icon.png"))
    # Windows-ICO mit mehreren Größen: Qt schreibt pro Datei ein Bild -> selbst zusammensetzen
    import struct
    from io import BytesIO

    from PySide6.QtCore import QBuffer, QByteArray, QIODevice

    sizes = [16, 24, 32, 48, 64, 128, 256]
    blobs = []
    for sz in sizes:
        ba = QByteArray()
        buf = QBuffer(ba)
        buf.open(QIODevice.OpenModeFlag.WriteOnly)
        render(sz).save(buf, "PNG")
        blobs.append(bytes(ba.data()))
    out = BytesIO()
    out.write(struct.pack("<HHH", 0, 1, len(sizes)))
    offset = 6 + 16 * len(sizes)
    for sz, blob in zip(sizes, blobs):
        dim = 0 if sz >= 256 else sz
        out.write(struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(blob), offset))
        offset += len(blob)
    for blob in blobs:
        out.write(blob)
    (ASSETS / "app_icon.ico").write_bytes(out.getvalue())
    print("Icons geschrieben:", ASSETS / "app_icon.png", ASSETS / "app_icon.ico")


if __name__ == "__main__":
    main()
