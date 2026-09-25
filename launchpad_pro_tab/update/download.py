"""Update-Paket herunterladen und prüfen (Größe + SHA-256)."""

from __future__ import annotations

import hashlib
import os
import threading
import time
from pathlib import Path
from typing import Callable

from .net import NetworkError, open_url

CHUNK = 256 * 1024
Progress = Callable[[int, int], None]     # (geladen, gesamt)


class DownloadCancelled(Exception):
    pass


class ChecksumError(NetworkError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def download(url: str, target: Path, *, sha256: str | None, size: int = 0,
             progress: Progress | None = None, cancel: threading.Event | None = None,
             timeout: float = 30.0) -> Path:
    """Lädt ``url`` nach ``target``. Ohne erwartete Prüfsumme wird nichts gespeichert.

    Die Datei entsteht zunächst als ``*.part`` und wird erst nach bestandener Prüfung
    umbenannt – ein abgebrochener oder manipulierter Download kann nie ausgeführt werden.
    """
    if not sha256:
        raise ChecksumError("Für dieses Update liegt keine Prüfsumme vor – automatische Installation abgelehnt.")
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    part = target.with_name(target.name + ".part")
    h = hashlib.sha256()
    done = 0
    try:
        with open_url(url, timeout=timeout) as resp, open(part, "wb") as out:
            total = int(resp.headers.get("Content-Length") or 0) or size
            last = 0.0
            while True:
                if cancel is not None and cancel.is_set():
                    raise DownloadCancelled()
                try:
                    block = resp.read(CHUNK)
                except OSError as exc:
                    raise NetworkError(f"Download abgebrochen: {exc}") from exc
                if not block:
                    break
                out.write(block)
                h.update(block)
                done += len(block)
                now = time.monotonic()
                if progress is not None and now - last > 0.05:
                    last = now
                    progress(done, total)
            out.flush()
            os.fsync(out.fileno())
        if progress is not None:
            progress(done, total or done)
        if size and done != size:
            raise ChecksumError(f"Download unvollständig ({done} von {size} Bytes).")
        if h.hexdigest().lower() != sha256.lower():
            raise ChecksumError("Prüfsumme stimmt nicht – die Datei ist beschädigt oder manipuliert.")
        os.replace(part, target)
        return target
    except BaseException:
        try:
            part.unlink()
        except OSError:
            pass
        raise
