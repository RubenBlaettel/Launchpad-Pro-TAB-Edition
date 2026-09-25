"""Baut das Linux-Programmpaket (``.tar.gz``) aus dem PyInstaller-Programmordner.

    pyinstaller packaging/launchpad_pro_tab.spec --noconfirm   # erzeugt dist/LaunchpadProTAB/
    python tools/build_linux_package.py                        # erzeugt dist/LaunchpadProTAB-<version>-linux-x86_64.tar.gz

Das Archiv enthält den Programmordner samt ``install.sh`` (Installation mit Menüeintrag,
Desktop-Verknüpfung und Dateizuordnung) und ``LIESMICH.txt``. Die Update-Funktion des
Programms lädt genau dieses Archiv aus den GitHub-Releases.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

README = """Launchpad Pro TAB Edition {version} – Linux
==========================================

Installieren (für den aktuellen Benutzer, ohne Administratorrechte):

    ./install.sh

Der Assistent fragt nach dem Installationsordner (Standard: ~/.local/share/launchpad-pro-tab)
und ob ein Eintrag im Anwendungsmenü, eine Desktop-Verknüpfung und die Zuordnung für
Projektdateien (.lptab) angelegt werden sollen.

Ohne Installation starten:  ./LaunchpadProTAB
Deinstallieren:             <Installationsordner>/uninstall.sh

Updates: Das Programm prüft beim Start, ob auf GitHub eine neue Version bereitsteht, und
installiert sie auf Wunsch automatisch.

Benötigt: Linux x86_64 mit glibc 2.35 oder neuer (z. B. Ubuntu 22.04, Debian 12, Fedora 36).
Falls die Oberfläche nicht startet: sudo apt install libxcb-cursor0 libxkbcommon-x11-0 libegl1
"""


def _normalize(info: tarfile.TarInfo) -> tarfile.TarInfo:
    info.uid = info.gid = 0
    info.uname = info.gname = ""
    return info


def main() -> int:
    from launchpad_pro_tab import __version__

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", default=__version__)
    ap.add_argument("--source", type=Path, default=ROOT / "dist" / "LaunchpadProTAB")
    ap.add_argument("--output", type=Path, default=ROOT / "dist")
    args = ap.parse_args()

    exe = args.source / "LaunchpadProTAB"
    if not exe.is_file():
        raise SystemExit(f"{exe} fehlt – zuerst PyInstaller (unter Linux) ausführen.")
    name = f"LaunchpadProTAB-{args.version}-linux-x86_64"
    staging = args.output / name
    if staging.exists():
        shutil.rmtree(staging)
    shutil.copytree(args.source, staging, symlinks=True)
    for script in ("install.sh", "uninstall.sh"):
        shutil.copy2(ROOT / "packaging" / "linux" / script, staging / script)
        (staging / script).chmod(0o755)
    (staging / "LIESMICH.txt").write_text(README.format(version=args.version), encoding="utf-8")

    archive = args.output / f"{name}.tar.gz"
    with tarfile.open(archive, "w:gz", compresslevel=9) as tar:
        tar.add(staging, arcname=name, filter=_normalize)
    shutil.rmtree(staging)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    print(f"Linux-Paket: {archive}  ({archive.stat().st_size / 1e6:.1f} MB)\nSHA-256:     {digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
