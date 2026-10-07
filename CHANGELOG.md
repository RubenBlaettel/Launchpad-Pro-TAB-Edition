# Änderungen

Alle nennenswerten Änderungen an Launchpad Pro TAB Edition. Der Abschnitt einer Version wird
beim Veröffentlichen automatisch als Versionshinweis ins GitHub-Release übernommen und im
Update-Dialog des Programms angezeigt.

## [Unveröffentlicht]

### Neu

- **Projekte in Registerkarten:** Mehrere Projekte sind gleichzeitig geöffnet – oben über dem
  Kachel-Raster lässt sich wie im Browser zwischen ihnen wechseln. Kacheln im Hintergrund spielen
  weiter (die Karte zeigt dann ▶ und die Anzahl), **ALLES STOPPEN** stoppt alle Karten.
  „+“ öffnet eine leere Karte mit Startseite; offene Karten werden beim nächsten Start
  wiederhergestellt. Geschlossen wird über das `×` oder die mittlere Maustaste; am Touchmonitor
  holt Antippen der Karte das Projekt nach vorne. Tastenkürzel: `Strg+Tab` / `Strg+Umschalt+Tab`,
  `Strg+T`, `Strg+W`.
- **Projektauswahl:** Ein Klick auf das Projektfeld (Bereich *Projekt*) öffnet die Liste der
  zuletzt geöffneten Projekte – offene springen zu ihrer Karte, andere öffnen sich in einer neuen.
- **Projekte löschen:** Der Papierkorb in der Projektauswahl (und auf der Startseite) verschiebt
  ein Projekt nach Rückfrage in den Papierkorb des Systems – wiederherstellbar. Ein geöffnetes
  Projekt wird vorher gespeichert und seine Registerkarte geschlossen. Im Show-Modus gesperrt.
- **Kacheln verschieben:** Eine Kachel auf eine andere ziehen tauscht die Plätze (auf eine leere
  verschiebt sie). Laufende Kacheln spielen dabei weiter. Mit der Maus startet ein Klick weiterhin
  sofort – beginnt man zu ziehen, bricht der gerade gestartete Ton ab. Im Show-Modus gesperrt.
- **Kachel zum Bearbeiten ziehen:** Eine Kachel lässt sich direkt in den Bereich
  *Bearbeiten & Schneiden* ziehen, um sie dort zu öffnen. Während des Ziehens ist der Bereich
  grün umrandet; ein Hinweis warnt, wenn dadurch eine andere offene Bearbeitung verworfen würde.
  Die bereits geöffnete Kachel bleibt unverändert offen.
- **Vollbild-Schalter** unter *Einstellungen › Darstellung*. Die Wahl bleibt gespeichert – das
  Programm startet dann direkt im Vollbild. `F11` schaltet weiterhin um und hält den Schalter
  aktuell; `--fullscreen` gilt nur für den jeweiligen Start.
- **Update-Suche nur mit Zustimmung:** Beim ersten Start fragt Launchpad Pro einmal, ob es
  automatisch nach Updates suchen darf – vorher baut das Programm keine Verbindung ins Internet auf.
  Änderbar unter *Einstellungen › Updates*; die Suche per Knopfdruck geht immer.
- **Microsoft-Store-Fassung:** Launchpad Pro gibt es als MSIX-Paket für den Microsoft Store. Dort
  signiert Microsoft das Programm – es startet damit auch auf PCs mit der *intelligenten
  App-Steuerung* von Windows 11, die den unsignierten Installer blockiert (Fehler 4551). Updates
  verteilt der Store automatisch; die Store-Fassung sucht nicht selbst im Internet.
- **Installer erkennt die intelligente App-Steuerung** und weist auf die Store-Fassung hin, statt
  ein Programm zu installieren, das danach nicht starten würde.
- **Open Source:** Launchpad Pro steht unter der MIT-Lizenz; Lizenztexte liegen im Programmordner.

### Verbessert

- **Schnelligkeit ändern klingt nicht mehr verzerrt:** Das Tempo wird jetzt mit einem
  Phase-Vocoder geändert. Das bisherige Verfahren (WSOLA) klang bei Musik mit mehreren Tönen rau
  und „kratzig“. Akkorde, Klavier und Glocken bleiben jetzt sauber (Störanteil im Test von −9 dB
  auf −30 bis −44 dB), Schläge und Einsätze bleiben knackig (kein Vorecho, keine doppelten
  Schläge), das Stereobild bleibt erhalten. Vorschau und gespeicherte Fassung klingen weiterhin
  gleich. Bereits gespeicherte Bearbeitungen behalten ihren Klang, bis man sie erneut speichert
  (Kachel bearbeiten → *Speichern*).
- README: Datenschutzerklärung, Code-Signatur und Hilfe bei „Fehler 4551“.

### Behoben

- MP3-, M4A- und andere über FFmpeg gelesene Dateien ließen sich mit der neuesten FFmpeg-Anbindung
  (PyAV 19) nicht mehr laden („unexpected keyword argument 'metadata_errors'“).
- Touchmonitor: Das Kachel-Menü (lange drücken) schloss sich sofort wieder, wenn der Finger etwas
  länger lag. Windows macht aus „Gedrückt halten“ beim Loslassen einen Rechtsklick, der neben dem
  Menü landete. Diese Nachbildung ist im Programmfenster jetzt abgeschaltet und wird zusätzlich
  herausgefiltert; Rechtsklicks mit Maus oder Touchpad funktionieren wie bisher.
- Klicks auf Farbkreise, Listenzeilen und Farbschema-Karten in Dialogen lösten zusätzlich die
  Kachel **hinter** dem Dialog aus. Auch Hinweis-Meldungen und die Show-Modus-Leiste lassen keine
  Klicks mehr an die Kacheln darunter durch; Antippen einer Meldung schließt sie.
- Heller Modus: Master-Lautstärke und Lautstärke-Fader im Editor haben jetzt eine hellgraue Bahn
  (vorher schwarz).

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
