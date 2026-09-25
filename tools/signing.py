"""Hilfsmittel für die digitale Signatur der Windows-Programmdateien (Authenticode).

Ablauf im Release-Workflow (siehe .github/workflows/build.yml):

    python tools/build_installer.py --signed-uninstaller-dir build/inno-signiert   # 1. Durchlauf, Code 3
    python tools/signing.py sammeln --programm dist/LaunchpadProTAB \\
        --inno build/inno-signiert --ziel build/zu-signieren --liste build/signieren.json
    … Ordner build/zu-signieren signieren lassen (SignPath) → build/signiert …
    python tools/signing.py einsetzen --quelle build/signiert --liste build/signieren.json
    python tools/build_installer.py --signed-uninstaller-dir build/inno-signiert   # 2. Durchlauf
    … Setup.exe signieren lassen …
    python tools/signing.py pruefen --programm dist/LaunchpadProTAB --setup dist/LaunchpadProTAB-Setup-*.exe

``sammeln`` legt alle *unsignierten* PE-Dateien (EXE/DLL/PYD) flach und durchnummeriert ab
(``0001.dll``, ``0002.exe`` …) – so braucht die Signatur-Konfiguration nur zwei Muster und kennt
keine Pfade. Bereits signierte Dateien (Qt, Python, Microsoft-Laufzeit) behalten ihre Signatur.
Die Zuordnung zu den Originalpfaden steht in der JSON-Liste (bleibt auf dem Build-Rechner).

Die Signaturprüfung hier ist rein strukturell (Zertifikatstabelle im PE-Kopf vorhanden); ob die
Signatur gültig und vertrauenswürdig ist, prüft der Workflow unter Windows mit
``Get-AuthenticodeSignature``.
"""

from __future__ import annotations

import argparse
import glob
import json
import shutil
import struct
import sys
from pathlib import Path

PE_SUFFIXES = (".exe", ".dll", ".pyd")
OWN_FILES = ("LaunchpadProTAB.exe",)       # mit --nur-eigene nur diese (plus Inno-Dateien)


def pe_signature_size(path: Path) -> int | None:
    """Größe der Authenticode-Zertifikatstabelle; 0 = unsigniert, None = keine PE-Datei."""
    try:
        with open(path, "rb") as f:
            head = f.read(4096)
    except OSError:
        return None
    if len(head) < 0x40 or head[:2] != b"MZ":
        return None
    pe = struct.unpack_from("<I", head, 0x3C)[0]
    if pe + 24 + 2 > len(head) or head[pe:pe + 4] != b"PE\0\0":
        return None
    magic = struct.unpack_from("<H", head, pe + 24)[0]
    if magic == 0x10B:            # PE32
        dirs = pe + 24 + 96
    elif magic == 0x20B:          # PE32+
        dirs = pe + 24 + 112
    else:
        return None
    if dirs + 5 * 8 > len(head):
        return None
    _offset, size = struct.unpack_from("<II", head, dirs + 4 * 8)   # Eintrag 4: Sicherheit
    return size


def is_signed(path: Path) -> bool:
    return bool(pe_signature_size(path))


def unsigned_program_files(program: Path, *, own_only: bool = False) -> list[Path]:
    files = []
    for path in sorted(program.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in PE_SUFFIXES:
            continue
        if own_only and path.name not in OWN_FILES:
            continue
        if pe_signature_size(path) == 0:
            files.append(path)
    return files


def collect(program: Path, inno: Path | None, target: Path, listing: Path, *, own_only: bool = False) -> int:
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)
    entries = []
    sources = unsigned_program_files(program, own_only=own_only)
    if inno is not None and inno.is_dir():
        sources += [p for p in sorted(inno.glob("uninst-*.e*")) if pe_signature_size(p) == 0]
    for number, source in enumerate(sources, 1):
        suffix = ".dll" if source.suffix.lower() in (".dll", ".pyd") else ".exe"
        name = f"{number:04d}{suffix}"
        shutil.copy2(source, target / name)
        entries.append({"datei": name, "original": str(source.resolve())})
    listing.parent.mkdir(parents=True, exist_ok=True)
    listing.write_text(json.dumps(entries, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"{len(entries)} Datei(en) zum Signieren nach {target} gelegt (Liste: {listing}).")
    for entry in entries:
        print(f"  {entry['datei']}  ←  {entry['original']}")
    return 0


def apply(source: Path, listing: Path) -> int:
    entries = json.loads(listing.read_text(encoding="utf-8"))
    problems = []
    for entry in entries:
        signed = source / entry["datei"]
        original = Path(entry["original"])
        if not signed.is_file():
            problems.append(f"fehlt im signierten Ergebnis: {entry['datei']} ({original.name})")
            continue
        if not is_signed(signed):
            problems.append(f"nicht signiert: {entry['datei']} ({original.name})")
            continue
        shutil.copyfile(signed, original)
    if problems:
        print("Signierte Dateien unvollständig:\n  " + "\n  ".join(problems), file=sys.stderr)
        return 1
    print(f"{len(entries)} signierte Datei(en) eingesetzt.")
    return 0


def verify(program: Path | None, setups: list[Path], *, own_only: bool = False) -> int:
    missing = []
    if program is not None:
        missing += [str(p) for p in unsigned_program_files(program, own_only=own_only)]
    missing += [str(p) for p in setups if not is_signed(p)]
    if missing:
        print("Ohne Signatur:\n  " + "\n  ".join(missing), file=sys.stderr)
        return 1
    print("Alle geprüften Programmdateien tragen eine Signatur.")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="befehl", required=True)
    s = sub.add_parser("sammeln", help="unsignierte Dateien zum Signieren ablegen")
    s.add_argument("--programm", type=Path, required=True, help="PyInstaller-Programmordner")
    s.add_argument("--inno", type=Path, help="Ordner mit uninst-*.e64 (Inno SignedUninstallerDir)")
    s.add_argument("--ziel", type=Path, required=True, help="Ordner, der signiert wird")
    s.add_argument("--liste", type=Path, required=True, help="JSON-Zuordnung (Ergebnis)")
    s.add_argument("--nur-eigene", action="store_true", help="nur LaunchpadProTAB.exe (plus Inno-Dateien)")
    e = sub.add_parser("einsetzen", help="signierte Dateien an ihre Originalorte zurücklegen")
    e.add_argument("--quelle", type=Path, required=True, help="Ordner mit den signierten Dateien")
    e.add_argument("--liste", type=Path, required=True, help="JSON-Zuordnung aus „sammeln“")
    p = sub.add_parser("pruefen", help="prüfen, dass alles signiert ist")
    p.add_argument("--programm", type=Path, help="Programmordner")
    p.add_argument("--setup", nargs="*", default=[], help="Installer-Dateien (Platzhalter erlaubt)")
    p.add_argument("--nur-eigene", action="store_true")
    args = ap.parse_args(argv)

    if args.befehl == "sammeln":
        return collect(args.programm, args.inno, args.ziel, args.liste, own_only=args.nur_eigene)
    if args.befehl == "einsetzen":
        return apply(args.quelle, args.liste)
    setups = [Path(m) for pattern in args.setup for m in sorted(glob.glob(pattern))]
    if args.setup and not setups:
        print("Keine Installer-Datei gefunden: " + " ".join(args.setup), file=sys.stderr)
        return 1
    return verify(args.programm, setups, own_only=args.nur_eigene)


if __name__ == "__main__":
    sys.exit(main())
