"""Hintergrundaufgaben: Prozess-Pool (CPU-lastig, mehrere Kerne) und Thread-Pool (I/O).

Ergebnisse werden per Qt-Signal in den UI-Thread zurückgeliefert, Callbacks laufen dort.
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

log = logging.getLogger(__name__)

Callback = Callable[[Any], None] | None
ErrorCallback = Callable[[str], None] | None


def _noop() -> int:
    return os.getpid()


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
        self._threads = ThreadPoolExecutor(max_workers=4, thread_name_prefix="lptab-io")
        self._ids = itertools.count(1)
        self._callbacks: dict[int, tuple[Callback, ErrorCallback]] = {}
        self._done.connect(self._on_done)
        self._failed.connect(self._on_failed)
        self.pending = 0

    # ------------------------------------------------------------------
    def warm_up(self) -> None:
        """Startet die Worker-Prozesse vorab, damit der erste Import nicht bremst."""
        pool = self._process_pool()
        if pool is not None:
            for _ in range(self._workers):
                try:
                    pool.submit(_noop)
                except Exception:
                    break

    def _process_pool(self) -> ProcessPoolExecutor | None:
        if not self._use_processes:
            return None
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
        if pool is None:
            self.submit_thread(fn, *args, on_done=on_done, on_error=on_error)
            return
        try:
            future = pool.submit(fn, *args)
        except (BrokenProcessPool, RuntimeError) as exc:
            log.warning("Prozess-Pool defekt (%s) – starte neu.", exc)
            self._pool = None
            pool = self._process_pool()
            if pool is None:
                self.submit_thread(fn, *args, on_done=on_done, on_error=on_error)
                return
            future = pool.submit(fn, *args)
        self._track(future, on_done, on_error)

    def submit_thread(self, fn: Callable, *args: Any, on_done: Callback = None, on_error: ErrorCallback = None) -> None:
        self._track(self._threads.submit(fn, *args), on_done, on_error)

    def _track(self, future: Future, on_done: Callback, on_error: ErrorCallback) -> None:
        cid = next(self._ids)
        self._callbacks[cid] = (on_done, on_error)
        self.pending += 1

        def finished(f: Future) -> None:  # läuft in einem Pool-Thread
            try:
                result = f.result()
            except BaseException as exc:  # noqa: BLE001 – alles an die UI melden
                msg = str(exc) or exc.__class__.__name__
                if isinstance(exc, BrokenProcessPool):
                    msg = "Interner Fehler im Hintergrundprozess."
                self._failed.emit(cid, msg)
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
        if self._pool is not None:
            try:
                self._pool.shutdown(wait=False, cancel_futures=True)
            except Exception:
                pass
            self._pool = None
