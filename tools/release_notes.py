"""Versionshinweise für ein GitHub-Release aus CHANGELOG.md erzeugen.

    python tools/release_notes.py 1.2.0 > notes.md

Nimmt den Abschnitt ``## [1.2.0] …`` aus CHANGELOG.md und ergänzt kurze
Installationshinweise. Der Text erscheint auch im Update-Dialog des Programms.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FOOTER = """
---

### Installation

- **Windows:** `LaunchpadProTAB-Setup-{v}.exe` herunterladen und ausführen.
- **Linux:** `LaunchpadProTAB-{v}-linux-x86_64.tar.gz` entpacken und `./install.sh` ausführen.

Bereits installierte Programme melden das Update beim nächsten Start und installieren es auf Wunsch automatisch.
"""


def section(changelog: str, version: str) -> str:
    pattern = re.compile(rf"^## \[{re.escape(version)}\][^\n]*\n(.*?)(?=^## \[|\Z)", re.MULTILINE | re.DOTALL)
    m = pattern.search(changelog)
    return m.group(1).strip() if m else ""


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    version = sys.argv[1].lstrip("v")
    text = section((ROOT / "CHANGELOG.md").read_text(encoding="utf-8"), version)
    if not text:
        text = f"Launchpad Pro TAB Edition {version}"
    sys.stdout.write(text + "\n" + FOOTER.format(v=version))
    return 0


if __name__ == "__main__":
    sys.exit(main())
