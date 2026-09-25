"""Projektverwaltung: Anlegen, Öffnen, Speichern, Speichern unter, Export/Import.

Aufbau eines Projektordners::

    <Ablageort>/<Projektname>/
        projekt.lptab            Konfiguration (JSON)
        audio/                   Kopien der Original-Audiodateien
        audio/bearbeitet/        gerenderte, bearbeitete Fassungen
        cover/                   Coverbilder (normalisiert)
        .autosave/               Zwischenstände (Absturzsicherung)
        .cache/                  dekodierte PCM-Daten (wird nicht exportiert)
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import zipfile
from pathlib import Path
from typing import Any

from .constants import (
    AUDIO_DIR,
    AUTOSAVE_DIR,
    CACHE_DIR,
    COVER_DIR,
    EDIT_SESSION_FILE,
    EDITED_DIR,
    EXPORT_EXCLUDE_DIRS,
    PROJECT_FILE_NAME,
)
from .models import ProjectData, clamp_grid
from .util import (
    atomic_write_json,
    copy_file,
    file_digest,
    now_iso,
    read_json,
    safe_filename,
    unique_path,
)

log = logging.getLogger(__name__)


class ProjectError(Exception):
    """Fehler mit einer für den Nutzer verständlichen (deutschen) Meldung."""


class Project:
    def __init__(self, root: Path, data: ProjectData):
        self.root = Path(root).resolve()
        self.data = data

    # ------------------------------------------------------------------
    # Pfade
    # ------------------------------------------------------------------
    @property
    def file(self) -> Path:
        return self.root / PROJECT_FILE_NAME

    @property
    def cache_dir(self) -> Path:
        return self.root / CACHE_DIR

    @property
    def autosave_dir(self) -> Path:
        return self.root / AUTOSAVE_DIR

    @property
    def name(self) -> str:
        return self.data.name

    def abs(self, rel: str | None) -> Path | None:
        if not rel:
            return None
        p = Path(rel)
        return p if p.is_absolute() else (self.root / p)

    def rel(self, path: Path) -> str:
        path = Path(path).resolve()
        try:
            return path.relative_to(self.root).as_posix()
        except ValueError:
            return str(path)

    # ------------------------------------------------------------------
    # Anlegen / Öffnen / Speichern
    # ------------------------------------------------------------------
    @classmethod
    def create(cls, name: str, location: Path, grid: int) -> "Project":
        name = name.strip()
        if not name:
            raise ProjectError("Bitte einen Projektnamen angeben.")
        location = Path(location).expanduser()
        try:
            location.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise ProjectError(f"Der Ablageort kann nicht angelegt werden:\n{exc}") from exc
        root = location / safe_filename(name)
        if root.exists() and any(root.iterdir()):
            if (root / PROJECT_FILE_NAME).exists():
                raise ProjectError(f"Am Ablageort existiert bereits ein Projekt „{root.name}“.")
            root = unique_path(root)
        project = cls(root, ProjectData(name=name, grid=clamp_grid(grid)))
        project._ensure_layout()
        project.save()
        return project

    @classmethod
    def open(cls, path: Path) -> "Project":
        path = Path(path).expanduser()
        if path.is_dir():
            file = path / PROJECT_FILE_NAME
        else:
            file = path
        if not file.exists():
            raise ProjectError(f"Keine Projektdatei gefunden:\n{file}")
        try:
            raw = read_json(file)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            # Datei beschädigt (z. B. Stromausfall) -> letzte Sicherung laden
            backup = file.parent / AUTOSAVE_DIR / (PROJECT_FILE_NAME + ".bak")
            if not backup.exists():
                raise ProjectError(f"Die Projektdatei ist beschädigt:\n{exc}") from exc
            log.warning("Projektdatei beschädigt (%s) – lade Sicherung.", exc)
            try:
                raw = read_json(backup)
            except Exception as exc2:
                raise ProjectError(f"Projektdatei und Sicherung sind beschädigt:\n{exc2}") from exc2
        try:
            data = ProjectData.from_dict(raw)
        except (ValueError, KeyError, TypeError) as exc:
            raise ProjectError(str(exc)) from exc
        project = cls(file.parent, data)
        project._ensure_layout()
        return project

    def _ensure_layout(self) -> None:
        for sub in (AUDIO_DIR, EDITED_DIR, COVER_DIR, AUTOSAVE_DIR, CACHE_DIR):
            (self.root / sub).mkdir(parents=True, exist_ok=True)

    def save(self) -> None:
        """Speichert atomar; die vorherige Fassung bleibt als .bak erhalten."""
        self._ensure_layout()
        self.data.modified = now_iso()
        payload = self.data.to_dict()
        if self.file.exists():
            try:
                shutil.copy2(self.file, self.autosave_dir / (PROJECT_FILE_NAME + ".bak"))
            except OSError:
                pass
        try:
            atomic_write_json(self.file, payload)
        except OSError as exc:
            raise ProjectError(f"Projekt konnte nicht gespeichert werden:\n{exc}") from exc

    def save_as(self, target_parent: Path, new_name: str | None = None, save_first: bool = True) -> "Project":
        """Kopiert das komplette Projekt an einen neuen Ort und liefert die neue Instanz.

        ``save_first=False``, wenn der Aufrufer bereits gespeichert hat (z. B. weil die Kopie
        in einem Hintergrund-Thread läuft und die Projektdaten nicht parallel gelesen werden sollen).
        """
        name = (new_name or self.data.name).strip() or self.data.name
        target_parent = Path(target_parent).expanduser()
        target = unique_path(target_parent / safe_filename(name))
        if target.resolve() == self.root:
            self.save()
            return self
        if str(target.resolve()).startswith(str(self.root) + os.sep):
            raise ProjectError("Ein Projekt kann nicht in seinen eigenen Ordner gespeichert werden.")
        if save_first:
            self.save()
        try:
            shutil.copytree(self.root, target, ignore=shutil.ignore_patterns(CACHE_DIR, "*.tmp"))
        except OSError as exc:
            raise ProjectError(f"Speichern unter fehlgeschlagen:\n{exc}") from exc
        clone = Project.open(target)
        clone.data.name = name
        clone.save()
        return clone

    # ------------------------------------------------------------------
    # Export / Import
    # ------------------------------------------------------------------
    def export_zip(self, zip_path: Path, save_first: bool = True) -> Path:
        if save_first:
            self.save()
        zip_path = Path(zip_path).expanduser()
        if zip_path.suffix.lower() != ".zip":
            zip_path = zip_path.with_suffix(".zip")
        zip_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = zip_path.with_name(zip_path.name + ".part")
        top = safe_filename(self.data.name)
        try:
            with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
                for dirpath, dirnames, filenames in os.walk(self.root):
                    rel_dir = Path(dirpath).relative_to(self.root)
                    if rel_dir.parts and rel_dir.parts[0] in EXPORT_EXCLUDE_DIRS:
                        dirnames[:] = []
                        continue
                    dirnames[:] = [d for d in dirnames if not (not rel_dir.parts and d in EXPORT_EXCLUDE_DIRS)]
                    for fn in filenames:
                        src = Path(dirpath) / fn
                        # Temp-Dateien und das Archiv selbst (Export in den Projektordner) auslassen
                        if fn.endswith((".tmp", ".part")) or src.resolve() in (tmp.resolve(), zip_path.resolve()):
                            continue
                        arc = Path(top) / rel_dir / fn
                        # Audio ist bereits komprimiert -> nicht erneut packen (schneller)
                        compress = zipfile.ZIP_STORED if src.suffix.lower() in _NO_COMPRESS else zipfile.ZIP_DEFLATED
                        zf.write(src, arc.as_posix(), compress_type=compress)
            os.replace(tmp, zip_path)
        except OSError as exc:
            try:
                tmp.unlink()
            except OSError:
                pass
            raise ProjectError(f"Export fehlgeschlagen:\n{exc}") from exc
        return zip_path

    @staticmethod
    def import_zip(zip_path: Path, dest_parent: Path) -> Path:
        """Entpackt ein exportiertes Projekt und liefert den Projektordner."""
        zip_path = Path(zip_path)
        try:
            zf = zipfile.ZipFile(zip_path)
        except (OSError, zipfile.BadZipFile) as exc:
            raise ProjectError(f"Die ZIP-Datei kann nicht gelesen werden:\n{exc}") from exc
        with zf:
            names = zf.namelist()
            project_files = [n for n in names if n.endswith("/" + PROJECT_FILE_NAME) or n == PROJECT_FILE_NAME]
            if not project_files:
                raise ProjectError("Die ZIP-Datei enthält kein Launchpad-Projekt.")
            inner = project_files[0].rsplit("/", 1)[0] if "/" in project_files[0] else ""
            folder_name = inner.split("/")[-1] if inner else zip_path.stem
            target = unique_path(Path(dest_parent) / safe_filename(folder_name))
            target.mkdir(parents=True)
            prefix = inner + "/" if inner else ""
            target_resolved = target.resolve()
            for member in zf.infolist():
                if not member.filename.startswith(prefix) or member.is_dir():
                    continue
                rel = member.filename[len(prefix):]
                dest = (target / rel).resolve()
                # Schutz vor "Zip-Slip" (Pfade außerhalb des Zielordners)
                if not str(dest).startswith(str(target_resolved) + os.sep):
                    continue
                dest.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(member) as src, open(dest, "wb") as dst:
                    shutil.copyfileobj(src, dst, 1 << 20)
        return target

    # ------------------------------------------------------------------
    # Dateien in das Projekt übernehmen
    # ------------------------------------------------------------------
    def import_audio(self, src: Path) -> str:
        """Kopiert eine Audiodatei nach ``audio/`` (Duplikate werden wiederverwendet)."""
        return self._import_file(Path(src), AUDIO_DIR)

    def _import_file(self, src: Path, sub: str) -> str:
        src = src.resolve()
        if not src.is_file():
            raise ProjectError(f"Datei nicht gefunden:\n{src}")
        target_dir = self.root / sub
        target_dir.mkdir(parents=True, exist_ok=True)
        # Liegt die Datei bereits im Projekt?
        try:
            src.relative_to(self.root)
            return self.rel(src)
        except ValueError:
            pass
        candidate = target_dir / src.name
        if candidate.exists():
            try:
                if candidate.stat().st_size == src.stat().st_size and file_digest(candidate) == file_digest(src):
                    return self.rel(candidate)
            except OSError:
                pass
            # gleicher Name, anderer Inhalt -> eindeutigen Namen suchen (oder Duplikat finden)
            n = 2
            while True:
                candidate = target_dir / f"{src.stem} ({n}){src.suffix}"
                if not candidate.exists():
                    break
                try:
                    if candidate.stat().st_size == src.stat().st_size and file_digest(candidate) == file_digest(src):
                        return self.rel(candidate)
                except OSError:
                    pass
                n += 1
        try:
            copy_file(src, candidate)
        except OSError as exc:
            raise ProjectError(f"Datei konnte nicht in das Projekt kopiert werden:\n{exc}") from exc
        return self.rel(candidate)

    def edited_target(self, stem: str, row: int, col: int, token: str) -> Path:
        name = safe_filename(f"{stem}_K{row + 1}-{col + 1}_{token}", fallback="bearbeitet") + ".flac"
        return self.root / EDITED_DIR / name

    def cover_target(self, stem: str, token: str, ext: str) -> Path:
        return self.root / COVER_DIR / (safe_filename(f"{stem}_{token}", fallback="cover") + ext)

    def remove_unreferenced(self, rel: str | None) -> None:
        """Löscht eine *bearbeitete* Fassung, wenn keine Kachel sie mehr nutzt."""
        if not rel or rel in self.data.referenced_files():
            return
        path = self.abs(rel)
        if path and path.exists() and (self.root / EDITED_DIR) in path.parents:
            try:
                path.unlink()
            except OSError:
                pass

    # ------------------------------------------------------------------
    # Zwischenstand "Bearbeiten & Schneiden" (Absturzsicherung)
    # ------------------------------------------------------------------
    @property
    def edit_session_file(self) -> Path:
        return self.autosave_dir / EDIT_SESSION_FILE

    def write_edit_session(self, state: dict[str, Any]) -> None:
        try:
            atomic_write_json(self.edit_session_file, state)
        except OSError as exc:
            log.warning("Zwischenstand konnte nicht gespeichert werden: %s", exc)

    def read_edit_session(self) -> dict[str, Any] | None:
        try:
            if self.edit_session_file.exists():
                return read_json(self.edit_session_file)
        except Exception as exc:
            log.warning("Zwischenstand unlesbar: %s", exc)
        return None

    def clear_edit_session(self) -> None:
        try:
            self.edit_session_file.unlink()
        except FileNotFoundError:
            pass
        except OSError as exc:
            log.warning("Zwischenstand konnte nicht gelöscht werden: %s", exc)


_NO_COMPRESS = frozenset({".mp3", ".m4a", ".aac", ".ogg", ".opus", ".flac", ".jpg", ".jpeg", ".png", ".wma", ".mp4"})
