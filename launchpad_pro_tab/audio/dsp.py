"""Vektorisierte DSP-Helfer (numpy): Wellenform-Peaks, Blenden, Limiter, Pegel."""

from __future__ import annotations

import math

import numpy as np

PEAK_BUCKET = 256  # Frames pro Peak-Bucket (≈5 ms bei 48 kHz)


def db_to_gain(db: float) -> float:
    return 10.0 ** (db / 20.0)


def gain_to_db(gain: float) -> float:
    return -math.inf if gain <= 0 else 20.0 * math.log10(gain)


def compute_peaks(pcm: np.ndarray, bucket: int = PEAK_BUCKET, chunk_buckets: int = 8192) -> np.ndarray:
    """Min/Max/RMS je Bucket der Mitte (L+R)/2 → Array (buckets, 3) float16.

    Arbeitet blockweise, damit auch sehr lange Dateien (memmap) wenig RAM brauchen.
    """
    frames = pcm.shape[0]
    n_buckets = (frames + bucket - 1) // bucket
    out = np.zeros((n_buckets, 3), dtype=np.float32)
    scale = 1.0 / 32768.0 if pcm.dtype == np.int16 else 1.0
    step = bucket * chunk_buckets
    for b0 in range(0, n_buckets, chunk_buckets):
        f0 = b0 * bucket
        f1 = min(frames, f0 + step)
        block = np.asarray(pcm[f0:f1], dtype=np.float32)
        mid = (block[:, 0] + block[:, 1]) * (0.5 * scale)
        nb = (mid.shape[0] + bucket - 1) // bucket
        pad = nb * bucket - mid.shape[0]
        if pad:
            mid = np.concatenate([mid, np.zeros(pad, dtype=np.float32)])
        m = mid.reshape(nb, bucket)
        out[b0:b0 + nb, 0] = m.min(axis=1)
        out[b0:b0 + nb, 1] = m.max(axis=1)
        out[b0:b0 + nb, 2] = np.sqrt(np.mean(m * m, axis=1))
    return out.astype(np.float16)


def aggregate_peaks(peaks: np.ndarray, b0: float, b1: float, columns: int) -> np.ndarray:
    """Fasst Buckets [b0, b1) auf ``columns`` Bildschirmspalten zusammen → (columns, 3)."""
    n = peaks.shape[0]
    columns = max(1, int(columns))
    out = np.zeros((columns, 3), dtype=np.float32)
    if n == 0 or b1 <= b0:
        return out
    edges = np.linspace(b0, b1, columns + 1)
    starts = np.clip(np.floor(edges[:-1]).astype(np.int64), 0, n - 1)
    end = int(np.clip(np.ceil(edges[-1]), starts[-1] + 1, n))
    valid = (edges[:-1] < n) & (edges[1:] > 0)
    s0 = int(starts[0])
    sub = peaks[s0:end].astype(np.float32)
    rel = starts - s0
    # reduceat: Spalte i umfasst sub[rel[i]:rel[i+1]] (letzte Spalte bis ``end``);
    # bei starkem Zoom (mehrere Spalten je Bucket) liefert es den Bucket selbst.
    out[:, 0] = np.where(valid, np.minimum.reduceat(sub[:, 0], rel), 0.0)
    out[:, 1] = np.where(valid, np.maximum.reduceat(sub[:, 1], rel), 0.0)
    out[:, 2] = np.where(valid, np.maximum.reduceat(sub[:, 2], rel), 0.0)
    return out


def columns_from_pcm(pcm: np.ndarray, f0: int, f1: int, columns: int) -> np.ndarray:
    """Wie ``aggregate_peaks``, aber direkt aus PCM (für sehr starken Zoom)."""
    columns = max(1, int(columns))
    out = np.zeros((columns, 3), dtype=np.float32)
    frames = pcm.shape[0]
    f0 = max(0, int(f0))
    f1 = min(frames, int(f1))
    if f1 <= f0:
        return out
    scale = 1.0 / 32768.0 if pcm.dtype == np.int16 else 1.0
    block = np.asarray(pcm[f0:f1], dtype=np.float32)
    mid = (block[:, 0] + block[:, 1]) * (0.5 * scale)
    edges = np.linspace(0, mid.shape[0], columns + 1).astype(np.int64)
    starts = np.minimum(edges[:-1], mid.shape[0] - 1)
    out[:, 0] = np.minimum.reduceat(mid, starts)
    out[:, 1] = np.maximum.reduceat(mid, starts)
    out[:, 2] = np.sqrt(np.maximum.reduceat(mid * mid, starts))
    return out


def apply_edge_fades(data: np.ndarray, samplerate: int, fade_ms: float) -> None:
    """Kurze Ein-/Ausblendung an den Schnittkanten (in-place) gegen Knackser."""
    n = min(data.shape[0] // 2, int(samplerate * fade_ms / 1000.0))
    if n <= 1:
        return
    ramp = (0.5 - 0.5 * np.cos(np.linspace(0.0, np.pi, n, dtype=np.float32)))[:, None]
    data[:n] *= ramp
    data[-n:] *= ramp[::-1]


def soft_limit(data: np.ndarray, samplerate: int, ceiling: float = 0.97, release_ms: float = 120.0) -> bool:
    """Look-ahead-freier Spitzenbegrenzer für das Offline-Rendering (in-place).

    Liefert ``True``, wenn der Limiter eingegriffen hat. Arbeitet blockweise mit
    geglätteter Gain-Reduktion, danach harte Sicherheitsbegrenzung.
    """
    frames = data.shape[0]
    if frames == 0:
        return False
    peak = float(np.max(np.abs(data)))
    if peak <= ceiling:
        return False
    block = max(64, int(samplerate * 0.002))
    n_blocks = (frames + block - 1) // block
    pad = n_blocks * block - frames
    absmax = np.max(np.abs(data), axis=1)
    if pad:
        absmax = np.concatenate([absmax, np.zeros(pad, dtype=absmax.dtype)])
    block_peaks = absmax.reshape(n_blocks, block).max(axis=1)
    # Ziel-Gain je Block; Look-ahead von einem Block (sofortiger Angriff im Vorblock)
    target = np.minimum(1.0, ceiling / np.maximum(block_peaks, 1e-9))
    target = np.minimum(target, np.concatenate([target[1:], [1.0]]))
    rel = math.exp(-block / (samplerate * release_ms / 1000.0))
    gains = np.empty(n_blocks, dtype=np.float32)
    g = 1.0
    for i, t in enumerate(target):
        g = t if t < g else t + (g - t) * rel
        gains[i] = g
    # Blockgrenzen linear interpolieren
    centers = (np.arange(n_blocks) + 0.5) * block
    env = np.interp(np.arange(frames), centers, gains).astype(np.float32)
    data *= env[:, None]
    np.clip(data, -ceiling, ceiling, out=data)
    return True


def float_to_int16(data: np.ndarray) -> np.ndarray:
    return (np.clip(data, -1.0, 1.0) * 32767.0).astype(np.int16)
