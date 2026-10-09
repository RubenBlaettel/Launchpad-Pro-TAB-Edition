"""Baut das Microsoft-Store-Paket (MSIX) aus dem PyInstaller-Programmordner.

    pyinstaller packaging/launchpad_pro_tab.spec --noconfirm   # erzeugt dist/LaunchpadProTAB/
    python tools/build_msix.py                                 # erzeugt dist/LaunchpadProTAB-<version>.msix

Das Paket bleibt **unsigniert**: Der Microsoft Store signiert es nach der Zertifizierung mit
seinem eigenen Zertifikat – damit startet TAB Soundboard auch auf PCs mit der intelligenten
App-Steuerung von Windows 11. Zum Testen außerhalb des Stores signiert
``tools/test_msix.ps1`` eine Kopie mit einem Test-Zertifikat.

Die Paket-Identität (Name, Herausgeber) vergibt Partner Center beim Reservieren des App-Namens;
sie steht in ``packaging/msix/store.json`` (Anleitung: ``docs/MICROSOFT_STORE.md``). Solange sie
fehlt, entsteht mit ``--test-identity`` ein Testpaket, das der Store nicht annimmt.

Benötigt das Windows SDK (``makeappx.exe``, ``makepri.exe``) – auf den Windows-Runnern von GitHub
vorhanden. Gesucht wird über die Umgebungsvariablen ``MAKEAPPX``/``MAKEPRI``, den Suchpfad und
``C:\\Program Files (x86)\\Windows Kits\\10``. ``--no-pack`` legt nur den Paketordner an (ohne SDK).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from string import Template
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from launchpad_pro_tab import __app_name__, __version__  # noqa: E402

TEMPLATE = ROOT / "packaging" / "msix" / "AppxManifest.xml"
STORE_JSON = ROOT / "packaging" / "msix" / "store.json"
DESCRIPTION = "Touch-optimiertes Soundboard für den Theaterbetrieb"
EXE_NAME = "LaunchpadProTAB.exe"

# Nur für Tests außerhalb des Stores (CI-Installation mit Test-Zertifikat)
TEST_IDENTITY = {
    "identity_name": "TABTheater.LaunchpadProTAB.Test",
    "publisher": "CN=Launchpad Pro TAB Test",
    "publisher_display_name": "TAB Theater (Testpaket)",
}

# Bilder des Pakets: (Datei, Breite, Höhe, Anteil des Symbols an der Höhe)
BASE_ASSETS = [
    ("StoreLogo.png", 50, 50, 1.0),
    ("Square44x44Logo.png", 44, 44, 1.0),
    ("Square150x150Logo.png", 150, 150, 0.62),
    ("Wide310x150Logo.png", 310, 150, 0.62),
    ("FileLogo.png", 44, 44, 1.0),
]
# Zusätzliche Varianten, die Windows über resources.pri auswählt (nur mit makepri):
# scale-200 für hochauflösende Bildschirme, targetsize für Taskleiste/Startmenü/Explorer
# (altform-unplated = ohne farbige Hinterlegung)
TARGET_SIZES = (16, 24, 32, 48, 256)


class BuildError(Exception):
    pass


# ---------------------------------------------------------------------------
# Version und Identität
# ---------------------------------------------------------------------------
def msix_version(version: str) -> str | None:
    """``1.2.0`` -> ``1.2.0.0``. Vorabversionen (mit Buchstaben) gibt es im Store nicht -> ``None``.

    Der Store verlangt eine 0 an vierter Stelle; jede Stelle höchstens 65535.
    """
    m = re.fullmatch(r"v?(\d+)\.(\d+)(?:\.(\d+))?", version.strip())
    if not m:
        return None
    parts = [int(m.group(1)), int(m.group(2)), int(m.group(3) or 0)]
    if any(p > 65535 for p in parts):
        raise BuildError(f"Version {version} passt nicht in das MSIX-Format (höchstens 65535 je Stelle).")
    return ".".join(map(str, parts)) + ".0"


def load_identity(path: Path = STORE_JSON, *, allow_test: bool = False) -> dict:
    """Identität aus ``store.json``; ohne Angaben (und mit ``allow_test``) die Test-Identität."""
    data = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    ident = {k: str(data.get(k) or "").strip() for k in
             ("display_name", "identity_name", "publisher", "publisher_display_name", "store_id")}
    ident["display_name"] = ident["display_name"] or __app_name__
    ident["test"] = not (ident["identity_name"] and ident["publisher"])
    if ident["test"]:
        if not allow_test:
            raise BuildError(f"In {path} fehlt die "
                             "Paket-Identität aus Partner Center (identity_name, publisher, "
                             "publisher_display_name) – siehe docs/MICROSOFT_STORE.md. Für ein Testpaket: "
                             "--test-identity.")
        ident.update(TEST_IDENTITY)
    if not re.fullmatch(r"[A-Za-z0-9.\-]{3,50}", ident["identity_name"]):
        raise BuildError(f"Ungültiger Paketname „{ident['identity_name']}“ (3–50 Zeichen: A–Z, 0–9, Punkt, Bindestrich).")
    if not ident["publisher"].startswith("CN="):
        raise BuildError(f"Herausgeber „{ident['publisher']}“ muss mit „CN=“ beginnen (Wert aus Partner Center übernehmen).")
    if not ident["publisher_display_name"]:
        raise BuildError("publisher_display_name fehlt (Anzeigename des Herausgebers aus Partner Center).")
    return ident


def render_manifest(ident: dict, version: str, template: Path = TEMPLATE) -> str:
    values = {
        "name": ident["identity_name"],
        "publisher": ident["publisher"],
        "publisher_display_name": ident["publisher_display_name"],
        "display_name": ident["display_name"],
        "description": DESCRIPTION,
        "version": version,
    }
    quoted = {k: escape(v, {'"': "&quot;"}) for k, v in values.items()}
    return Template(template.read_text(encoding="utf-8")).substitute(quoted)


# ---------------------------------------------------------------------------
# Bilder
# ---------------------------------------------------------------------------
def _qt_app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtGui import QGuiApplication

    return QGuiApplication.instance() or QGuiApplication(sys.argv[:1])


def _image(width: int, height: int, share: float):
    """Programm-Icon (tools/make_icon.py, in Zielgröße gezeichnet) mittig auf transparentem Grund."""
    from make_icon import render
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QImage, QPainter

    size = max(1, round(min(width, height) * share))
    icon = render(size)
    if (size, size) == (width, height):
        return icon
    img = QImage(width, height, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.drawImage((width - size) // 2, (height - size) // 2, icon)
    p.end()
    return img


def write_assets(folder: Path, *, variants: bool) -> list[Path]:
    """Legt die Paketbilder an; ``variants`` = zusätzlich Skalierungs-/Größenvarianten (für makepri)."""
    _app = _qt_app()  # noqa: F841 – muss leben, solange gezeichnet wird
    folder.mkdir(parents=True, exist_ok=True)
    jobs: list[tuple[str, int, int, float]] = list(BASE_ASSETS)
    if variants:
        for name, w, h, share in BASE_ASSETS:
            stem = name[:-4]
            jobs.append((f"{stem}.scale-200.png", w * 2, h * 2, share))
        for stem in ("Square44x44Logo", "FileLogo"):
            for size in TARGET_SIZES:
                jobs.append((f"{stem}.targetsize-{size}.png", size, size, 1.0))
                jobs.append((f"{stem}.targetsize-{size}_altform-unplated.png", size, size, 1.0))
    written = []
    for name, w, h, share in jobs:
        target = folder / name
        if not _image(w, h, share).save(str(target)):
            raise BuildError(f"Bild konnte nicht gespeichert werden: {target}")
        written.append(target)
    return written


# ---------------------------------------------------------------------------
# Windows SDK
# ---------------------------------------------------------------------------
def find_sdk_tool(name: str) -> str | None:
    env = os.environ.get(name.upper())
    if env and Path(env).is_file():
        return env
    found = shutil.which(f"{name}.exe") or shutil.which(name)
    if found:
        return found
    kits = Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Windows Kits" / "10"
    candidates = sorted(kits.glob(f"bin/10.*/x64/{name}.exe"), key=lambda p: _version_key(p.parent.parent.name),
                        reverse=True)
    candidates.append(kits / "App Certification Kit" / f"{name}.exe")
    return next((str(c) for c in candidates if c.is_file()), None)


def _version_key(text: str) -> tuple[int, ...]:
    return tuple(int(x) for x in re.findall(r"\d+", text))


def _run(cmd: list[str]) -> None:
    print("  >", " ".join(f'"{c}"' if " " in c else c for c in cmd), flush=True)
    proc = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    if proc.returncode != 0:
        raise BuildError(f"{Path(cmd[0]).name} meldet Code {proc.returncode}:\n{proc.stdout}\n{proc.stderr}")


def make_pri(layout: Path, makepri: str) -> None:
    """resources.pri: Windows wählt damit die passende Bildvariante (Größe, Skalierung, Design).

    Indiziert werden nur die Bilder (und das Manifest), nicht die Tausende Programmdateien.
    """
    with tempfile.TemporaryDirectory(prefix="lptab-pri-") as tmp:
        src = Path(tmp) / "quelle"
        shutil.copytree(layout / "Assets", src / "Assets")
        shutil.copy2(layout / "AppxManifest.xml", src / "AppxManifest.xml")
        config = Path(tmp) / "priconfig.xml"
        _run([makepri, "createconfig", "/cf", str(config), "/dq", "de-DE", "/pv", "10.0.0", "/o"])
        # Keine getrennten Ressourcenpakete (Sprache/Skalierung) – alles in eine resources.pri
        text = re.sub(r"<packaging>.*?</packaging>", "", config.read_text(encoding="utf-8"), flags=re.DOTALL)
        config.write_text(text, encoding="utf-8")
        _run([makepri, "new", "/pr", str(src), "/cf", str(config), "/mn", str(src / "AppxManifest.xml"),
              "/of", str(layout / "resources.pri"), "/o"])


# ---------------------------------------------------------------------------
# Bauen
# ---------------------------------------------------------------------------
def build_layout(source: Path, layout: Path, ident: dict, version: str, *, variants: bool) -> None:
    if not (source / EXE_NAME).is_file() or not (source / "_internal").is_dir():
        raise BuildError(f"{source} enthält kein PyInstaller-Programm ({EXE_NAME} + _internal). "
                         "Zuerst: pyinstaller packaging/launchpad_pro_tab.spec --noconfirm")
    if layout.exists():
        shutil.rmtree(layout)
    shutil.copytree(source, layout)
    (layout / "AppxManifest.xml").write_text(render_manifest(ident, version), encoding="utf-8")
    write_assets(layout / "Assets", variants=variants)


def build(source: Path, out_dir: Path, *, store_json: Path = STORE_JSON, allow_test: bool = False,
          pack: bool = True, work_dir: Path | None = None) -> Path | None:
    """Baut Paketordner (und mit ``pack`` die .msix). Liefert die Paketdatei bzw. den Ordner;
    ``None`` bei Vorabversionen (die der Store nicht kennt)."""
    version = msix_version(__version__)
    if version is None:
        print(f"Version {__version__} ist eine Vorabversion – kein Store-Paket.")
        return None
    ident = load_identity(store_json, allow_test=allow_test)
    if ident["test"]:
        msg = ("Store-Paket mit TEST-Identität gebaut – nur zum Testen, der Store nimmt es nicht an. "
               "Identität aus Partner Center in packaging/msix/store.json eintragen (docs/MICROSOFT_STORE.md).")
        print(f"::warning::{msg}" if os.environ.get("GITHUB_ACTIONS") else f"WARNUNG: {msg}")
    work = work_dir or ROOT / "build" / "msix"
    layout = work / "paket"
    makeappx = makepri = None
    if pack:
        makeappx, makepri = find_sdk_tool("makeappx"), find_sdk_tool("makepri")
        if makeappx is None:
            raise BuildError("makeappx.exe nicht gefunden – Windows SDK installieren oder MAKEAPPX setzen.")
    print(f"Paketordner {layout} (Version {version}, {ident['identity_name']}) …", flush=True)
    build_layout(source, layout, ident, version, variants=bool(makepri))
    if not pack:
        return layout
    if makepri:
        make_pri(layout, makepri)
    else:
        print("makepri.exe nicht gefunden – Paket ohne Bildvarianten (resources.pri).")
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"LaunchpadProTAB-{__version__}.msix"
    _run([makeappx, "pack", "/d", str(layout), "/p", str(target), "/o"])
    print(f"Store-Paket: {target} ({target.stat().st_size / 1e6:.1f} MB)")
    return target


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--source", type=Path, default=ROOT / "dist" / "LaunchpadProTAB",
                    help="PyInstaller-Programmordner (Standard: dist/LaunchpadProTAB)")
    ap.add_argument("--out-dir", type=Path, default=ROOT / "dist", help="Zielordner der .msix (Standard: dist)")
    ap.add_argument("--store-json", type=Path, default=STORE_JSON, help="Identität aus Partner Center")
    ap.add_argument("--test-identity", action="store_true",
                    help="ohne Identität aus Partner Center ein Testpaket bauen (nicht für den Store)")
    ap.add_argument("--no-pack", action="store_true", help="nur den Paketordner anlegen (ohne Windows SDK)")
    args = ap.parse_args(argv)
    try:
        build(args.source, args.out_dir, store_json=args.store_json, allow_test=args.test_identity,
              pack=not args.no_pack)
    except BuildError as exc:
        print(f"FEHLER: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
