"""Erzeugt die Bilder für den Windows-Installer (Inno Setup).

    python tools/make_installer_images.py

* ``packaging/windows/wizard-large.png`` – Seitenbild der Willkommens-/Abschlussseite
  (Seitenverhältnis 164:314, in 2,5-facher Auflösung für hohe DPI-Stufen)
* ``packaging/windows/wizard-small.png`` – Symbol oben rechts auf den übrigen Seiten
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
OUT = ROOT / "packaging" / "windows"
FONTS = ROOT / "launchpad_pro_tab" / "assets" / "fonts"

LARGE = (410, 785)       # 164:314
SMALL = 147

PADS = ["#D64DFF", "#1FD6FF", "#FFC61A", "#14D9A0", "#FF4FA3", "#7A5CFF", "#FF5252", "#2EE66E", "#3D8BFF"]


def render_large():
    import math

    from PySide6.QtCore import QPointF, QRectF, Qt
    from PySide6.QtGui import QColor, QFont, QImage, QLinearGradient, QPainter, QPainterPath, QPen, QRadialGradient

    from make_icon import render as render_icon

    w, h = LARGE
    img = QImage(w, h, QImage.Format.Format_ARGB32)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    bg = QLinearGradient(0, 0, 0, h)
    bg.setColorAt(0.0, QColor("#171A24"))
    bg.setColorAt(1.0, QColor("#07080B"))
    p.fillRect(0, 0, w, h, bg)

    # Pad-Raster im Hintergrund (angeschnitten, mit Leuchten)
    pad, gap = 74.0, 16.0
    cols, rows = 5, 6
    x0 = w - cols * (pad + gap) + 34
    y0 = 440.0
    p.setPen(Qt.PenStyle.NoPen)
    for r in range(rows):
        for c in range(cols):
            x, y = x0 + c * (pad + gap), y0 + r * (pad + gap)
            i = (r * 7 + c * 3) % len(PADS)
            lit = (r + c) % 3 == 0
            color = QColor(PADS[i])
            fade = max(0.0, min(1.0, (y - h * 0.38) / (h * 0.55)))
            if lit:
                glow = QRadialGradient(QPointF(x + pad / 2, y + pad / 2), pad * 1.1)
                glow.setColorAt(0, QColor(color.red(), color.green(), color.blue(), int(120 * fade)))
                glow.setColorAt(1, QColor(color.red(), color.green(), color.blue(), 0))
                p.setBrush(glow)
                p.drawEllipse(QPointF(x + pad / 2, y + pad / 2), pad * 1.1, pad * 1.1)
                g = QLinearGradient(0, y, 0, y + pad)
                g.setColorAt(0, color.lighter(130))
                g.setColorAt(1, color.darker(140))
                g_alpha = int(255 * (0.25 + 0.75 * fade))
                p.setOpacity(g_alpha / 255)
                p.setBrush(g)
            else:
                p.setOpacity(0.35 + 0.4 * fade)
                p.setBrush(QColor("#1C202A"))
            p.drawRoundedRect(QRectF(x, y, pad, pad), 14, 14)
            p.setOpacity(1.0)

    # Abdunklung oben für gut lesbaren Titel
    shade = QLinearGradient(0, 0, 0, h * 0.62)
    shade.setColorAt(0.0, QColor(10, 11, 15, 245))
    shade.setColorAt(0.75, QColor(10, 11, 15, 200))
    shade.setColorAt(1.0, QColor(10, 11, 15, 0))
    p.fillRect(0, 0, w, int(h * 0.62), shade)

    # Logo + Schrift
    icon = render_icon(150)
    p.drawImage(QRectF((w - 150) / 2, 78, 150, 150), icon)
    font = QFont("Inter")
    font.setPixelSize(44)
    font.setWeight(QFont.Weight.Bold)
    p.setFont(font)
    p.setPen(QColor("#EEF1F7"))
    p.drawText(QRectF(0, 262, w, 60), Qt.AlignmentFlag.AlignHCenter, "Launchpad Pro")
    font.setPixelSize(22)
    font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 6)
    p.setFont(font)
    p.setPen(QColor("#D64DFF"))
    p.drawText(QRectF(0, 322, w, 40), Qt.AlignmentFlag.AlignHCenter, "TAB EDITION")

    # Wellenform (Bild 1) als Akzentlinie
    path = QPainterPath()
    base = 405.0
    for i in range(0, w + 1, 3):
        t = i / w
        amp = 16 * math.sin(math.pi * t) * (0.55 + 0.45 * math.sin(i * 0.11) * math.cos(i * 0.037))
        yv = base + amp * math.sin(i * 0.33)
        path.moveTo(i, base - abs(yv - base))
        path.lineTo(i, base + abs(yv - base))
    p.setPen(QPen(QColor(20, 217, 146, 200), 2))
    p.drawPath(path)
    p.end()
    return img


def main() -> None:
    from PySide6.QtGui import QFontDatabase, QGuiApplication

    from make_icon import render as render_icon

    _app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    for ttf in FONTS.glob("*.ttf"):
        QFontDatabase.addApplicationFont(str(ttf))
    OUT.mkdir(parents=True, exist_ok=True)
    render_large().save(str(OUT / "wizard-large.png"))
    render_icon(SMALL).save(str(OUT / "wizard-small.png"))
    print("Installer-Bilder geschrieben nach", OUT)


if __name__ == "__main__":
    main()
