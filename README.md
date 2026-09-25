# Launchpad Pro TAB Edition

**Touch-optimierte Launchpad-Software für den Theaterbetrieb.** Audiodateien werden auf farbige,
frei gestaltbare Kacheln gelegt und per Fingertipp (oder Mausklick) mit sehr geringer Latenz
abgespielt – wie bei einem Hardware-Launchpad aus der Veranstaltungstechnik. Dazu gibt es eine
eingebaute Schnitt-/Bearbeitungsfunktion, Projektverwaltung mit automatischem Speichern und einen
Master-Fader für die Windows-Systemlautstärke.

![Hauptansicht](docs/images/02_hauptansicht.png)

> Die Bilder in dieser Anleitung werden automatisch mit `tools/make_screenshots.py` aus der echten
> Anwendung erzeugt. Sie entstanden auf einem Build-Rechner **ohne Soundkarte** – deshalb steht oben
> „Keine Audioausgabe“ und beim Master-Fader „Simuliert“. Auf einem normalen Windows-PC erscheinen
> dort das Audiogerät (z. B. „Lautsprecher (Windows WASAPI) · 48,0 kHz · 10 ms Latenz“) und die echte
> Windows-Lautstärke.

---

## Inhalt

1. [Funktionen im Überblick](#funktionen-im-überblick)
2. [Installation und Start](#installation-und-start)
3. [Bedienungsanleitung](#bedienungsanleitung)
   - [Aufbau der Oberfläche](#aufbau-der-oberfläche)
   - [Projekte](#projekte)
   - [Kacheln belegen](#kacheln-belegen)
   - [Abspielen](#abspielen)
   - [Raster ändern](#raster-ändern)
   - [Bearbeiten & Schneiden](#bearbeiten--schneiden)
   - [Master-Lautstärke](#master-lautstärke)
   - [Einstellungen](#einstellungen)
   - [Tastenkürzel](#tastenkürzel)
4. [Speichern, Sicherheit und Projektordner](#speichern-sicherheit-und-projektordner)
5. [Unterstützte Formate](#unterstützte-formate)
6. [Fehlerbehebung](#fehlerbehebung)
7. [Für Entwickler: Technik & Architektur](#für-entwickler-technik--architektur)
8. [Lizenzen der verwendeten Komponenten](#lizenzen-der-verwendeten-komponenten)

---

## Funktionen im Überblick

| Bereich | Funktion |
|---|---|
| **Kachel-Raster** | 3×3 bis 7×7 Kacheln (Dropdown), eigene Farbe, Titel und Coverbild je Kachel, Leuchten + Restzeit + Fortschrittsbalken während der Wiedergabe |
| **Abspielen** | Linksklick/Tippen = Start, erneut = Stopp (mit kurzem Fade gegen Knackser); mehrere Kacheln gleichzeitig; Schleife je Kachel; **ALLES STOPPEN**; Multi-Touch |
| **Belegen** | Rechtsklick/lang drücken öffnet die Auswahlliste (Audio-Datei, Coverbild, Titel, Farbe, Schleife, **Bearbeiten**, **Löschen** mit „Rückgängig“); Drag & Drop aus dem Explorer oder aus der Liste „Zuletzt verwendet“ |
| **Bearbeiten & Schneiden** | Wellenform (grün auf schwarz), Ausschnitt wählen, Zoom, Schnelligkeit 0,5×–2,0× **ohne Tonhöhenänderung** (Rastpunkt „normal“), Lautstärke 10 %–200 % per Fader (Rastpunkt 100 %), Vorhören, Speichern auf die Kachel – nicht-destruktiv, jederzeit wieder änderbar |
| **Projekte** | Neu, Öffnen, Speichern, Speichern unter, Export als ZIP; alle Audio- und Bilddateien liegen im Projektordner; zyklisches automatisches Speichern; das letzte Projekt wird beim Start geöffnet |
| **Sicherheit** | Speichern beim Schließen, atomares Schreiben + Sicherungskopie, Wiederherstellung einer laufenden Bearbeitung nach einem Absturz, **Show-Modus** (sperrt alle Bearbeitungen während der Vorstellung) |
| **Master** | Roter, horizontaler Master-Fader für die **Windows-Systemlautstärke**, Stummschalter, Stereo-Pegelanzeige mit LIMIT-Anzeige |
| **Leistung** | Vorab dekodierte Audiodaten (kein Laden beim Antippen), WASAPI-Ausgabe mit ~10 ms Puffer, Dekodieren/Rendern parallel auf mehreren CPU-Kernen, GPU-beschleunigte Oberfläche (Qt Quick) |

---

## Installation und Start

### Variante A – fertiges Windows-Programm (empfohlen für den Theater-PC)

Bei jedem Push baut GitHub automatisch ein Windows-Programm:

1. Im Repository auf **Actions** → Workflow **CI** → den neuesten erfolgreichen Lauf öffnen.
2. Unten unter *Artifacts* **LaunchpadProTAB-Windows** herunterladen und entpacken.
3. `LaunchpadProTAB.exe` starten (keine Installation und kein Python nötig).
   Für den Desktop einfach eine Verknüpfung zur EXE anlegen.

### Variante B – Start mit Python (Windows, Linux, macOS)

Voraussetzung: **Python 3.10 oder neuer** (empfohlen 3.12) von [python.org](https://www.python.org/downloads/)
– unter Windows bei der Installation den Haken **„Add python.exe to PATH“** setzen.

| System | Start |
|---|---|
| Windows | Doppelklick auf **`start.bat`** |
| Linux / macOS | `./start.sh` |

Beim **ersten Start** wird automatisch eine eigene Python-Umgebung (`.venv`) angelegt und alle
Abhängigkeiten werden installiert (Internetverbindung nötig, dauert 1–2 Minuten). Danach startet das
Programm sofort.

Manuell geht es so:

```bash
python -m venv .venv
.venv\Scripts\activate            # Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m launchpad_pro_tab
```

Nützliche Startoptionen:

| Option | Wirkung |
|---|---|
| `--fullscreen` | Vollbild (z. B. für ein Touch-Terminal); `F11` schaltet jederzeit um |
| `--project <Pfad>` | bestimmtes Projekt (Ordner, `projekt.lptab` oder Export-ZIP) öffnen |
| `--no-audio` | ohne Soundkarte starten (stumm) |
| `--smoke-test` | Selbsttest: Oberfläche laden, Beispieldateien dekodieren, beenden (Code 0 = OK) |

**Systemvoraussetzungen:** Windows 10/11 (64 bit), 4 GB RAM (8 GB empfohlen), Grafikkarte mit
DirectX 11 (jede Onboard-Grafik der letzten 10 Jahre). Optimiert für Touchscreens ab 1366×768,
ideal 1920×1080.

---

## Bedienungsanleitung

### Aufbau der Oberfläche

![Startbildschirm](docs/images/01_start.png)

| Bereich | Inhalt |
|---|---|
| **Kopfleiste** | Audio-Status, Anzahl laufender Kacheln, **Raster**-Dropdown, **Show-Modus**, **ALLES STOPPEN**, Einstellungen |
| **Links oben – Zuletzt verwendet** | zuletzt benutzte Audiodateien (Suche, `+` zum Hinzufügen, `×` zum Entfernen) |
| **Links – Optionen** | **Projekt**, **Bearbeiten & Schneiden**, **Master-Lautstärke** |
| **Rechts – Kachel-Raster** | die Launchpad-Kacheln |

Beim allerersten Start erscheint rechts der Willkommensbildschirm mit **Neues Projekt** und
**Projekt öffnen**. Ab dann wird beim Start immer das zuletzt benutzte Projekt geladen.

### Projekte

Oben im Bereich **Projekt** stehen der Name des aktuellen Projekts, der Ablageort und der
Speicherstatus („Gespeichert um 14:32“).

| Schaltfläche | Funktion |
|---|---|
| **Öffnen** | Liste der zuletzt geöffneten Projekte; **Durchsuchen …** öffnet Projektordner (`projekt.lptab`) oder exportierte Projekte (`.zip`, werden automatisch entpackt) |
| **Neu** | Pop-up mit **Projektname**, **Ablageort** und **Kachelanzahl** – unten links **Abbrechen**, unten rechts **Projekt erstellen** |
| **Speichern** | sofort speichern (zusätzlich zum automatischen Speichern) |
| **Speichern unter …** | komplettes Projekt (inkl. Audio, Cover, Bearbeitungen) in einen gewählten Ordner kopieren und dort weiterarbeiten |
| **Exportieren** | ganzes Projekt als **ZIP-Datei** (zum Weitergeben, Sichern oder Umziehen auf einen anderen PC) |

![Neues Projekt](docs/images/04_neues_projekt.png)

![Projekt öffnen](docs/images/10_projekt_oeffnen.png)

### Kacheln belegen

Es gibt drei Wege, eine Kachel mit Musik zu belegen:

1. **Rechtsklick** (Maus) oder **lange drücken** (Touch, ca. ½ Sekunde – ein Ring zeigt den
   Fortschritt) öffnet die **Auswahlliste** der Kachel. Links stehen die zuletzt verwendeten
   Audiodateien – antippen genügt. Über **Datei durchsuchen …** wählt man eine neue Datei.
   Eine **leere Kachel** öffnet die Auswahlliste schon beim einfachen Antippen.
2. **Drag & Drop aus dem Explorer:** Audiodatei direkt auf die Kachel ziehen. Mehrere Dateien auf
   einmal belegen die Kachel und die jeweils nächsten freien Kacheln.
3. **Drag & Drop aus „Zuletzt verwendet“:** einen Eintrag **waagrecht nach rechts** auf die Kachel
   ziehen (senkrechtes Wischen scrollt die Liste).

Die Audiodatei wird dabei **in den Projektordner kopiert** – das Projekt bleibt vollständig, auch
wenn die Originaldatei später verschoben wird.

In der Auswahlliste lassen sich außerdem einstellen:

- **Coverbild** (JPG, PNG, ICO) – wird automatisch kachelfüllend eingepasst. Alternativ ein Bild
  per Drag & Drop auf eine *bereits belegte* Kachel ziehen.
- **Titel** (ohne Eingabe wird der Dateiname angezeigt)
- **Farbe** (12 Launchpad-Farben)
- **Schleife (Loop)** – die Kachel wiederholt, bis sie erneut angetippt wird
- **Bearbeiten** – öffnet die Spur im Bereich *Bearbeiten & Schneiden*
- **Löschen** – Kachel wird wieder unbelegt (unten erscheint kurz **Rückgängig**)

![Auswahlliste einer Kachel](docs/images/03_kachelmenue.png)

### Abspielen

- **Maus:** Linksklick startet sofort beim Drücken. Erneuter Klick stoppt (mit kurzem Ausblenden).
- **Touch:** kurzes Antippen startet/stoppt. **Mehrere Finger gleichzeitig** funktionieren.
- Beliebig viele Kacheln können **gleichzeitig** laufen (z. B. Regen-Atmo + Donner).
  Ein Limiter schützt dabei vor Übersteuerung (Anzeige **LIMIT** beim Master).
- Laufende Kacheln **leuchten**, zeigen die **Restzeit** und einen **Fortschrittsbalken**.
- **ALLES STOPPEN** (oder Taste `Esc`) beendet alle Kacheln sofort.

![Kachel-Raster während der Wiedergabe](docs/images/08_raster.png)

#### Show-Modus (für die Vorstellung)

Der Schalter **Show-Modus** in der Kopfleiste sperrt alles, was während einer Vorstellung nicht
passieren darf: Kein Menü durch versehentliches langes Drücken, kein Drag & Drop, kein Bearbeiten,
kein Rasterwechsel. Zusätzlich lösen Kacheln bei Touch **schon beim Berühren** aus (noch schneller).
Oben erscheint ein gelber Hinweis, solange der Show-Modus aktiv ist.

![Show-Modus](docs/images/09_show_modus.png)

### Raster ändern

Das Dropdown **Raster** in der Kopfleiste stellt 3×3 bis 7×7 Kacheln ein. Beim **Vergrößern** bleiben
alle Kacheln erhalten. Beim **Verkleinern** erscheint immer eine Rückfrage; sie nennt die Zahl der
belegten Kacheln, die außerhalb des neuen Rasters liegen. Mit **Fortfahren** werden deren Inhalte
verworfen, mit **Abbrechen** bleibt alles, wie es war.

![Raster verkleinern](docs/images/05_raster_verkleinern.png)

### Bearbeiten & Schneiden

Der Bereich ist ausgegraut, bis in der Auswahlliste einer Kachel **Bearbeiten** gewählt wird.

![Bearbeiten & Schneiden](docs/images/06_bearbeiten.png)

1. **Wellenform:** zeigt die ganze Audiospur (grün auf schwarz mit Zeitraster). Der Bereich
   zwischen den gelben Markierungen ist die **Auswahl** (der Ausschnitt, der später gespielt wird).
   - Gelbe Markierungen **ziehen**, um Anfang und Ende festzulegen.
   - In die Wellenform **tippen** setzt die Abspielposition (weißer Strich).
   - **Zoom:** Tasten unten rechts in der Wellenform, zwei Finger (Pinch) oder Mausrad; bei Zoom
     die Wellenform mit einem Finger verschieben. Der Balken darunter zeigt, welcher Teil zu sehen ist.
2. **Anfang hier / Ende hier:** setzt die Auswahl exakt an die aktuelle Abspielposition – ideal
   zum Schneiden „nach Gehör“: abspielen, an der richtigen Stelle **Pause**, **Anfang hier**.
3. **Schnelligkeit:** 0,5× bis 2,0×; die **Tonhöhe bleibt erhalten** (keine „Micky-Maus-Stimme“).
   Der Regler rastet bei **normal** (1,0×) ein; Doppeltippen setzt ihn zurück. Unter den Zeiten
   steht die resultierende Länge („Auswahl 0:33,4 → 0:26,7“).
4. **Tasten:** **Von Anfang** (zum Auswahlanfang), **Schritt zurück / Schritt vor** (1 Sekunde;
   gedrückt halten = Dauerlauf), **Play**, **Pause**, **Zurücksetzen** (alles auf Standard: ganze
   Datei, 1,0×, 100 %).
5. **Lautstärke-Fader** (rechts, Mischpult-Optik): 10 % bis 200 %, rastet bei **100 %** ein;
   Doppeltippen = 100 %. Bei Werten über 100 % verhindert ein Limiter Verzerrungen.
6. **Speichern:** rendert die Bearbeitung und legt sie auf die Kachel. Danach ist der Bereich wieder
   ausgegraut und auf Standardwerte zurückgesetzt. **Verwerfen** (oben rechts) schließt ohne zu
   speichern.

Die Bearbeitung ist **nicht-destruktiv**: Die Originaldatei bleibt unverändert im Projekt, die
bearbeitete Fassung liegt zusätzlich unter `audio/bearbeitet/`. Wird die Kachel später erneut
bearbeitet, erscheinen die bisherigen Einstellungen (Auswahl, Tempo, Lautstärke) wieder und können
angepasst werden – auch nach einem Neustart. Der Zwischenstand einer laufenden Bearbeitung wird alle
5 Sekunden gesichert und nach einem Absturz automatisch wiederhergestellt.

### Master-Lautstärke

Der **rote, horizontale Master-Fader** steuert direkt die **Windows-Systemlautstärke** (dieselbe wie
das Lautsprechersymbol in der Taskleiste). Änderungen von außen (Tastatur-Lautstärketasten)
werden übernommen. Links daneben der **Stummschalter**, darunter die Stereo-Pegelanzeige der App mit
**LIMIT**-Anzeige.

![Master-Lautstärke](docs/images/07_master.png)

### Einstellungen

Über das Regler-Symbol oben rechts:

- **Audio-Ausgabe:** Standardgerät (automatisch, unter Windows über WASAPI mit geringer Latenz) oder
  ein bestimmtes Gerät (z. B. USB-Audiointerface des Mischpults).
- **Puffergröße:** *Automatisch* ist die niedrigste stabile Latenz. Bei Knacksern auf schwachen
  Rechnern 512 oder 1024 wählen.

![Einstellungen](docs/images/11_einstellungen.png)

### Tastenkürzel

| Taste | Funktion |
|---|---|
| `Esc` | ALLES STOPPEN |
| `Strg+S` | Projekt speichern |
| `Strg+Umschalt+S` | Speichern unter |
| `Strg+E` | Projekt exportieren |
| `Strg+O` / `Strg+N` | Projekt öffnen / neues Projekt |
| `Leertaste` | Play/Pause im Bereich *Bearbeiten & Schneiden* |
| `F11` | Vollbild ein/aus |

---

## Speichern, Sicherheit und Projektordner

- **Automatisch:** Jede Änderung wird nach 2 Sekunden gespeichert, zusätzlich spätestens alle
  30 Sekunden. Der Status steht im Bereich *Projekt*.
- **Beim Schließen** wird das Projekt immer zuerst sicher gespeichert. Sollte das fehlschlagen
  (z. B. USB-Stick abgezogen), fragt das Programm nach, statt still Daten zu verlieren.
- **Absturzsicher:** Gespeichert wird in eine temporäre Datei, die erst danach die alte ersetzt.
  Die vorherige Fassung bleibt als Sicherung erhalten und wird bei einer beschädigten Projektdatei
  automatisch geladen.
- **Beim nächsten Start** wird das zuletzt geöffnete Projekt automatisch geladen.

Aufbau eines Projektordners:

```text
Sommerstück 2026/
├── projekt.lptab          Konfiguration aller Kacheln (JSON, lesbar)
├── audio/                 Kopien der Original-Audiodateien
│   └── bearbeitet/        gerenderte, bearbeitete Fassungen (FLAC, 24 bit)
├── cover/                 Coverbilder
├── .autosave/             Sicherungen + Zwischenstand der Bearbeitung
└── .cache/                vorbereitete Audiodaten (wird automatisch neu erzeugt, nicht exportiert)
```

Standard-Ablageort für neue Projekte: `Dokumente\Launchpad Pro TAB\`.
Programmeinstellungen und Protokoll (`launchpad.log`): `%APPDATA%\LaunchpadProTAB\`.

---

## Unterstützte Formate

| Art | Formate |
|---|---|
| **Audio** | WAV, FLAC, MP3, OGG/Vorbis, Opus, M4A/AAC, ALAC, WMA, AIFF, AC3, MP2, AMR, WebM/MKA, CAF, W64, sowie die Tonspur von MP4/MOV-Videos (FFmpeg) |
| **Coverbilder** | JPG, PNG, ICO (bei ICO wird automatisch die größte enthaltene Bildgröße verwendet) |
| **Export** | ZIP (ganzes Projekt) |
| **Bearbeitete Spuren** | FLAC, 24 bit, in der Samplerate der Audioausgabe |

Mono-Dateien werden auf beide Kanäle verteilt, Mehrkanal-Dateien (z. B. 5.1) normgerecht auf Stereo
heruntergemischt, abweichende Sampleraten in hoher Qualität umgerechnet.

---

## Fehlerbehebung

| Problem | Lösung |
|---|---|
| Kein Ton, oben steht „Keine Audioausgabe“ | Audiogerät prüfen (angeschlossen? in Windows aktiviert?), dann in den **Einstellungen** das Gerät neu wählen. |
| Knacksen / Aussetzer | In den **Einstellungen** eine größere Puffergröße (512 oder 1024) wählen. Energiesparmodus von Windows auf „Höchstleistung“ stellen. |
| Master-Fader zeigt „Simuliert“ | Die Systemlautstärke ist nicht erreichbar (z. B. kein Wiedergabegerät). Der Fader funktioniert dann nur optisch. |
| Kachel zeigt „Datei fehlt“ | Die Audiodatei wurde aus dem Projektordner entfernt. Kachel neu belegen. |
| Datei lässt sich nicht laden | Format beschädigt oder ohne Tonspur – Meldung unten lesen; ggf. Datei in WAV/MP3 umwandeln. |
| Programm startet nicht | `launchpad.log` und `absturz.log` in `%APPDATA%\LaunchpadProTAB\` ansehen. |

---

## Für Entwickler: Technik & Architektur

**Technologie:** Python 3 + **PySide6 (Qt 6)**, Oberfläche komplett in **Qt Quick/QML**
(GPU-gerendert über Direct3D 11 unter Windows), Audio über **PortAudio/WASAPI** (`sounddevice`),
Dekodierung über **libsndfile** (`soundfile`) und **FFmpeg** (`av`), Resampling mit **soxr**,
DSP mit **numpy**, Windows-Lautstärke über **Core Audio** (`pycaw`).

```text
┌────────────────────────── QML (launchpad_pro_tab/qml) ──────────────────────────┐
│ Main · TopBar · TileGrid/Tile · RecentList · ProjectSection · EditorSection ·    │
│ MasterSection · TileMenu · Dialoge · VFader/HFader/SpeedSlider/LevelMeter        │
└───────────────▲──────────────────────────▲──────────────────────────▲───────────┘
                │ Properties/Slots/Signale  │                          │
┌───────────────┴────────┐  ┌──────────────┴─────────┐  ┌─────────────┴───────────┐
│ bridge.Backend         │  │ bridge.EditorController│  │ bridge.MasterVolume-    │
│ Projekte, Kacheln,     │  │ Vorschau, Auswahl,     │  │ Controller (Thread)     │
│ Drag&Drop, Autosave    │  │ Tempo, Gain, Rendern   │  └─────────────▲───────────┘
└───────┬───────┬────────┘  └──────┬─────────────────┘                │
        │       │ TaskRunner (Prozess-Pool = mehrere CPU-Kerne)        │
┌───────▼──┐ ┌──▼───────────────────────────┐  ┌───────────────┐ ┌───┴──────────────┐
│ core     │ │ audio.tasks: decode → cache, │  │ audio.engine  │ │ system.volume    │
│ Projekt, │ │ render_edit (WSOLA, Limiter) │  │ Mixer im      │ │ Windows / Linux /│
│ Modelle, │ └──────────────────────────────┘  │ Audio-Thread  │ │ macOS / Dummy    │
│ Settings │                                   └───────▲───────┘ └──────────────────┘
└──────────┘                                           │ PortAudio (WASAPI)
```

**Maßnahmen für geringe Latenz und hohe Leistung**

- Jede Audiodatei wird **einmalig** im Hintergrund (eigene Prozesse, mehrere Kerne) dekodiert und als
  int16-PCM im `.cache` des Projekts abgelegt. Beim Antippen wird nur eine „Stimme“ im Mixer
  angelegt – keine Datei- oder Dekodierarbeit. Der Anfang jeder Datei wird vorab in den Speicher
  geladen, ein Prefetch-Thread liest laufende Dateien voraus (memory mapping, kaum RAM-Verbrauch).
- Der Mixer läuft im Audio-Thread von PortAudio (WASAPI, „low latency“) und bekommt Befehle über eine
  lock-freie Warteschlange. Mausklicks lösen **beim Drücken** aus.
- Tonhöhenerhaltendes **Time-Stretching (WSOLA)** ist streamingfähig: dieselbe Implementierung
  läuft live in der Vorschau und beim Rendern (was man hört, wird gespeichert). Bei 1,0× arbeitet sie
  bit-genau.
- Die Oberfläche wird von der GPU gezeichnet; Animationen (Leuchten, Fortschritt) laufen im
  Render-Thread. Die Wellenform wird nur bei Zoom/Auswahl neu gezeichnet.

**Schnittstellen (austauschbare Bausteine)**

| Schnittstelle | Implementierungen |
|---|---|
| `audio.output.OutputBackend` | `SoundDeviceBackend` (PortAudio/WASAPI), `NullBackend` (ohne Soundkarte) |
| `audio.decoder.decode()` | libsndfile → FFmpeg (automatischer Fallback) |
| `system.volume.SystemVolume` | `WindowsVolume` (Core Audio), `PulseVolume`, `WirePlumberVolume`, `AlsaVolume`, `MacVolume`, `DummyVolume` |
| `bridge.Backend` | einzige Schnittstelle der Oberfläche zur Logik (Slots/Properties/Signale) |

**Projektstruktur**

```text
launchpad_pro_tab/
├── app.py              Start, Logging, Qt-Anwendung, Smoke-Test
├── core/               Qt-frei: models, project, settings, paths, util, constants
├── audio/              decoder, cache, dsp, timestretch, engine, output, tasks
├── system/volume.py    Systemlautstärke je Betriebssystem
├── bridge/             backend, editor, models, waveform (QML-Element), volume, covers, tasks
├── qml/                komplette Oberfläche + icons/ (SVG)
└── assets/             Schrift Inter (OFL), Programm-Icon
tests/                  pytest (Kernlogik, Audio, UI inkl. simulierter Maus/Touch-Eingaben)
tools/                  make_screenshots.py, demo_assets.py, make_icons.py, make_icon.py
packaging/              PyInstaller-Spec für die Windows-EXE
.github/workflows/      CI: Tests (Linux + Windows), EXE-Build + Smoke-Test der EXE
```

**Entwickeln und prüfen**

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q                                   # alle Tests (ohne Soundkarte/Bildschirm)
python -m launchpad_pro_tab --smoke-test              # Oberfläche + Dekodierung prüfen
xvfb-run -a -s "-screen 0 1920x1080x24" python tools/make_screenshots.py   # README-Bilder (Linux)
pyinstaller packaging/launchpad_pro_tab.spec --noconfirm                   # Windows-EXE
```

Weitere Hinweise für die Weiterentwicklung (auch mit Claude Code) stehen in [`CLAUDE.md`](CLAUDE.md).

---

## Lizenzen der verwendeten Komponenten

Siehe [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md). Alle Klänge und Bilder in den Screenshots
sind synthetisch erzeugt (`tools/demo_assets.py`).
