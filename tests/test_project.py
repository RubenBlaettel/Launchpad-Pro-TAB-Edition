import json
import zipfile
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from launchpad_pro_tab.core.constants import PROJECT_FILE_NAME
from launchpad_pro_tab.core.project import Project, ProjectError


def test_create_open_save_roundtrip(tmp_path: Path):
    p = Project.create("Sommerstück 2026", tmp_path, 5)
    assert p.file.exists()
    for sub in ("audio", "audio/bearbeitet", "cover", ".autosave", ".cache"):
        assert (p.root / sub).is_dir()
    p.data.tile(0, 1).audio = "audio/x.wav"
    p.data.tile(0, 1).title = "Donner"
    p.save()
    q = Project.open(p.root)
    assert q.name == "Sommerstück 2026" and q.data.grid == 5
    assert q.data.peek(0, 1).title == "Donner"
    # Öffnen über die Projektdatei selbst
    assert Project.open(p.file).root == p.root


def test_create_rejects_empty_name_and_existing_project(tmp_path: Path):
    with pytest.raises(ProjectError):
        Project.create("   ", tmp_path, 4)
    Project.create("Doppelt", tmp_path, 4)
    with pytest.raises(ProjectError):
        Project.create("Doppelt", tmp_path, 4)


def test_save_keeps_backup_and_recovers_from_corruption(tmp_path: Path):
    p = Project.create("Sicher", tmp_path, 4)
    p.data.tile(0, 0).audio = "audio/a.wav"
    p.save()
    p.save()  # erzeugt .bak der vorherigen Fassung
    backup = p.autosave_dir / (PROJECT_FILE_NAME + ".bak")
    assert backup.exists()
    p.file.write_text("{ kaputt", encoding="utf-8")
    q = Project.open(p.root)
    assert q.data.peek(0, 0).audio == "audio/a.wav"


def test_import_audio_copies_and_deduplicates(tmp_path: Path, wav_file):
    p = Project.create("Import", tmp_path / "proj", 4)
    src = wav_file("klang.wav", 0.2)
    rel1 = p.import_audio(src)
    rel2 = p.import_audio(src)
    assert rel1 == rel2 == "audio/klang.wav"
    # gleicher Name, anderer Inhalt -> eigener Name
    d = tmp_path / "anders"
    d.mkdir()
    sf.write(d / "klang.wav", np.zeros((1000, 2), np.float32), 48000)
    rel3 = p.import_audio(d / "klang.wav")
    assert rel3 == "audio/klang (2).wav"
    assert p.import_audio(d / "klang.wav") == rel3
    # Datei liegt bereits im Projekt
    assert p.import_audio(p.root / rel1) == rel1


def test_save_as_copies_without_cache(tmp_path: Path, wav_file):
    p = Project.create("Original", tmp_path / "a", 4)
    rel = p.import_audio(wav_file("x.wav", 0.1))
    p.data.tile(0, 0).audio = rel
    (p.cache_dir / "dummy.pcm").write_bytes(b"123")
    p.save()
    q = p.save_as(tmp_path / "b", "Kopie")
    assert q.root != p.root and q.name == "Kopie"
    assert (q.root / rel).exists()
    assert not (q.cache_dir / "dummy.pcm").exists()
    assert q.data.peek(0, 0).audio == rel


def test_export_and_import_zip(tmp_path: Path, wav_file):
    p = Project.create("Export Test", tmp_path / "a", 4)
    rel = p.import_audio(wav_file("x.wav", 0.1))
    p.data.tile(1, 1).audio = rel
    (p.cache_dir / "dummy.pcm").write_bytes(b"123")
    p.write_edit_session({"tile": [1, 1]})
    p.save()
    zip_path = p.export_zip(tmp_path / "export")
    assert zip_path.suffix == ".zip"
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
    assert any(n.endswith(PROJECT_FILE_NAME) for n in names)
    assert any(n.endswith("audio/x.wav") for n in names)
    assert not any(".cache" in n or ".autosave" in n for n in names)
    target = Project.import_zip(zip_path, tmp_path / "import")
    q = Project.open(target)
    assert q.data.peek(1, 1).audio == rel and (q.root / rel).exists()


def test_import_zip_blocks_path_traversal(tmp_path: Path):
    evil = tmp_path / "evil.zip"
    with zipfile.ZipFile(evil, "w") as zf:
        zf.writestr("Projekt/" + PROJECT_FILE_NAME, json.dumps({"format": "launchpad-pro-tab", "name": "X"}))
        zf.writestr("Projekt/../../boese.txt", "nein")
    target = Project.import_zip(evil, tmp_path / "ziel")
    assert (target / PROJECT_FILE_NAME).exists()
    assert not (tmp_path / "boese.txt").exists()


def test_import_zip_without_project_fails(tmp_path: Path):
    bad = tmp_path / "leer.zip"
    with zipfile.ZipFile(bad, "w") as zf:
        zf.writestr("irgendwas.txt", "x")
    with pytest.raises(ProjectError):
        Project.import_zip(bad, tmp_path)


def test_edit_session_roundtrip(tmp_path: Path):
    p = Project.create("Session", tmp_path, 4)
    assert p.read_edit_session() is None
    p.write_edit_session({"tile": [0, 2], "params": {"speed": 1.2}})
    assert p.read_edit_session()["tile"] == [0, 2]
    p.clear_edit_session()
    assert p.read_edit_session() is None


def test_remove_unreferenced_only_deletes_edited_files(tmp_path: Path):
    p = Project.create("Aufräumen", tmp_path, 4)
    edited = p.root / "audio/bearbeitet/alt.flac"
    edited.write_bytes(b"x")
    original = p.root / "audio/orig.wav"
    original.write_bytes(b"x")
    p.remove_unreferenced("audio/bearbeitet/alt.flac")
    p.remove_unreferenced("audio/orig.wav")
    assert not edited.exists() and original.exists()
