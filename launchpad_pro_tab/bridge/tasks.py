"""Hintergrundaufgaben: Prozess-Pool (CPU-lastig, mehrere Kerne) und Thread-Pool (I/O).

Ergebnisse werden per Qt-Signal in den UI-Thread zurückgeliefert, Callbacks laufen dort.

Robustheit: Können keine Worker-Prozesse gestartet werden (z. B. weil eine Sicherheits-
software das auf einem abgesicherten PC verhindert) oder bricht der Pool ab, wird die
betroffene Aufgabe automatisch in einem Thread wiederholt. Nach wiederholtem Ausfall
arbeitet die Anwendung dauerhaft mit Threads weiter – langsamer, aber zuverlässig.
"""

from __future__ import annotations

import itertools
import logging
import multiprocessing
import os
from concurrent.futures import Future, ProcessPoolExecutor, ThreadPoolExecutor
from concurrent.futures.process import BrokenProcessPool
from typing import Any, Callable

from PySide6.QtCore import QObject, Signal, Slot

from ..audio.tasks import ping

log = logging.getLogger(__name__)

Callback = Callable[[Any], None] | None
ErrorCallback = Callable[[str], None] | None

MAX_POOL_FAILURES = 2


class TaskRunner(QObject):
    _done = Signal(int, object)
    _failed = Signal(int, str)

    def __init__(self, use_processes: bool = True, parent: QObject | None = None):
        super().__init__(parent)
        cpu = os.cpu_count() or 2
        # Einen Kern für Audio + Oberfläche freihalten
        self._workers = max(1, min(6, cpu - 1))
        self._use_processes = use_processes
        self._pool: ProcessPoolExecutor | None = None
        self._pool_failures = 0
        self._pool_broken = False
        self._threads = ThreadPoolExecutor(max_workers=4, thread_name_prefix="lptab-io")
        self._ids = itertools.count(1)
        self._callbacks: dict[int, tuple[Callback, ErrorCallback]] = {}
        self._done.connect(self._on_done)
        self._failed.connect(self._on_failed)
        self.pending = 0

    @property
    def uses_processes(self) -> bool:
        return self._use_processes

    # ------------------------------------------------------------------
    def warm_up(self) -> None:
        """Startet die Worker-Prozesse vorab, damit der erste Import nicht bremst."""
        pool = self._process_pool()
        if pool is not None:
            for _ in range(self._workers):
                try:
                    pool.submit(ping)  # Qt-frei: Worker laden nur numpy & Co.
                except Exception:
                    break

    def _discard_pool(self) -> None:
        pool, self._pool = self._pool, None
        if pool is not None:
            try:
                pool.shutdown(wait=False, cancel_futures=True)
            except Exception:
                pass

    def _process_pool(self) -> ProcessPoolExecutor | None:
        if not self._use_processes:
            return None
        if self._pool_broken:
            self._pool_broken = False
            self._pool_failures += 1
            self._discard_pool()
            if self._pool_failures >= MAX_POOL_FAILURES:
                log.warning("Worker-Prozesse wiederholt ausgefallen – arbeite ab jetzt mit Threads.")
                self._use_processes = False
                return None
            log.warning("Worker-Prozesse ausgefallen – starte den Prozess-Pool neu.")
        if self._pool is None:
            try:
                ctx = multiprocessing.get_context("spawn")
                self._pool = ProcessPoolExecutor(max_workers=self._workers, mp_context=ctx)
            except Exception as exc:
                log.warning("Prozess-Pool nicht verfügbar (%s) – nutze Threads.", exc)
                self._use_processes = False
                return None
        return self._pool

    def submit_process(self, fn: Callable, *args: Any, on_done: Callback = None, on_error: ErrorCallback = None) -> None:
        pool = self._process_pool()
        future: Future | None = None
        if pool is not None:
            try:
                future = pool.submit(fn, *args)
            except Exception as exc:  # BrokenProcessPool, RuntimeError (bereits beendet) …
                log.warning("Prozess-Pool nicht nutzbar (%s).", exc)
                self._pool_broken = True
        if future is None:
            self.submit_thread(fn, *args, on_done=on_done, on_error=on_error)
            return
        self._track(future, on_done, on_error, fallback=(fn, args))

    def submit_thread(self, fn: Callable, *args: Any, on_done: Callback = None, on_error: ErrorCallback = None) -> None:
        self._track(self._threads.submit(fn, *args), on_done, on_error)

    def _track(self, future: Future, on_done: Callback, on_error: ErrorCallback,
               fallback: tuple[Callable, tuple] | None = None) -> None:
        cid = next(self._ids)
        self._callbacks[cid] = (on_done, on_error)
        self.pending += 1

        def finished(f: Future, may_retry: bool = True) -> None:  # läuft in einem Pool-Thread
            try:
                result = f.result()
            except BrokenProcessPool:
                # Worker-Prozess gestorben/nicht startbar -> Aufgabe im Thread wiederholen
                self._pool_broken = True
                if may_retry and fallback is not None:
                    try:
                        retry = self._threads.submit(fallback[0], *fallback[1])
                        retry.add_done_callback(lambda f2: finished(f2, False))
                        return
                    except RuntimeError:
                        pass  # Anwendung wird gerade beendet
                self._failed.emit(cid, "Interner Fehler im Hintergrundprozess.")
            except BaseException as exc:  # noqa: BLE001 – alles an die UI melden
                self._failed.emit(cid, str(exc) or exc.__class__.__name__)
            else:
                self._done.emit(cid, result)

        future.add_done_callback(finished)

    @Slot(int, object)
    def _on_done(self, cid: int, result: Any) -> None:
        self.pending -= 1
        on_done, _ = self._callbacks.pop(cid, (None, None))
        if on_done is not None:
            try:
                on_done(result)
            except Exception:
                log.exception("Fehler im Task-Callback")

    @Slot(int, str)
    def _on_failed(self, cid: int, message: str) -> None:
        self.pending -= 1
        _, on_error = self._callbacks.pop(cid, (None, None))
        log.warning("Hintergrundaufgabe fehlgeschlagen: %s", message)
        if on_error is not None:
            try:
                on_error(message)
            except Exception:
                log.exception("Fehler im Fehler-Callback")

    def shutdown(self) -> None:
        self._threads.shutdown(wait=False, cancel_futures=True)
        self._discard_pool()
