"""Programmweite Einstellungen (JSON im Benutzer-Konfigurationsordner)."""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .constants import STOP_FADE_MS_DEFAULT
from .paths import config_dir
from .util import atomic_write_json, now_iso, read_json

log = logging.getLogger(__name__)

SETTINGS_FILE = "einstellungen.json"
MAX_RECENT_PROJECTS = 20
MAX_RECENT_AUDIO = 100
THEME_MODES = ("dark", "light", "system")


@dataclass
class AppSettings:
    last_project: str | None = None
    recent_projects: list[dict[str, Any]] = field(default_factory=list)
    recent_audio: list[dict[str, Any]] = field(default_factory=list)
    audio_device: str | None = None      # Gerätename (None = Standard)
    audio_hostapi: str | None = None     # z. B. "Windows WASAPI"
    buffer_frames: int = 0               # 0 = automatisch (niedrige Latenz)
    stop_fade_ms: float = STOP_FADE_MS_DEFAULT
    projects_dir: str | None = None
    window: dict[str, Any] = field(default_factory=dict)
    theme: str = "dark"                  # "dark" | "light" | "system"
    update_check: bool | None = None     # beim Start nach Updates suchen – None: noch nicht gefragt
    update_prereleases: bool = False     # auch Vorabversionen (Beta) anbieten
    update_skipped: str | None = None    # "Diese Version überspringen"
    update_last_check: str | None = None
    last_version: str | None = None      # zuletzt gestartete Programmversion

    _path: Path | None = field(default=None, repr=False, compare=False)

    # ------------------------------------------------------------------
    @classmethod
    def load(cls, path: Path | None = None) -> "AppSettings":
        path = path or (config_dir() / SETTINGS_FILE)
        settings = cls()
        if path.exists():
            try:
                raw = read_json(path)
                for key, value in raw.items():
                    if key in cls.__dataclass_fields__ and not key.startswith("_"):
                        setattr(settings, key, value)
                # Version 1.1.0 kannte nur „update_auto_check“ (Standard an, ohne Rückfrage):
                # ausdrücklich abgeschaltet bleibt aus, sonst wird einmal gefragt.
                if "update_check" not in raw and raw.get("update_auto_check") is False:
                    settings.update_check = False
            except Exception as exc:  # beschädigte Datei -> Standardwerte
                log.warning("Einstellungen konnten nicht gelesen werden (%s) – Standardwerte.", exc)
        settings._path = path
        settings._sanitize()
        return settings

    def save(self) -> None:
        if self._path is None:
            self._path = config_dir() / SETTINGS_FILE
        data = {k: v for k, v in asdict(self).items() if not k.startswith("_")}
        try:
            atomic_write_json(self._path, data)
        except OSError as exc:
            log.error("Einstellungen konnten nicht gespeichert werden: %s", exc)

    def _sanitize(self) -> None:
        if not isinstance(self.recent_projects, list):
            self.recent_projects = []
        if not isinstance(self.recent_audio, list):
            self.recent_audio = []
        self.recent_projects = [p for p in self.recent_projects if isinstance(p, dict) and p.get("path")]
        self.recent_audio = [a for a in self.recent_audio if isinstance(a, dict) and a.get("path")]
        try:
            self.buffer_frames = int(self.buffer_frames)
        except (TypeError, ValueError):
            self.buffer_frames = 0
        try:
            self.stop_fade_ms = float(self.stop_fade_ms)
        except (TypeError, ValueError):
            self.stop_fade_ms = STOP_FADE_MS_DEFAULT
        if self.theme not in THEME_MODES:
            self.theme = "dark"
        if self.update_check is not None:
            self.update_check = bool(self.update_check)
        self.update_prereleases = bool(self.update_prereleases)
        for key in ("update_skipped", "update_last_check", "last_version"):
            if not isinstance(getattr(self, key), (str, type(None))):
                setattr(self, key, None)

    # ------------------------------------------------------------------
    def remember_project(self, path: Path, name: str) -> None:
        key = str(Path(path).resolve())
        self.recent_projects = [p for p in self.recent_projects if p.get("path") != key]
        self.recent_projects.insert(0, {"path": key, "name": name, "opened": now_iso()})
        del self.recent_projects[MAX_RECENT_PROJECTS:]
        self.last_project = key

    def forget_project(self, path: str) -> None:
        self.recent_projects = [p for p in self.recent_projects if p.get("path") != path]
        if self.last_project == path:
            self.last_project = None

    def remember_audio(self, path: Path, duration: float | None = None) -> dict[str, Any]:
        key = str(Path(path).resolve())
        previous = next((a for a in self.recent_audio if a.get("path") == key), None)
        self.recent_audio = [a for a in self.recent_audio if a.get("path") != key]
        entry = {
            "path": key,
            "name": Path(key).name,
            "duration": float(duration if duration is not None else (previous or {}).get("duration") or 0.0),
            "used": now_iso(),
        }
        self.recent_audio.insert(0, entry)
        del self.recent_audio[MAX_RECENT_AUDIO:]
        return entry

    def update_audio_duration(self, path: Path, duration: float) -> bool:
        key = str(Path(path).resolve())
        for entry in self.recent_audio:
            if entry.get("path") == key:
                entry["duration"] = float(duration)
                return True
        return False

    def forget_audio(self, path: str) -> None:
        self.recent_audio = [a for a in self.recent_audio if a.get("path") != path]
