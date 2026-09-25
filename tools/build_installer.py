"""Baut den Windows-Installer (Inno Setup 7) aus dem PyInstaller-Programmordner.

    pyinstaller packaging/launchpad_pro_tab.spec --noconfirm   # erzeugt dist/LaunchpadProTAB/
    python tools/build_installer.py                            # erzeugt dist/LaunchpadProTAB-Setup-<version>.exe

ISCC wird gesucht über die Umgebungsvariable ``ISCC`` (darf auch einen Befehl mit Argumenten
enthalten, z. B. ``wine C:\\InnoSetup\\ISCC.exe``), den Suchpfad und die üblichen
Installationsordner von Inno Setup 7.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

ISS = ROOT / "packaging" / "windows" / "LaunchpadProTAB.iss"


def find_iscc() -> list[str]:
    env = os.environ.get("ISCC")
    if env:
        return shlex.split(env, posix=(os.name != "nt"))
    found = shutil.which("ISCC") or shutil.which("iscc")
    if found:
        return [found]
    for base in (os.environ.get("ProgramFiles", r"C:\Program Files"),
                 os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
                 os.environ.get("LOCALAPPDATA", "") + r"\Programs"):
        for name in ("Inno Setup 7", "Inno Setup 8"):
            candidate = Path(base) / name / "ISCC.exe"
            if candidate.is_file():
                return [str(candidate)]
    raise SystemExit("ISCC (Inno Setup 7) nicht gefunden – bitte installieren oder ISCC=… setzen.")


def tool_path(path: Path, iscc: list[str]) -> str:
    """Pfad so, wie ISCC ihn versteht (unter Wine: Windows-Pfad)."""
    if os.name != "nt" and iscc and Path(iscc[0]).name.startswith("wine"):
        return subprocess.run(["winepath", "-w", str(path)], check=True, capture_output=True,
                              text=True).stdout.strip()
    return str(path)


def numeric_version(version: str) -> str:
    m = re.match(r"^\s*v?(\d+)(?:\.(\d+))?(?:\.(\d+))?", version)
    if not m:
        raise SystemExit(f"Ungültige Versionsnummer: {version}")
    return ".".join(g or "0" for g in m.groups())


def main() -> int:
    from launchpad_pro_tab import __version__

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", default=__version__, help="Versionsnummer (Standard: aus dem Programm)")
    ap.add_argument("--source", type=Path, default=ROOT / "dist" / "LaunchpadProTAB",
                    help="Programmordner aus dem PyInstaller-Build")
    ap.add_argument("--output", type=Path, default=ROOT / "dist", help="Zielordner für den Installer")
    args = ap.parse_args()

    exe = args.source / "LaunchpadProTAB.exe"
    if not exe.is_file():
        raise SystemExit(f"{exe} fehlt – zuerst PyInstaller ausführen.")
    args.output.mkdir(parents=True, exist_ok=True)
    iscc = find_iscc()
    cmd = [
        *iscc,
        f"/DAppVersion={args.version}",
        f"/DAppVersionNumeric={numeric_version(args.version)}",
        f"/DSourceDir={tool_path(args.source.resolve(), iscc)}",
        f"/DOutputDir={tool_path(args.output.resolve(), iscc)}",
        tool_path(ISS, iscc),
    ]
    print("»", " ".join(cmd), flush=True)
    rc = subprocess.run(cmd).returncode
    if rc != 0:
        return rc
    setup = args.output / f"LaunchpadProTAB-Setup-{args.version}.exe"
    if not setup.is_file():
        print(f"Installer nicht gefunden: {setup}", file=sys.stderr)
        return 1
    digest = hashlib.sha256(setup.read_bytes()).hexdigest()
    print(f"Installer: {setup}  ({setup.stat().st_size / 1e6:.1f} MB)\nSHA-256:   {digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
