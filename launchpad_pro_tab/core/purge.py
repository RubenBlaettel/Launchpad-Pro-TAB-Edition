"""Benutzerdaten entfernen (Deinstallation mit „Alle Projekte und Einstellungen löschen“).

Wird vom Windows-Deinstaller bzw. vom Linux-Deinstallationsskript aufgerufen:

    LaunchpadProTAB --purge-user-data --yes

Sicherheitsregeln – es wird nie „einfach ein Ordner“ gelöscht:

* Als Projekt gilt nur ein Ordner mit einer gültigen ``projekt.lptab`` dieses Programms.
* In Projektordnern werden nur die vom Programm angelegten Einträge gelöscht
  (``projekt.lptab``, ``audio/``, ``cover/``, ``.autosave/``, ``.cache/``). Eigene Dateien, die
  jemand zusätzlich dort abgelegt hat, bleiben erhalten – samt Ordner.
* Geschützte Orte (Laufwerkswurzel, Benutzerordner, Dokumente, Desktop, Musik …) werden
  niemals als Projekt behandelt.
* Exportierte ZIP-Dateien werden nicht angefasst.
"""

from __future__ import annotations

import json
import logging
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from .. import __app_name__
from .constants import AUDIO_DIR, AUTOSAVE_DIR, CACHE_DIR, COVER_DIR, PROJECT_FILE_NAME, PROJECT_FORMAT
from .paths import cache_dir, config_dir, default_projects_dir
from .settings import AppSettings

log = logging.getLogger(__name__)

# Vom Programm in einem Projektordner angelegte Einträge
PROJECT_ENTRIES = (PROJECT_FILE_NAME, AUDIO_DIR, COVER_DIR, AUTOSAVE_DIR, CACHE_DIR)


@dataclass
class PurgePlan:
    projects: list[Path] = field(default_factory=list)
    projects_root: Path | None = None       # Standard-Projektordner (wird gelöscht, wenn danach leer)
    data_dirs: list[Path] = field(default_factory=list)   # Einstellungen, Protokolle, Update-Downloads

    def describe(self) -> list[str]:
        lines = [f"Projekt: {p}" for p in self.projects]
        if self.projects_root is not None:
            lines.append(f"Projektordner (falls danach leer): {self.projects_root}")
        lines += [f"Programmdaten: {d}" for d in self.data_dirs]
        return lines


@dataclass
class PurgeReport:
    deleted: list[str] = field(default_factory=list)
    kept: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _resolve(path: Path) -> Path:
    try:
        return path.expanduser().resolve()
    except OSError:
        return path.expanduser().absolute()


def protected_dirs(extra: list[Path] | None = None) -> set[Path]:
    """Orte, die nie gelöscht werden dürfen – auch nicht, wenn dort eine Projektdatei liegt."""
    home = Path.home()
    names = ("Documents", "Dokumente", "Desktop", "Schreibtisch", "Music", "Musik", "Downloads",
             "Videos", "Pictures", "Bilder", "OneDrive")
    out = {_resolve(home), _resolve(home.parent)}
    out.update(_resolve(home / n) for n in names)
    for p in extra or []:
        out.add(_resolve(p))
    return out


def is_project_dir(path: Path) -> bool:
    """Enthält der Ordner eine Projektdatei dieses Programms?"""
    file = path / PROJECT_FILE_NAME
    try:
        if not file.is_file():
            return False
        with open(file, encoding="utf-8-sig") as fh:
            data = json.load(fh)
    except (OSError, ValueError, UnicodeDecodeError):
        # Beschädigte Projektdatei: über die Sicherung erkennen
        backup = path / AUTOSAVE_DIR / (PROJECT_FILE_NAME + ".bak")
        try:
            with open(backup, encoding="utf-8-sig") as fh:
                data = json.load(fh)
        except (OSError, ValueError, UnicodeDecodeError):
            return False
    return isinstance(data, dict) and data.get("format") == PROJECT_FORMAT


def _project_candidates(settings: AppSettings) -> list[Path]:
    paths: list[str] = []
    if settings.last_project:
        paths.append(settings.last_project)
    paths += [str(p.get("path")) for p in settings.recent_projects if p.get("path")]
    out = []
    for raw in paths:
        p = Path(raw)
        out.append(p.parent if p.name == PROJECT_FILE_NAME else p)
    return out


def plan_purge(settings: AppSettings | None = None, documents: Path | None = None,
               extra_dirs: list[Path] | None = None) -> PurgePlan:
    """Was würde gelöscht? ``extra_dirs``: weitere Programmordner (z. B. Qts QML-Cache);
    sie werden nur übernommen, wenn der Programmname im Pfad vorkommt."""
    settings = settings or AppSettings.load()
    root = Path(settings.projects_dir) if settings.projects_dir else default_projects_dir(documents)
    root = _resolve(root)
    guard = protected_dirs([documents] if documents else None)

    candidates = _project_candidates(settings)
    if root.is_dir():
        try:
            candidates += [p for p in root.iterdir() if p.is_dir()]
        except OSError:
            pass

    projects: list[Path] = []
    seen: set[Path] = set()
    for cand in candidates:
        path = _resolve(cand)
        if path in seen:
            continue
        seen.add(path)
        if path in guard or path.parent == path:
            continue        # Laufwerkswurzel, Benutzerordner, Dokumente … niemals
        if is_project_dir(path):
            projects.append(path)

    candidates_data = [cache_dir(), config_dir()]
    candidates_data += [d for d in (extra_dirs or []) if __app_name__ in str(d)]
    data_dirs = []
    for d in candidates_data:
        d = _resolve(Path(d))
        if d not in guard and d.parent != d and d not in data_dirs:
            data_dirs.append(d)
    return PurgePlan(
        projects=sorted(projects),
        projects_root=root if root not in guard and root.parent != root else None,
        data_dirs=data_dirs,
    )


def _remove(path: Path, report: PurgeReport) -> None:
    try:
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        elif path.exists() or path.is_symlink():
            path.unlink()
        else:
            return
        report.deleted.append(str(path))
    except OSError as exc:
        report.errors.append(f"{path}: {exc}")


def execute_purge(plan: PurgePlan) -> PurgeReport:
    report = PurgeReport()
    for project in plan.projects:
        for name in PROJECT_ENTRIES:
            _remove(project / name, report)
        try:
            project.rmdir()                      # nur, wenn nichts Fremdes übrig ist
            report.deleted.append(str(project))
        except OSError:
            report.kept.append(str(project))
    root = plan.projects_root
    if root is not None and root.is_dir():
        try:
            root.rmdir()
            report.deleted.append(str(root))
        except OSError:
            report.kept.append(str(root))
    for data_dir in plan.data_dirs:
        # Protokolldateien können noch offen sein (Windows) – dann bleiben Reste stehen
        _remove(data_dir, report)
        if __app_name__ in data_dir.name:
            try:
                data_dir.parent.rmdir()          # leerer Herstellerordner („TAB Theater“)
            except OSError:
                pass
    return report
