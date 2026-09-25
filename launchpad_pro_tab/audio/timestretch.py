"""Tonhöhenerhaltendes Time-Stretching (WSOLA) – streamingfähig.

WSOLA (Waveform Similarity Overlap-Add, Verhelst & Roelands 1993) schneidet das Signal
in überlappende Fenster und sucht für jedes Fenster innerhalb einer kleinen Toleranz die
Position, die am besten an das vorherige Fenster anschließt (normierte Kreuzkorrelation per
FFT). Dadurch ändert sich das Tempo, die Tonhöhe bleibt erhalten.

Derselbe ``WsolaStretcher`` wird für die Echtzeit-Vorschau (im Audio-Callback, Tempo
jederzeit änderbar) und für das finale Rendern verwendet – was man hört, wird gespeichert.
Bei Tempo 1,0 arbeitet er bit-genau (reine Überlappung ohne Verschiebung).
"""

from __future__ import annotations

from collections import deque

import numpy as np


class WsolaStretcher:
    def __init__(
        self,
        source: np.ndarray,
        samplerate: int,
        start: int = 0,
        end: int | None = None,
        frame_ms: float = 40.0,
        tolerance_ms: float = 10.0,
    ):
        if source.ndim != 2 or source.shape[1] != 2:
            raise ValueError("source muss die Form (frames, 2) haben")
        self.src = source
        self.samplerate = int(samplerate)
        self.scale = np.float32(1.0 / 32768.0) if source.dtype == np.int16 else np.float32(1.0)
        self.total = int(source.shape[0])
        n = int(round(samplerate * frame_ms / 1000.0))
        self.N = max(64, n + (n & 1))
        self.Hs = self.N // 2
        self.tol = max(16, int(round(samplerate * tolerance_ms / 1000.0)))
        k = np.arange(self.N, dtype=np.float64)
        self.win = (0.5 - 0.5 * np.cos(2.0 * np.pi * k / self.N)).astype(np.float32)[:, None]
        self.win_first = self.win.copy()
        self.win_first[: self.Hs] = 1.0  # erstes Fenster ohne Einblendung
        self.fft_len = 1 << int(self.N + 2 * self.tol - 1).bit_length()
        self.speed = 1.0
        self.start = 0
        self.end = self.total
        self.set_region(start, end)
        self.seek(self.start)

    # ------------------------------------------------------------------
    def set_region(self, start: int, end: int | None) -> None:
        end = self.total if end is None else int(end)
        self.start = int(min(max(0, start), self.total))
        self.end = int(min(max(self.start, end), self.total))

    def seek(self, pos: int) -> None:
        pos = int(min(max(self.start, pos), self.end))
        self._a = float(pos)            # nominelle Analyseposition des nächsten Fensters
        self._prev: int | None = None   # tatsächliche Position des vorherigen Fensters
        self._ola = np.zeros((self.N, 2), dtype=np.float32)
        self._queue: deque[list] = deque()  # [daten, a_start, tempo, offset]
        self._queued = 0
        self._done = pos >= self.end
        self._position = float(pos)

    @property
    def position(self) -> float:
        """Eingangsposition (Frame) des nächsten auszugebenden Samples."""
        return self._position

    @property
    def finished(self) -> bool:
        return self._done and self._queued == 0

    # ------------------------------------------------------------------
    def _get(self, p: int, length: int) -> np.ndarray:
        out = np.zeros((length, 2), dtype=np.float32)
        lo = max(p, self.start)
        hi = min(p + length, self.end)
        if hi > lo:
            np.multiply(self.src[lo:hi], self.scale, out=out[lo - p: hi - p], casting="unsafe")
        return out

    def _mono(self, p: int, length: int) -> np.ndarray:
        x = self._get(p, length)
        return x[:, 0] + x[:, 1]

    def _best_offset(self, template: np.ndarray, region: np.ndarray, nlags: int) -> int:
        L = self.fft_len
        corr = np.fft.irfft(np.fft.rfft(region, L) * np.conj(np.fft.rfft(template, L)), L)[:nlags]
        sq = region.astype(np.float64) ** 2
        cs = np.empty(sq.shape[0] + 1, dtype=np.float64)
        cs[0] = 0.0
        np.cumsum(sq, out=cs[1:])
        energy = cs[self.N: self.N + nlags] - cs[:nlags]
        score = corr / np.sqrt(np.maximum(energy, 1e-9))
        return int(np.argmax(score))

    def _process_frame(self) -> None:
        N, Hs = self.N, self.Hs
        speed = self.speed
        if self._prev is None:
            p = int(round(self._a))
            win = self.win_first
        elif abs(speed - 1.0) < 1e-6:
            # Tempo 1,0: natürliche Fortsetzung -> exakte Rekonstruktion
            p = self._prev + Hs
            self._a = float(p)
            win = self.win
        else:
            natural = self._prev + Hs
            template = self._mono(natural, N)
            center = int(round(self._a))
            lo = max(self.start, center - self.tol)
            hi = max(lo, min(center + self.tol, self.end - 1))
            nlags = hi - lo + 1
            if nlags > 1 and np.any(template):
                region = self._mono(lo, nlags - 1 + N)
                p = lo + self._best_offset(template, region, nlags)
            else:
                p = min(max(center, lo), hi)
            win = self.win
        frame = self._get(p, N)
        frame *= win
        self._ola += frame
        out = self._ola[:Hs].copy()
        self._ola[: N - Hs] = self._ola[Hs:]
        self._ola[N - Hs:] = 0.0
        self._queue.append([out, self._a, speed, 0])
        self._queued += Hs
        self._prev = p
        self._a += Hs * speed
        if self._a >= self.end:
            tail = self._ola[: N - Hs].copy()
            self._queue.append([tail, float(self.end), speed, 0])
            self._queued += tail.shape[0]
            self._ola[:] = 0.0
            self._done = True

    def read(self, n: int) -> tuple[np.ndarray, int]:
        """Erzeugt bis zu ``n`` Ausgabe-Frames → (Puffer (n, 2) float32, gefüllte Frames)."""
        while self._queued < n and not self._done:
            self._process_frame()
        out = np.zeros((n, 2), dtype=np.float32)
        filled = 0
        q = self._queue
        while filled < n and q:
            item = q[0]
            data, _a0, _spd, off = item
            take = min(n - filled, data.shape[0] - off)
            out[filled: filled + take] = data[off: off + take]
            filled += take
            off += take
            self._queued -= take
            if off >= data.shape[0]:
                q.popleft()
            else:
                item[3] = off
        if q:
            data, a0, spd, off = q[0]
            self._position = min(float(self.end), a0 + off * spd)
        else:
            self._position = float(self.end) if self._done else min(self._a, float(self.end))
        return out, filled


def stretch(pcm: np.ndarray, samplerate: int, start: int, end: int, speed: float, block: int = 16384) -> np.ndarray:
    """Offline-Variante: liefert den Bereich [start, end) mit Tempo ``speed`` als float32."""
    start = max(0, int(start))
    end = min(pcm.shape[0], int(end))
    scale = np.float32(1.0 / 32768.0) if pcm.dtype == np.int16 else np.float32(1.0)
    if end <= start:
        return np.zeros((0, 2), dtype=np.float32)
    if abs(speed - 1.0) < 1e-6:
        return np.asarray(pcm[start:end], dtype=np.float32) * scale
    st = WsolaStretcher(pcm, samplerate, start, end)
    st.speed = float(speed)
    expected = int(round((end - start) / float(speed)))
    out = np.zeros((expected, 2), dtype=np.float32)
    pos = 0
    while pos < expected:
        n = min(block, expected - pos)
        chunk, filled = st.read(n)
        out[pos: pos + filled] = chunk[:filled]
        pos += filled
        if filled < n:
            break
    return out
