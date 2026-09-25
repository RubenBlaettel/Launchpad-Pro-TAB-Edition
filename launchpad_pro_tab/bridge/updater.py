"""QML-Schnittstelle der Update-Funktion (``updater``).

Prüft beim Start (und danach alle 12 Stunden) im Hintergrund, ob auf GitHub eine neuere
Version veröffentlicht wurde, zeigt Hinweis + Versionshinweise und führt das Update auf
Wunsch vollständig aus (Download -> Prüfsumme -> Installer bzw. Ordnertausch -> Neustart).
Netzwerkfehler (z. B. Bühnenrechner ohne Internet) werden beim automatischen Prüfen
still protokolliert – es erscheint dann einfach kein Hinweis.
"""

from __future__ import annotations

import logging
import os
import shutil
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import Property, QObject, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices

from .. import __version__
from ..core.paths import cache_dir
from ..core.util import now_iso
from ..update import install
from ..update.download import DownloadCancelled, download
from ..update.install import InstallError, InstallKind
from ..update.releases import Asset, Release, fetch_releases, pick_update, releases_page, releases_url, resolve_checksum
from .qtutil import PropertyObject, rprop

if TYPE_CHECKING:
    from ..core.settings import AppSettings
    from .tasks import TaskRunner

log = logging.getLogger(__name__)

CHECK_INTERVAL_MS = 12 * 60 * 60 * 1000
STARTUP_DELAY_MS = 4000


def _mb(n: int) -> str:
    return f"{n / 1_000_000:.1f} MB".replace(".", ",")


class UpdateController(PropertyObject):
    stateChanged = Signal()
    releaseChanged = Signal()
    progressChanged = Signal()
    optionsChanged = Signal()
    updateFound = Signal(str, arguments=["version"])
    quitRequested = Signal()

    def __init__(self, runner: TaskRunner, settings: AppSettings, parent: QObject | None = None,
                 *, kind: InstallKind | None = None):
        super().__init__(parent)
        self._runner = runner
        self._settings = settings
        self._kind = kind or install.detect_install_kind()
        self._release: Release | None = None
        self._asset: Asset | None = None
        self._manual = False
        self._cancel = threading.Event()
        self._dl_done = 0
        self._dl_total = 0
        self._dl_start = 0.0
        # Wird vom Backend gesetzt: speichert das Projekt und gibt Audio/Worker frei
        self.prepare_hook = None
        self.project_hook = None
        self.busy_hook = None

        self._state = "idle"
        self._message = ""
        self._progress = 0.0
        self._progress_text = ""

        self._poll = QTimer(self)
        self._poll.setInterval(100)
        self._poll.timeout.connect(self._update_progress)
        self._periodic = QTimer(self)
        self._periodic.setInterval(CHECK_INTERVAL_MS)
        self._periodic.timeout.connect(lambda: self.check(False))

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------
    state = rprop(str, "_state", stateChanged)
    message = rprop(str, "_message", stateChanged)
    progress = rprop(float, "_progress", progressChanged)
    progressText = rprop(str, "_progress_text", progressChanged)
    currentVersion = Property(str, lambda self: __version__, constant=True)
    installKind = Property(str, lambda self: self._kind.value, constant=True)

    def _rel(self, attr: str, default: Any = "") -> Any:
        return getattr(self._release, attr) if self._release is not None else default

    latestVersion = Property(str, lambda self: str(self._rel("version")), notify=releaseChanged)
    releaseTitle = Property(str, lambda self: self._rel("title"), notify=releaseChanged)
    releaseNotes = Property(str, lambda self: self._rel("notes"), notify=releaseChanged)
    releaseUrl = Property(str, lambda self: self._rel("html_url") or releases_page(), notify=releaseChanged)
    prerelease = Property(bool, lambda self: bool(self._rel("prerelease", False)), notify=releaseChanged)

    def _release_date(self) -> str:
        published: datetime | None = self._rel("published", None)
        return published.astimezone().strftime("%d.%m.%Y") if published else ""

    releaseDate = Property(str, _release_date, notify=releaseChanged)
    downloadSize = Property(str, lambda self: _mb(self._asset.size) if self._asset and self._asset.size else "",
                            notify=releaseChanged)
    available = Property(bool, lambda self: self._state in ("available", "downloading", "installing"),
                         notify=stateChanged)
    canInstall = Property(bool, lambda self: self._asset is not None, notify=releaseChanged)

    def _hint(self) -> str:
        if self._release is not None and self._asset is None and self._kind in (
            InstallKind.WINDOWS_INSTALLER, InstallKind.WINDOWS_PORTABLE, InstallKind.LINUX_BUNDLE
        ):
            return "Für dieses System enthält die neue Version kein passendes Paket – bitte die Download-Seite öffnen."
        return install.install_hint(self._kind)

    installHint = Property(str, _hint, notify=releaseChanged)
    autoCheck = Property(bool, lambda self: bool(self._settings.update_auto_check), notify=optionsChanged)
    includePrereleases = Property(bool, lambda self: bool(self._settings.update_prereleases), notify=optionsChanged)

    def _last_check(self) -> str:
        raw = self._settings.update_last_check
        if not raw:
            return "Noch nie nach Updates gesucht."
        try:
            dt = datetime.fromisoformat(raw)
        except ValueError:
            return ""
        day = "heute" if dt.date() == datetime.now().date() else dt.strftime("%d.%m.%Y")
        return f"Zuletzt gesucht: {day}, {dt:%H:%M} Uhr"

    lastCheckText = Property(str, _last_check, notify=optionsChanged)

    def _set_state(self, state: str, message: str | None = None) -> None:
        changed = state != self._state or (message is not None and message != self._message)
        self._state = state
        if message is not None:
            self._message = message
        if changed:
            self.stateChanged.emit()

    # ------------------------------------------------------------------
    # Start / Einstellungen
    # ------------------------------------------------------------------
    def start(self, delay_ms: int = STARTUP_DELAY_MS) -> None:
        """Automatische Prüfung kurz nach dem Start (die Oberfläche lädt zuerst)."""
        if self._settings.update_auto_check:
            QTimer.singleShot(delay_ms, lambda: self.check(False))
            self._periodic.start()

    @Slot(bool)
    def setAutoCheck(self, enabled: bool) -> None:  # noqa: N802
        self._settings.update_auto_check = bool(enabled)
        self._settings.save()
        if enabled:
            self._periodic.start()
        else:
            self._periodic.stop()
        self.optionsChanged.emit()

    @Slot(bool)
    def setIncludePrereleases(self, enabled: bool) -> None:  # noqa: N802
        self._settings.update_prereleases = bool(enabled)
        self._settings.save()
        self.optionsChanged.emit()

    # ------------------------------------------------------------------
    # Prüfen
    # ------------------------------------------------------------------
    @Slot()
    def checkNow(self) -> None:  # noqa: N802
        self.check(True)

    def check(self, manual: bool = True) -> None:
        if self._state in ("checking", "downloading", "installing"):
            return
        self._manual = manual
        self._set_state("checking", "Suche nach Updates …")
        self._runner.submit_thread(fetch_releases, releases_url(), on_done=self._checked, on_error=self._check_failed)

    def _checked(self, releases: list[Release]) -> None:
        self._settings.update_last_check = now_iso()
        self._settings.save()
        self.optionsChanged.emit()
        skipped = None if self._manual else self._settings.update_skipped
        release = pick_update(releases, __version__, include_prereleases=self._settings.update_prereleases,
                              skipped=skipped)
        if release is None:
            self._release, self._asset = None, None
            self.releaseChanged.emit()
            self._set_state("uptodate", f"Launchpad Pro ist auf dem neuesten Stand (Version {__version__}).")
            return
        pattern = install.asset_pattern(self._kind)
        self._release = release
        self._asset = release.asset(pattern) if pattern else None
        self.releaseChanged.emit()
        self._set_state("available", f"Version {release.version} ist verfügbar.")
        log.info("Update verfügbar: %s (%s)", release.version, self._asset.name if self._asset else "kein Paket")
        self.updateFound.emit(str(release.version))

    def _check_failed(self, message: str) -> None:
        log.info("Update-Prüfung fehlgeschlagen: %s", message)
        if self._manual:
            self._set_state("error", message)
        else:
            self._set_state("idle", "")

    # ------------------------------------------------------------------
    # Aktionen im Dialog
    # ------------------------------------------------------------------
    @Slot()
    def skipVersion(self) -> None:  # noqa: N802
        if self._release is None:
            return
        self._settings.update_skipped = str(self._release.version)
        self._settings.save()
        self._release, self._asset = None, None
        self.releaseChanged.emit()
        self._set_state("idle", "")

    @Slot()
    def openReleasePage(self) -> None:  # noqa: N802
        QDesktopServices.openUrl(QUrl(self._rel("html_url") or releases_page()))

    @Slot()
    def cancelDownload(self) -> None:  # noqa: N802
        self._cancel.set()

    @Slot()
    def startUpdate(self) -> None:  # noqa: N802
        if self._state not in ("available", "error") or self._release is None or self._asset is None:
            return
        release, asset = self._release, self._asset
        self._cancel.clear()
        self._dl_done, self._dl_total, self._dl_start = 0, asset.size, time.monotonic()
        self._progress, self._progress_text = 0.0, ""
        self.progressChanged.emit()
        self._set_state("downloading", f"Version {release.version} wird heruntergeladen …")
        target = cache_dir() / "updates" / asset.name

        def work() -> Path:
            checksum = resolve_checksum(release, asset)
            return download(asset.url, target, sha256=checksum, size=asset.size,
                            progress=self._on_progress, cancel=self._cancel)

        self._poll.start()
        self._runner.submit_thread(work, on_done=self._downloaded, on_error=self._download_failed)

    def _on_progress(self, done: int, total: int) -> None:  # Download-Thread
        self._dl_done = done
        self._dl_total = total

    def _update_progress(self) -> None:
        total = self._dl_total or 0
        done = self._dl_done
        self._progress = done / total if total else 0.0
        elapsed = max(0.001, time.monotonic() - self._dl_start)
        rate = done / elapsed
        text = f"{_mb(done)} von {_mb(total)}" if total else _mb(done)
        if done > 0:
            text += f"  ·  {_mb(int(rate))}/s"
        self._progress_text = text
        self.progressChanged.emit()

    def _download_failed(self, message: str) -> None:
        self._poll.stop()
        if self._cancel.is_set() or message == DownloadCancelled.__name__:
            self._set_state("available", "Download abgebrochen.")
        else:
            self._set_state("error", f"Update fehlgeschlagen: {message}")

    def _downloaded(self, path: Path) -> None:
        self._poll.stop()
        self._update_progress()
        self._set_state("installing", "Update wird installiert – Launchpad Pro startet gleich neu …")
        QTimer.singleShot(150, lambda: self._install(path))

    # ------------------------------------------------------------------
    # Installieren
    # ------------------------------------------------------------------
    def _install(self, package: Path) -> None:
        try:
            if self._kind is InstallKind.LINUX_BUNDLE:
                self._install_linux(package)
            elif self._kind in (InstallKind.WINDOWS_INSTALLER, InstallKind.WINDOWS_PORTABLE):
                self._prepare()
                silent = self._kind is InstallKind.WINDOWS_INSTALLER
                args = install.windows_installer_args(wait_pid=os.getpid(), silent=silent, restart=silent,
                                                      log_file=package.with_name("installation.log"))
                install.start_windows_installer(package, args)
                self.quitRequested.emit()
            else:
                raise InstallError(install.install_hint(self._kind))
        except (InstallError, OSError) as exc:
            log.exception("Update konnte nicht installiert werden")
            self._set_state("error", f"Update fehlgeschlagen: {exc}")

    def _prepare(self) -> None:
        if self.prepare_hook is not None and not self.prepare_hook():
            raise InstallError("Das Projekt konnte nicht gespeichert werden – Update abgebrochen.")

    def _install_linux(self, package: Path) -> None:
        install_dir = install.app_dir()
        parent = install.staging_parent(install_dir, cache_dir() / "updates")
        if self.busy_hook is not None:
            self.busy_hook("Update wird entpackt …")

        def work() -> Path:
            return install.extract_bundle(package, parent)

        def extracted(new_root: Path) -> None:
            if self.busy_hook is not None:
                self.busy_hook("")
            try:
                self._prepare()
                project = self.project_hook() if self.project_hook is not None else None
                cmd = install.finish_command(new_root, install_dir, os.getpid(), install.restart_args(project))
                install.spawn_detached(cmd)
            except (InstallError, OSError) as exc:
                log.exception("Update konnte nicht installiert werden")
                self._set_state("error", f"Update fehlgeschlagen: {exc}")
                return
            self.quitRequested.emit()

        def failed(message: str) -> None:
            if self.busy_hook is not None:
                self.busy_hook("")
            self._set_state("error", f"Update fehlgeschlagen: {message}")

        self._runner.submit_thread(work, on_done=extracted, on_error=failed)

    def cleanup(self) -> None:
        """Reste früherer Updates entfernen (läuft im Hintergrund-Thread)."""
        folder = cache_dir() / "updates"
        if folder.is_dir():
            for entry in folder.iterdir():
                try:
                    if entry.is_dir():
                        if entry.name.startswith(".launchpad-update-"):
                            shutil.rmtree(entry, ignore_errors=True)
                    elif entry.suffix.lower() in (".exe", ".gz", ".part"):
                        entry.unlink()
                except OSError:
                    pass           # z. B. Installer läuft gerade noch
        if self._kind is InstallKind.LINUX_BUNDLE:
            install.cleanup_previous()

    def shutdown(self) -> None:
        self._cancel.set()
        self._poll.stop()
        self._periodic.stop()
