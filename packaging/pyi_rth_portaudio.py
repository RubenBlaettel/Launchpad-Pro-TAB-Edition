# PyInstaller-Laufzeit-Hook (läuft vor dem Programmstart im gepackten Programm):
# sounddevice sucht PortAudio über ctypes.util.find_library("portaudio"). Unter Linux liegt
# die Bibliothek im Programmpaket und steht nicht im ldconfig-Cache – daher hier zuerst im
# Paket suchen, dann wie gewohnt im System.
import ctypes.util
import os
import sys

_find_library = ctypes.util.find_library


def _find_library_bundled(name):
    if name == "portaudio" and sys.platform.startswith("linux"):
        base = getattr(sys, "_MEIPASS", "")
        for candidate in ("libportaudio.so.2", "libportaudio.so"):
            path = os.path.join(base, candidate)
            if os.path.exists(path):
                return path
    return _find_library(name)


ctypes.util.find_library = _find_library_bundled
