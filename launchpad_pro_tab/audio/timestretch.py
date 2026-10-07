"""Tonhöhenerhaltendes Time-Stretching (Phase-Vocoder) – streamingfähig.

Bis v1.1 arbeitete hier WSOLA (Zeitbereich, 40-ms-Fenster). Das klang bei Musik rau und
„verzerrt“: Alle 20 ms wird überblendet, und bei mehreren gleichzeitigen Tönen passt keine
Schnittstelle für alle – Lautstärke und Phase schwanken mit ~50 Hz. Der Phase-Vocoder schiebt
stattdessen die Phase jeder Frequenz einzeln weiter (Messwerte siehe CLAUDE.md):

* Hann-Fenster ≈ 85 ms, 75 % Überlappung. Der Phasenfortschritt je Frequenz stammt aus einem
  zweiten Spektrum genau einen Synthese-Hop früher im Eingang – eindeutig auch bei 2×, ohne
  Phase-Unwrapping.
* Identity Phase Locking (Laroche & Dolson 1999): Alle Frequenzen um eine Spektralspitze drehen
  mit der Spitze mit – Klangfarbe bleibt, wenig „Phasiness“.
* Stereo: Beide Kanäle erhalten dieselbe Phasendrehung (Bezug: betragsgewichtete Summe), damit
  bleiben Stereobild und Mono-Kompatibilität erhalten.
* Transienten (Schläge, Konsonanten, Einsätze): Phasen zurück auf das Original und einige Fenster
  lang Tempo 1 – die Zeit wird danach ausgeglichen. So gibt es kein Vorecho und keine doppelten
  Schläge. Setzt etwas nur in einem Kanal ein, werden nur die ansteigenden Frequenzen
  zurückgesetzt, damit Töne im anderen Kanal ungestört weiterklingen.

Derselbe ``TimeStretcher`` wird für die Echtzeit-Vorschau (im Audio-Callback, Tempo jederzeit
änderbar) und für das finale Rendern verwendet – was man hört, wird gespeichert.
Bei Tempo 1,0 gibt er das Signal unverändert aus.
"""

from __future__ import annotations

import math
from collections import deque

import numpy as np

TWO_PI = 2.0 * np.pi


class TimeStretcher:
    WINDOW_MS = 70.0     # aufgerundet auf eine Zweierpotenz: 44,1/48 kHz -> 4096 Samples (≈ 85 ms)
    OVERLAP = 4          # Synthese-Hop = Fensterlänge / 4
    # Energieanstieg einer Frequenz je Hop, der als Einsatz zählt: +5 dB. Bei +3 dB erreicht schon
    # Rauschen (Gewitter, Ausklang von MP3s) zufällig ~1/3 der Frequenzen und löst Fehlalarme aus.
    ONSET_RISE = 3.16
    ONSET_SHARE = 0.35   # Anteil ansteigender Frequenzen, ab dem ein Fenster eine Transiente ist
    REPAY = 0.25         # Anteil der Zeitschuld, der je Fenster nach einer Transiente ausgeglichen wird

    def __init__(self, source: np.ndarray, samplerate: int, start: int = 0, end: int | None = None):
        if source.ndim != 2 or source.shape[1] != 2:
            raise ValueError("source muss die Form (frames, 2) haben")
        self.src = source
        self.samplerate = int(samplerate)
        self.scale = 1.0 / 32768.0 if source.dtype == np.int16 else 1.0
        self.total = int(source.shape[0])
        self.N = 1 << max(8, math.ceil(math.log2(self.samplerate * self.WINDOW_MS / 1000.0)))
        self.Hs = self.N // self.OVERLAP
        k = np.arange(self.N, dtype=np.float64)
        w = 0.5 - 0.5 * np.cos(2.0 * np.pi * k / self.N)
        self.win = w[:, None]
        self.win_out = (w * (self.Hs / np.sum(w * w)))[:, None]  # Hann² überlappt sich zu 1,5
        self.bins = np.arange(self.N // 2 + 1)
        self._no_shift = np.zeros(self.bins.shape[0])
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
        self._seek_pos = pos
        self._frames = 0                   # Analysefenster seit dem Springen
        self._u = float(pos)               # Mitte des aktuellen Analysefensters (Eingangsframe)
        self._centers: deque[float] = deque(maxlen=3)
        self._phase: np.ndarray | None = None   # Synthesephase des letzten Fensters je Frequenz
        self._prev_spec: np.ndarray | None = None
        self._prev_mag: np.ndarray | None = None
        self._prev_p = 0
        self._last_score = 0.0
        self._debt = 0.0                   # Eingangsframes, die wir dem Soll voraus (>0) bzw. hinterher sind
        self._lock = self.OVERLAP - 2      # verbleibende Fenster mit Tempo 1 (Vorlauf, siehe _advance)
        self._ola = np.zeros((self.N, 2), dtype=np.float64)
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
        out = np.zeros((length, 2), dtype=np.float64)
        lo = max(p, self.start)
        hi = min(p + length, self.end)
        if hi > lo:
            seg = out[lo - p: hi - p]
            seg[:] = self.src[lo:hi]
            if self.scale != 1.0:
                seg *= self.scale
        return out

    def _advance(self, speed: float) -> None:
        """Nächste Analyseposition: Soll-Schritt, nach Transienten Tempo 1 und danach Ausgleich."""
        ideal = self.Hs * speed
        if self._frames < 2:
            # Vorlauf mit Tempo 1: Fenster 1 liegt auf ``_seek_pos`` = erstes ausgegebenes Sample
            # (siehe _emit). Bis zum ersten Ausgabeabschnitt laufen alle Fenster mit Tempo 1 –
            # der Anfang kommt dadurch exakt wie im Original, die Zeit wird danach ausgeglichen.
            self._u = float(self._seek_pos - self.Hs * (1 - self._frames))
            return
        if self._lock > 0:
            self._lock -= 1
            step = float(self.Hs)
        else:
            step = min(max(ideal - self.REPAY * self._debt, 0.5 * ideal), 2.0 * ideal)
        self._debt += step - ideal
        if self._lock == 0 and abs(self._debt) < 1.0:
            self._debt = 0.0  # Rest verwerfen, damit Tempo 1,0 wieder exakt im Hop-Raster läuft
        self._u += step

    def _onset(self, power: np.ndarray, prev_power: np.ndarray, speed: float) -> np.ndarray | bool:
        """Transienten-Erkennung. Liefert False, True (alle Frequenzen zurücksetzen) oder eine
        Maske der ansteigenden Frequenzen (Einsatz nur in einem Kanal)."""
        energy = power[:, 0] + power[:, 1]
        prev_energy = prev_power[:, 0] + prev_power[:, 1]
        rising = self._rising(energy, prev_energy)
        score = float(np.count_nonzero(rising)) / max(1, np.count_nonzero(energy > self._floor(energy)))
        onset = score > self.ONSET_SHARE and score > self._last_score
        self._last_score = score
        if not onset:
            return False
        if abs(speed - 1.0) > 1e-6 and self._lock == 0 and abs(self._debt) < self.N:
            self._lock = self.OVERLAP - 1
        # Nur Kanäle mit nennenswertem Anteil stimmen ab (ein stummer Kanal zählt nicht)
        total = float(energy.sum())
        for c in (0, 1):
            pc = power[:, c]
            if pc.sum() < 0.01 * total:
                continue
            share = np.count_nonzero(self._rising(pc, prev_power[:, c]))
            if share <= self.ONSET_SHARE * np.count_nonzero(pc > self._floor(pc)):
                return rising
        return True

    def _floor(self, energy: np.ndarray) -> float:
        return float(energy.max()) * 1e-7 + 1e-18

    def _rising(self, energy: np.ndarray, prev_energy: np.ndarray) -> np.ndarray:
        return (energy > self._floor(energy)) & (energy > self.ONSET_RISE * prev_energy)

    def _phase_shift(self, block: np.ndarray, p: int, spec: np.ndarray, power: np.ndarray,
                     speed: float) -> np.ndarray:
        """Phasendrehung je Frequenz gegenüber der Analyse (0 = Original)."""
        if self._phase is None:
            return self._no_shift
        if p - self._prev_p == self.Hs:
            prev = self._prev_spec  # Tempo 1: Das Vorgängerfenster liegt genau einen Hop zurück
        else:
            prev = np.fft.rfft(block[: self.N] * self.win, axis=0)
        # Bezug wie im letzten Fenster gewichtet -> Differenz ist ein reiner Zeitversatz
        prev_phase = np.angle((prev * self._prev_mag).sum(axis=1))
        # Der harte Schnitt am Ende des Bereichs ist kein Einsatz (dahinter gibt es nichts zu dehnen)
        onset = self._onset(power, prev.real ** 2 + prev.imag ** 2, speed) if p + self.N <= self.end else False
        if onset is True:
            return self._no_shift
        energy = power[:, 0] + power[:, 1]
        peaks = np.flatnonzero((energy[1:-1] > energy[:-2]) & (energy[1:-1] >= energy[2:])) + 1
        if peaks.size:
            bounds = (peaks[:-1] + peaks[1:] + 1) // 2
            owner = peaks[np.searchsorted(bounds, self.bins, side="right")]
        else:
            owner = self.bins
        shift = (self._phase - prev_phase)[owner]
        if onset is not False:
            shift = np.where(onset[owner], 0.0, shift)
        return shift

    def _process_frame(self) -> None:
        N, Hs = self.N, self.Hs
        speed = float(self.speed)
        self._advance(speed)
        u = self._u
        p = int(round(u)) - N // 2
        block = self._get(p - Hs, N + Hs)
        spec = np.fft.rfft(block[Hs:] * self.win, axis=0)
        mag = np.abs(spec)
        power = mag * mag
        shift = self._phase_shift(block, p, spec, power, speed)
        frame = np.fft.irfft(spec * np.exp(1j * shift)[:, None], N, axis=0)
        self._phase = np.mod(np.angle((spec * mag).sum(axis=1)) + shift, TWO_PI)
        self._prev_spec, self._prev_mag, self._prev_p = spec, mag, p
        self._ola += frame * self.win_out
        out = self._ola[:Hs].copy()
        self._ola[:-Hs] = self._ola[Hs:]
        self._ola[-Hs:] = 0.0
        self._centers.append(u)
        self._frames += 1
        if self._frames >= 4:
            self._emit(out)

    def _emit(self, out: np.ndarray) -> None:
        # Fertig überlappt ist jetzt der Abschnitt ab der Mitte des Fensters von vor zwei Schritten
        # (Fensterlänge = 4 Hops) – bei Tempo 1 also genau der Eingang ab dessen Mitte.
        a0 = self._centers[0]
        spd = (self._centers[1] - self._centers[0]) / self.Hs
        if a0 >= self.end:
            self._done = True
            return
        if a0 + self.Hs * spd > self.end:
            out = out[: max(0, min(self.Hs, math.ceil((self.end - a0) / spd)))]
            self._done = True
        if out.shape[0]:
            self._queue.append([out.astype(np.float32), a0, spd, 0])
            self._queued += out.shape[0]

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
            self._position = float(self.end) if self._done else min(self._u, float(self.end))
        return out, filled


def stretch(pcm: np.ndarray, samplerate: int, start: int, end: int, speed: float, block: int = 16384) -> np.ndarray:
    """Offline-Variante: liefert den Bereich [start, end) mit Tempo ``speed`` als float32.

    Die Länge ist ≈ (end - start) / speed; nach einer Transiente kurz vor dem Ende kann sie um
    einige Millisekunden abweichen (der Zeitausgleich hat dann keinen Platz mehr).
    """
    start = max(0, int(start))
    end = min(pcm.shape[0], int(end))
    scale = np.float32(1.0 / 32768.0) if pcm.dtype == np.int16 else np.float32(1.0)
    if end <= start:
        return np.zeros((0, 2), dtype=np.float32)
    if abs(speed - 1.0) < 1e-6:
        return np.asarray(pcm[start:end], dtype=np.float32) * scale
    st = TimeStretcher(pcm, samplerate, start, end)
    st.speed = float(speed)
    out = np.zeros((int((end - start) / float(speed) + 2 * st.N / float(speed)) + block, 2), dtype=np.float32)
    pos = 0
    while not st.finished:
        n = min(block, out.shape[0] - pos)
        if n <= 0:
            break
        chunk, filled = st.read(n)
        out[pos: pos + filled] = chunk[:filled]
        pos += filled
        if filled < n:
            break
    return out[:pos]
