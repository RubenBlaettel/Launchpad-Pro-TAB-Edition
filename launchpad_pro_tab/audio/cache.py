"""PCM-Cache: einmal dekodieren, danach blitzschnell per memmap laden.

Jede Audiodatei wird für die aktuelle Ausgabe-Samplerate genau einmal dekodiert und als
rohes int16-Stereo (``<key>.pcm``) plus Wellenform-Peaks (``<key>.peaks.npy``) im
``.cache``-Ordner des Projekts abgelegt. Beim erneuten Öffnen eines Projekts entfällt
damit jede Dekodierung; das Betriebssystem verwaltet den Speicher (memory mapping).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .decoder import decode
from .dsp import compute_peaks, float_to_int16

log = logging.getLogger(__name__)

CACHE_VERSION = 1
BYTES_PER_FRAME = 4  # int16 * 2 Kanäle


@dataclass(frozen=True)
class CacheEntry:
    key: str
    directory: str
    frames: int
    samplerate: int
    duration: float
    source: str

    @property
    def pcm_path(self) -> Path:
        return Path(self.directory) / f"{self.key}.pcm"

    @property
    def peaks_path(self) -> Path:
        return Path(self.directory) / f"{self.key}.peaks.npy"

    @property
    def meta_path(self) -> Path:
        return Path(self.directory) / f"{self.key}.json"

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "directory": self.directory,
            "frames": self.frames,
            "samplerate": self.samplerate,
            "duration": self.duration,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "CacheEntry":
        return cls(d["key"], d["directory"], int(d["frames"]), int(d["samplerate"]), float(d["duration"]), d["source"])


def cache_key(src: Path, samplerate: int) -> str:
    st = Path(src).stat()
    raw = f"{Path(src).name}|{st.st_size}|{st.st_mtime_ns}|{samplerate}|v{CACHE_VERSION}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:24]


def lookup(cache_dir: Path, src: Path, samplerate: int) -> CacheEntry | None:
    """Liefert einen gültigen Cache-Eintrag oder ``None`` (sehr schnell, nur stat/JSON)."""
    try:
        key = cache_key(src, samplerate)
    except OSError:
        return None
    meta = Path(cache_dir) / f"{key}.json"
    if not meta.exists():
        return None
    try:
        with open(meta, "r", encoding="utf-8") as fh:
            d = json.load(fh)
        entry = CacheEntry(key, str(cache_dir), int(d["frames"]), int(d["samplerate"]), float(d["duration"]), str(src))
        if entry.pcm_path.stat().st_size != entry.frames * BYTES_PER_FRAME or not entry.peaks_path.exists():
            return None
        return entry
    except (OSError, ValueError, KeyError):
        return None


def build(cache_dir: Path, src: Path, samplerate: int) -> CacheEntry:
    """Dekodiert ``src`` und schreibt PCM + Peaks + Metadaten (läuft im Worker-Prozess)."""
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    key = cache_key(src, samplerate)
    data, sr = decode(src, samplerate)
    peaks = compute_peaks(data)
    pcm = float_to_int16(data)
    entry = CacheEntry(key, str(cache_dir), int(pcm.shape[0]), int(sr), pcm.shape[0] / float(sr), str(src))

    tmp_pcm = entry.pcm_path.with_suffix(".pcm.tmp")
    pcm.tofile(tmp_pcm)
    _replace(tmp_pcm, entry.pcm_path)
    tmp_peaks = entry.peaks_path.with_name(entry.key + ".peaks.tmp.npy")
    np.save(tmp_peaks, peaks)
    _replace(tmp_peaks, entry.peaks_path)
    # Metadaten zuletzt schreiben – sie markieren den Eintrag als vollständig.
    tmp_meta = entry.meta_path.with_suffix(".json.tmp")
    with open(tmp_meta, "w", encoding="utf-8") as fh:
        json.dump({"frames": entry.frames, "samplerate": entry.samplerate, "duration": entry.duration,
                   "source": Path(src).name}, fh)
    _replace(tmp_meta, entry.meta_path)
    return entry


def ensure(cache_dir: Path, src: Path, samplerate: int) -> CacheEntry:
    return lookup(cache_dir, src, samplerate) or build(cache_dir, src, samplerate)


def open_pcm(entry: CacheEntry) -> np.ndarray:
    """Read-only memmap (frames, 2) int16 des Cache-Eintrags."""
    if entry.frames == 0:
        return np.zeros((0, 2), dtype=np.int16)
    return np.memmap(entry.pcm_path, dtype=np.int16, mode="r", shape=(entry.frames, 2))


def load_peaks(entry: CacheEntry) -> np.ndarray:
    return np.load(entry.peaks_path)


def warm(pcm: np.ndarray, start: int = 0, frames: int = 0) -> None:
    """Liest Seiten einer memmap vor (512 Frames = 2 KiB; eine Berührung je Seite genügt)."""
    if pcm.shape[0] == 0:
        return
    end = pcm.shape[0] if frames <= 0 else min(pcm.shape[0], start + frames)
    if end > start:
        np.asarray(pcm[start:end:512, 0]).sum()


def cleanup(cache_dir: Path, keep_keys: set[str]) -> int:
    """Löscht nicht mehr benötigte Cache-Dateien. Gibt die Anzahl gelöschter Dateien zurück."""
    removed = 0
    cache_dir = Path(cache_dir)
    if not cache_dir.is_dir():
        return 0
    for f in cache_dir.iterdir():
        key = f.name.split(".", 1)[0]
        if key in keep_keys:
            continue
        try:
            f.unlink()
            removed += 1
        except OSError:
            pass  # z. B. unter Windows noch gemappt – beim nächsten Mal
    return removed


def _replace(src: Path, dst: Path) -> None:
    try:
        os.replace(src, dst)
    except PermissionError:
        # Ziel ist (unter Windows) noch gemappt: Inhalt ist identisch, Temp verwerfen.
        try:
            os.unlink(src)
        except OSError:
            pass
