"""Deinstallation mit „Alle Projekte und Einstellungen löschen“ (``--purge-user-data``)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import ROOT
from launchpad_pro_tab.core import purge
from launchpad_pro_tab.core.project import Project
from launchpad_pro_tab.core.settings import AppSettings


@pytest.fixture
def home(tmp_path, monkeypatch):
    """Eigener Benutzerordner mit Einstellungen, Cache und Projektordner."""
    h = tmp_path / "home"
    (h / "Documents").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    monkeypatch.setenv("LPTAB_CONFIG_DIR", str(h / ".config" / "launchpad-pro-tab"))
    monkeypatch.setenv("LPTAB_CACHE_DIR", str(h / ".cache" / "launchpad-pro-tab"))
    monkeypatch.setenv("LPTAB_PROJECTS_DIR", str(h / "Documents" / "Launchpad Pro TAB"))
    return h


def test_purge_deletes_only_own_data(home, tmp_path):
    projects_root = home / "Documents" / "Launchpad Pro TAB"
    a = Project.create("Sommerstück", projects_root, 4)
    (a.root / "audio" / "ton.wav").write_bytes(b"RIFF")
    b = Project.create("Gastspiel", tmp_path / "USB-Stick", 3)          # woanders, nur in der Liste
    c = Project.create("Mit eigenen Dateien", tmp_path / "Theater", 3)
    (c.root / "Notizen.txt").write_text("bitte behalten")               # fremde Datei
    foreign = tmp_path / "Fremd"
    foreign.mkdir()
    (foreign / "projekt.lptab").write_text(json.dumps({"format": "etwas-anderes"}))
    # Projektdatei direkt im Dokumente-Ordner: geschützter Ort, darf nie gelöscht werden
    (home / "Documents" / "projekt.lptab").write_text(json.dumps({"format": "launchpad-pro-tab"}))
    (home / "Documents" / "audio").mkdir()
    (home / "Documents" / "audio" / "Lieblingslied.mp3").write_bytes(b"ID3")

    settings = AppSettings.load()
    for proj in (a, b, c):
        settings.remember_project(proj.root, proj.name)
    settings.recent_projects.append({"path": str(foreign), "name": "Fremd"})
    settings.recent_projects.append({"path": str(home / "Documents"), "name": "Dokumente"})
    settings.recent_projects.append({"path": str(tmp_path / "gibt-es-nicht"), "name": "weg"})
    settings.save()
    cache = Path(purge.cache_dir())
    (cache / "updates").mkdir(parents=True, exist_ok=True)

    plan = purge.plan_purge(documents=home / "Documents")
    assert sorted(plan.projects) == sorted([a.root.resolve(), b.root.resolve(), c.root.resolve()])
    assert all("Fremd" not in str(p) for p in plan.projects)
    report = purge.execute_purge(plan)

    assert not a.root.exists() and not b.root.exists()
    assert not projects_root.exists()                                   # war danach leer
    assert c.root.exists() and (c.root / "Notizen.txt").exists()        # fremde Datei bleibt
    assert not (c.root / "projekt.lptab").exists() and not (c.root / "audio").exists()
    assert (foreign / "projekt.lptab").exists()
    assert (home / "Documents" / "audio" / "Lieblingslied.mp3").exists()
    assert not (home / ".config" / "launchpad-pro-tab").exists()
    assert not (home / ".cache" / "launchpad-pro-tab").exists()
    assert str(c.root.resolve()) in report.kept
    assert report.errors == []


def test_purge_cli_dry_run_and_confirmed(home):
    env = {**os.environ, "PYTHONPATH": str(ROOT)}
    proj = Project.create("CLI-Test", home / "Documents" / "Launchpad Pro TAB", 3)
    settings = AppSettings.load()
    settings.remember_project(proj.root, proj.name)
    settings.save()

    dry = subprocess.run([sys.executable, "-m", "launchpad_pro_tab", "--purge-user-data"],
                         env=env, capture_output=True, text=True, timeout=120)
    assert dry.returncode == 0 and "CLI-Test" in dry.stdout
    assert proj.root.exists()                                           # ohne --yes nichts löschen

    real = subprocess.run([sys.executable, "-m", "launchpad_pro_tab", "--purge-user-data", "--yes"],
                          env=env, capture_output=True, text=True, timeout=120)
    assert real.returncode == 0, real.stdout + real.stderr
    assert not proj.root.exists()
    assert not (home / ".config" / "launchpad-pro-tab").exists()
