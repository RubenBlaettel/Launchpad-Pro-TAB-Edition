"""Registerkarten: mehrere gleichzeitig geöffnete Projekte (wie Tabs im Browser).

Jede Karte hält den kompletten Laufzeitzustand ihres Projekts (geladene Audiodaten, Lade-
Tokens, Anzeige-Zustand der Kacheln). Kacheln im Hintergrund spielen daher ungestört weiter;
in der Audio-Engine sind sie über ``(uid, Zeile, Spalte)`` eindeutig.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import numpy as np
from PySide6.QtCore import Property, QAbstractListModel, QByteArray, QModelIndex, Qt, Signal

from ..core.project import Project
from .models import TileRuntime, _roles

Key = tuple[int, int]
EngineKey = tuple[int, int, int]


@dataclass(eq=False)
class ProjectTab:
    """Eine Registerkarte – mit Projekt oder leer (Startseite)."""

    uid: int
    project: Project | None = None
    pcm: dict[Key, np.ndarray] = field(default_factory=dict)       # abspielbereite Audiodaten (memmap)
    tokens: dict[Key, int] = field(default_factory=dict)           # verwirft veraltete Ladeergebnisse
    runtime: dict[Key, TileRuntime] = field(default_factory=dict)  # lädt/spielt/Fortschritt je Kachel
    playing: int = 0                                               # Anzahl laufender Kacheln
    dirty: bool = False
    last_saved: datetime | None = None

    def engine_key(self, key: Key) -> EngineKey:
        return (self.uid, key[0], key[1])

    def rt(self, key: Key) -> TileRuntime:
        rt = self.runtime.get(key)
        if rt is None:
            rt = self.runtime[key] = TileRuntime()
        return rt

    def next_token(self, key: Key) -> int:
        token = self.tokens.get(key, 0) + 1
        self.tokens[key] = token
        return token

    def reset(self, project: Project | None) -> None:
        """Neues Projekt in dieser Karte: Laufzeitzustand verwerfen."""
        self.project = project
        self.pcm.clear()
        self.runtime.clear()
        self.playing = 0
        self.dirty = False
        self.last_saved = None
        # Tokens bleiben erhalten (weiterzählen) -> alte Ladeergebnisse passen garantiert nicht mehr


class TabsModel(QAbstractListModel):
    """Die Registerkarten für die Tab-Leiste in QML."""

    ROLE_NAMES = _roles("uid", "title", "path", "hasProject", "dirty", "playing", "active")
    _ROLE = {bytes(v).decode(): k for k, v in ROLE_NAMES.items()}
    countChanged = Signal()
    count = Property(int, lambda self: self.rowCount(), notify=countChanged)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tabs: list[ProjectTab] = []
        self._active: ProjectTab | None = None

    def set_tabs(self, tabs: list[ProjectTab], active: ProjectTab | None) -> None:
        self.beginResetModel()
        self._tabs = list(tabs)
        self._active = active
        self.endResetModel()
        self.countChanged.emit()

    def set_active(self, active: ProjectTab | None) -> None:
        old, self._active = self._active, active
        if old is not None:
            self.refresh(old, "active")
        if active is not None and active is not old:
            self.refresh(active, "active")

    def refresh(self, tab: ProjectTab, *role_names: str) -> None:
        try:
            row = self._tabs.index(tab)
        except ValueError:
            return
        idx = self.index(row, 0)
        self.dataChanged.emit(idx, idx, [self._ROLE[n] for n in role_names])

    def roleNames(self) -> dict[int, QByteArray]:  # noqa: N802 (Qt-API)
        return self.ROLE_NAMES

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._tabs)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or index.row() >= len(self._tabs):
            return None
        tab = self._tabs[index.row()]
        name = bytes(self.ROLE_NAMES.get(role, b"")).decode()
        project = tab.project
        if name == "uid":
            return tab.uid
        if name == "title":
            return project.name if project is not None else "Neuer Tab"
        if name == "path":
            return str(project.root) if project is not None else ""
        if name == "hasProject":
            return project is not None
        if name == "dirty":
            return tab.dirty
        if name == "playing":
            return tab.playing
        if name == "active":
            return tab is self._active
        return None
