"""Hilfen für QObject-Properties mit Änderungssignal (weniger Boilerplate)."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Property, QObject, QUrl, Signal


def rprop(ptype: Any, attr: str, notify: Signal) -> Property:
    """Nur-Lese-Property, die das Attribut ``attr`` liefert."""
    return Property(ptype, lambda self: getattr(self, attr), notify=notify)


class PropertyObject(QObject):
    def _set(self, attr: str, value: Any, signal: str) -> bool:
        if getattr(self, attr) != value:
            setattr(self, attr, value)
            getattr(self, signal).emit()
            return True
        return False


def to_local_path(url_or_path: Any) -> str:
    """Akzeptiert QUrl, 'file:///…'-Strings oder normale Pfade."""
    if isinstance(url_or_path, QUrl):
        return url_or_path.toLocalFile() if url_or_path.isLocalFile() else url_or_path.toString()
    text = str(url_or_path or "")
    if text.startswith("file:"):
        return QUrl(text).toLocalFile()
    return text


def file_url(path: str | None) -> str:
    return QUrl.fromLocalFile(str(path)).toString() if path else ""
