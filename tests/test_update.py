"""Update-Funktion: Versionen, GitHub-Releases, geprüfter Download, Installationswege.

Alle Netzwerkzugriffe gehen an einen lokalen Test-Server (kein Internet nötig).
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import subprocess
import sys
import tarfile
import textwrap
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from conftest import ROOT, wait_until
from launchpad_pro_tab.update import install, releases
from launchpad_pro_tab.update.download import ChecksumError, DownloadCancelled, download
from launchpad_pro_tab.update.install import InstallKind
from launchpad_pro_tab.update.net import NetworkError, check_url
from launchpad_pro_tab.update.releases import parse_checksums, parse_release, pick_update
from launchpad_pro_tab.update.version import is_newer, parse_version


# ---------------------------------------------------------------------------
# Versionen
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("newer, older", [
    ("1.1.0", "1.0.0"), ("v1.10.0", "1.9.9"), ("2", "1.99.99"), ("1.2.0", "1.2.0-rc.1"),
    ("1.2.0rc1", "1.2.0b3"), ("1.2.0-beta.2", "1.2.0-beta.1"), ("1.2.0a1", "1.2.0.dev1"),
])
def test_version_order(newer, older):
    assert is_newer(newer, older)
    assert not is_newer(older, newer)


def test_version_parse_edge_cases():
    assert str(parse_version("v1.2.3")) == "1.2.3"
    assert parse_version("1.2.3-beta.1").is_prerelease
    assert not parse_version("1.2.3").is_prerelease
    assert parse_version("nightly") is None and parse_version("") is None
    assert not is_newer("1.0.0", "1.0.0")
    assert not is_newer("unsinn", "1.0.0")
    assert is_newer("1.0.1", "unsinn")


# ---------------------------------------------------------------------------
# Releases auswählen
# ---------------------------------------------------------------------------
def _raw(tag, *, pre=False, draft=False, assets=()):
    return {"tag_name": tag, "name": f"Version {tag}", "body": "Neu", "draft": draft, "prerelease": pre,
            "html_url": f"https://example.invalid/{tag}", "published_at": "2026-10-01T10:00:00Z",
            "assets": list(assets)}


def test_parse_release_and_pick_update():
    digest = "a" * 64
    rels = [r for r in (parse_release(x) for x in [
        _raw("v1.0.0"),
        _raw("v1.2.0", assets=[{"name": "LaunchpadProTAB-Setup-1.2.0.exe", "browser_download_url": "https://x/s.exe",
                                "size": 10, "digest": f"sha256:{digest}"}]),
        _raw("v1.3.0-beta.1", pre=True),
        _raw("v9.9.9", draft=True),             # Entwurf: ignorieren
        _raw("kaputt"),                         # unlesbares Tag: ignorieren
    ]) if r is not None]
    assert [str(r.version) for r in rels] == ["1.0.0", "1.2.0", "1.3.0-beta.1"]
    stable = pick_update(rels, "1.1.0")
    assert str(stable.version) == "1.2.0"
    assert stable.asset(install.WINDOWS_ASSET).sha256 == digest
    assert stable.published.year == 2026
    assert str(pick_update(rels, "1.1.0", include_prereleases=True).version) == "1.3.0-beta.1"
    assert pick_update(rels, "1.2.0") is None                       # schon aktuell
    assert pick_update(rels, "1.1.0", skipped="1.2.0") is None      # übersprungen
    assert pick_update(rels, "2.0.0") is None
    # Übersprungene Version gilt nicht mehr, sobald es eine neuere gibt
    newer = rels + [parse_release(_raw("v1.2.1"))]
    assert str(pick_update(newer, "1.1.0", skipped="1.2.0").version) == "1.2.1"


def test_asset_patterns_match_release_names():
    import re

    assert re.search(install.WINDOWS_ASSET, "LaunchpadProTAB-Setup-1.1.0.exe")
    assert re.search(install.LINUX_ASSET, "LaunchpadProTAB-1.1.0-linux-x86_64.tar.gz")
    assert not re.search(install.WINDOWS_ASSET, "LaunchpadProTAB-1.1.0-linux-x86_64.tar.gz")
    assert not re.search(install.LINUX_ASSET, "SHA256SUMS.txt")


def test_parse_checksums():
    text = f"{'b' * 64}  LaunchpadProTAB-Setup-1.2.0.exe\n{'C' * 64} *paket.tar.gz\nkaputt\n"
    sums = parse_checksums(text)
    assert sums == {"LaunchpadProTAB-Setup-1.2.0.exe": "b" * 64, "paket.tar.gz": "c" * 64}


def test_only_https_or_localhost():
    check_url("https://api.github.com/x")
    check_url("http://127.0.0.1:8000/x")
    for bad in ("http://example.com/x", "ftp://example.com/x", "file:///etc/passwd"):
        with pytest.raises(NetworkError):
            check_url(bad)


# ---------------------------------------------------------------------------
# Lokaler "GitHub"-Server
# ---------------------------------------------------------------------------
class FakeGitHub:
    def __init__(self):
        self.files: dict[str, bytes] = {}
        self.releases: list[dict] = []
        self.requests: list[str] = []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):  # still
                pass

            def do_GET(self):  # noqa: N802
                outer.requests.append(self.path)
                if self.path.startswith("/api/releases"):
                    body = json.dumps(outer.releases).encode()
                    self._send(200, body, "application/json")
                elif self.path.startswith("/weiter/"):
                    self.send_response(302)
                    self.send_header("Location", "/files/" + self.path.split("/", 2)[2])
                    self.end_headers()
                elif self.path.startswith("/files/") and self.path[7:] in outer.files:
                    self._send(200, outer.files[self.path[7:]], "application/octet-stream")
                else:
                    self._send(404, b"nicht gefunden", "text/plain")

            def _send(self, code, body, ctype):
                self.send_response(code)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def add_release(self, tag, files: dict[str, bytes], *, with_digest=True, pre=False, sums=True):
        assets = []
        for name, data in files.items():
            self.files[name] = data
            a = {"name": name, "browser_download_url": f"{self.url}/weiter/{name}", "size": len(data)}
            if with_digest:
                a["digest"] = "sha256:" + hashlib.sha256(data).hexdigest()
            assets.append(a)
        if sums:
            text = "".join(f"{hashlib.sha256(d).hexdigest()}  {n}\n" for n, d in files.items()).encode()
            self.files["SHA256SUMS.txt"] = text
            assets.append({"name": "SHA256SUMS.txt", "browser_download_url": f"{self.url}/files/SHA256SUMS.txt",
                           "size": len(text)})
        self.releases.insert(0, {**_raw(tag, pre=pre), "body": "## Neu\n\n- Test", "assets": assets})

    def close(self):
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture
def github():
    server = FakeGitHub()
    yield server
    server.close()


def test_fetch_download_and_verify(github, tmp_path):
    payload = os.urandom(300_000)
    github.add_release("v1.2.0", {"LaunchpadProTAB-Setup-1.2.0.exe": payload}, with_digest=False)
    rels = releases.fetch_releases(github.url + "/api/releases")
    rel = pick_update(rels, "1.1.0")
    asset = rel.asset(install.WINDOWS_ASSET)
    # Ohne GitHub-Digest: Prüfsumme aus SHA256SUMS.txt
    checksum = releases.resolve_checksum(rel, asset)
    assert checksum == hashlib.sha256(payload).hexdigest()
    seen = []
    target = download(asset.url, tmp_path / asset.name, sha256=checksum, size=asset.size,
                      progress=lambda d, t: seen.append((d, t)))
    assert target.read_bytes() == payload
    assert seen[-1] == (len(payload), len(payload))
    assert not list(tmp_path.glob("*.part"))


def test_download_rejects_bad_checksum_and_cancel(github, tmp_path):
    github.add_release("v1.2.0", {"LaunchpadProTAB-Setup-1.2.0.exe": b"x" * 5000})
    url = github.url + "/files/LaunchpadProTAB-Setup-1.2.0.exe"
    with pytest.raises(ChecksumError):
        download(url, tmp_path / "setup.exe", sha256="0" * 64)
    with pytest.raises(ChecksumError):                  # ohne Prüfsumme wird nichts geladen
        download(url, tmp_path / "setup.exe", sha256=None)
    stop = threading.Event()
    stop.set()
    with pytest.raises(DownloadCancelled):
        download(url, tmp_path / "setup.exe", sha256="0" * 64, cancel=stop)
    assert list(tmp_path.iterdir()) == []               # nichts Halbfertiges liegt herum


def test_network_errors_are_readable(github):
    with pytest.raises(NetworkError, match="Keine veröffentlichten Versionen"):
        releases.fetch_releases(github.url + "/gibt-es-nicht")
    with pytest.raises(NetworkError):
        releases.fetch_releases("http://127.0.0.1:9/nichts")      # Port 9: niemand hört zu


# ---------------------------------------------------------------------------
# Installationsart & Windows-Installer
# ---------------------------------------------------------------------------
def test_detect_install_kind(tmp_path):
    assert install.detect_install_kind(frozen=False) is InstallKind.SOURCE
    assert install.detect_install_kind(frozen=True, platform_name="win32", directory=tmp_path) is InstallKind.WINDOWS_PORTABLE
    (tmp_path / "unins000.exe").write_bytes(b"")
    assert install.detect_install_kind(frozen=True, platform_name="win32", directory=tmp_path) is InstallKind.WINDOWS_INSTALLER
    import platform
    if platform.machine().lower() in ("x86_64", "amd64"):
        assert install.detect_install_kind(frozen=True, platform_name="linux", directory=tmp_path) is InstallKind.LINUX_BUNDLE
    assert install.detect_install_kind(frozen=True, platform_name="darwin", directory=tmp_path) is InstallKind.UNSUPPORTED


def test_windows_installer_arguments(tmp_path):
    args = install.windows_installer_args(wait_pid=4242, silent=True, restart=True,
                                          ready_file=tmp_path / "bereit.flag", log_file=tmp_path / "i.log")
    assert "/LPTABWAITPID=4242" in args and "/SILENT" in args and "/SUPPRESSMSGBOXES" in args
    assert f"/LPTABREADY={tmp_path / 'bereit.flag'}" in args
    assert "/LPTABRESTART=1" in args and any(a.startswith("/LOG=") for a in args)
    portable = install.windows_installer_args(wait_pid=1, silent=False, restart=False)
    assert "/SILENT" not in portable and "/LPTABRESTART=1" not in portable


def test_installer_script_matches_program():
    """Mutex, AppUserModelID und Parameter im Inno-Skript passen zum Programm."""
    from launchpad_pro_tab.system import integration

    iss = (ROOT / "packaging" / "windows" / "LaunchpadProTAB.iss").read_text(encoding="utf-8")
    assert f'#define AppMutexName "{integration.MUTEX_NAME}"' in iss
    assert f'#define AppUserModelId "{integration.APP_USER_MODEL_ID}"' in iss
    for param in ("LPTABWAITPID", "LPTABRESTART", "LPTABPURGE", "LPTABREADY"):
        assert f"{{param:{param}|" in iss
    assert "--purge-user-data --yes" in iss
    assert "OutputBaseFilename=LaunchpadProTAB-Setup-{#AppVersion}" in iss
    assert "DefaultDirName={autopf}\\" in iss                      # C:\Program Files


def test_wait_for_pid():
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(0.4)"])
    assert install.wait_for_pid(proc.pid, timeout=10)
    proc.wait()
    assert install.wait_for_pid(proc.pid, timeout=1)


# ---------------------------------------------------------------------------
# Linux: Programmordner austauschen
# ---------------------------------------------------------------------------
def _fake_bundle_archive(path: Path, version: str, *, evil: bool = False) -> Path:
    marker = path.parent / "gestartet.txt"
    script = textwrap.dedent(f"""\
        #!/bin/sh
        echo "{version} $*" > "{marker}"
        """).encode()
    with tarfile.open(path, "w:gz") as tar:
        top = f"LaunchpadProTAB-{version}-linux-x86_64"
        for name, data, mode in ((f"{top}/LaunchpadProTAB", script, 0o755),
                                 (f"{top}/_internal/version.txt", version.encode(), 0o644),
                                 (f"{top}/install.sh", b"#!/bin/sh\n", 0o755)):
            info = tarfile.TarInfo(name)
            info.size, info.mode = len(data), mode
            tar.addfile(info, io.BytesIO(data))
        if evil:
            info = tarfile.TarInfo("../ausbruch.txt")
            info.size = 4
            tar.addfile(info, io.BytesIO(b"boom"))
    return path


def _installed(tmp_path: Path) -> Path:
    app = tmp_path / "launchpad-pro-tab"
    (app / "_internal").mkdir(parents=True)
    (app / "LaunchpadProTAB").write_text("#!/bin/sh\necho alt\n")
    (app / "LaunchpadProTAB").chmod(0o755)
    (app / "_internal" / "version.txt").write_text("1.1.0")
    (app / install.INSTALL_INFO).write_text("version=1.1.0\nfile=/tmp/x.desktop\n")
    return app


@pytest.mark.skipif(sys.platform == "win32", reason="Linux-Paket")
def test_linux_bundle_extract_and_swap(tmp_path):
    app = _installed(tmp_path)
    archive = _fake_bundle_archive(tmp_path / "paket.tar.gz", "1.2.0")
    new_root = install.extract_bundle(archive, tmp_path)
    assert new_root.name == "LaunchpadProTAB-1.2.0-linux-x86_64"
    old = install.swap_directories(app, new_root)
    assert (app / "_internal" / "version.txt").read_text() == "1.2.0"
    assert (app / install.INSTALL_INFO).read_text().startswith("version=1.1.0")   # Installationsdaten bleiben
    assert old.name.startswith(install.OLD_PREFIX) and (old / "_internal" / "version.txt").read_text() == "1.1.0"
    install.cleanup_previous(app)
    assert not old.exists()
    assert not [p for p in tmp_path.iterdir() if p.name.startswith(".launchpad-update-")]


@pytest.mark.skipif(sys.platform == "win32", reason="Linux-Paket")
def test_linux_bundle_rejects_unsafe_archive(tmp_path):
    archive = _fake_bundle_archive(tmp_path / "paket.tar.gz", "1.2.0", evil=True)
    target = tmp_path / "ziel"
    target.mkdir()
    with pytest.raises(Exception):
        install.extract_bundle(archive, target)
    assert not (tmp_path / "ausbruch.txt").exists()
    assert list(target.iterdir()) == []                      # Staging wieder aufgeräumt


@pytest.mark.skipif(sys.platform == "win32", reason="Linux-Paket")
def test_linux_finish_update_helper(tmp_path):
    """Hilfsprozess der neuen Version: wartet, tauscht den Ordner und startet neu (execv)."""
    app = _installed(tmp_path)
    archive = _fake_bundle_archive(tmp_path / "paket.tar.gz", "1.2.0")
    new_root = install.extract_bundle(archive, tmp_path)
    old_proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(0.5)"])
    code = textwrap.dedent(f"""
        import sys
        from pathlib import Path
        sys.path.insert(0, {str(ROOT)!r})
        from launchpad_pro_tab.update import install
        install.app_dir = lambda: Path({str(new_root)!r})
        install.finish_linux_update(Path({str(app)!r}), {old_proc.pid}, ["--project", "/x/Show"])
    """)
    result = subprocess.run([sys.executable, "-c", code], timeout=60)
    old_proc.wait()
    assert result.returncode == 0
    assert (tmp_path / "gestartet.txt").read_text().strip() == "1.2.0 --project /x/Show"
    assert (app / "_internal" / "version.txt").read_text() == "1.2.0"
    assert not new_root.parent.exists()                      # Staging-Ordner entfernt


# ---------------------------------------------------------------------------
# UpdateController (QML-Schnittstelle)
# ---------------------------------------------------------------------------
def test_update_controller_flow(qapp, github, tmp_path, monkeypatch):
    from launchpad_pro_tab import __version__
    from launchpad_pro_tab.bridge.tasks import TaskRunner
    from launchpad_pro_tab.bridge.updater import UpdateController
    from launchpad_pro_tab.core.settings import AppSettings

    archive = _fake_bundle_archive(tmp_path / "LaunchpadProTAB-9.0.0-linux-x86_64.tar.gz", "9.0.0")
    github.add_release("v9.0.0", {archive.name: archive.read_bytes()})
    monkeypatch.setenv("LPTAB_UPDATE_URL", github.url + "/api/releases")
    install_dir = _installed(tmp_path / "prog")
    monkeypatch.setattr(install, "app_dir", lambda: install_dir)
    spawned = []
    monkeypatch.setattr(install, "spawn_detached", lambda cmd: spawned.append(cmd))

    settings = AppSettings.load(tmp_path / "einstellungen.json")
    runner = TaskRunner(use_processes=False)
    upd = UpdateController(runner, settings, kind=InstallKind.LINUX_BUNDLE)
    found, quit_ = [], []
    upd.updateFound.connect(found.append)
    upd.quitRequested.connect(lambda: quit_.append(True))
    prepared = []
    upd.prepare_hook = lambda: prepared.append(True) or True
    upd.project_hook = lambda: "/x/Show"
    try:
        upd.check(False)
        assert wait_until(qapp, lambda: upd.state == "available", 10), upd.message
        assert found == ["9.0.0"] and upd.latestVersion == "9.0.0" and upd.canInstall
        assert upd.currentVersion == __version__ and "Neu" in upd.releaseNotes
        assert settings.update_last_check

        # Überspringen -> automatische Prüfung schweigt, manuelle zeigt die Version wieder
        upd.skipVersion()
        assert settings.update_skipped == "9.0.0" and not upd.available
        upd.check(False)
        assert wait_until(qapp, lambda: upd.state == "uptodate", 10)
        upd.checkNow()
        assert wait_until(qapp, lambda: upd.state == "available", 10)

        # Aktualisieren: Download + Prüfung + Entpacken + Hilfsprozess + Beenden
        upd.startUpdate()
        assert wait_until(qapp, lambda: quit_ or upd.state == "error", 20), upd.message
        assert quit_ and prepared, upd.message
        cmd = spawned[-1]
        assert cmd[1] == "--finish-update" and cmd[2] == str(install_dir)
        assert cmd[cmd.index("--") + 1:] == ["--project", "/x/Show"]
        assert Path(cmd[0]).is_file()                     # neue Version liegt entpackt bereit
    finally:
        upd.shutdown()
        runner.shutdown()


class _FakeInstallerProcess:
    def __init__(self):
        self.returncode = None

    def poll(self):
        return self.returncode


@pytest.mark.parametrize("uac_approved", [True, False])
def test_update_controller_windows_waits_for_elevated_installer(qapp, github, tmp_path, monkeypatch, uac_approved):
    """Windows: erst beenden, wenn der Installer mit Adminrechten läuft; bei Abbruch weiterlaufen."""
    from launchpad_pro_tab.bridge.tasks import TaskRunner
    from launchpad_pro_tab.bridge.updater import UpdateController
    from launchpad_pro_tab.core.settings import AppSettings

    github.add_release("v9.0.0", {"LaunchpadProTAB-Setup-9.0.0.exe": b"MZ" + os.urandom(20_000)})
    monkeypatch.setenv("LPTAB_UPDATE_URL", github.url + "/api/releases")
    started, fake = [], _FakeInstallerProcess()

    def fake_start(setup, args):
        started.append((Path(setup), args))
        return fake

    monkeypatch.setattr(install, "start_windows_installer", fake_start)
    runner = TaskRunner(use_processes=False)
    upd = UpdateController(runner, AppSettings.load(tmp_path / "e.json"), kind=InstallKind.WINDOWS_INSTALLER)
    quit_, resumed = [], []
    upd.quitRequested.connect(lambda: quit_.append(True))
    upd.prepare_hook = lambda: True
    upd.resume_hook = lambda: resumed.append(True)
    try:
        upd.check(False)
        assert wait_until(qapp, lambda: upd.state == "available", 10), upd.message
        upd.startUpdate()
        assert wait_until(qapp, lambda: started, 20), upd.message
        setup, args = started[0]
        assert setup.read_bytes().startswith(b"MZ")                        # geprüfter Download
        ready = Path(next(a for a in args if a.startswith("/LPTABREADY=")).split("=", 1)[1])
        wait_until(qapp, lambda: False, 0.6)
        assert upd.state == "installing" and not quit_                     # wartet auf die Sicherheitsabfrage
        if uac_approved:
            ready.write_text("bereit")                                     # Setup läuft mit Adminrechten
            assert wait_until(qapp, lambda: quit_, 5)
            assert not ready.exists() and not resumed
        else:
            fake.returncode = 2                                            # Abfrage abgelehnt
            assert wait_until(qapp, lambda: upd.state == "error", 5)
            assert resumed and not quit_
            assert "Sicherheitsabfrage" in upd.message
    finally:
        upd.shutdown()
        runner.shutdown()


def test_update_controller_offline_is_silent(qapp, tmp_path, monkeypatch):
    from launchpad_pro_tab.bridge.tasks import TaskRunner
    from launchpad_pro_tab.bridge.updater import UpdateController
    from launchpad_pro_tab.core.settings import AppSettings

    monkeypatch.setenv("LPTAB_UPDATE_URL", "http://127.0.0.1:9/nichts")
    runner = TaskRunner(use_processes=False)
    upd = UpdateController(runner, AppSettings.load(tmp_path / "e.json"), kind=InstallKind.WINDOWS_INSTALLER)
    try:
        upd.check(False)                        # automatisch: kein Fehler anzeigen
        assert wait_until(qapp, lambda: upd.state == "idle", 10)
        assert upd.message == ""
        upd.checkNow()                          # manuell: verständliche Meldung
        assert wait_until(qapp, lambda: upd.state == "error", 10)
        assert "Verbindung" in upd.message or "Zeitüberschreitung" in upd.message
    finally:
        upd.shutdown()
        runner.shutdown()
