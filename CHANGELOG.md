# Änderungen

Alle nennenswerten Änderungen an Launchpad Pro TAB Edition. Der Abschnitt einer Version wird
beim Veröffentlichen automatisch als Versionshinweis ins GitHub-Release übernommen und im
Update-Dialog des Programms angezeigt.

## [Unveröffentlicht]

### Neu

- **Update-Suche nur mit Zustimmung:** Beim ersten Start fragt Launchpad Pro einmal, ob es
  automatisch nach Updates suchen darf – vorher baut das Programm keine Verbindung ins Internet auf.
  Änderbar unter *Einstellungen › Updates*; die Suche per Knopfdruck geht immer.
- **Digitale Signatur (vorbereitet):** Installer, Deinstaller, Programm und mitgelieferte
  Bibliotheken ohne Herstellersignatur werden über SignPath signiert, sobald die kostenlose
  Open-Source-Signatur eingerichtet ist. Dann blockiert die *intelligente App-Steuerung* von
  Windows 11 die Installation nicht mehr (Fehler 4551).
- **Open Source:** Launchpad Pro steht unter der MIT-Lizenz; Lizenztexte liegen im Programmordner.

### Verbessert

- README: Datenschutzerklärung, Code-Signatur-Richtlinie und Hilfe bei „Fehler 4551“.

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
