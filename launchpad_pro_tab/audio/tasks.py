"""Rechenintensive Aufgaben, die in Worker-Prozessen (mehrere CPU-Kerne) laufen.

Die Funktionen nehmen und liefern nur einfache Datentypen (Pfade, dicts), damit sie
problemlos zwischen Prozessen übertragen werden können. Große Audiodaten werden nie über
Prozessgrenzen kopiert, sondern im PCM-Cache abgelegt und per memmap geöffnet.
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np

from ..core.constants import RENDER_FADE_MS
from ..core.models import EditParams
from . import cache
from .decoder import probe
from .dsp import apply_edge_fades, soft_limit
from .timestretch import stretch


def worker_init() -> None:
    """Start jedes Worker-Prozesses: beendet ihn, sobald das Hauptprogramm endet.

    Auch wenn das Hauptprogramm abstürzt oder hart beendet wird – sonst blieben verwaiste
    Worker zurück, die Programmdateien sperren (Update/Deinstallation schlagen dann fehl).
    """
    import multiprocessing
    import threading

    parent = multiprocessing.parent_process()
    if parent is None:
        return

    def watch() -> None:
        parent.join()
        os._exit(0)

    threading.Thread(target=watch, name="lptab-elternwaechter", daemon=True).start()


def ping() -> int:
    """Startet einen Worker vorab (Import von soundfile/av/soxr), ohne Qt zu laden.

    Dadurch ist die erste echte Dekodierung nicht durch Bibliotheks-Importe verzögert.
    """
    for module in ("soundfile", "av", "soxr"):
        try:
            __import__(module)
        except Exception:  # fehlt ein Backend, meldet es sich später beim Dekodieren
            pass
    return os.getpid()


def prepare(src: str, cache_dir: str, samplerate: int) -> dict:
    """Stellt sicher, dass ``src`` dekodiert im Cache liegt. Liefert den Cache-Eintrag."""
    entry = cache.ensure(Path(cache_dir), Path(src), int(samplerate))
    return entry.to_dict()


def probe_file(src: str) -> dict:
    info = probe(src)
    return {"duration": info.duration, "samplerate": info.samplerate, "channels": info.channels, "codec": info.codec}


def render_edit(src: str, cache_dir: str, samplerate: int, params: dict, out_path: str) -> dict:
    """Rendert Schnitt + Tempo + Lautstärke der Originaldatei als FLAC (24 bit).

    Es wird exakt derselbe Algorithmus wie in der Vorschau verwendet (WYSIWYG).
    """
    import soundfile as sf

    sr = int(samplerate)
    entry = cache.ensure(Path(cache_dir), Path(src), sr)
    pcm = cache.open_pcm(entry)
    p = (EditParams.from_dict(params) or EditParams()).normalized(entry.duration)
    f0 = int(round(p.start * sr))
    f1 = int(round((p.end if p.end is not None else entry.duration) * sr))
    data = stretch(pcm, sr, f0, f1, p.speed)
    del pcm
    if abs(p.gain - 1.0) > 1e-6:
        data *= np.float32(p.gain)
    limited = soft_limit(data, sr)
    apply_edge_fades(data, sr, RENDER_FADE_MS)

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.stem + ".tmp.flac")
    sf.write(str(tmp), data, sr, format="FLAC", subtype="PCM_24")
    os.replace(tmp, out)
    out_entry = cache.ensure(Path(cache_dir), out, sr)
    return {"cache": out_entry.to_dict(), "duration": out_entry.duration, "limited": bool(limited)}
