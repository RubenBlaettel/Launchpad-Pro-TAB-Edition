"""Windows-Integration: Instanz-Mutex (für den Installer), Taskleisten-Kennung,
„Gedrückt halten“ für Touch/Stift und Erkennung des Microsoft-Store-Pakets (MSIX).

Unter anderen Systemen sind die Funktionen wirkungslos.
"""

from __future__ import annotations

import functools
import logging
import sys

log = logging.getLogger(__name__)

APPMODEL_ERROR_NO_PACKAGE = 15700
ERROR_INSUFFICIENT_BUFFER = 122

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


@functools.lru_cache(maxsize=1)
def package_family_name() -> str | None:
    """Paketfamilie, wenn das Programm als MSIX-Paket läuft (Microsoft Store), sonst ``None``."""
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        from ctypes import wintypes

        func = ctypes.WinDLL("kernel32").GetCurrentPackageFamilyName
    except (OSError, AttributeError):       # vor Windows 8 gibt es keine Pakete
        return None
    func.argtypes = [ctypes.POINTER(wintypes.UINT), wintypes.LPWSTR]
    func.restype = wintypes.LONG
    length = wintypes.UINT(0)
    rc = func(ctypes.byref(length), None)
    if rc != ERROR_INSUFFICIENT_BUFFER:     # APPMODEL_ERROR_NO_PACKAGE = kein Paket
        return None
    buf = ctypes.create_unicode_buffer(length.value)
    if func(ctypes.byref(length), buf) != 0:
        return None
    return buf.value or None


def set_app_user_model_id() -> None:
    """Gleiche Taskleisten-Gruppe/Symbol wie die Verknüpfungen des Installers.

    Im MSIX-Paket vergibt Windows die Kennung selbst – eine eigene würde das Anheften an
    die Taskleiste und die Sprungliste des Pakets stören.
    """
    if sys.platform != "win32" or package_family_name():
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
