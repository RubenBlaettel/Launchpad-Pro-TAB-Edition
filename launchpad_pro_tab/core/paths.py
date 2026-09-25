"""Plattformabhängige Speicherorte (Einstellungen, Logs, Standard-Projektordner)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from .. import __app_id__

APP_DIR_NAME = "Launchpad Pro TAB"


def config_dir() -> Path:
    """Ordner für Einstellungen/Logs. Über ``LPTAB_CONFIG_DIR`` überschreibbar (Tests)."""
    override = os.environ.get("LPTAB_CONFIG_DIR")
    if override:
        path = Path(override)
    elif sys.platform == "win32":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        path = Path(base) / __app_id__
    elif sys.platform == "darwin":
        path = Path.home() / "Library" / "Application Support" / __app_id__
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
        path = Path(base) / "launchpad-pro-tab"
    path.mkdir(parents=True, exist_ok=True)
    return path


def default_documents_dir() -> Path:
    """Fallback, falls Qt (QStandardPaths) keinen Dokumente-Ordner liefert."""
    home = Path.home()
    for name in ("Documents", "Dokumente"):
        candidate = home / name
        if candidate.is_dir():
            return candidate
    return home


def default_projects_dir(documents: Path | None = None) -> Path:
    override = os.environ.get("LPTAB_PROJECTS_DIR")
    if override:
        return Path(override)
    return (documents or default_documents_dir()) / APP_DIR_NAME
