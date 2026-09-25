"""Farbschema der Anwendung (Dunkel/Hell/wie System).

Das QML-Design liest nur ``backend.darkTheme``. Zusätzlich wird Qt das gewünschte Schema
mitgeteilt (``QStyleHints.setColorScheme``, Qt ≥ 6.8) – dadurch passen sich unter Windows
auch Titelleiste und Fensterrahmen an.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QStyleHints

log = logging.getLogger(__name__)


def style_hints() -> QStyleHints | None:
    return QGuiApplication.styleHints() if QGuiApplication.instance() is not None else None


def system_prefers_dark() -> bool:
    """Wünscht das Betriebssystem ein dunkles Design? Unbekannt -> dunkel (Bühnen-Standard)."""
    hints = style_hints()
    if hints is None:
        return True
    return hints.colorScheme() != Qt.ColorScheme.Light


def apply_color_scheme(mode: str) -> bool:
    """Setzt das Schema für ``mode`` ("dark" | "light" | "system") und liefert, ob dunkel."""
    hints = style_hints()
    if hints is None:
        return mode != "light"
    try:
        if mode == "system":
            if hasattr(hints, "unsetColorScheme"):
                hints.unsetColorScheme()
            return system_prefers_dark()
        if hasattr(hints, "setColorScheme"):
            hints.setColorScheme(Qt.ColorScheme.Dark if mode == "dark" else Qt.ColorScheme.Light)
    except Exception as exc:  # noqa: BLE001 – ältere Qt-Versionen/Plattformen: nur QML-Farben
        log.debug("Farbschema konnte nicht an Qt übergeben werden: %s", exc)
    return mode != "light"
