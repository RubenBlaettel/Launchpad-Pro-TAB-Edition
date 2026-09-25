"""Qt-Listenmodelle für QML: Kacheln, zuletzt genutzte Audiodateien, Projekte."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PySide6.QtCore import Property, QAbstractListModel, QByteArray, QModelIndex, Qt, Signal, Slot

from ..core.models import ProjectData, TileData
from ..core.util import format_time
from .qtutil import file_url


@dataclass
class TileRuntime:
    loading: bool = False
    playing: bool = False
    progress: float = 0.0
    remaining: float = 0.0
    missing: bool = False
    error: str = ""


def _roles(*names: str) -> dict[int, QByteArray]:
    return {Qt.ItemDataRole.UserRole + 1 + i: QByteArray(n.encode()) for i, n in enumerate(names)}


class TileModel(QAbstractListModel):
    ROLE_NAMES = _roles(
        "tileIndex", "row", "col", "empty", "title", "tileColor", "coverUrl", "durationText",
        "loop", "playing", "progress", "remainingText", "loading", "edited", "missing", "sourceName",
        "errorText",
    )
    _ROLE = {bytes(v).decode(): k for k, v in ROLE_NAMES.items()}
    countChanged = Signal()
    count = Property(int, lambda self: self.rowCount(), notify=countChanged)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._project: ProjectData | None = None
        self._project_root: Path | None = None
        self._runtime: dict[tuple[int, int], TileRuntime] = {}

    # ------------------------------------------------------------------
    def set_project(self, project: ProjectData | None, root: Path | None) -> None:
        self.beginResetModel()
        self._project = project
        self._project_root = root
        self._runtime = {}
        self.endResetModel()
        self.countChanged.emit()

    def reset(self) -> None:
        self.beginResetModel()
        self.endResetModel()
        self.countChanged.emit()

    def runtime(self, key: tuple[int, int]) -> TileRuntime:
        rt = self._runtime.get(key)
        if rt is None:
            rt = TileRuntime()
            self._runtime[key] = rt
        return rt

    def clear_runtime(self, key: tuple[int, int]) -> None:
        self._runtime.pop(key, None)

    def index_for(self, key: tuple[int, int]) -> int:
        if self._project is None:
            return -1
        r, c = key
        n = self._project.grid
        return r * n + c if (0 <= r < n and 0 <= c < n) else -1

    def refresh(self, key: tuple[int, int], *role_names: str) -> None:
        i = self.index_for(key)
        if i < 0:
            return
        idx = self.index(i, 0)
        roles = [self._ROLE[n] for n in role_names] if role_names else []
        self.dataChanged.emit(idx, idx, roles)

    # ------------------------------------------------------------------
    def roleNames(self) -> dict[int, QByteArray]:  # noqa: N802 (Qt-API)
        return self.ROLE_NAMES

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        if parent.isValid() or self._project is None:
            return 0
        return self._project.grid * self._project.grid

    @Slot(result=int)
    def gridSize(self) -> int:  # noqa: N802
        return self._project.grid if self._project else 0

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or self._project is None:
            return None
        r, c = divmod(index.row(), self._project.grid)
        tile: TileData | None = self._project.peek(r, c)
        rt = self._runtime.get((r, c))
        name = bytes(self.ROLE_NAMES.get(role, b"")).decode()
        if name == "tileIndex":
            return index.row()
        if name == "row":
            return r
        if name == "col":
            return c
        if name == "empty":
            return tile is None or tile.is_empty
        if name == "title":
            return tile.display_title if tile else ""
        if name == "tileColor":
            return tile.color if tile else "#D64DFF"
        if name == "coverUrl":
            if tile and tile.cover and self._project_root is not None:
                return file_url(str(self._project_root / tile.cover))
            return ""
        if name == "durationText":
            return format_time(tile.duration) if tile and tile.duration > 0 else ""
        if name == "loop":
            return bool(tile and tile.loop)
        if name == "playing":
            return bool(rt and rt.playing)
        if name == "progress":
            return float(rt.progress) if rt else 0.0
        if name == "remainingText":
            return format_time(-(rt.remaining)) if rt and rt.playing else ""
        if name == "loading":
            return bool(rt and rt.loading)
        if name == "edited":
            return bool(tile and tile.is_edited)
        if name == "missing":
            return bool(rt and rt.missing)
        if name == "sourceName":
            return tile.source_name if tile else ""
        if name == "errorText":
            return rt.error if rt else ""
        return None


class RecentAudioModel(QAbstractListModel):
    ROLE_NAMES = _roles("path", "fileUrl", "name", "ext", "durationText", "exists")
    countChanged = Signal()
    count = Property(int, lambda self: self.rowCount(), notify=countChanged)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: list[dict[str, Any]] = []

    def set_items(self, items: list[dict[str, Any]]) -> None:
        self.beginResetModel()
        self._items = [dict(i) for i in items]
        for item in self._items:
            item["exists"] = Path(item["path"]).exists()
        self.endResetModel()
        self.countChanged.emit()

    def roleNames(self) -> dict[int, QByteArray]:  # noqa: N802
        return self.ROLE_NAMES

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._items)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or index.row() >= len(self._items):
            return None
        item = self._items[index.row()]
        name = bytes(self.ROLE_NAMES.get(role, b"")).decode()
        if name == "path":
            return item["path"]
        if name == "fileUrl":
            return file_url(item["path"])
        if name == "name":
            return item.get("name") or Path(item["path"]).name
        if name == "ext":
            return Path(item["path"]).suffix.lstrip(".").upper()[:4]
        if name == "durationText":
            d = float(item.get("duration") or 0.0)
            return format_time(d) if d > 0 else ""
        if name == "exists":
            return bool(item.get("exists", True))
        return None


class RecentProjectsModel(QAbstractListModel):
    ROLE_NAMES = _roles("path", "name", "openedText", "exists", "current")
    countChanged = Signal()
    count = Property(int, lambda self: self.rowCount(), notify=countChanged)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: list[dict[str, Any]] = []
        self._current = ""

    def set_items(self, items: list[dict[str, Any]], current: str = "") -> None:
        self.beginResetModel()
        self._items = [dict(i) for i in items]
        self._current = current
        for item in self._items:
            item["exists"] = Path(item["path"]).exists()
        self.endResetModel()
        self.countChanged.emit()

    def roleNames(self) -> dict[int, QByteArray]:  # noqa: N802
        return self.ROLE_NAMES

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._items)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or index.row() >= len(self._items):
            return None
        item = self._items[index.row()]
        name = bytes(self.ROLE_NAMES.get(role, b"")).decode()
        if name == "path":
            return item["path"]
        if name == "name":
            return item.get("name") or Path(item["path"]).name
        if name == "openedText":
            opened = str(item.get("opened") or "")
            return opened[:16].replace("T", " ") if opened else ""
        if name == "exists":
            return bool(item.get("exists"))
        if name == "current":
            return item["path"] == self._current
        return None
