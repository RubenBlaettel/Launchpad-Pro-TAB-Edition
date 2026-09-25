"""Dekodiert (fast) beliebige Audioformate in float32-Stereo-PCM.

Strategie (Schnittstelle ``decode``/``probe``):

1. libsndfile (``soundfile``) für WAV, FLAC, OGG/Vorbis, AIFF, … – sehr schnell.
2. FFmpeg (``PyAV``) für MP3, AAC/M4A, WMA, Opus, ALAC, AC3, Video-Container, …
3. Fällt ein Backend aus, wird automatisch das jeweils andere versucht.

Resampling erfolgt einheitlich in hoher Qualität mit ``soxr``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from ..core.constants import FFMPEG_EXTENSIONS, SNDFILE_EXTENSIONS

log = logging.getLogger(__name__)


class DecodeError(Exception):
    pass


@dataclass
class AudioInfo:
    duration: float
    samplerate: int
    channels: int
    codec: str


# ---------------------------------------------------------------------------
# Kanal-/Samplerate-Anpassung
# ---------------------------------------------------------------------------
def to_stereo(data: np.ndarray) -> np.ndarray:
    """(frames, ch) -> (frames, 2) float32."""
    if data.ndim == 1:
        data = data[:, None]
    ch = data.shape[1]
    if ch == 2:
        out = data
    elif ch == 1:
        out = np.repeat(data, 2, axis=1)
    elif ch >= 6:
        # 5.1 (L R C LFE Ls Rs) nach ITU-R BS.775 heruntermischen
        c = data[:, 2] * 0.7071
        left = data[:, 0] + c + data[:, 4] * 0.7071
        right = data[:, 1] + c + data[:, 5] * 0.7071
        out = np.stack([left, right], axis=1) / 2.4142
    else:
        left = data[:, 0::2].mean(axis=1)
        right = data[:, 1::2].mean(axis=1)
        out = np.stack([left, right], axis=1)
    return np.ascontiguousarray(out, dtype=np.float32)


def resample(data: np.ndarray, sr_in: int, sr_out: int) -> np.ndarray:
    if sr_in == sr_out or data.shape[0] == 0:
        return np.ascontiguousarray(data, dtype=np.float32)
    import soxr

    out = soxr.resample(data, sr_in, sr_out, quality="HQ")
    return np.ascontiguousarray(out, dtype=np.float32)


# ---------------------------------------------------------------------------
# Backends
# ---------------------------------------------------------------------------
def _decode_sndfile(path: Path) -> tuple[np.ndarray, int]:
    import soundfile as sf

    data, sr = sf.read(str(path), dtype="float32", always_2d=True)
    return data, int(sr)


def _decode_ffmpeg(path: Path) -> tuple[np.ndarray, int]:
    import av

    try:
        container = av.open(str(path), metadata_errors="ignore")
    except Exception as exc:  # av.error.* erben von Exception
        raise DecodeError(str(exc)) from exc
    with container:
        streams = [s for s in container.streams if s.type == "audio"]
        if not streams:
            raise DecodeError("Die Datei enthält keine Audiospur.")
        stream = streams[0]
        stream.thread_type = "AUTO"
        sr = int(stream.rate or stream.codec_context.sample_rate or 0)
        resampler = None
        chunks: list[np.ndarray] = []
        for frame in container.decode(stream):
            if resampler is None:
                sr = int(frame.sample_rate or sr or 48000)
                # Packed float32 Stereo; FFmpeg übernimmt das korrekte Downmixing
                resampler = av.AudioResampler(format="flt", layout="stereo", rate=sr)
            for out in resampler.resample(frame):
                chunks.append(out.to_ndarray().reshape(-1, 2))
        if resampler is not None:
            for out in resampler.resample(None):
                chunks.append(out.to_ndarray().reshape(-1, 2))
    if not chunks:
        raise DecodeError("Die Audiospur ist leer.")
    return np.concatenate(chunks, axis=0), sr


def decode(path: Path | str, target_sr: int | None = None) -> tuple[np.ndarray, int]:
    """Liefert ``(pcm, samplerate)`` mit ``pcm`` als float32-Array der Form (frames, 2)."""
    path = Path(path)
    if not path.is_file():
        raise DecodeError(f"Datei nicht gefunden: {path}")
    ext = path.suffix.lower()
    order = (_decode_sndfile, _decode_ffmpeg) if ext in SNDFILE_EXTENSIONS else (_decode_ffmpeg, _decode_sndfile)
    if ext not in SNDFILE_EXTENSIONS and ext not in FFMPEG_EXTENSIONS:
        order = (_decode_ffmpeg, _decode_sndfile)
    errors: list[str] = []
    for backend in order:
        try:
            data, sr = backend(path)
            break
        except Exception as exc:
            errors.append(f"{backend.__name__}: {exc}")
    else:
        raise DecodeError("Format wird nicht unterstützt oder Datei ist beschädigt.\n" + "\n".join(errors))
    data = to_stereo(data)
    if target_sr and sr != target_sr:
        data = resample(data, sr, target_sr)
        sr = target_sr
    return data, sr


def probe(path: Path | str) -> AudioInfo:
    """Schnelle Metadaten-Abfrage (ohne komplett zu dekodieren)."""
    path = Path(path)
    ext = path.suffix.lower()
    if ext in SNDFILE_EXTENSIONS:
        try:
            import soundfile as sf

            info = sf.info(str(path))
            return AudioInfo(float(info.duration), int(info.samplerate), int(info.channels), info.format)
        except Exception:
            pass
    try:
        import av

        with av.open(str(path), metadata_errors="ignore") as container:
            stream = next(s for s in container.streams if s.type == "audio")
            if stream.duration is not None and stream.time_base is not None:
                duration = float(stream.duration * stream.time_base)
            elif container.duration is not None:
                duration = container.duration / 1_000_000.0
            else:
                duration = 0.0
            return AudioInfo(duration, int(stream.rate or 0), int(stream.channels or 2), stream.codec_context.name)
    except StopIteration as exc:
        raise DecodeError("Die Datei enthält keine Audiospur.") from exc
    except Exception as exc:
        raise DecodeError(str(exc)) from exc
