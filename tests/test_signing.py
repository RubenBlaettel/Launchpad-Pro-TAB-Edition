"""Signier-Hilfsmittel (tools/signing.py): unsignierte Windows-Dateien sammeln, signiert
zurücklegen und prüfen – mit künstlichen PE-Dateien, ohne Windows und ohne Zertifikat."""

from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

from conftest import ROOT

sys.path.insert(0, str(ROOT / "tools"))

import signing  # noqa: E402


def _pe(path: Path, *, signed: bool = False, pe32plus: bool = True) -> Path:
    """Minimale PE-Datei; „signiert“ = Eintrag der Zertifikatstabelle gesetzt + Daten angehängt."""
    e_lfanew = 0x80
    opt = 0x20B if pe32plus else 0x10B
    dirs = e_lfanew + 24 + (112 if pe32plus else 96)
    data = bytearray(dirs + 16 * 8)
    data[:2] = b"MZ"
    struct.pack_into("<I", data, 0x3C, e_lfanew)
    data[e_lfanew:e_lfanew + 4] = b"PE\0\0"
    struct.pack_into("<H", data, e_lfanew + 24, opt)
    if signed:
        struct.pack_into("<II", data, dirs + 4 * 8, len(data), 64)
        data += b"\x30" * 64
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(bytes(data))
    return path


def _sign(path: Path) -> None:
    raw = path.read_bytes()
    _pe(path, signed=True, pe32plus=struct.unpack_from("<H", raw, 0x80 + 24)[0] == 0x20B)


def test_signature_detection(tmp_path):
    assert signing.pe_signature_size(_pe(tmp_path / "a.exe")) == 0
    assert signing.pe_signature_size(_pe(tmp_path / "b.dll", signed=True)) == 64
    assert signing.pe_signature_size(_pe(tmp_path / "c.dll", pe32plus=False, signed=True)) == 64
    (tmp_path / "text.exe").write_text("kein Programm")
    assert signing.pe_signature_size(tmp_path / "text.exe") is None
    assert signing.pe_signature_size(tmp_path / "fehlt.exe") is None


def test_collect_sign_apply_verify(tmp_path):
    prog = tmp_path / "LaunchpadProTAB"
    _pe(prog / "LaunchpadProTAB.exe")
    _pe(prog / "_internal" / "numpy" / "core.pyd")
    _pe(prog / "_internal" / "Qt6Core.dll", signed=True)          # Herstellersignatur bleibt
    (prog / "_internal" / "daten.txt").write_text("x")
    inno = tmp_path / "inno"
    _pe(inno / "uninst-7.1.0-abcdef1234.e64")
    target, listing = tmp_path / "zu-signieren", tmp_path / "liste.json"

    assert signing.main(["pruefen", "--programm", str(prog)]) == 1
    assert signing.main(["sammeln", "--programm", str(prog), "--inno", str(inno),
                         "--ziel", str(target), "--liste", str(listing)]) == 0
    entries = json.loads(listing.read_text(encoding="utf-8"))
    assert [e["datei"] for e in entries] == ["0001.exe", "0002.dll", "0003.exe"]
    assert [Path(e["original"]).name for e in entries] == ["LaunchpadProTAB.exe", "core.pyd",
                                                            "uninst-7.1.0-abcdef1234.e64"]
    assert sorted(p.name for p in target.iterdir()) == ["0001.exe", "0002.dll", "0003.exe"]

    # Unvollständiges Ergebnis wird abgelehnt, nichts wird überschrieben
    signed = tmp_path / "signiert"
    signed.mkdir()
    for name in ("0001.exe", "0002.dll"):
        (signed / name).write_bytes((target / name).read_bytes())
        _sign(signed / name)
    assert signing.main(["einsetzen", "--quelle", str(signed), "--liste", str(listing)]) == 1

    (signed / "0003.exe").write_bytes((target / "0003.exe").read_bytes())
    _sign(signed / "0003.exe")
    assert signing.main(["einsetzen", "--quelle", str(signed), "--liste", str(listing)]) == 0
    assert signing.is_signed(prog / "LaunchpadProTAB.exe")
    assert signing.is_signed(prog / "_internal" / "numpy" / "core.pyd")
    assert signing.is_signed(inno / "uninst-7.1.0-abcdef1234.e64")
    assert signing.main(["pruefen", "--programm", str(prog)]) == 0

    setup = _pe(tmp_path / "dist" / "LaunchpadProTAB-Setup-9.9.9.exe")
    pattern = str(tmp_path / "dist" / "LaunchpadProTAB-Setup-*.exe")
    assert signing.main(["pruefen", "--setup", pattern]) == 1
    _sign(setup)
    assert signing.main(["pruefen", "--programm", str(prog), "--setup", pattern]) == 0
    assert signing.main(["pruefen", "--setup", str(tmp_path / "gibt-es-nicht-*.exe")]) == 1


def test_collect_only_own_files(tmp_path):
    prog = tmp_path / "LaunchpadProTAB"
    _pe(prog / "LaunchpadProTAB.exe")
    _pe(prog / "_internal" / "fremd.dll")
    listing = tmp_path / "liste.json"
    assert signing.main(["sammeln", "--programm", str(prog), "--ziel", str(tmp_path / "z"),
                         "--liste", str(listing), "--nur-eigene"]) == 0
    entries = json.loads(listing.read_text(encoding="utf-8"))
    assert [Path(e["original"]).name for e in entries] == ["LaunchpadProTAB.exe"]
    assert signing.main(["pruefen", "--programm", str(prog), "--nur-eigene"]) == 1


def test_signpath_configuration_matches_collected_names():
    """Die SignPath-Konfiguration signiert genau die Dateitypen, die „sammeln“ ablegt."""
    xml = (ROOT / "packaging" / "signpath" / "artifact-configuration.xml").read_text(encoding="utf-8")
    assert '<include path="*.exe"' in xml and '<include path="*.dll"' in xml
    assert "<authenticode-sign" in xml
    workflow = (ROOT / ".github" / "workflows" / "build.yml").read_text(encoding="utf-8")
    assert "signpath/github-action-submit-signing-request" in workflow
    assert "--signed-uninstaller-dir build/inno-signiert" in workflow
