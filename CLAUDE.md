# CLAUDE.md – Langzeitgedächtnis für Launchpad Pro TAB Edition

Diese Datei ist die Arbeitsgrundlage für Claude (und Menschen), um auf jedem Gerät mit denselben
Voraussetzungen weiterzuarbeiten. **Bei jeder größeren Änderung aktualisieren.**

## 1. Worum geht es?

Touch-optimierte Launchpad-/Soundboard-Software für einen **Theaterverein** („TAB“). Kacheln im
Raster (3×3 … 7×7) werden mit Audiodateien belegt und per Tippen/Klick abgespielt. Zielplattform:
**Windows 10/11 mit Touchscreen**; läuft auch unter Linux/macOS. Sprache der Oberfläche,
Kommentare, Doku: **Deutsch**.

### Arbeitsregeln des Auftraggebers (verbindlich)

- Effizienz/geringe Latenz haben Priorität (Multithreading/mehrere Kerne/GPU wo sinnvoll).
- Saubere **Schnittstellen** (austauschbare Backends, eine QML-Fassade `Backend`).
- **Bei Unklarheiten nachfragen** (AskUserQuestion-Tool), nicht raten.
- **Vor jedem Push Lauffähigkeit prüfen**: `pytest`, `--smoke-test`, bei UI-Änderungen Screenshots
  ansehen. Nur fehlerfrei pushen.
- **README.md** mit Anleitung + aktuellen Bildern der Oberfläche pflegen (`tools/make_screenshots.py`).
- Diese **CLAUDE.md** aktuell halten.
- Entwicklungszweig bisher: `claude/launchpad-pro-tab-frontend-pqz33o` (Remote: GitHub
  `RubenBlaettel/Launchpad-Pro-TAB-Edition`). PRs nur auf ausdrücklichen Wunsch.

### Entscheidungen aus Rückfragen (Stand v1.0)

| Frage | Entscheidung |
|---|---|
| Technologie | **Python + PySide6 (Qt 6, QML/Qt Quick)** |
| Antippen einer laufenden Kachel | **Start/Stopp-Umschalter**, mehrere Kacheln parallel, Schleife je Kachel, „ALLES STOPPEN“ |
| Tempo-Regler | **Tonhöhe bleibt erhalten** (Time-Stretch, WSOLA), 0,5×–2,0×, Rastpunkt 1,0× |

### Eigene Designentscheidungen (begründet, bei Bedarf mit Nutzer abstimmen)

- **Show-Modus** (Kopfleiste): sperrt Menü/Drag&Drop/Bearbeiten, Touch löst beim *Berühren* aus.
  Grund: Im normalen Modus muss Touch bis zum Loslassen warten, um „lang drücken“ zu erkennen.
- Maus-Linksklick löst **beim Drücken** aus (geringste Latenz), Rechtsklick öffnet das Menü.
- Leere Kachel antippen = Auswahlliste zum Belegen.
- Audio wird beim Belegen **in den Projektordner kopiert** (Duplikate per SHA-1 erkannt).
- Bearbeitungen sind **nicht-destruktiv**: `TileData.original` + `TileData.edit` (Parameter) +
  gerenderte FLAC-Datei in `audio/bearbeitet/`. Erneutes Bearbeiten lädt das Original + Parameter.
- „Schritt vor/zurück“ = 1 s, Taste gedrückt halten = Auto-Repeat.
- Löschen einer Kachel mit **Rückgängig** (Toast, 8 s) statt Rückfrage.
- Beim Raster-Verkleinern werden Kachel-*Belegungen* verworfen; Audiokopien bleiben im `audio/`-Ordner
  (Sicherheit), verwaiste gerenderte Bearbeitungen werden beim nächsten Öffnen gelöscht.

## 2. Schnellstart für Entwicklung

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
python -m pip install -r requirements-dev.txt
python -m pytest -q                                     # ~50 Tests, ~10 s, ohne Soundkarte/Bildschirm
python -m launchpad_pro_tab --smoke-test                # Exit-Code 0 = OK
python -m launchpad_pro_tab                             # App starten (--no-audio, --fullscreen, --project)
```

**Claude Code im Web / Linux-Container** braucht zusätzlich Systembibliotheken, sonst
`ImportError: libEGL.so.1` bzw. kein PortAudio:

```bash
apt-get install -y libegl1 libgl1 libgl1-mesa-dri libxkbcommon0 libxkbcommon-x11-0 libfontconfig1 \
  libdbus-1-3 libportaudio2 xvfb libxcb-cursor0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 \
  libxcb-randr0 libxcb-render-util0 libxcb-shape0 libxcb-xinerama0 libxcb-xkb1 libxcb-xfixes0
```

- Tests: `QT_QPA_PLATFORM=offscreen` (setzt `tests/conftest.py` automatisch). Offscreen nutzt den
  Software-Renderer → **MultiEffect/Shader werden dort nicht gezeichnet** (keine Fehlermeldung).
- Echte Screenshots mit GPU-Effekten: **Xvfb + Mesa llvmpipe**:
  `xvfb-run -a -s "-screen 0 1920x1080x24" python tools/make_screenshots.py` → `docs/images/*.png`.
  Danach die Bilder mit dem Read-Tool ansehen und prüfen!
- Windows-EXE: `pyinstaller packaging/launchpad_pro_tab.spec --noconfirm` → `dist/LaunchpadProTAB/`.
  Das CI (`.github/workflows/ci.yml`) testet unter Linux + Windows, baut die EXE, führt
  `LaunchpadProTAB.exe --smoke-test` aus und lädt sie als Artefakt `LaunchpadProTAB-Windows` hoch.

## 3. Architektur (wo liegt was?)

```text
launchpad_pro_tab/
  app.py              create_app() (für App, Tests, Screenshots), main(), smoke_test(), Logging
  core/               KEIN Qt! constants, models (ProjectData/TileData/EditParams), project (Dateisystem),
                      settings (AppSettings JSON), paths (LPTAB_CONFIG_DIR/LPTAB_PROJECTS_DIR), util
  audio/              KEIN Qt! (wird in Worker-Prozessen importiert)
    decoder.py        decode(path, sr) -> float32 (frames,2); soundfile zuerst für WAV/FLAC/OGG/AIFF,
                      sonst PyAV/FFmpeg; soxr-Resampling; to_stereo (5.1-Downmix)
    cache.py          PCM-Cache im Projekt-.cache: <key>.pcm (int16 stereo), <key>.peaks.npy, <key>.json
                      key = sha1(Dateiname|Größe|mtime|Samplerate|Version); open_pcm() = np.memmap
    dsp.py            Peaks (min/max/rms je 256 Frames), aggregate_peaks, soft_limit, Kantenblenden
    timestretch.py    WsolaStretcher (streaming, Tempo live änderbar, bit-genau bei 1.0), stretch()
    engine.py         AudioEngine: Mixer im PortAudio-Callback, Befehls-deque, Snapshots, Limiter,
                      Pegel, Vorschau-Stimme (_PreviewVoice), Prefetch-Thread
    output.py         SoundDeviceBackend (WASAPI bevorzugt), NullBackend, Geräteliste
    tasks.py          Prozess-Aufgaben: prepare(), render_edit(), probe_file()
  system/volume.py    SystemVolume-Protokoll + Windows(pycaw)/Pulse/WirePlumber/ALSA/macOS/Dummy
  bridge/             Qt-Brücke
    backend.py        Backend (QML: `backend`) – Projekte, Kacheln, DnD, Autosave, Tick (30 Hz)
    editor.py         EditorController (QML: `editor`) – Bearbeiten & Schneiden
    volume.py         MasterVolumeController (QML: `master`) – eigener Thread
    models.py         TileModel, RecentAudioModel, RecentProjectsModel (QAbstractListModel)
    waveform.py       WaveformView (QQuickPaintedItem, `import LaunchpadPro`)
    covers.py         Cover importieren (ICO: größtes Bild, max. 1024 px)
    tasks.py          TaskRunner: ProcessPool(spawn) + ThreadPool, Ergebnisse per Signal in UI-Thread
    qtutil.py         rprop()/PropertyObject._set(), to_local_path()
  qml/                Main.qml + Komponenten (flach), Theme.qml (Singleton via qmldir), icons/*.svg
tools/                make_screenshots.py, demo_assets.py (synthetische Klänge/Cover), make_icons.py, make_icon.py
tests/                test_models, test_project, test_audio, test_settings_volume, test_ui (inkl. Touch/Maus)
```

### Datenfluss Kachel antippen

`Tile.qml` (TapHandler) → `backend.triggerTile(i)` → `engine.toggle(key, pcm, loop)` (deque) →
Audio-Callback entscheidet atomar Start/Stopp → `engine.snapshot` → `Backend._tick()` (30 Hz)
→ `TileModel.refresh()` → QML zeigt Leuchten/Restzeit.

### Datenfluss Belegen

`assignAudio` → Thread: `Project.import_audio` (Kopie) → Prozess: `tasks.prepare` (Dekodieren →
Cache) → UI-Thread: `open_pcm` (memmap) + Kopf vorladen → Kachel bereit. Tokens (`_tokens[key]`)
verwerfen veraltete Ergebnisse.

## 4. Invarianten & Regeln (nicht brechen!)

- **Projektdaten (`ProjectData`) nur im UI-Thread lesen/schreiben.** Hintergrund-Threads bekommen
  fertige Werte (siehe `Backend._schedule_cleanup`, `export_zip(save_first=False)`).
- **Audio-Callback darf nie blockieren oder werfen**: keine Locks, keine Datei-I/O, keine
  Python-Objekt-Erzeugung im großen Stil; Befehle nur über `AudioEngine._cmds`.
- `audio/` und `core/` importieren **kein PySide6** (Worker-Prozesse, Tests).
- Große Audiodaten nie zwischen Prozessen kopieren → immer über den Cache (Datei + memmap).
- Mischen in float32: int16-Daten immer mit `np.float32`-Skalar multiplizieren (sonst float64!).
- `sys.setswitchinterval(0.001)` in `main()` – verkürzt GIL-Wartezeit des Audio-Threads.
- Projektformat: `projekt.lptab` (JSON, `format`/`version`). Bei Formatänderungen
  `PROJECT_FORMAT_VERSION` erhöhen und Migration in `ProjectData.from_dict` ergänzen.
- Pfade im Projekt **relativ** speichern (`Project.rel()`), damit Projekte verschiebbar bleiben.
- Speichern immer atomar (`util.atomic_write_json`); vorherige Fassung → `.autosave/projekt.lptab.bak`.
- Neue UI-Texte auf Deutsch, Touch-Ziele ≥ 48 px (`Theme.touch`).

## 5. Stolperfallen (bereits einmal passiert)

- QML: `id: scale` (oder andere Namen von Item-Properties wie `left`, `right`, `state`) **überschattet**
  Properties → Bindungen liefern Unsinn. Eigene Properties nicht `left/right/name` nennen
  (`IconImage.name` ist FINAL → daher ist `Icon.qml` ein Item-Wrapper).
- QML: `Qt.colorEqual("", …)` wirft „Invalid color name“ → Strings vergleichen.
- QML: Enums wie `Popup.CloseOnEscape` brauchen `import QtQuick.Controls.Basic` in *der* Datei.
- QML-Funktionen in JS-Array-Modellen (`model: [{f: () => …}]`) nicht verwenden.
- `Popup.opened` ist schon während der Schließ-Animation `false` → in Tests auf `visible` warten.
- Repeater-Delegates sind **keine QObject-Kinder** → `findChild` findet sie nicht; über
  `childItems()` suchen (siehe `tests/test_ui.py::_find_item`).
- `json.JSONDecodeError` ist eine Unterklasse von `ValueError` → Reihenfolge der `except` beachten.
- QML-Engine vor dem Backend zerstören (`AppContext.dispose()`), sonst „Cannot read property … of null“.
- PyInstaller: `collect_data_files()` findet das Paket während der Spec-Auswertung nicht →
  Daten per `os.walk` einsammeln (siehe Spec). Immer `--smoke-test` gegen die EXE laufen lassen.
- MultiEffect-„Leuchten“: `shadowEnabled` auf eine unsichtbare Quell-Rechteckfläche wirkt deutlich
  besser als `blurEnabled`.
- Offscreen-Plattform im Test: Bildschirm nur 800×800 → Layout eng, aber funktionsfähig.

## 6. Teststrategie

- `tests/test_audio.py`: Formate (WAV/FLAC/OGG/MP3/AIFF via libsndfile, M4A/Opus via FFmpeg),
  Resampling, WSOLA (Länge, Tonhöhe, Streaming), Cache, Rendern, Engine (Fade, Loop, Limiter, Vorschau).
- `tests/test_project.py`: Anlegen/Öffnen/Speichern, Sicherung bei beschädigter Datei, Import/
  Duplikate, Speichern unter, ZIP-Export/-Import inkl. Zip-Slip-Schutz, Zwischenstand.
- `tests/test_ui.py`: komplette Oberfläche mit Backend; Belegen, DnD, Cover (PNG/ICO), Abspielen,
  Bearbeiten/Rendern, Absturz-Wiederherstellung, Raster, Löschen/Rückgängig, Export,
  **echte Maus-/Touch-Ereignisse** (QTest) inkl. Langdrücken und Show-Modus.
- Neue Features immer mit Test + Screenshot-Kontrolle.

## 7. Ideen / mögliche nächste Schritte

- MIDI-Eingang (physisches Launchpad als Fernbedienung) – Schnittstelle: `backend.triggerTile(i)`.
- Tastatur-Belegung für Kacheln, Cue-Liste/Szenenfolge, Fade-in/Fade-out-Regler je Kachel,
  „Exklusiv“-Gruppen (Kachel stoppt andere), zweiter Ausgang zum Vorhören (Kopfhörer).
- Projekt-Aufräumen (unbenutzte Audiokopien löschen) mit Rückfrage.
- Lock-Datei gegen gleichzeitiges Öffnen desselben Projekts auf zwei Rechnern.
- Streaming-Dekodierung für sehr lange Dateien (> 30 min), aktuell wird komplett dekodiert.
