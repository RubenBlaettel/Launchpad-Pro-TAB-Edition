"""Windows-Integration: Instanz-Mutex (für den Installer), Taskleisten-Kennung und
„Gedrückt halten“ für Touch/Stift.

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


# Fenster-Eigenschaft des Windows-Tablet-Dienstes (gilt für Finger und Stift)
PRESS_AND_HOLD_PROPERTY = "MicrosoftTabletPenServiceProperty"
TABLET_DISABLE_PRESSANDHOLD = 0x00000001


def disable_press_and_hold(hwnd: int) -> bool:
    """Windows' „Gedrückt halten = Rechtsklick“ für das Programmfenster abschalten.

    Windows zeigt beim langen Drücken einen eigenen Ring und schickt beim Loslassen einen
    Rechtsklick. Das Programm erkennt „lang drücken“ selbst (Kachel-Menü) – der zusätzliche
    Rechtsklick landete neben dem gerade geöffneten Menü und schloss es sofort wieder.
    """
    if sys.platform != "win32" or not hwnd:
        return False
    try:
        import ctypes
        from ctypes import wintypes

        # eigene DLL-Objekte: argtypes nicht für andere Nutzer von ctypes.windll verändern
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        kernel32.GlobalAddAtomW.argtypes = [wintypes.LPCWSTR]
        kernel32.GlobalAddAtomW.restype = wintypes.ATOM
        user32.SetPropW.argtypes = [wintypes.HWND, wintypes.LPCWSTR, wintypes.HANDLE]
        user32.SetPropW.restype = wintypes.BOOL
        if not kernel32.GlobalAddAtomW(PRESS_AND_HOLD_PROPERTY):
            raise OSError(ctypes.get_last_error())
        if not user32.SetPropW(hwnd, PRESS_AND_HOLD_PROPERTY, TABLET_DISABLE_PRESSANDHOLD):
            raise OSError(ctypes.get_last_error())
        return True
    except Exception as exc:  # noqa: BLE001
        log.debug("„Gedrückt halten“ nicht abgeschaltet: %s", exc)
        return False
