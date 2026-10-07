"""Tests für Dekodierung, PCM-Cache, DSP, Time-Stretch, Engine und Rendering."""

from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from conftest import SR, dominant_frequency, sine
from launchpad_pro_tab.audio import cache, dsp, tasks
from launchpad_pro_tab.audio.decoder import DecodeError, decode, probe
from launchpad_pro_tab.audio.engine import AudioEngine
from launchpad_pro_tab.audio.timestretch import TimeStretcher, stretch


# ---------------------------------------------------------------------------
# Dekodierung
# ---------------------------------------------------------------------------
def _encode_av(path: Path, data: np.ndarray, sr: int, codec: str, fmt: str) -> None:
    import av

    with av.open(str(path), "w", format=fmt) as container:
        stream = container.add_stream(codec, rate=sr, layout="stereo")
        frame_size = 1024
        for i in range(0, len(data), frame_size):
            chunk = np.ascontiguousarray(data[i:i + frame_size].T)
            if chunk.shape[1] < frame_size:
                chunk = np.pad(chunk, ((0, 0), (0, frame_size - chunk.shape[1])))
            frame = av.AudioFrame.from_ndarray(chunk, format="fltp", layout="stereo")
            frame.sample_rate = sr
            frame.pts = i
            for pkt in stream.encode(frame):
                container.mux(pkt)
        for pkt in stream.encode(None):
            container.mux(pkt)


@pytest.mark.parametrize("ext,kwargs", [
    (".wav", {}),
    (".flac", {}),
    (".ogg", {"format": "OGG", "subtype": "VORBIS"}),
    (".mp3", {"format": "MP3", "subtype": "MPEG_LAYER_III"}),
    (".aiff", {"format": "AIFF"}),
])
def test_decode_sndfile_formats(tmp_path, ext, kwargs):
    x = sine(440, 1.0, 44100)
    path = tmp_path / f"t{ext}"
    sf.write(path, x, 44100, **kwargs)
    data, sr = decode(path, SR)
    assert sr == SR and data.dtype == np.float32 and data.shape[1] == 2
    assert abs(data.shape[0] / SR - 1.0) < 0.08
    assert abs(dominant_frequency(data, SR) - 440) < 5
    assert abs(probe(path).duration - 1.0) < 0.08


@pytest.mark.parametrize("name,codec,fmt", [("t.m4a", "aac", "ipod"), ("t.opus", "libopus", "ogg")])
def test_decode_ffmpeg_formats(tmp_path, name, codec, fmt):
    sr = 48000
    x = sine(523.25, 1.0, sr)
    path = tmp_path / name
    try:
        _encode_av(path, x, sr, codec, fmt)
    except Exception as exc:  # Encoder in dieser FFmpeg-Build nicht vorhanden
        pytest.skip(f"Encoder {codec} nicht verfügbar: {exc}")
    data, out_sr = decode(path, SR)
    assert out_sr == SR and data.shape[1] == 2
    assert abs(data.shape[0] / SR - 1.0) < 0.1
    assert abs(dominant_frequency(data, SR) - 523.25) < 6


def test_decode_with_pyav_19_open_signature(tmp_path, monkeypatch):
    """PyAV 19 kennt ``metadata_errors`` nicht mehr – Dekodieren und Dauer müssen trotzdem gehen."""
    import av

    sr = 48000
    path = tmp_path / "t.m4a"
    try:
        _encode_av(path, sine(440.0, 1.0, sr), sr, "aac", "ipod")
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Encoder aac nicht verfügbar: {exc}")
    real_open = av.open
    calls = []

    def open_v19(file, *args, **kwargs):
        calls.append(sorted(kwargs))
        if "metadata_errors" in kwargs or "metadata_encoding" in kwargs:
            raise TypeError("open() got an unexpected keyword argument 'metadata_errors'")
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr(av, "open", open_v19)
    data, out_sr = decode(path, SR)
    assert out_sr == SR and abs(dominant_frequency(data, SR) - 440) < 6
    assert abs(probe(path).duration - 1.0) < 0.1
    assert [] in calls                                   # Aufruf ohne den alten Parameter


def test_decode_mono_and_resample(tmp_path):
    path = tmp_path / "mono.wav"
    sf.write(path, sine(300, 0.5, 22050, channels=1), 22050)
    data, sr = decode(path, SR)
    assert data.shape == (SR // 2, 2)
    assert np.allclose(data[:, 0], data[:, 1])
    assert abs(dominant_frequency(data, SR) - 300) < 5


def test_decode_errors(tmp_path):
    with pytest.raises(DecodeError):
        decode(tmp_path / "gibt_es_nicht.wav")
    bad = tmp_path / "kaputt.mp3"
    bad.write_bytes(b"das ist kein audio" * 100)
    with pytest.raises(DecodeError):
        decode(bad)


# ---------------------------------------------------------------------------
# DSP
# ---------------------------------------------------------------------------
def test_aggregate_peaks_matches_bruteforce():
    rng = np.random.default_rng(0)
    pcm = (rng.normal(0, 0.3, (SR * 2, 2))).astype(np.float32)
    peaks = dsp.compute_peaks(pcm)
    assert peaks.shape == ((SR * 2 + dsp.PEAK_BUCKET - 1) // dsp.PEAK_BUCKET, 3)
    cols = dsp.aggregate_peaks(peaks, 0, peaks.shape[0], 50)
    mid = (pcm[:, 0] + pcm[:, 1]) / 2
    per_col = peaks.shape[0] / 50
    for c in (0, 17, 49):
        b0, b1 = int(np.floor(c * per_col)), int(np.floor((c + 1) * per_col)) if c < 49 else peaks.shape[0]
        seg = mid[b0 * dsp.PEAK_BUCKET: b1 * dsp.PEAK_BUCKET]
        assert cols[c, 1] == pytest.approx(seg.max(), abs=2e-3)
        assert cols[c, 0] == pytest.approx(seg.min(), abs=2e-3)


def test_columns_from_pcm_and_zoomed_aggregate():
    pcm = sine(100, 0.2, SR)
    cols = dsp.columns_from_pcm(pcm, 0, 400, 400)
    assert cols.shape == (400, 3)
    peaks = dsp.compute_peaks(pcm)
    zoom = dsp.aggregate_peaks(peaks, 2.0, 2.5, 20)  # mehrere Spalten je Bucket
    assert np.all(zoom[:, 1] >= zoom[:, 0])


def test_soft_limit_and_fades():
    x = sine(440, 0.5, SR, amp=1.8)
    assert dsp.soft_limit(x, SR)
    assert np.max(np.abs(x)) <= 0.97 + 1e-6
    y = sine(440, 0.5, SR, amp=0.5)
    assert not dsp.soft_limit(y, SR)
    dsp.apply_edge_fades(y, SR, 5.0)
    assert abs(y[0, 0]) < 1e-6 and abs(y[-1, 0]) < 1e-3


# ---------------------------------------------------------------------------
# Time-Stretch
# ---------------------------------------------------------------------------
def _read_all(st: TimeStretcher, block: int = 777) -> np.ndarray:
    out = []
    while True:
        chunk, filled = st.read(block)
        out.append(chunk[:filled])
        if filled < block:
            return np.concatenate(out)


def _chord(seconds: float) -> tuple[np.ndarray, list[float]]:
    """Klavierähnlicher Akkord (Bass + Cmaj7, leicht inharmonische Obertöne) – mehrstimmig,
    hier klang das frühere WSOLA rau/„verzerrt“."""
    t = np.arange(int(SR * seconds)) / SR
    freqs = [f0 * h * (1 + 0.0004 * h * h) for f0 in (65.41, 261.63, 329.63, 392.0, 493.88) for h in (1, 2, 3, 4)]
    x = sum(np.sin(2 * np.pi * f * t + i) / (1 + i % 4) for i, f in enumerate(freqs))
    x = (0.2 * x / np.max(np.abs(x))).astype(np.float32)
    return np.stack([x, x], axis=1), freqs


def _off_tone_db(y: np.ndarray, freqs: list[float]) -> float:
    """Anteil der Energie abseits der erwarteten Töne (Rauigkeit, Verzerrung) in dB."""
    m = y[:, 0].astype(np.float64)
    spec = np.abs(np.fft.rfft(m * np.blackman(len(m)))) ** 2
    f = np.fft.rfftfreq(len(m), 1 / SR)
    near = np.min(np.abs(f[:, None] - np.asarray(freqs)[None, :]), axis=1) < 6.0
    return float(10 * np.log10(spec[~near].sum() / spec.sum()))


def test_stretch_is_exact_at_speed_one():
    x = sine(440, 1.0, SR)
    y = _read_all(TimeStretcher(x, SR))
    assert len(y) == len(x)
    assert np.max(np.abs(y - x)) < 1e-5
    # auch für einen Ausschnitt aus int16-Daten (so liegen sie im PCM-Cache)
    pcm = (x * 32767).astype(np.int16)
    y = _read_all(TimeStretcher(pcm, SR, start=12345, end=40000))
    assert len(y) == 40000 - 12345
    assert np.max(np.abs(y - pcm[12345:40000] / 32768.0)) < 1e-5


@pytest.mark.parametrize("speed", [0.5, 0.8, 1.25, 2.0])
def test_stretch_keeps_pitch_and_changes_length(speed):
    x = sine(440, 2.0, SR)
    y = stretch(x, SR, 0, len(x), speed)
    assert abs(len(y) - len(x) / speed) <= 2
    assert abs(dominant_frequency(y, SR) - 440) < 3


@pytest.mark.parametrize("speed", [0.5, 0.75, 1.5, 2.0])
def test_stretch_polyphonic_without_roughness(speed):
    x, freqs = _chord(3.0)
    y = stretch(x, SR, 0, len(x), speed)[SR // 2: -SR // 2]
    assert _off_tone_db(x, freqs) < -80
    assert _off_tone_db(y, freqs) < -25  # früheres WSOLA: ≈ -9 dB, Phase-Vocoder: -30 … -44 dB


def test_stretch_keeps_transients_sharp():
    """Schläge bleiben einzeln und scharf: kein Vorecho, keine Verdopplung, Spitze und Rhythmus erhalten."""
    rng = np.random.default_rng(7)
    x = np.zeros(int(SR * 2.4))
    k = np.arange(int(0.1 * SR))
    hits = [0.31, 0.83, 1.42, 1.97]
    for t0 in hits:
        i = int(t0 * SR)
        x[i: i + len(k)] += rng.standard_normal(len(k)) * np.exp(-k / (0.01 * SR))
    x = (0.5 * x / np.max(np.abs(x))).astype(np.float32)
    for speed in (0.5, 0.75, 1.5, 2.0):
        y = stretch(np.stack([x, x], axis=1), SR, 0, len(x), speed)[:, 0]
        onsets = []
        for t0 in hits:
            c = int(t0 / speed * SR)
            seg = y[c - int(0.1 * SR): c + int(0.15 * SR)].astype(np.float64)
            a = np.abs(seg)
            onset = int(np.argmax(a > 0.5 * a.max()))
            onsets.append(c - int(0.1 * SR) + onset)
            pre = seg[max(0, onset - int(0.04 * SR)): onset - int(0.0015 * SR)]
            assert (pre ** 2).sum() < 1e-3 * (seg ** 2).sum()  # Vorecho unter -30 dB
            original = np.max(np.abs(x[int(t0 * SR): int(t0 * SR) + len(k)]))
            assert a.max() > 0.8 * original
            # Schläge sitzen höchstens ein halbes Fenster neben der idealen Stelle …
            assert abs(onsets[-1] - c) < 0.05 * SR
        # … aber alle gleich: Der Rhythmus bleibt gleichmäßig
        ideal = np.diff(hits) / speed * SR
        assert np.max(np.abs(np.diff(onsets) - ideal)) < 0.008 * SR


def test_stretch_preserves_stereo_image():
    x, _ = _chord(2.0)
    x[:, 0] = np.roll(x[:, 1], 12)  # links 0,25 ms später -> Schallquelle rechts
    y = stretch(x, SR, 0, len(x), 0.75)[SR // 2: -SR // 2].astype(np.float64)
    left, right = y[:, 0], y[:, 1]
    lags = range(-40, 41)
    corr = [np.dot(left[40:-40], np.roll(right, lag)[40:-40]) for lag in lags]
    best = int(np.argmax(corr))
    assert list(lags)[best] == 12
    assert corr[best] / np.sqrt(np.dot(left[40:-40], left[40:-40]) * np.dot(right[40:-40], right[40:-40])) > 0.99


def test_stretch_live_speed_changes_stay_clean():
    x = sine(440, 12.0, SR)
    st = TimeStretcher(x, SR)
    out = []
    for i in range(400):  # ≈ 4 s; das Tempo wird wie am Regler laufend verändert
        st.speed = 1.25 + 0.75 * np.sin(i / 25)
        chunk, filled = st.read(480)
        out.append(chunk[:filled])
    y = np.concatenate(out)[SR // 4:]
    assert _off_tone_db(y, [440.0]) < -60


def test_stretch_streaming_speed_change_and_position():
    x = sine(330, 3.0, SR)
    st = TimeStretcher(x, SR, start=SR // 2, end=int(2.5 * SR))
    st.speed = 2.0
    st.read(SR // 2)                       # 0,5 s Ausgabe bei 2× = 1 s Eingabe
    assert st.position == pytest.approx(SR * 1.5, abs=0.02 * SR)
    st.speed = 0.5
    st.read(SR // 2)                       # 0,5 s bei 0,5× = 0,25 s Eingabe
    # Der Tempowechsel greift nach zwei Fenstern (≈ 43 ms, so lange läuft noch 2×)
    assert st.position == pytest.approx(SR * 1.75, abs=0.07 * SR)
    st.seek(SR)
    assert st.position == SR


# ---------------------------------------------------------------------------
# PCM-Cache + Rendering
# ---------------------------------------------------------------------------
def test_cache_build_lookup_cleanup(tmp_path, wav_file):
    src = wav_file("c.wav", 0.5)
    cdir = tmp_path / ".cache"
    assert cache.lookup(cdir, src, SR) is None
    entry = cache.build(cdir, src, SR)
    assert entry.frames == SR // 2 and entry.pcm_path.exists() and entry.peaks_path.exists()
    hit = cache.lookup(cdir, src, SR)
    assert hit is not None and hit.key == entry.key
    pcm = cache.open_pcm(entry)
    assert pcm.shape == (SR // 2, 2) and pcm.dtype == np.int16
    assert cache.load_peaks(entry).shape[1] == 3
    del pcm
    # andere Samplerate -> anderer Eintrag
    assert cache.lookup(cdir, src, 44100) is None
    (cdir / "fremd.pcm").write_bytes(b"x")
    removed = cache.cleanup(cdir, {entry.key})
    assert removed == 1 and cache.lookup(cdir, src, SR) is not None


def test_render_edit(tmp_path, wav_file):
    src = wav_file("r.wav", 2.0, amp=0.4)
    out = tmp_path / "audio" / "bearbeitet" / "r_edit.flac"
    res = tasks.render_edit(str(src), str(tmp_path / ".cache"), SR,
                            {"start": 0.5, "end": 1.5, "speed": 1.25, "gain": 1.5}, str(out))
    assert out.exists()
    info = sf.info(out)
    assert info.subtype == "PCM_24" and info.samplerate == SR
    assert res["duration"] == pytest.approx(0.8, abs=0.01)
    data, _ = sf.read(out)
    assert np.max(np.abs(data)) == pytest.approx(0.6, abs=0.02)
    assert not res["limited"]
    loud_src = wav_file("laut.wav", 1.0, amp=0.7)
    loud = tasks.render_edit(str(loud_src), str(tmp_path / ".cache"), SR,
                             {"start": 0, "end": None, "speed": 1.0, "gain": 2.0}, str(tmp_path / "laut.flac"))
    assert loud["limited"]
    data, _ = sf.read(tmp_path / "laut.flac")
    assert np.max(np.abs(data)) <= 0.975


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
def _engine() -> AudioEngine:
    eng = AudioEngine()
    eng.samplerate = SR
    return eng


def _int16(x: np.ndarray) -> np.ndarray:
    return (x * 32767).astype(np.int16)


def test_engine_toggle_start_stop_with_fade():
    eng = _engine()
    pcm = _int16(sine(440, 1.0, SR))
    eng.toggle("a", pcm)
    out = eng.render_offline(SR // 4)
    assert "a" in eng.snapshot and np.max(np.abs(out)) == pytest.approx(0.5, abs=0.01)
    eng.toggle("a", pcm)  # zweites Tippen = Stopp mit kurzem Fade
    out = eng.render_offline(SR // 10)
    assert "a" not in eng.snapshot
    fade = int(SR * eng.stop_fade_ms / 1000)
    assert np.max(np.abs(out[fade + 10:])) == 0.0
    assert np.max(np.abs(out[:10])) > 0.1  # kein harter Abbruch


def test_engine_voice_ends_and_loop_continues():
    eng = _engine()
    pcm = _int16(sine(440, 0.25, SR))
    eng.toggle("einmal", pcm, loop=False)
    eng.toggle("schleife", pcm, loop=True)
    eng.render_offline(SR // 2)
    assert "einmal" not in eng.snapshot and "schleife" in eng.snapshot
    eng.set_loop("schleife", False)
    eng.render_offline(SR // 2)
    assert eng.snapshot == {}


def test_engine_parallel_voices_are_limited():
    eng = _engine()
    pcm = _int16(sine(440, 0.5, SR, amp=0.6))
    for k in range(4):
        eng.toggle(k, pcm)
    out = eng.render_offline(SR // 4)
    assert len(eng.snapshot) == 4
    assert np.max(np.abs(out)) <= 1.0
    l, r, limiting = eng.take_levels()
    assert limiting and l > 0.9
    eng.stop_all()
    eng.render_offline(SR // 5)
    assert eng.snapshot == {}


def test_engine_kill_and_restart():
    eng = _engine()
    pcm = _int16(sine(440, 1.0, SR))
    eng.play("x", pcm)
    eng.render_offline(1000)
    eng.play("x", pcm)  # Neustart: alte Stimme blendet aus, neue beginnt
    eng.render_offline(1000)
    assert eng.snapshot["x"][0] == 1000
    eng.kill("x")
    eng.render_offline(SR // 20)
    assert eng.snapshot == {}


def test_engine_stop_group_and_rekey():
    eng = _engine()
    pcm = _int16(sine(440, 1.0, SR))
    eng.toggle((1, 0, 0), pcm)             # Registerkarte 1
    eng.render_offline(1000)
    eng.toggle((1, 0, 1), pcm)
    eng.toggle((2, 0, 0), pcm)             # Registerkarte 2
    eng.render_offline(500)
    # Tausch (0,0) <-> (0,1) in Karte 1: Stimmen laufen unter dem neuen Schlüssel weiter
    eng.rekey({(1, 0, 0): (1, 0, 1), (1, 0, 1): (1, 0, 0)})
    eng.render_offline(500)
    assert set(eng.snapshot) == {(1, 0, 0), (1, 0, 1), (2, 0, 0)}
    assert eng.snapshot[(1, 0, 1)][0] == 2000   # die zuerst gestartete Stimme liegt jetzt auf (0,1)
    assert eng.snapshot[(1, 0, 0)][0] == 1000
    eng.stop_group(1)                      # Karte 1 schließen -> nur deren Kacheln ausblenden
    eng.render_offline(SR // 10)
    assert set(eng.snapshot) == {(2, 0, 0)}


def test_engine_prefetch_releases_finished_voices():
    """Der Vorlade-Thread hält keine beendete Stimme fest – sonst bliebe ihre memmap (und unter
    Windows der Projektordner) gesperrt, z. B. beim Löschen eines Projekts."""
    import gc
    import time
    import weakref

    eng = AudioEngine()
    eng.start_null(SR)
    try:
        pcm = _int16(sine(440, 2.0, SR))
        ref = weakref.ref(pcm)
        eng.toggle("x", pcm, loop=True)
        end = time.monotonic() + 3
        while "x" not in eng.snapshot and time.monotonic() < end:
            time.sleep(0.01)
        time.sleep(0.5)                    # mehrere Vorlade-Durchgänge mit der laufenden Stimme
        eng.kill("x")
        del pcm
        end = time.monotonic() + 3
        while ref() is not None and time.monotonic() < end:
            time.sleep(0.05)
            gc.collect()
        assert ref() is None
    finally:
        eng.shutdown()


def test_engine_preview_play_pause_seek_and_end():
    eng = _engine()
    pcm = _int16(sine(440, 2.0, SR))
    eng.preview_load(pcm)
    eng.preview_region(SR // 2, SR)       # Auswahl 0,5 … 1,0 s
    eng.preview_speed(1.0)
    eng.preview_seek(SR // 2)
    eng.preview_play()
    eng.render_offline(SR // 4)
    playing, pos = eng.preview_state
    assert playing and pos == pytest.approx(0.75 * SR, abs=0.03 * SR)
    eng.preview_pause()
    eng.render_offline(SR // 10)
    _, p1 = eng.preview_state
    eng.render_offline(SR // 10)
    _, p2 = eng.preview_state
    assert p1 == p2  # pausiert = Position steht
    eng.preview_play()
    eng.render_offline(SR)                 # über das Auswahlende hinaus
    playing, pos = eng.preview_state
    assert not playing and pos == SR // 2  # zurück an den Auswahlanfang
    assert ("preview_end", None) in list(eng.events)
    eng.preview_load(None)
    eng.render_offline(100)
