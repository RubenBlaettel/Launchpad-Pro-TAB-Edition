# Drittanbieter-Komponenten

Launchpad Pro TAB Edition selbst steht unter der MIT-Lizenz (siehe `LICENSE`, © 2026 TAB Theater).
Es verwendet folgende Open-Source-Komponenten. Sie werden über `pip` installiert bzw. im
Windows-Installer und im Linux-Paket mitgeliefert.

| Komponente | Zweck | Lizenz |
|---|---|---|
| [Qt 6](https://www.qt.io/) / [PySide6](https://doc.qt.io/qtforpython-6/) | Oberfläche (Qt Quick/QML) | LGPL-3.0 |
| [NumPy](https://numpy.org/) | Signalverarbeitung | BSD-3-Clause |
| [python-sounddevice](https://github.com/spatialaudio/python-sounddevice) + [PortAudio](http://www.portaudio.com/) | Audio-Ausgabe | MIT |
| [python-soundfile](https://github.com/bastibe/python-soundfile) + [libsndfile](https://libsndfile.github.io/libsndfile/) | Audio lesen/schreiben | BSD-3-Clause / LGPL-2.1 |
| [PyAV](https://github.com/PyAV-Org/PyAV) + [FFmpeg](https://ffmpeg.org/) | Dekodierung vieler Formate | BSD-3-Clause / LGPL-2.1+ |
| [python-soxr](https://github.com/dofuuz/python-soxr) + libsoxr | Resampling | LGPL-2.1+ |
| [certifi](https://github.com/certifi/python-certifi) | Stammzertifikate für die Update-Prüfung (HTTPS) | MPL-2.0 |
| [pycaw](https://github.com/AndreMiras/pycaw), [comtypes](https://github.com/enthought/comtypes) | Windows-Systemlautstärke | MIT |
| [Inter](https://rsms.me/inter/) (Schriftart, `launchpad_pro_tab/assets/fonts`) | Typografie | SIL Open Font License 1.1 (siehe `Inter-LICENSE.txt`) |
| [PyInstaller](https://pyinstaller.org/) (Bootloader im Programmpaket) | Programmpaket ohne Python-Installation | GPL-2.0 mit Ausnahme für die Weitergabe gebündelter Programme |
| [Inno Setup](https://jrsoftware.org/isinfo.php) (Laufzeit im Windows-Installer) | Installation/Deinstallation unter Windows | Inno-Setup-Lizenz (frei, auch kommerziell) |

Die Icons (`launchpad_pro_tab/qml/icons`, erzeugt mit `tools/make_icons.py`), das Programm-Icon, die
Bilder des Installers (`tools/make_installer_images.py`) und alle Demo-Klänge/-Bilder wurden für
dieses Projekt selbst erstellt.
