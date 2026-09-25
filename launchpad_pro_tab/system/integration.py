"""Windows-Integration: Instanz-Mutex (für den Installer) und Taskleisten-Kennung.

Unter anderen Systemen sind die Funktionen wirkungslos.
"""

from __future__ import annotations

import logging
import sys

log = logging.getLogger(__name__)

# Muss mit AppMutex im Installer-Skript (packaging/windows/LaunchpadProTAB.iss) übereinstimmen
MUTEX_NAME = "LaunchpadProTAB-Instanz"
# Muss mit AppUserModelID der Startmenü-/Desktop-Verknüpfungen übereinstimmen
APP_USER_MODEL_ID = "TABTheater.LaunchpadProTAB"

_handles: list[int] = []


def create_instance_mutex() -> None:
    """Named Mutex, an dem Installer/Deinstaller erkennen, dass das Programm läuft."""
    if sys.platform != "win32":
        return
    import ctypes

    kernel32 = ctypes.windll.kernel32
    kernel32.CreateMutexW.restype = ctypes.c_void_p
    for name in (MUTEX_NAME, "Global\\" + MUTEX_NAME):
        handle = kernel32.CreateMutexW(None, False, name)
        if handle:
            _handles.append(handle)     # bis Prozessende offen halten
        else:
            log.debug("Mutex %s nicht angelegt (Fehler %s)", name, kernel32.GetLastError())


def set_app_user_model_id() -> None:
    """Gleiche Taskleisten-Gruppe/Symbol wie die Verknüpfungen des Installers."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except Exception as exc:  # noqa: BLE001
        log.debug("AppUserModelID nicht gesetzt: %s", exc)
