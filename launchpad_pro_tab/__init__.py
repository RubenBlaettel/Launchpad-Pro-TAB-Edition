"""Launchpad Pro TAB Edition – touch-optimierte Launchpad-Software für den Theaterbetrieb.

Das Paket ist bewusst in Schichten aufgebaut:

* ``core``   – reine Python-Logik (Datenmodell, Projekte, Einstellungen), ohne Qt
* ``audio``  – Dekodierung, PCM-Cache, Low-Latency-Engine, Time-Stretch, Rendering
* ``system`` – Betriebssystem-Schnittstellen (z. B. Windows-Systemlautstärke)
* ``bridge`` – Qt/QML-Brücke (QObjects, Models, eigene QML-Items)
* ``qml``    – die komplette Benutzeroberfläche in Qt Quick

Wichtig: Dieses Modul darf kein Qt importieren, weil die Audio-Worker-Prozesse
(``audio.tasks``) das Paket ebenfalls laden und schlank bleiben sollen.
"""

__app_name__ = "Launchpad Pro TAB Edition"
__app_id__ = "LaunchpadProTAB"
__version__ = "1.1.0"
__organization__ = "TAB Theater"
# GitHub-Repository, aus dessen Releases sich das Programm aktualisiert
__repository__ = "RubenBlaettel/Launchpad-Pro-TAB-Edition"
