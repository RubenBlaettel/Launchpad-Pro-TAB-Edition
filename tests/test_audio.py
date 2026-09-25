"""Tests für Dekodierung, PCM-Cache, DSP, Time-Stretch, Engine und Rendering."""

from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from conftest import SR, dominant_frequency, sine
from launchpad_pro_tab.audio import cache, dsp, tasks
from launchpad_pro_tab.audio.decoder import DecodeError, decode, probe
from launchpad_pro_tab.audio.engine import AudioEngine
from launchpad_pro_tab.audio.timestretch import WsolaStretcher, stretch


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
def test_stretch_is_exact_at_speed_one():
    x = sine(440, 1.0, SR)
    st = WsolaStretcher(x, SR)
    out = []
    while True:
        chunk, filled = st.read(777)
        out.append(chunk[:filled])
        if filled < 777:
            break
    y = np.concatenate(out)
    assert np.max(np.abs(y[: len(x)] - x)) < 1e-5


@pytest.mark.parametrize("speed", [0.5, 0.8, 1.25, 2.0])
def test_stretch_keeps_pitch_and_changes_length(speed):
    x = sine(440, 2.0, SR)
    y = stretch(x, SR, 0, len(x), speed)
    assert abs(len(y) - len(x) / speed) <= 2
    assert abs(dominant_frequency(y, SR) - 440) < 3


def test_stretch_streaming_speed_change_and_position():
    x = sine(330, 3.0, SR)
    st = WsolaStretcher(x, SR, start=SR // 2, end=int(2.5 * SR))
    st.speed = 2.0
    st.read(SR // 2)                       # 0,5 s Ausgabe bei 2× = 1 s Eingabe
    assert st.position == pytest.approx(SR * 1.5, abs=0.02 * SR)
    st.speed = 0.5
    st.read(SR // 2)                       # 0,5 s bei 0,5× = 0,25 s Eingabe
    assert st.position == pytest.approx(SR * 1.75, abs=0.03 * SR)
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
