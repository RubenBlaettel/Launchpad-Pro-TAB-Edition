# Änderungen

Alle nennenswerten Änderungen an Launchpad Pro TAB Edition. Der Abschnitt einer Version wird
beim Veröffentlichen automatisch als Versionshinweis ins GitHub-Release übernommen und im
Update-Dialog des Programms angezeigt.

## [1.1.0] – 2026-09-25

### Neu

- **Heller Modus:** Neben dem dunklen Bühnen-Design gibt es jetzt ein helles Design – umschaltbar
  über das Sonnen-/Mond-Symbol oben rechts oder unter *Einstellungen › Darstellung*
  (Dunkel, Hell oder wie Windows).
- **Windows-Installer:** Installation nach `C:\Program Files` mit Auswahl des Zielordners,
  Desktop-Verknüpfung, Startmenü-Eintrag und Dateizuordnung für Projekte (`.lptab`).
  Deinstallation über *Windows-Einstellungen › Apps* oder den Installer – auf Wunsch samt
  aller Projekte und Einstellungen.
- **Automatische Updates:** Beim Start sucht das Programm auf GitHub nach neuen Versionen,
  zeigt die Neuerungen an und installiert das Update auf Wunsch selbst (Download mit
  Prüfsummenkontrolle, danach Neustart). Unter Linux ebenso über das neue Programmpaket.
- **Linux-Paket** mit `install.sh`: Menüeintrag, Desktop-Verknüpfung, Dateizuordnung,
  Deinstallation mit `uninstall.sh`.
- Einstellungen mit Reitern: Darstellung, Audio, Updates, Info.
- Doppelklick auf eine Projektdatei öffnet das Projekt; ein zweiter Programmstart holt das
  laufende Fenster nach vorne (nie zwei Audio-Engines gleichzeitig).

### Verbessert

- Einstellungs- und Projektdateien werden auch mit BOM (z. B. vom Windows-Editor) gelesen.
- Hintergrundprozesse (Dekodieren, Rendern) beenden sich jetzt auch dann, wenn das Programm
  abstürzt oder hart beendet wird – sie blockieren keine Programmdateien mehr.

## [1.0.0] – 2026-09-25

- Erste Version: touch-optimiertes Kachel-Raster (3×3 bis 7×7), Low-Latency-Audio-Engine,
  Bearbeiten & Schneiden mit Wellenform, tonhöhenerhaltendes Time-Stretching,
  Projektverwaltung mit automatischem Speichern und Master-Fader für die Windows-Lautstärke.
