"""Installationsart erkennen und ein heruntergeladenes Update anwenden.

Windows (per Installer installiert)
    Der Installer (Inno Setup) wird still mit ``/LPTABWAITPID=<pid>`` gestartet, das
    Programm beendet sich. Der Installer wartet, bis der Prozess beendet ist, ersetzt die
    Programmdateien und startet Launchpad Pro als normaler Benutzer neu.

Windows (portable, ohne Installer)
    Der Installer wird sichtbar gestartet – danach ist das Programm regulär installiert.

Linux (Programmpaket ``*.tar.gz``)
    Das Archiv wird neben den Programmordner entpackt. Ein Hilfsprozess der *neuen*
    Version wartet, bis die alte beendet ist, tauscht die Ordner (alt -> ``.old-…``) und
    startet das Programm neu. Ohne Schreibrechte (z. B. ``/opt``) übernimmt ``pkexec``
    mit ``install.sh --update`` den Austausch.
"""

from __future__ import annotations

import logging
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from enum import Enum
from pathlib import Path

log = logging.getLogger(__name__)

EXE_NAME_WINDOWS = "LaunchpadProTAB.exe"
EXE_NAME_LINUX = "LaunchpadProTAB"
WINDOWS_ASSET = r"^LaunchpadProTAB-Setup-[^/]+\.exe$"
LINUX_ASSET = r"^LaunchpadProTAB-[^/]+-linux-x86_64\.tar\.gz$"
INSTALL_INFO = ".install-info"          # von install.sh geschrieben (Menü/Desktop-Einträge)
OLD_PREFIX = ".alt-"                     # Überbleibsel eines Updates (beim Start gelöscht)


class InstallKind(str, Enum):
    WINDOWS_INSTALLER = "windows-installer"
    WINDOWS_PORTABLE = "windows-portable"
    LINUX_BUNDLE = "linux-bundle"
    SOURCE = "source"
    UNSUPPORTED = "unsupported"


class InstallError(Exception):
    pass


# ---------------------------------------------------------------------------
# Erkennen
# ---------------------------------------------------------------------------
def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def app_dir() -> Path:
    """Programmordner der laufenden Installation (Ordner der EXE bzw. des Quellcodes)."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def detect_install_kind(*, frozen: bool | None = None, platform_name: str | None = None,
                        directory: Path | None = None) -> InstallKind:
    frozen = is_frozen() if frozen is None else frozen
    platform_name = platform_name or sys.platform
    directory = directory or app_dir()
    if not frozen:
        return InstallKind.SOURCE
    if platform_name == "win32":
        has_uninstaller = any(directory.glob("unins*.exe"))
        return InstallKind.WINDOWS_INSTALLER if has_uninstaller else InstallKind.WINDOWS_PORTABLE
    if platform_name.startswith("linux") and platform.machine().lower() in ("x86_64", "amd64"):
        return InstallKind.LINUX_BUNDLE
    return InstallKind.UNSUPPORTED


def asset_pattern(kind: InstallKind) -> str | None:
    if kind in (InstallKind.WINDOWS_INSTALLER, InstallKind.WINDOWS_PORTABLE):
        return WINDOWS_ASSET
    if kind is InstallKind.LINUX_BUNDLE:
        return LINUX_ASSET
    return None


def install_hint(kind: InstallKind) -> str:
    return {
        InstallKind.WINDOWS_INSTALLER: "Das Update wird heruntergeladen und geprüft. Danach speichert Launchpad Pro das "
                                       "Projekt, beendet sich, der Installer aktualisiert das Programm und startet es neu.",
        InstallKind.WINDOWS_PORTABLE: "Diese Programmversion wurde ohne Installer entpackt. Das Update startet den "
                                      "Installer – danach ist Launchpad Pro regulär installiert (Startmenü, Updates).",
        InstallKind.LINUX_BUNDLE: "Das Update wird heruntergeladen und geprüft. Danach wird der Programmordner "
                                  "ausgetauscht und Launchpad Pro neu gestartet.",
        InstallKind.SOURCE: "Launchpad Pro läuft aus dem Quellcode. Bitte den neuen Stand von GitHub holen "
                            "(z. B. „git pull“) oder den Installer von der Download-Seite verwenden.",
        InstallKind.UNSUPPORTED: "Für dieses System gibt es kein automatisches Update – bitte die Download-Seite öffnen.",
    }[kind]


# ---------------------------------------------------------------------------
# Windows
# ---------------------------------------------------------------------------
def windows_installer_args(*, wait_pid: int, silent: bool, restart: bool, log_file: Path | None = None) -> list[str]:
    args = [f"/LPTABWAITPID={wait_pid}"]
    if silent:
        args += ["/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART"]
    if restart:
        args.append("/LPTABRESTART=1")
    if log_file is not None:
        args.append(f"/LOG={log_file}")
    return args


def start_windows_installer(setup: Path, args: list[str]) -> None:
    """Startet den Installer unabhängig vom laufenden Programm."""
    if sys.platform != "win32":
        raise InstallError("Der Windows-Installer kann nur unter Windows gestartet werden.")
    flags = getattr(subprocess, "DETACHED_PROCESS", 0x8) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x200)
    try:
        subprocess.Popen([str(setup), *args], close_fds=True, creationflags=flags, cwd=str(Path(setup).parent))
    except OSError as exc:
        if getattr(exc, "winerror", None) != 740:        # ERROR_ELEVATION_REQUIRED
            raise InstallError(f"Installer konnte nicht gestartet werden: {exc}") from exc
        import ctypes

        params = subprocess.list2cmdline(args)
        rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", str(setup), params, str(Path(setup).parent), 1)
        if rc <= 32:
            raise InstallError(f"Installer konnte nicht gestartet werden (Code {rc}).") from exc


# ---------------------------------------------------------------------------
# Linux
# ---------------------------------------------------------------------------
def _find_bundle_root(folder: Path) -> Path:
    for candidate in [folder, *sorted(p for p in folder.iterdir() if p.is_dir())]:
        exe = candidate / EXE_NAME_LINUX
        if exe.is_file() and (candidate / "_internal").is_dir():
            return candidate
    raise InstallError("Das Update-Archiv enthält kein gültiges Programmpaket.")


def extract_bundle(archive: Path, parent: Path) -> Path:
    """Entpackt das Archiv sicher in einen neuen Ordner unterhalb von ``parent``."""
    staging = Path(tempfile.mkdtemp(prefix=".launchpad-update-", dir=parent))
    try:
        with tarfile.open(archive, "r:gz") as tar:
            try:
                tar.extractall(staging, filter="data")          # verhindert ../ und absolute Pfade
            except TypeError:                                   # Python < 3.10.12 ohne filter
                for member in tar.getmembers():
                    target = (staging / member.name).resolve()
                    if not str(target).startswith(str(staging.resolve()) + os.sep):
                        raise InstallError(f"Unsicherer Pfad im Archiv: {member.name}")
                tar.extractall(staging)  # noqa: S202 – Pfade oben geprüft
        root = _find_bundle_root(staging)
        exe = root / EXE_NAME_LINUX
        exe.chmod(exe.stat().st_mode | 0o755)
        return root
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def can_write(directory: Path) -> bool:
    return os.access(directory, os.W_OK) and os.access(directory.parent, os.W_OK)


def staging_parent(install_dir: Path, fallback: Path) -> Path:
    """Wohin das Update entpackt wird: neben den Programmordner (schneller Austausch per
    Umbenennen) oder – ohne Schreibrechte dort – in den Cache-Ordner des Benutzers."""
    return install_dir.parent if can_write(install_dir) else fallback


def finish_command(new_root: Path, install_dir: Path, wait_pid: int, restart: list[str]) -> list[str]:
    """Befehl für den Hilfsprozess der neuen Version (siehe :func:`finish_linux_update`)."""
    return [str(new_root / EXE_NAME_LINUX), "--finish-update", str(install_dir),
            "--wait-pid", str(wait_pid), "--", *restart]


def pkexec_command(new_root: Path, install_dir: Path) -> list[str]:
    script = new_root / "install.sh"
    if not script.is_file():
        raise InstallError("Keine Schreibrechte für den Programmordner und kein install.sh im Update.")
    pkexec = shutil.which("pkexec")
    if pkexec is None:
        raise InstallError(f"Keine Schreibrechte für {install_dir}. Bitte das Update mit Administratorrechten "
                           f"installieren: sudo sh {script} --update --target {install_dir}")
    return [pkexec, "/bin/sh", str(script), "--update", "--target", str(install_dir), "--source", str(new_root)]


def spawn_detached(cmd: list[str]) -> None:
    kwargs: dict = {"close_fds": True}
    if sys.platform == "win32":
        kwargs["creationflags"] = getattr(subprocess, "DETACHED_PROCESS", 0x8) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x200)
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kwargs)


def wait_for_pid(pid: int, timeout: float = 30.0) -> bool:
    """Wartet, bis Prozess ``pid`` beendet ist. ``True`` = beendet (oder nie gelaufen)."""
    if pid <= 0 or pid == os.getpid():
        return True
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not _pid_alive(pid):
            return True
        time.sleep(0.1)
    return not _pid_alive(pid)


def _pid_alive(pid: int) -> bool:
    if sys.platform == "win32":
        import ctypes

        SYNCHRONIZE = 0x00100000
        handle = ctypes.windll.kernel32.OpenProcess(SYNCHRONIZE, False, pid)
        if not handle:
            return False
        try:
            return ctypes.windll.kernel32.WaitForSingleObject(handle, 0) == 0x102  # WAIT_TIMEOUT
        finally:
            ctypes.windll.kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    # Zombie (beendet, aber noch nicht abgeholt) gilt als beendet
    try:
        with open(f"/proc/{pid}/stat", encoding="ascii", errors="replace") as fh:
            return fh.read().split(") ", 1)[1][:1] != "Z"
    except (OSError, IndexError):
        return True


def swap_directories(install_dir: Path, new_root: Path) -> Path:
    """Tauscht den Programmordner aus. Liefert den Pfad der alten Version (``.alt-…``)."""
    install_dir = install_dir.resolve()
    old = install_dir.with_name(f"{OLD_PREFIX}{install_dir.name}-{time.strftime('%Y%m%d-%H%M%S')}")
    info = install_dir / INSTALL_INFO
    if info.is_file() and not (new_root / INSTALL_INFO).exists():
        shutil.copy2(info, new_root / INSTALL_INFO)
    os.rename(install_dir, old)
    try:
        os.rename(new_root, install_dir)
    except OSError:
        os.rename(old, install_dir)          # zurückrollen – alte Version bleibt lauffähig
        raise
    return old


def finish_linux_update(install_dir: Path, wait_pid: int, restart: list[str]) -> int:
    """Läuft in der *neuen* Version (Hilfsprozess): warten, austauschen, neu starten."""
    new_root = app_dir()
    staging = new_root.parent
    if not wait_for_pid(wait_pid, timeout=60):
        log.error("Alte Programmversion beendet sich nicht – Update abgebrochen.")
        return 1
    try:
        if can_write(install_dir):
            swap_directories(install_dir, new_root)
        else:
            rc = subprocess.run(pkexec_command(new_root, install_dir), check=False).returncode
            if rc != 0:
                raise InstallError(f"Installation mit Administratorrechten abgebrochen (Code {rc}).")
    except (OSError, InstallError) as exc:
        log.error("Programmordner konnte nicht ausgetauscht werden: %s", exc)
    finally:
        if staging.name.startswith(".launchpad-update-"):
            shutil.rmtree(staging, ignore_errors=True)
    exe = install_dir / EXE_NAME_LINUX            # neue – oder bei Fehler weiterhin alte – Version
    os.execv(str(exe), [str(exe), *restart])
    return 0  # pragma: no cover – execv kehrt nicht zurück


def cleanup_previous(directory: Path | None = None) -> None:
    """Löscht Reste früherer Updates (``.alt-…``, abgebrochene ``.launchpad-update-…``)."""
    directory = (directory or app_dir()).resolve()
    parent = directory.parent
    try:
        entries = list(parent.iterdir())
    except OSError:
        return
    for entry in entries:
        if entry == directory:
            continue
        if entry.name.startswith(f"{OLD_PREFIX}{directory.name}-") or entry.name.startswith(".launchpad-update-"):
            shutil.rmtree(entry, ignore_errors=True)


def restart_args(project: str | None = None) -> list[str]:
    return ["--project", project] if project else []
