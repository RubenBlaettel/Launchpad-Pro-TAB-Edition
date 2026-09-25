# Drittanbieter-Komponenten

Launchpad Pro TAB Edition verwendet folgende Open-Source-Komponenten. Sie werden über `pip`
installiert bzw. in der Windows-EXE mitgeliefert.

| Komponente | Zweck | Lizenz |
|---|---|---|
| [Qt 6](https://www.qt.io/) / [PySide6](https://doc.qt.io/qtforpython-6/) | Oberfläche (Qt Quick/QML) | LGPL-3.0 |
| [NumPy](https://numpy.org/) | Signalverarbeitung | BSD-3-Clause |
| [python-sounddevice](https://github.com/spatialaudio/python-sounddevice) + [PortAudio](http://www.portaudio.com/) | Audio-Ausgabe | MIT |
| [python-soundfile](https://github.com/bastibe/python-soundfile) + [libsndfile](https://libsndfile.github.io/libsndfile/) | Audio lesen/schreiben | BSD-3-Clause / LGPL-2.1 |
| [PyAV](https://github.com/PyAV-Org/PyAV) + [FFmpeg](https://ffmpeg.org/) | Dekodierung vieler Formate | BSD-3-Clause / LGPL-2.1+ |
| [python-soxr](https://github.com/dofuuz/python-soxr) + libsoxr | Resampling | LGPL-2.1+ |
| [pycaw](https://github.com/AndreMiras/pycaw), [comtypes](https://github.com/enthought/comtypes) | Windows-Systemlautstärke | MIT |
| [Inter](https://rsms.me/inter/) (Schriftart, `launchpad_pro_tab/assets/fonts`) | Typografie | SIL Open Font License 1.1 (siehe `Inter-LICENSE.txt`) |

Die Icons (`launchpad_pro_tab/qml/icons`, erzeugt mit `tools/make_icons.py`), das Programm-Icon und
alle Demo-Klänge/-Bilder wurden für dieses Projekt selbst erstellt.
