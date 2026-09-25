"""Kleine, Qt-freie Hilfsfunktionen (Dateisystem, Formatierung)."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

_INVALID_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVED_WIN = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def safe_filename(name: str, fallback: str = "Projekt", max_len: int = 80) -> str:
    """Erzeugt einen unter Windows, macOS und Linux gültigen Datei-/Ordnernamen."""
    cleaned = _INVALID_CHARS.sub("_", name).strip().strip(".")
    cleaned = re.sub(r"\s+", " ", cleaned)
    if not cleaned:
        cleaned = fallback
    if cleaned.upper() in _RESERVED_WIN:
        cleaned = f"_{cleaned}"
    return cleaned[:max_len].rstrip(" .") or fallback


def unique_path(path: Path) -> Path:
    """Hängt " (2)", " (3)" … an, falls ``path`` bereits existiert."""
    if not path.exists():
        return path
    stem, suffix = path.stem, path.suffix
    if path.is_dir() or not suffix:
        stem, suffix = path.name, ""
    n = 2
    while True:
        candidate = path.with_name(f"{stem} ({n}){suffix}")
        if not candidate.exists():
            return candidate
        n += 1


def file_digest(path: Path, chunk: int = 1 << 20) -> str:
    """SHA-1 über den Dateiinhalt (zum Erkennen doppelter Importe)."""
    h = hashlib.sha1()
    with open(path, "rb") as fh:
        while True:
            block = fh.read(chunk)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def atomic_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    """Schreibt Text absturzsicher: erst in eine Temp-Datei, dann atomar ersetzen."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding=encoding, newline="\n") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        _replace_with_retry(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _replace_with_retry(src: str, dst: Path, attempts: int = 8) -> None:
    # Unter Windows kann ein Virenscanner/Indexer die Zieldatei kurz sperren.
    import time

    for i in range(attempts):
        try:
            os.replace(src, dst)
            return
        except PermissionError:
            if i == attempts - 1:
                raise
            time.sleep(0.05 * (i + 1))


def atomic_write_json(path: Path, data: Any) -> None:
    atomic_write_text(path, json.dumps(data, ensure_ascii=False, indent=2))


def read_json(path: Path) -> Any:
    # "utf-8-sig": auch Dateien mit BOM lesen (z. B. von Hand mit dem Windows-Editor bearbeitet)
    with open(path, "r", encoding="utf-8-sig") as fh:
        return json.load(fh)


def copy_file(src: Path, dst: Path) -> Path:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return dst


def format_time(seconds: float, with_tenths: bool = False) -> str:
    """0:07 / 3:25 / 1:02:03 – optional mit Zehntelsekunden (0:07,4)."""
    if seconds is None or seconds != seconds:  # NaN
        seconds = 0.0
    neg = seconds < 0
    seconds = abs(seconds)
    if with_tenths:
        tenths = int(round(seconds * 10))
        whole, t = divmod(tenths, 10)
    else:
        whole, t = int(round(seconds)), 0
    h, rem = divmod(whole, 3600)
    m, s = divmod(rem, 60)
    text = f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
    if with_tenths:
        text += f",{t}"
    return f"-{text}" if neg else text


def is_relative_to(path: Path, base: Path) -> bool:
    try:
        path.resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False
