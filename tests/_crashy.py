"""Hilfsfunktion für Tests: stürzt nur in einem Worker-Prozess ab (simuliert blockierte Prozesse)."""

import multiprocessing
import os


def crash_in_worker() -> int:
    if multiprocessing.parent_process() is not None:
        os._exit(3)  # Worker "stirbt" -> BrokenProcessPool im Hauptprozess
    return 42
