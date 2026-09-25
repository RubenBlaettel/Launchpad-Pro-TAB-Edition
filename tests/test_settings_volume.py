import time

from launchpad_pro_tab.core.settings import MAX_RECENT_AUDIO, AppSettings
from launchpad_pro_tab.system.volume import DummyVolume, create_system_volume


def test_settings_roundtrip_and_corruption(tmp_path):
    path = tmp_path / "einstellungen.json"
    s = AppSettings.load(path)
    s.buffer_frames = 256
    s.remember_project(tmp_path / "Projekt A", "Projekt A")
    s.save()
    again = AppSettings.load(path)
    assert again.buffer_frames == 256
    assert again.last_project == str((tmp_path / "Projekt A").resolve())
    path.write_text("{ nicht json", encoding="utf-8")
    broken = AppSettings.load(path)
    assert broken.buffer_frames == 0 and broken.recent_projects == []


def test_recent_audio_order_dedupe_and_limit(tmp_path):
    s = AppSettings.load(tmp_path / "s.json")
    a, b = tmp_path / "a.wav", tmp_path / "b.wav"
    s.remember_audio(a, 1.0)
    s.remember_audio(b, 2.0)
    s.remember_audio(a)  # erneut benutzt -> nach oben, Dauer bleibt
    assert [e["name"] for e in s.recent_audio] == ["a.wav", "b.wav"]
    assert s.recent_audio[0]["duration"] == 1.0
    for i in range(MAX_RECENT_AUDIO + 10):
        s.remember_audio(tmp_path / f"f{i}.wav")
    assert len(s.recent_audio) == MAX_RECENT_AUDIO
    s.forget_audio(s.recent_audio[0]["path"])
    assert len(s.recent_audio) == MAX_RECENT_AUDIO - 1


def test_dummy_volume():
    v = DummyVolume()
    v.set_volume(1.7)
    v.set_mute(True)
    assert v.get() == (1.0, True)
    assert create_system_volume() is not None  # darf nie werfen


def test_master_volume_controller(qapp):
    from launchpad_pro_tab.bridge.volume import MasterVolumeController

    backend = DummyVolume()
    ctrl = MasterVolumeController(backend_factory=lambda: backend)
    try:
        ctrl.setVolume(0.3)
        ctrl.setMuted(True)
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline and backend.get() != (0.3, True):
            qapp.processEvents()
            time.sleep(0.02)
        assert backend.get() == (0.3, True)
        assert ctrl.volume == 0.3 and ctrl.muted
        # externe Änderung wird übernommen (nach der Schonfrist)
        ctrl._last_user_change = 0
        backend.set_volume(0.8)
        deadline = time.monotonic() + 4
        while time.monotonic() < deadline and abs(ctrl.volume - 0.8) > 1e-3:
            qapp.processEvents()
            time.sleep(0.02)
        assert abs(ctrl.volume - 0.8) < 1e-3
    finally:
        ctrl.shutdown()
