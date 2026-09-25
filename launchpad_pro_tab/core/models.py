"""Datenmodell eines Projekts (Kacheln, Bearbeitungsparameter) inkl. JSON-Serialisierung."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from .constants import (
    GAIN_MAX,
    GAIN_MIN,
    GRID_DEFAULT,
    GRID_MAX,
    GRID_MIN,
    PROJECT_FORMAT,
    PROJECT_FORMAT_VERSION,
    SPEED_MAX,
    SPEED_MIN,
    TILE_COLOR_DEFAULT,
)
from .util import now_iso


def clamp(value: float, lo: float, hi: float) -> float:
    return lo if value < lo else hi if value > hi else value


def clamp_grid(n: int) -> int:
    return int(clamp(int(n), GRID_MIN, GRID_MAX))


@dataclass
class EditParams:
    """Nicht-destruktive Bearbeitung einer Original-Audiodatei.

    ``start``/``end`` sind Sekunden in der Originaldatei (``end=None`` = bis zum Ende).
    """

    start: float = 0.0
    end: float | None = None
    speed: float = 1.0
    gain: float = 1.0

    def normalized(self, duration: float) -> "EditParams":
        start = clamp(float(self.start), 0.0, max(0.0, duration))
        end = duration if self.end is None else clamp(float(self.end), 0.0, duration)
        if end <= start:
            start, end = 0.0, duration
        return EditParams(
            start=start,
            end=end,
            speed=clamp(float(self.speed), SPEED_MIN, SPEED_MAX),
            gain=clamp(float(self.gain), GAIN_MIN, GAIN_MAX),
        )

    def is_identity(self, duration: float, eps: float = 1e-3) -> bool:
        p = self.normalized(duration)
        return (
            p.start <= eps
            and (p.end is None or p.end >= duration - eps)
            and abs(p.speed - 1.0) < 1e-4
            and abs(p.gain - 1.0) < 1e-4
        )

    def to_dict(self) -> dict[str, Any]:
        return {"start": round(self.start, 6), "end": None if self.end is None else round(self.end, 6),
                "speed": round(self.speed, 6), "gain": round(self.gain, 6)}

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "EditParams | None":
        if not data:
            return None
        end = data.get("end")
        return cls(
            start=float(data.get("start", 0.0)),
            end=None if end is None else float(end),
            speed=float(data.get("speed", 1.0)),
            gain=float(data.get("gain", 1.0)),
        )


@dataclass
class TileData:
    """Eine Kachel im Raster. Pfade sind relativ zum Projektordner gespeichert."""

    row: int
    col: int
    title: str = ""
    color: str = TILE_COLOR_DEFAULT
    audio: str | None = None       # abspielbare Datei (Original oder bearbeitete Fassung)
    original: str | None = None    # Originaldatei (Kopie im Projektordner)
    cover: str | None = None
    loop: bool = False
    edit: EditParams | None = None  # gesetzt, wenn ``audio`` eine bearbeitete Fassung ist
    duration: float = 0.0           # Dauer von ``audio`` in Sekunden
    source_name: str = ""           # ursprünglicher Dateiname (Anzeige)

    @property
    def is_empty(self) -> bool:
        return not self.audio

    @property
    def has_content(self) -> bool:
        """True, wenn die Kachel irgendetwas Speichernswertes enthält."""
        return bool(self.audio or self.cover or self.title or self.color != TILE_COLOR_DEFAULT or self.loop)

    @property
    def is_edited(self) -> bool:
        return self.edit is not None and self.audio is not None and self.audio != self.original

    @property
    def display_title(self) -> str:
        if self.title:
            return self.title
        if self.source_name:
            name = self.source_name
            return name.rsplit(".", 1)[0] if "." in name else name
        return ""

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "row": self.row,
            "col": self.col,
            "title": self.title,
            "color": self.color,
            "audio": self.audio,
            "original": self.original,
            "cover": self.cover,
            "loop": self.loop,
            "duration": round(self.duration, 4),
            "source_name": self.source_name,
        }
        if self.edit is not None:
            data["edit"] = self.edit.to_dict()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TileData":
        return cls(
            row=int(data["row"]),
            col=int(data["col"]),
            title=str(data.get("title") or ""),
            color=str(data.get("color") or TILE_COLOR_DEFAULT),
            audio=data.get("audio") or None,
            original=data.get("original") or data.get("audio") or None,
            cover=data.get("cover") or None,
            loop=bool(data.get("loop", False)),
            edit=EditParams.from_dict(data.get("edit")),
            duration=float(data.get("duration") or 0.0),
            source_name=str(data.get("source_name") or ""),
        )

    def clear(self) -> None:
        """Setzt die Kachel auf 'unbelegt' zurück (Position bleibt)."""
        self.title = ""
        self.color = TILE_COLOR_DEFAULT
        self.audio = None
        self.original = None
        self.cover = None
        self.loop = False
        self.edit = None
        self.duration = 0.0
        self.source_name = ""

    def copy(self) -> "TileData":
        return TileData.from_dict(self.to_dict())


@dataclass
class ProjectData:
    name: str
    grid: int = GRID_DEFAULT
    tiles: dict[tuple[int, int], TileData] = field(default_factory=dict)
    created: str = field(default_factory=now_iso)
    modified: str = field(default_factory=now_iso)

    # -- Kacheln -------------------------------------------------------------
    def tile(self, row: int, col: int) -> TileData:
        """Liefert die Kachel an (row, col) – legt bei Bedarf eine leere an."""
        key = (row, col)
        t = self.tiles.get(key)
        if t is None:
            t = TileData(row=row, col=col)
            self.tiles[key] = t
        return t

    def peek(self, row: int, col: int) -> TileData | None:
        return self.tiles.get((row, col))

    def index_of(self, row: int, col: int) -> int:
        return row * self.grid + col

    def pos_of(self, index: int) -> tuple[int, int]:
        return divmod(int(index), self.grid)

    def tiles_outside(self, n: int) -> list[TileData]:
        """Kacheln, die bei einem Raster von n×n wegfallen würden (nur belegte)."""
        return [t for (r, c), t in self.tiles.items() if (r >= n or c >= n) and t.has_content]

    def resize(self, n: int) -> list[TileData]:
        """Ändert die Rastergröße; wegfallende Kacheln werden verworfen und zurückgegeben."""
        n = clamp_grid(n)
        removed = [t for (r, c), t in self.tiles.items() if r >= n or c >= n]
        for t in removed:
            del self.tiles[(t.row, t.col)]
        self.grid = n
        return [t for t in removed if t.has_content]

    def assigned_tiles(self) -> Iterable[TileData]:
        return (t for t in self.tiles.values() if not t.is_empty)

    def referenced_files(self) -> set[str]:
        refs: set[str] = set()
        for t in self.tiles.values():
            for p in (t.audio, t.original, t.cover):
                if p:
                    refs.add(p)
        return refs

    # -- Serialisierung ------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        tiles = [t.to_dict() for (r, c), t in sorted(self.tiles.items()) if t.has_content]
        return {
            "format": PROJECT_FORMAT,
            "version": PROJECT_FORMAT_VERSION,
            "name": self.name,
            "created": self.created,
            "modified": self.modified,
            "grid": {"rows": self.grid, "cols": self.grid},
            "tiles": tiles,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProjectData":
        if data.get("format") not in (None, PROJECT_FORMAT):
            raise ValueError("Die Datei ist keine Launchpad-Pro-TAB-Projektdatei.")
        version = int(data.get("version", 1))
        if version > PROJECT_FORMAT_VERSION:
            raise ValueError(
                f"Das Projekt wurde mit einer neueren Programmversion erstellt (Format {version})."
            )
        grid_info = data.get("grid", {})
        if isinstance(grid_info, dict):
            grid = clamp_grid(max(int(grid_info.get("rows", GRID_DEFAULT)), int(grid_info.get("cols", GRID_DEFAULT))))
        else:
            grid = clamp_grid(int(grid_info))
        project = cls(
            name=str(data.get("name") or "Projekt"),
            grid=grid,
            created=str(data.get("created") or now_iso()),
            modified=str(data.get("modified") or now_iso()),
        )
        for raw in data.get("tiles", []):
            tile = TileData.from_dict(raw)
            if 0 <= tile.row < grid and 0 <= tile.col < grid:
                project.tiles[(tile.row, tile.col)] = tile
        return project
