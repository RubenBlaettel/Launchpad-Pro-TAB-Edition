"""Screenshots des Windows-Installers für die README (unter Linux mit Wine).

Voraussetzungen (Ubuntu): ``wine64 wine32:i386 xvfb xdotool imagemagick`` und Inno Setup 7
in einem Wine-Präfix (siehe CLAUDE.md, Abschnitt „Windows-Installer unter Linux testen“).

    WINEPREFIX=~/.wine-inno python tools/make_installer_screenshots.py dist/LaunchpadProTAB-Setup-1.1.0.exe

Der Installer wird in einer eigenen Xvfb-Anzeige durchgeklickt (Installation, erneuter Start
mit Wartungsseite, Deinstallation mit Lösch-Abfrage); die Bilder landen in
``docs/images/installer/``. Hinweis: Wine zeichnet mit eigenen Schriftarten – unter Windows 11
sieht der Assistent etwas moderner aus, Inhalt und Ablauf sind identisch.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "images" / "installer"
DISPLAY = ":58"


class Wizard:
    def __init__(self, setup: Path):
        self.setup = setup
        self.env = dict(os.environ, WINEDEBUG="-all", DISPLAY=DISPLAY)

    def xdo(self, *args: str) -> str:
        return subprocess.run(["xdotool", *args], env=self.env, capture_output=True, text=True).stdout.strip()

    def window(self, title: str, timeout: float = 40) -> str:
        end = time.time() + timeout
        while time.time() < end:
            ids = [i for i in self.xdo("search", "--name", title).split() if i]
            if ids:
                return ids[-1]
            time.sleep(0.3)
        raise SystemExit(f"Fenster „{title}“ nicht gefunden")

    def shot(self, win: str, name: str) -> None:
        time.sleep(1.2)
        subprocess.run(["import", "-window", win, str(OUT / name)], env=self.env, check=True)
        print("gespeichert:", OUT / name)

    def key(self, win: str, *keys: str) -> None:
        self.xdo("windowactivate", "--sync", win)
        for k in keys:
            self.xdo("key", "--window", win, k)
            time.sleep(0.5)

    def run(self, *args: str) -> subprocess.Popen:
        return subprocess.Popen(["wine", str(self.setup), *args], env=self.env)

    def wait_for_log(self, log: Path, text: str, timeout: float = 600) -> None:
        end = time.time() + timeout
        while time.time() < end:
            if log.exists() and text in log.read_text(encoding="utf-8", errors="replace"):
                return
            time.sleep(1)
        raise SystemExit(f"„{text}“ erscheint nicht in {log}")


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    OUT.mkdir(parents=True, exist_ok=True)
    xvfb = subprocess.Popen(["Xvfb", DISPLAY, "-screen", "0", "1280x900x24"])
    time.sleep(1.5)
    wiz = Wizard(Path(sys.argv[1]).resolve())
    try:
        # Erstinstallation (das Protokoll zeigt, wann alle Dateien kopiert sind)
        log = Path(os.environ.get("WINEPREFIX", str(Path.home() / ".wine"))) / "drive_c" / "lptab-screenshots.log"
        log.unlink(missing_ok=True)
        proc = wiz.run("/LOG=C:\\lptab-screenshots.log")
        w = wiz.window("Launchpad Pro")
        wiz.shot(w, "1_willkommen.png"); wiz.key(w, "Return")
        wiz.shot(w, "2_zielordner.png"); wiz.key(w, "Return")
        wiz.shot(w, "3_aufgaben.png"); wiz.key(w, "Return")
        wiz.shot(w, "4_bereit.png"); wiz.key(w, "Return")
        wiz.wait_for_log(log, "Installation process succeeded")
        time.sleep(2)
        wiz.shot(w, "5_fertig.png")
        wiz.key(w, "space", "Return")                  # „starten“ abwählen, Fertigstellen
        proc.wait(timeout=60)

        # Erneuter Start: Wartungsseite -> Deinstallieren
        proc = wiz.run()
        w = wiz.window("Launchpad Pro")
        wiz.key(w, "Return")
        wiz.shot(w, "6_wartung.png")
        wiz.key(w, "Down")
        wiz.key(w, "Return")                           # startet den Deinstaller
        u = wiz.window("deinstallieren")
        wiz.shot(u, "7_deinstallieren.png")
        wiz.key(u, "Return")
        c = wiz.window("entfernen")
        wiz.shot(c, "8_bestaetigen.png")
        wiz.key(c, "j")
        time.sleep(6)
        done = wiz.window("entfernen")
        wiz.key(done, "Return")
    finally:
        subprocess.run(["wineserver", "-k"], env=wiz.env)
        xvfb.terminate()
    return 0


if __name__ == "__main__":
    sys.exit(main())
