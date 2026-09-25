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


def test_task_runner_falls_back_to_threads(qapp):
    """Fallen die Worker-Prozesse aus, wird im Thread wiederholt und später dauerhaft umgeschaltet."""
    import _crashy
    from conftest import wait_until

    from launchpad_pro_tab.bridge.tasks import TaskRunner

    runner = TaskRunner(use_processes=True)
    results: list = []
    try:
        for expected in (1, 2, 3):
            runner.submit_process(_crashy.crash_in_worker, on_done=results.append, on_error=results.append)
            assert wait_until(qapp, lambda: len(results) == expected, 60)
            assert results[-1] == 42
        assert not runner.uses_processes
        assert runner.pending == 0
    finally:
        runner.shutdown()


def test_workers_end_when_main_program_dies(tmp_path):
    """Verwaiste Worker würden Programmdateien sperren (Update/Deinstallation) – sie müssen
    sich selbst beenden, wenn das Hauptprogramm abstürzt."""
    import subprocess
    import sys
    import time

    from conftest import ROOT
    from launchpad_pro_tab.update.install import _pid_alive

    script = tmp_path / "eltern.py"
    script.write_text(
        "import os, sys\n"
        f"sys.path.insert(0, {str(ROOT)!r})\n"
        "import multiprocessing as mp\n"
        "from concurrent.futures import ProcessPoolExecutor\n"
        "from launchpad_pro_tab.audio.tasks import ping, worker_init\n"
        "if __name__ == '__main__':\n"
        "    pool = ProcessPoolExecutor(2, mp_context=mp.get_context('spawn'), initializer=worker_init)\n"
        "    pids = {pool.submit(ping).result() for _ in range(6)}\n"
        "    print(' '.join(map(str, pids)), flush=True)\n"
        "    os._exit(0)   # Absturz simulieren: kein Aufräumen\n",
        encoding="utf-8",
    )
    out = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, timeout=120)
    pids = [int(p) for p in out.stdout.split()]
    assert pids, out.stderr
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline and any(_pid_alive(p) for p in pids):
        time.sleep(0.1)
    assert not any(_pid_alive(p) for p in pids), "Worker laufen nach dem Ende des Hauptprogramms weiter"
