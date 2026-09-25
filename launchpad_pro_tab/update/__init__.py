"""Update-Funktion: neue Versionen über GitHub-Releases finden, laden, prüfen, installieren.

Qt-frei (wie ``core``/``audio``), damit die Logik ohne Oberfläche testbar bleibt. Die
Anbindung an QML übernimmt ``bridge.updater.UpdateController``.

Ablauf:

1. ``releases.fetch_releases()`` fragt die GitHub-API ab (``/repos/<repo>/releases``).
2. ``releases.pick_update()`` wählt die neueste passende Version (optional inkl. Beta).
3. ``install.detect_install_kind()`` erkennt, wie das Programm installiert ist, und
   ``install.asset_for()`` das passende Paket (Windows-Installer bzw. Linux-Archiv).
4. ``download.download()`` lädt das Paket und prüft Größe und SHA-256-Prüfsumme.
5. ``install`` startet den Installer (Windows, still, mit Neustart) bzw. tauscht den
   Programmordner aus (Linux) und startet das Programm neu.
"""
