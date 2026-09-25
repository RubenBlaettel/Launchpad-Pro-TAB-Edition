"""Coverbilder (JPG, PNG, ICO) einlesen und für die Kacheln normalisieren.

* ICO-Dateien enthalten oft mehrere Größen – es wird automatisch die größte genommen.
* Sehr große Fotos werden auf max. 1024 px verkleinert (spart RAM/GPU-Speicher).
* Das Einpassen "kachelfüllend" übernimmt QML (``Image.PreserveAspectCrop``).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QImage, QImageReader

MAX_COVER_PX = 1024


class CoverError(Exception):
    pass


def read_best_image(path: Path) -> QImage:
    reader = QImageReader(str(path))
    reader.setAutoTransform(True)  # EXIF-Drehung von Handyfotos berücksichtigen
    if not reader.canRead():
        raise CoverError("Das Bild kann nicht gelesen werden (unterstützt: JPG, PNG, ICO).")
    best = QImage()
    count = max(1, reader.imageCount())
    for i in range(count):
        if i > 0 and not reader.jumpToImage(i):
            break
        img = reader.read()
        if img.isNull():
            continue
        if best.isNull() or img.width() * img.height() > best.width() * best.height():
            best = img
    if best.isNull():
        raise CoverError(f"Das Bild ist beschädigt: {reader.errorString()}")
    return best


def import_cover(src: Path, target_dir: Path) -> Path:
    """Liest ``src``, normalisiert es und speichert es im Projekt. Liefert den Zielpfad."""
    src = Path(src)
    img = read_best_image(src)
    if max(img.width(), img.height()) > MAX_COVER_PX:
        img = img.scaled(QSize(MAX_COVER_PX, MAX_COVER_PX), Qt.AspectRatioMode.KeepAspectRatio,
                         Qt.TransformationMode.SmoothTransformation)
    token = hashlib.sha1(f"{src.name}|{src.stat().st_size}|{src.stat().st_mtime_ns}".encode()).hexdigest()[:8]
    has_alpha = img.hasAlphaChannel()
    ext = ".png" if has_alpha or src.suffix.lower() in (".png", ".ico") else ".jpg"
    stem = "".join(ch if ch.isalnum() or ch in "-_ " else "_" for ch in src.stem)[:60] or "cover"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{stem}_{token}{ext}"
    if not target.exists():
        ok = img.save(str(target), "PNG" if ext == ".png" else "JPG", -1 if ext == ".png" else 90)
        if not ok:
            raise CoverError("Das Coverbild konnte nicht gespeichert werden.")
    return target
