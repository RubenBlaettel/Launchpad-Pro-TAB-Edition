# -*- mode: python ; coding: utf-8 -*-
# PyInstaller-Konfiguration für die Programmversion (Ordner mit ausführbarer Datei).
#
#   pip install -r requirements-dev.txt
#   pyinstaller packaging/launchpad_pro_tab.spec --noconfirm
#
# Ergebnis: dist/LaunchpadProTAB/LaunchpadProTAB(.exe)
# Danach:   python tools/build_installer.py       (Windows-Installer, Inno Setup 7)
#           python tools/build_linux_package.py   (Linux-Paket .tar.gz mit install.sh)
import os
import shutil
import sys

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))  # noqa: F821 – von PyInstaller gesetzt
sys.path.insert(0, ROOT)

from PyInstaller.utils.hooks import collect_submodules  # noqa: E402


def package_data(*subdirs):
    """QML-Dateien, Icons, Schriften usw. mit ihrer Ordnerstruktur übernehmen."""
    out = []
    pkg = os.path.join(ROOT, "launchpad_pro_tab")
    for sub in subdirs:
        for dirpath, _dirs, files in os.walk(os.path.join(pkg, sub)):
            for fn in files:
                if fn.endswith((".pyc", ".py")):
                    continue
                rel = os.path.relpath(dirpath, ROOT)
                out.append((os.path.join(dirpath, fn), rel))
    return out


datas = package_data("qml", "assets")
if len(datas) < 40:
    raise SystemExit(f"Zu wenige Programmdateien gefunden ({len(datas)}) – Pfad prüfen: {ROOT}")
hiddenimports = (
    collect_submodules("launchpad_pro_tab")
    + ["soxr", "soundfile", "sounddevice", "av", "numpy"]
    + (["pycaw.pycaw", "comtypes", "comtypes.client"] if os.name == "nt" else [])
)

a = Analysis(  # noqa: F821
    [os.path.join(ROOT, "run_launchpad.py")],
    pathex=[ROOT],
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["tkinter", "matplotlib", "PySide6.QtWebEngineCore", "PySide6.Qt3DCore"],
    runtime_hooks=[os.path.join(SPECPATH, "pyi_rth_portaudio.py")],  # noqa: F821
    noarchive=False,
)
# Linux: die ALSA-Bibliothek des Systems verwenden (passend zu dessen PipeWire-/PulseAudio-
# Plugins). Eine mitgelieferte libasound findet die Plugins anderer Distributionen nicht.
a.binaries = [b for b in a.binaries if not os.path.basename(b[0]).startswith("libasound.so")]
pyz = PYZ(a.pure)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="LaunchpadProTAB",
    icon=os.path.join(ROOT, "launchpad_pro_tab", "assets", "app_icon.ico") if os.name == "nt" else None,
    console=False,          # keine Konsole
    disable_windowed_traceback=False,
    upx=False,
)
coll = COLLECT(  # noqa: F821
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="LaunchpadProTAB",
)

# Lizenztexte gut sichtbar neben das Programm legen (landen so auch im Installer und im Linux-Paket)
for _name, _target in (("LICENSE", "LICENSE.txt"), ("THIRD_PARTY_NOTICES.md", "THIRD_PARTY_NOTICES.md")):
    shutil.copy2(os.path.join(ROOT, _name), os.path.join(DISTPATH, "LaunchpadProTAB", _target))  # noqa: F821
