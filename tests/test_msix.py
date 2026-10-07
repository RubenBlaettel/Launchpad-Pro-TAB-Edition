"""Microsoft-Store-Paket (tools/build_msix.py): Version, Identität, Manifest, Paketordner.

Das eigentliche Packen (makeappx) und die Installation prüft das CI unter Windows
(tools/test_msix.ps1); hier geht es um alles, was ohne Windows SDK prüfbar ist.
"""

from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from conftest import ROOT

sys.path.insert(0, str(ROOT / "tools"))

import build_installer  # noqa: E402
import build_msix  # noqa: E402

NS = {
    "m": "http://schemas.microsoft.com/appx/manifest/foundation/windows10",
    "uap": "http://schemas.microsoft.com/appx/manifest/uap/windows10",
    "uap3": "http://schemas.microsoft.com/appx/manifest/uap/windows10/3",
    "desktop": "http://schemas.microsoft.com/appx/manifest/desktop/windows10",
    "rescap": "http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities",
}
STORE_IDENTITY = {
    "display_name": "Launchpad Pro TAB Edition",
    "identity_name": "12345RubenBlaettel.LaunchpadProTABEdition",
    "publisher": "CN=A1B2C3D4-E5F6-4711-8899-AABBCCDDEEFF",
    "publisher_display_name": "Ruben & TAB",
    "store_id": "9nblggh4nns1",
}


def _store_json(tmp_path: Path, **values) -> Path:
    path = tmp_path / "store.json"
    path.write_text(json.dumps(values), encoding="utf-8")
    return path


def _fake_program(tmp_path: Path) -> Path:
    src = tmp_path / "LaunchpadProTAB"
    (src / "_internal" / "PySide6").mkdir(parents=True)
    (src / "LaunchpadProTAB.exe").write_bytes(b"MZ")
    (src / "_internal" / "PySide6" / "Qt6Core.dll").write_bytes(b"MZ")
    (src / "LICENSE.txt").write_text("MIT", encoding="utf-8")
    return src


@pytest.mark.parametrize("version, expected", [
    ("1.2.0", "1.2.0.0"), ("v1.10.3", "1.10.3.0"), ("2.0", "2.0.0.0"),
    ("1.3.0-beta.1", None), ("1.3.0b1", None), ("unsinn", None),
])
def test_msix_version(version, expected):
    assert build_msix.msix_version(version) == expected


def test_msix_version_limit():
    with pytest.raises(build_msix.BuildError):
        build_msix.msix_version("1.70000.0")


def test_identity_from_partner_center(tmp_path):
    ident = build_msix.load_identity(_store_json(tmp_path, **STORE_IDENTITY))
    assert not ident["test"]
    assert ident["identity_name"] == STORE_IDENTITY["identity_name"]
    assert ident["publisher"] == STORE_IDENTITY["publisher"]


def test_identity_missing_needs_test_flag(tmp_path):
    path = _store_json(tmp_path, display_name="Launchpad Pro TAB Edition", identity_name="", publisher="")
    with pytest.raises(build_msix.BuildError, match="Partner Center"):
        build_msix.load_identity(path)
    ident = build_msix.load_identity(path, allow_test=True)
    assert ident["test"] and ident["publisher"] == build_msix.TEST_IDENTITY["publisher"]
    # Die Datei im Repository ist gültig (leer = Testpaket oder echte Werte)
    build_msix.load_identity(build_msix.STORE_JSON, allow_test=True)


@pytest.mark.parametrize("field, value", [
    ("identity_name", "Mit Leerzeichen"), ("identity_name", "ab"), ("publisher", "O=Kein CN"),
    ("publisher_display_name", ""),
])
def test_identity_validation(tmp_path, field, value):
    with pytest.raises(build_msix.BuildError):
        build_msix.load_identity(_store_json(tmp_path, **{**STORE_IDENTITY, field: value}))


def test_manifest(tmp_path):
    ident = build_msix.load_identity(_store_json(tmp_path, **STORE_IDENTITY))
    root = ET.fromstring(build_msix.render_manifest(ident, "1.2.0.0"))
    identity = root.find("m:Identity", NS).attrib
    assert identity == {"Name": STORE_IDENTITY["identity_name"], "Publisher": STORE_IDENTITY["publisher"],
                        "Version": "1.2.0.0", "ProcessorArchitecture": "x64"}
    assert root.findtext("m:Properties/m:PublisherDisplayName", namespaces=NS) == "Ruben & TAB"   # maskiert
    assert root.findtext("m:Properties/m:DisplayName", namespaces=NS) == "Launchpad Pro TAB Edition"
    app = root.find("m:Applications/m:Application", NS)
    assert app.get("Executable") == build_msix.EXE_NAME and app.get("EntryPoint") == "Windows.FullTrustApplication"
    assert root.find("m:Capabilities/rescap:Capability", NS).get("Name") == "runFullTrust"
    assert [e.text for e in app.iterfind(".//uap:FileType", NS)] == [".lptab"]
    assert app.find(".//desktop:ExecutionAlias", NS).get("Alias") == build_msix.EXE_NAME
    # Alle Bilder, auf die das Manifest verweist, legt build_msix an
    referenced = {v.split("\\")[-1] for el in root.iter() for k, v in el.attrib.items() if v.startswith("Assets\\")}
    referenced |= {el.text.split("\\")[-1] for el in root.iter() if (el.text or "").startswith("Assets\\")}
    assert referenced <= {name for name, *_ in build_msix.BASE_ASSETS}


def test_layout_without_sdk(qapp, tmp_path):
    from PySide6.QtGui import QImage

    src = _fake_program(tmp_path)
    store = _store_json(tmp_path, **STORE_IDENTITY)
    layout = build_msix.build(src, tmp_path / "out", store_json=store, pack=False, work_dir=tmp_path / "work")
    assert (layout / "LaunchpadProTAB.exe").is_file()
    assert (layout / "_internal" / "PySide6" / "Qt6Core.dll").is_file()
    root = ET.parse(layout / "AppxManifest.xml").getroot()
    assert root.find("m:Identity", NS).get("Version") == build_msix.msix_version(build_msix.__version__)
    for name, width, height, _share in build_msix.BASE_ASSETS:
        img = QImage(str(layout / "Assets" / name))
        assert (img.width(), img.height()) == (width, height), name
        assert img.hasAlphaChannel()
    # Zweiter Lauf ersetzt den Paketordner vollständig
    (layout / "alt.txt").write_text("x", encoding="utf-8")
    build_msix.build(src, tmp_path / "out", store_json=store, pack=False, work_dir=tmp_path / "work")
    assert not (layout / "alt.txt").exists()


def test_variants_for_resources_pri(qapp, tmp_path):
    files = {p.name for p in build_msix.write_assets(tmp_path, variants=True)}
    assert "Square44x44Logo.targetsize-256_altform-unplated.png" in files
    assert "Wide310x150Logo.scale-200.png" in files
    assert {name for name, *_ in build_msix.BASE_ASSETS} <= files


def test_no_store_package_for_prereleases(tmp_path, monkeypatch):
    monkeypatch.setattr(build_msix, "__version__", "1.3.0-beta.1")
    assert build_msix.build(_fake_program(tmp_path), tmp_path / "out", pack=False) is None


def test_missing_program_folder(tmp_path):
    with pytest.raises(build_msix.BuildError, match="PyInstaller"):
        build_msix.build(tmp_path / "fehlt", tmp_path / "out", allow_test=True, pack=False,
                         work_dir=tmp_path / "work")


def test_installer_gets_store_id(tmp_path):
    assert build_installer.store_id(_store_json(tmp_path, **STORE_IDENTITY)) == "9NBLGGH4NNS1"
    assert build_installer.store_id(_store_json(tmp_path, store_id="")) is None
    assert build_installer.store_id(tmp_path / "fehlt.json") is None
    with pytest.raises(SystemExit):
        build_installer.store_id(_store_json(tmp_path, store_id="https://apps.microsoft.com/x"))


def test_ci_builds_and_tests_store_package():
    """Store-Paket entsteht aus den unveränderten Programmdateien – vor jeder Test-Signatur."""
    build = (ROOT / ".github" / "workflows" / "build.yml").read_text(encoding="utf-8")
    msix, signing = build.index("tools/build_msix.py"), build.index("Zu signierende Dateien sammeln")
    assert msix < signing
    assert "tools/test_msix.ps1" in build and "LaunchpadProTAB-Microsoft-Store" in build
    script = (ROOT / "tools" / "test_msix.ps1").read_bytes()
    assert script.isascii()          # Windows PowerShell 5.1 liest Skripte ohne BOM als ANSI
