"""Startskript (auch Einstiegspunkt für den PyInstaller-Build)."""

import multiprocessing
import sys

from launchpad_pro_tab.app import main

if __name__ == "__main__":
    multiprocessing.freeze_support()  # nötig für Worker-Prozesse in der Windows-EXE
    sys.exit(main())
