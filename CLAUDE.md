# CLAUDE.md – Langzeitgedächtnis für Launchpad Pro TAB Edition

Diese Datei ist die Arbeitsgrundlage für Claude (und Menschen), um auf jedem Gerät mit denselben
Voraussetzungen weiterzuarbeiten. **Bei jeder größeren Änderung aktualisieren.**

## 1. Worum geht es?

Touch-optimierte Launchpad-/Soundboard-Software für einen **Theaterverein** („TAB“). Kacheln im
Raster (3×3 … 7×7) werden mit Audiodateien belegt und per Tippen/Klick abgespielt. Zielplattform:
**Windows 10/11 mit Touchscreen**; läuft auch unter Linux/macOS. Sprache der Oberfläche,
Kommentare, Doku: **Deutsch**. Aktuelle Version: siehe `launchpad_pro_tab/__init__.py`
(einzige Quelle der Versionsnummer; `pyproject.toml` liest sie dynamisch).

### Arbeitsregeln des Auftraggebers (verbindlich)

- Effizienz/geringe Latenz haben Priorität (Multithreading/mehrere Kerne/GPU wo sinnvoll).
- Saubere **Schnittstellen** (austauschbare Backends, QML-Fassaden `backend`, `editor`, `master`, `updater`).
- **Bei Unklarheiten nachfragen** (AskUserQuestion-Tool), nicht raten.
- **Vor jedem Push Lauffähigkeit prüfen**: `pytest`, `--smoke-test`, bei UI-Änderungen Screenshots
  ansehen. Nur fehlerfrei pushen. Danach CI beobachten, bis alles grün ist.
- **README.md** mit Anleitung + aktuellen Bildern der Oberfläche pflegen (`tools/make_screenshots.py`,
  Installer-Bilder: `tools/make_installer_screenshots.py`).
- Diese **CLAUDE.md** aktuell halten, **CHANGELOG.md** bei jeder Version ergänzen.
- Entwicklungszweig bisher: `claude/launchpad-pro-tab-frontend-pqz33o` (Remote: GitHub
  `RubenBlaettel/Launchpad-Pro-TAB-Edition`, Standardzweig `main`, Repository öffentlich).
  PRs nur auf ausdrücklichen Wunsch. v1.1 ist über PR #1 in `main` – für Folgearbeiten den Zweig
  zuerst auf `origin/main` setzen.

### Entscheidungen aus Rückfragen

| Frage | Entscheidung |
|---|---|
| Technologie (v1.0) | **Python + PySide6 (Qt 6, QML/Qt Quick)** |
| Antippen einer laufenden Kachel (v1.0) | **Start/Stopp-Umschalter**, mehrere Kacheln parallel, Schleife je Kachel, „ALLES STOPPEN“ |
| Tempo-Regler (v1.0) | **Tonhöhe bleibt erhalten** (Time-Stretch, WSOLA), 0,5×–2,0×, Rastpunkt 1,0× |
| Update-Quelle (v1.1) | Repo war privat → Nutzer macht das **Repository öffentlich**; Updates direkt aus dessen GitHub-Releases (keine Tokens). |
| Erstes Release (v1.1) | **v1.1.0 veröffentlicht** (25.09.2026): Nutzer hat PR #1 nach `main` gemergt und das Release in der GitHub-Oberfläche angelegt; `release.yml` hat die Assets angehängt. |
| Installer von Windows 11 blockiert (intelligente App-Steuerung, Fehler 4551) | **Signatur über die SignPath Foundation** (kostenlos für Open Source); Einrichtung: `docs/SIGNPATH.md`. |
| Lizenz (Voraussetzung SignPath) | **MIT**, Rechteinhaber **TAB Theater** (`LICENSE`). |
| Update-Suche vs. Datenschutzerklärung (SignPath) | **Beim ersten Start einmal fragen**; ohne Zustimmung keine Verbindung ins Netz. |

### Eigene Designentscheidungen (begründet, bei Bedarf mit Nutzer abstimmen)

- **Show-Modus** (Kopfleiste): sperrt Menü/Drag&Drop/Bearbeiten/Update-Installation, Touch löst beim
  *Berühren* aus. Grund: Im normalen Modus muss Touch bis zum Loslassen warten, um „lang drücken“ zu erkennen.
- Maus-Linksklick löst **beim Drücken** aus (geringste Latenz), Rechtsklick öffnet das Menü.
- Leere Kachel antippen = Auswahlliste zum Belegen.
- Audio wird beim Belegen **in den Projektordner kopiert** (Duplikate per SHA-1 erkannt).
- Bearbeitungen sind **nicht-destruktiv**: `TileData.original` + `TileData.edit` (Parameter) +
  gerenderte FLAC-Datei in `audio/bearbeitet/`. Erneutes Bearbeiten lädt das Original + Parameter.
- „Schritt vor/zurück“ = 1 s, Taste gedrückt halten = Auto-Repeat.
- Löschen einer Kachel mit **Rückgängig** (Toast, 8 s) statt Rückfrage.
- Beim Raster-Verkleinern werden Kachel-*Belegungen* verworfen; Audiokopien bleiben im `audio/`-Ordner
  (Sicherheit), verwaiste gerenderte Bearbeitungen werden beim nächsten Öffnen gelöscht.
- **Design (v1.1):** Standard bleibt **Dunkel** (Bühne). Modi: `dark` / `light` / `system`
  (`AppSettings.theme`). Schnellumschalter (Sonne/Mond) in der Kopfleiste schaltet Dunkel↔Hell.
  Im hellen Modus: Akzentfarben dunkler (Kontrast ≥ 4,5:1 auf Weiß), Wellenform hell mit grünem
  Verlauf, **Fader-Bahnen bleiben schwarz** (Mischpult-Optik, Bild 3), Logo bleibt dunkel.
- **Installer (v1.1):** Inno Setup 7, 64-Bit, `C:\Program Files\Launchpad Pro TAB Edition`, drei
  Checkboxen (Desktop, Startmenü, Dateizuordnung `.lptab`, alle an), Wartungsseite beim erneuten
  Start („Aktualisieren/Reparieren“ oder „Deinstallieren“), Deinstaller mit Checkbox „Alle Projekte
  und Einstellungen löschen“ (aus) + danach Standard-Bestätigung (lässt sich in Inno nicht abschalten).
- **Updates (v1.1):** Prüfung beim Start (+ alle 12 h) **nur mit Zustimmung** (`AppSettings.update_check`:
  `None` = noch nicht gefragt → `UpdateConsentDialog` 4 s nach dem Start, nicht im Show-Modus/über
  anderen Dialogen; Fenster ohne Antwort geschlossen → nächster Start fragt erneut; 1.1.0-Einstellung
  `update_auto_check: false` wird als „Nein“ übernommen), nie automatische Installation; Hinweis als
  Knopf in der Kopfleiste + Toast (im Show-Modus nur Knopf). Manuelle Suche ignoriert „Übersprungen“.
  Optional Vorabversionen (Beta). Prüfsumme ist Pflicht (GitHub-`digest` oder `SHA256SUMS.txt`).
- **Einzelinstanz (v1.1):** zweiter Start übergibt Projektpfad per `QLocalServer` an die laufende
  Instanz → nie zwei Audio-Engines; ermöglicht Doppelklick auf `projekt.lptab`.

## 2. Schnellstart für Entwicklung

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
python -m pip install -r requirements-dev.txt
python -m pytest -q                                     # ~80 Tests, ~15 s, ohne Soundkarte/Bildschirm
python -m launchpad_pro_tab --smoke-test                # Exit-Code 0 = OK
python -m launchpad_pro_tab                             # App starten (--no-audio, --fullscreen, --project, --no-update-check)
```

**Claude Code im Web / Linux-Container** braucht zusätzlich Systembibliotheken, sonst
`ImportError: libEGL.so.1` bzw. kein PortAudio:

```bash
apt-get install -y libegl1 libgl1 libgl1-mesa-dri libxkbcommon0 libxkbcommon-x11-0 libfontconfig1 \
  libdbus-1-3 libportaudio2 xvfb libxcb-cursor0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 \
  libxcb-randr0 libxcb-render-util0 libxcb-shape0 libxcb-xinerama0 libxcb-xkb1 libxcb-xfixes0
```

- Tests: `QT_QPA_PLATFORM=offscreen` (setzt `tests/conftest.py` automatisch, ebenso temporäre
  `LPTAB_CONFIG_DIR/LPTAB_PROJECTS_DIR/LPTAB_CACHE_DIR` und `LPTAB_UPDATE_URL` auf einen toten Port –
  Tests fragen nie das echte GitHub ab). Offscreen nutzt den Software-Renderer → **MultiEffect/Shader
  werden dort nicht gezeichnet** (keine Fehlermeldung).
- Echte Screenshots mit GPU-Effekten: **Xvfb + Mesa llvmpipe**:
  `xvfb-run -a -s "-screen 0 1920x1080x24" python tools/make_screenshots.py` → `docs/images/*.png`
  (dunkel + hell, Update-Dialog mit simuliertem Release). Danach die Bilder mit dem Read-Tool ansehen!
- Programmordner: `pyinstaller packaging/launchpad_pro_tab.spec --noconfirm` → `dist/LaunchpadProTAB/`.
  Linux-Paket: `python tools/build_linux_package.py` + Test `sh tools/test_linux_package.sh <tar.gz>`
  (als **normaler Benutzer**, root installiert nach /opt; im Container z. B. `useradd -m theater`, `su theater -c …`).

### Windows-Installer unter Linux bauen/testen (Wine)

Inno Setup lässt sich im Container unter Wine betreiben (schnelle Syntax-/Ablaufprüfung vor dem CI):

```bash
dpkg --add-architecture i386 && apt-get update
apt-get install -y wine64 wine32:i386 xdotool imagemagick   # ggf. libgd3 auf die i386-Version angleichen
curl -L -o is.exe https://github.com/jrsoftware/issrc/releases/download/is-7_1_0/innosetup-7.1.0-x64.exe
# SHA-256: 0362a383ed217d4c4239b5933866dd96d3eb2102737da92f80f6057a4b40df2f
export WINEPREFIX=~/.wine-inno DISPLAY=:57; Xvfb :57 &            # Präfix MIT wine32 anlegen (WOW64!)
wine is.exe /VERYSILENT /SUPPRESSMSGBOXES /SP- /DIR='C:\InnoSetup'
ISCC="wine $WINEPREFIX/drive_c/InnoSetup/ISCC.exe" python tools/build_installer.py --source <Ordner mit LaunchpadProTAB.exe>
```

Unter Linux gibt es keine echte Windows-EXE – für Ablauf-Tests genügt ein Platzhalter
(`hostname.exe` aus dem Wine-Präfix als `LaunchpadProTAB.exe`). Stille Installation/Deinstallation,
Wartungsseite und Deinstallations-Dialog funktionieren unter Wine; `--purge-user-data` testet nur das
CI (echte EXE). Screenshots: `WINEPREFIX=… python tools/make_installer_screenshots.py <setup.exe>`.
Signierablauf ohne SignPath: `apt-get install osslsigncode`, Test-Zertifikat per
`openssl req -x509 … -addext extendedKeyUsage=codeSigning`, dann `osslsigncode sign -certs … -key …
-in a.exe -out b.exe` statt SignPath (Beispiel-Dateien von Inno sind schon signiert → für Tests mit
`osslsigncode remove-signature` unsigniert machen).

## 3. Architektur (wo liegt was?)

```text
launchpad_pro_tab/
  __init__.py         __version__ (einzige Quelle), __repository__ (Update-Quelle)
  app.py              main(): Einzelinstanz, Windows-Mutex, --purge-user-data, --finish-update, --wait-pid;
                      create_app() (für App, Tests, Screenshots), smoke_test(), Logging
  core/               KEIN Qt! constants, models (ProjectData/TileData/EditParams), project (Dateisystem),
                      settings (AppSettings JSON inkl. theme/update_*), paths (config/cache/projects; Env-
                      Overrides LPTAB_CONFIG_DIR/LPTAB_PROJECTS_DIR/LPTAB_CACHE_DIR), purge, util
    purge.py          „Alle Projekte und Einstellungen löschen“: nur Ordner mit gültiger projekt.lptab,
                      nur eigene Einträge (projekt.lptab, audio, cover, .autosave, .cache), geschützte Orte
  audio/              KEIN Qt! (wird in Worker-Prozessen importiert)
    decoder.py        decode(path, sr) -> float32 (frames,2); soundfile zuerst für WAV/FLAC/OGG/AIFF,
                      sonst PyAV/FFmpeg; soxr-Resampling; to_stereo (5.1-Downmix)
    cache.py          PCM-Cache im Projekt-.cache: <key>.pcm (int16 stereo), <key>.peaks.npy, <key>.json
    dsp.py            Peaks (min/max/rms je 256 Frames), aggregate_peaks, soft_limit, Kantenblenden
    timestretch.py    WsolaStretcher (streaming, Tempo live änderbar, bit-genau bei 1.0), stretch()
    engine.py         AudioEngine: Mixer im PortAudio-Callback, Befehls-deque, Snapshots, Limiter,
                      Pegel, Vorschau-Stimme (_PreviewVoice), Prefetch-Thread
    output.py         SoundDeviceBackend (WASAPI bevorzugt), NullBackend, Geräteliste
    tasks.py          Prozess-Aufgaben: prepare(), render_edit(), probe_file(), ping();
                      worker_init(): Worker beenden sich selbst, wenn das Hauptprogramm endet
  update/             KEIN Qt!
    version.py        parse_version/is_newer (1.2.0, v1.2.0, 1.3.0-beta.1, 1.3.0b1 …)
    net.py            urllib, nur https (http nur localhost), Zertifikate: System, Fallback certifi
    releases.py       fetch_releases (GitHub-API), pick_update, Asset-Digest, SHA256SUMS; LPTAB_UPDATE_URL
    download.py       download(): *.part, Größe + SHA-256 Pflicht, Abbruch per Event
    install.py        InstallKind (Windows-Installer/portabel, Linux-Paket, Quellcode), Installer-Argumente,
                      Linux: extract_bundle (tar filter="data"), swap_directories, finish_linux_update, pkexec
  system/volume.py    SystemVolume-Protokoll + Windows(pycaw)/Pulse/WirePlumber/ALSA/macOS/Dummy
  system/integration.py  Windows: Named Mutex (für AppMutex des Installers), AppUserModelID
  bridge/             Qt-Brücke
    backend.py        Backend (QML: `backend`) – Projekte, Kacheln, DnD, Autosave, Tick (30 Hz),
                      Theme (themeMode/darkTheme/setThemeMode/toggleTheme), prepare_for_update()
    appearance.py     Farbschema an Qt melden (QStyleHints.setColorScheme → Windows-Titelleiste)
    updater.py        UpdateController (QML: `updater`) – prüfen, Dialogzustand, Download, Installation
    single_instance.py  QLocalServer/QLocalSocket, Name je Benutzer
    editor.py         EditorController (QML: `editor`) – Bearbeiten & Schneiden
    volume.py         MasterVolumeController (QML: `master`) – eigener Thread
    models.py         TileModel, RecentAudioModel, RecentProjectsModel (QAbstractListModel)
    waveform.py       WaveformView (QQuickPaintedItem, `import LaunchpadPro`, Property `dark`)
    covers.py         Cover importieren (ICO: größtes Bild, max. 1024 px)
    tasks.py          TaskRunner: ProcessPool(spawn) + ThreadPool, Ergebnisse per Signal in UI-Thread;
                      BrokenProcessPool -> Thread; stop_processes() vor Updates (keine Dateisperren)
    qtutil.py         rprop()/PropertyObject._set(), to_local_path()
  qml/                Main.qml + Komponenten (flach), Theme.qml (Singleton via qmldir, Farben für
                      BEIDE Modi), SettingsDialog (Reiter), UpdateDialog, UpdateConsentDialog
                      (Zustimmung Update-Suche), ThemePreview, icons/*.svg
packaging/
  launchpad_pro_tab.spec   PyInstaller (Windows + Linux), Laufzeit-Hook pyi_rth_portaudio.py; legt
                           LICENSE.txt + THIRD_PARTY_NOTICES.md neben die EXE
  windows/LaunchpadProTAB.iss  Inno Setup 7 (+ wizard-large.png/wizard-small.png aus tools/make_installer_images.py);
                           Signatur per /DSignToolName (lokal) oder /DSignedUninstallerDir (extern, 2 Durchläufe)
  signpath/artifact-configuration.xml  SignPath-Konfiguration „windows“ (signiert *.exe/*.dll im ZIP)
  linux/install.sh, uninstall.sh  (install/--update/--uninstall, .install-info listet angelegte Dateien)
tools/                make_screenshots.py, make_installer_screenshots.py, demo_assets.py, make_icons.py,
                      make_icon.py, make_installer_images.py, build_installer.py (--sign-tool,
                      --signed-uninstaller-dir; Code 3 = „erst signieren“), signing.py (sammeln/
                      einsetzen/pruefen), test_sign.ps1 (CI-Test-Zertifikat), build_linux_package.py,
                      test_windows_installer.ps1, test_linux_package.sh, release_notes.py
tests/                test_models, test_project, test_audio, test_settings_volume, test_ui (Touch/Maus,
                      Theme, Update-Dialog, Zustimmungsfrage), test_update (lokaler Fake-GitHub-Server),
                      test_purge, test_single_instance, test_signing (künstliche PE-Dateien)
docs/                 images/ (README-Bilder), SIGNPATH.md (Antrag + Einrichtung der Code-Signatur)
.github/workflows/    build.yml (wiederverwendbar, Input `sign`), ci.yml (jeder Push), release.yml (Tag v*)
```

### Datenfluss Kachel antippen

`Tile.qml` (TapHandler) → `backend.triggerTile(i)` → `engine.toggle(key, pcm, loop)` (deque) →
Audio-Callback entscheidet atomar Start/Stopp → `engine.snapshot` → `Backend._tick()` (30 Hz)
→ `TileModel.refresh()` → QML zeigt Leuchten/Restzeit.

### Datenfluss Belegen

`assignAudio` → Thread: `Project.import_audio` (Kopie) → Prozess: `tasks.prepare` (Dekodieren →
Cache) → UI-Thread: `open_pcm` (memmap) + Kopf vorladen → Kachel bereit. Tokens (`_tokens[key]`)
verwerfen veraltete Ergebnisse.

### Datenfluss Update

`Backend.start(check_updates=True)` (nur aus `main()`) → `updater.start()` → ohne Antwort auf die
Zustimmungsfrage: 4 s später `consentPending` → QML-Timer öffnet `UpdateConsentDialog` →
`answerConsent(bool)` (bei Ja sofort prüfen) · mit Zustimmung: 4 s später Thread:
`fetch_releases` → `pick_update` → `updateFound` (QML: Toast + Knopf `updatePill`) →
`startUpdate()` → Thread: `resolve_checksum` + `download` (Fortschritt per 100-ms-Timer) →
`_install`: `prepare_hook` = `Backend.prepare_for_update()` (Audio stoppen, speichern,
Worker-Prozesse beenden) → **Windows**: Installer `/SILENT /LPTABWAITPID /LPTABREADY /LPTABRESTART`
starten; erst wenn Setup (mit Adminrechten) die `LPTABREADY`-Datei anlegt → `quitRequested` →
QML `Qt.quit()`; endet der Installer vorher (UAC abgelehnt) → `resume_hook` (Worker wieder an),
Fehlermeldung, Programm läuft weiter. Inno wartet in `InitializeSetup` auf den Prozess und in
`PrepareToInstall` (max. 30 s), bis `LaunchpadProTAB.exe` nicht mehr in Verwendung ist (Worker), ersetzt
`_internal` komplett, startet per `runasoriginaluser` neu → **Linux**: `extract_bundle` neben den
Programmordner, `spawn_detached(<neu>/LaunchpadProTAB --finish-update <ordner> --wait-pid <pid> -- --project …)`,
beenden; der Hilfsprozess tauscht die Ordner und `execv`t die neue Version. Beim nächsten Start
räumt `updater.cleanup()` Downloads und `.alt-*`-Ordner weg; `Backend._announce_version()` meldet
„aktualisiert auf …“ (vergleicht `settings.last_version`).

### Datenfluss Signatur (Release, `SIGNATUR=signpath`; CI: `test` mit Test-Zertifikat)

PyInstaller → `build_installer.py --signed-uninstaller-dir build/inno-signiert` (1. Durchlauf, Code 3:
Inno legt `uninst-<InnoVersion>-<Hash>.e64` unsigniert ab – das ist der Deinstaller **und** die
`Setup-x.y.z.tmp`, die Setup im Temp-Ordner startet) → `signing.py sammeln` (unsignierte EXE/DLL/PYD +
uninst-Datei → `build/zu-signieren/0001.dll …`, Zuordnung `build/signieren.json`) → Artefakt →
SignPath-Action (Freigabe per E-Mail) → `build/signiert` → `signing.py einsetzen` → 2. Durchlauf
(Inno übernimmt die Signatur, prüft den Inhalt) → Smoke-Test der signierten EXE → Setup.exe als
Artefakt → SignPath (2. Freigabe) → `signing.py pruefen` + `Get-AuthenticodeSignature` (Valid) →
Installer-E2E-Test (prüft Signatur von EXE und `unins000.exe`) → Release.

## 4. Invarianten & Regeln (nicht brechen!)

- **Projektdaten (`ProjectData`) nur im UI-Thread lesen/schreiben.** Hintergrund-Threads bekommen
  fertige Werte (siehe `Backend._schedule_cleanup`, `export_zip(save_first=False)`).
- **Audio-Callback darf nie blockieren oder werfen**: keine Locks, keine Datei-I/O, keine
  Python-Objekt-Erzeugung im großen Stil; Befehle nur über `AudioEngine._cmds`.
- `audio/`, `core/` und `update/` importieren **kein PySide6** (Worker-Prozesse, Tests).
- Große Audiodaten nie zwischen Prozessen kopieren → immer über den Cache (Datei + memmap).
- Mischen in float32: int16-Daten immer mit `np.float32`-Skalar multiplizieren (sonst float64!).
- `sys.setswitchinterval(0.001)` in `main()` – verkürzt GIL-Wartezeit des Audio-Threads.
- Projektformat: `projekt.lptab` (JSON, `format`/`version`). Bei Formatänderungen
  `PROJECT_FORMAT_VERSION` erhöhen und Migration in `ProjectData.from_dict` ergänzen.
- Pfade im Projekt **relativ** speichern (`Project.rel()`), damit Projekte verschiebbar bleiben.
- Speichern immer atomar (`util.atomic_write_json`); vorherige Fassung → `.autosave/projekt.lptab.bak`.
  Lesen mit `utf-8-sig` (BOM-tolerant).
- Neue UI-Texte auf Deutsch, Touch-Ziele ≥ 48 px (`Theme.touch`).
- **Farben nur über `Theme.*`** (jeweils für Dunkel UND Hell definiert). Feste Farben nur auf
  farbigen Kachelflächen, Fader-Kappen und in `ThemePreview.qml`.
- **Updates:** nie ohne SHA-256 installieren, nur https; Tag `vX.Y.Z` muss `__version__` entsprechen
  (prüft release.yml), sonst Update-Schleife. Asset-Namen sind Schnittstelle zwischen
  `release.yml`/Build-Skripten und `update/install.py` (`WINDOWS_ASSET`, `LINUX_ASSET`).
- **Installer:** `AppIdGuid` im .iss **niemals ändern** (Updates/Deinstallation hängen daran).
  `AppMutexName`/`AppUserModelId` im .iss = `system/integration.py` (Test prüft das).
- Update-/Installer-Parameter (`/LPTABWAITPID`, `/LPTABREADY`, `/LPTABRESTART`, `/LPTABPURGE`, `--purge-user-data`,
  `--finish-update`, `--wait-pid`) sind Schnittstellen – Änderungen immer an beiden Seiten + Tests.
- **Datenschutz:** Das Programm baut **ohne ausdrückliche Zustimmung keine Netzverbindung** auf
  (Update-Suche erst nach „Ja“ bzw. per Knopf). Die Datenschutzerklärung im README ist Voraussetzung
  der SignPath-Signatur – neue Netzfunktionen immer mit Zustimmung + README-Abschnitt „Datenschutz“.
- **Signatur:** Nur Dateien signieren, die GitHub Actions aus diesem Repository baut; Test-Zertifikat
  (`tools/test_sign.ps1`) nie für Releases. Werden Programmdateien nach dem Signieren verändert
  (z. B. Ressourcen), ist die Signatur kaputt – Signieren ist immer der letzte Schritt vor dem Paketieren.

## 5. Stolperfallen (bereits einmal passiert)

- QML: `id: scale` (oder andere Namen von Item-Properties wie `left`, `right`, `state`) **überschattet**
  Properties → Bindungen liefern Unsinn. Eigene Properties nicht `left/right/name` nennen
  (`IconImage.name` ist FINAL → daher ist `Icon.qml` ein Item-Wrapper).
- QML: `Qt.colorEqual("", …)` wirft „Invalid color name“ → Strings vergleichen.
- QML: Enums wie `Popup.CloseOnEscape` brauchen `import QtQuick.Controls.Basic` in *der* Datei.
- QML-Funktionen in JS-Array-Modellen (`model: [{f: () => …}]`) nicht verwenden.
- `Popup.opened` ist schon während der Schließ-Animation `false` → in Tests auf `visible` warten.
- Repeater-Delegates sind **keine QObject-Kinder** → `findChild` findet sie nicht; über
  `childItems()` von `window.contentItem()` suchen (siehe `tests/test_ui.py::_find_item`; auch
  Popup-Inhalte und die Kopfleiste hängen darunter).
- `json.JSONDecodeError` ist eine Unterklasse von `ValueError` → Reihenfolge der `except` beachten.
- QML-Engine vor dem Backend zerstören (`AppContext.dispose()`), sonst „Cannot read property … of null“.
- PyInstaller: `collect_data_files()` findet das Paket während der Spec-Auswertung nicht →
  Daten per `os.walk` einsammeln (siehe Spec). Immer `--smoke-test` gegen das Paket laufen lassen.
- PyInstaller **Linux**: `sounddevice` findet das mitgelieferte `libportaudio.so.2` nicht
  (`find_library` sucht nur im System) → Laufzeit-Hook `packaging/pyi_rth_portaudio.py`.
  `libasound.so.2` **nicht** mitliefern (Spec filtert), sonst fehlen PipeWire/Pulse-ALSA-Plugins
  anderer Distributionen. Test: System-`libportaudio.so.2` wegschieben, Paket starten.
- MultiEffect-„Leuchten“: `shadowEnabled` auf eine unsichtbare Quell-Rechteckfläche wirkt deutlich
  besser als `blurEnabled`.
- Offscreen-Plattform im Test: Bildschirm nur 800×800 → Layout eng, aber funktionsfähig.
- Eigene Skripte, die `create_app()` nutzen, brauchen `if __name__ == "__main__":` – sonst starten die
  Worker-Prozesse (spawn) das Skript erneut und der Pool bricht ab.
- Worker-Aufgaben dürfen nur Qt-freie Module referenzieren (sonst lädt jeder Worker Qt) –
  daher liegt z. B. das Aufwärmen in `audio.tasks.ping`.
- **Inno Setup 7:** `CreateCustomForm(ClientWidth, ClientHeight, KeepSizeX, KeepSizeY)` (Größe fest ab
  6.6); `ExecAsOriginalUser` gibt es im Deinstaller nicht; der AppMutex wird **nach**
  `InitializeSetup` geprüft (deshalb dort auf `LPTABWAITPID` warten), mit `/SUPPRESSMSGBOXES` bricht
  „Programm läuft noch“ sonst ab. Deinstaller-Reihenfolge: `InitializeUninstall` → Standard-Bestätigung
  → `usAppMutexCheck` → `usUninstall` → Dateien → `usPostUninstall`.
- Inno: `AppId={{{#AppIdGuid}}` – drei öffnende und **zwei** schließende Klammern, sonst fehlt die
  schließende Klammer im Registry-Schlüssel (`…_is1`) und die Wartungsseite erkennt nichts.
- Inno 64-Bit-Setup läuft unter Wine nur mit **wine32** (prüft WOW64: „does not support the version
  of Windows“).
- PowerShell: `Start-Process … -PassThru` ohne `-Wait` → vor dem Warten `$p.Handle` abfragen, sonst
  ist `ExitCode` leer. `Set-Content -Encoding UTF8` schreibt in Windows PowerShell 5 ein BOM.
- Windows PowerShell **5.1** liest `.ps1` ohne BOM als ANSI: ein „–“ (UTF-8 `E2 80 93`) wird zu `â€“`
  und `“` beendet Zeichenketten → Skripte für 5.1 (`shell: powershell`, z. B. `tools/test_sign.ps1`)
  nur in ASCII. `pwsh` (7.x) liest UTF-8.
- Bash-Heredoc mit `<<'EOF'` endet an der ersten Zeile „EOF“ – auch mitten in eingebettetem
  Python-Code! Für Skripte mit solchen Zeilen andere Endmarken nutzen oder die Datei mit Write anlegen.
- `pkill -f "<muster>"` trifft auch die eigene Shell, wenn das Muster in deren Befehlszeile steht
  (Abhilfe: `pgrep -f '[s]pawn_main'` – die Klammer verhindert den Selbsttreffer).
- `ProcessPoolExecutor`-Worker überleben einen Absturz/hartes Beenden des Hauptprogramms (jeder
  Worker hält auch das Schreibende der Queue) und sperren dann `LaunchpadProTAB.exe`/DLLs →
  Update/Deinstallation scheitern. Deshalb `initializer=worker_init` (wartet auf
  `multiprocessing.parent_process()` und beendet den Worker). Test: `test_workers_end_when_main_program_dies`.
- Einzelinstanz unter Windows: Client und Server im **selben** Prozess funktionieren mit Named Pipes
  nicht zuverlässig (blockierende Waits) → Test startet den zweiten Programmstart als eigenen Prozess;
  der Server bestätigt jeden Auftrag (`ok`), damit keine Daten beim schnellen Beenden verloren gehen.
- Inno: Die Selbst-Erhöhung (UAC) passiert **vor** `[Code]` – `InitializeSetup` läuft nur im
  erhöhten Prozess; lehnt man UAC ab, endet Setup mit `ecCancelledBeforeInstall`.
- Release v1.1.0: Das Repository wurde genau während `gh release upload` von privat auf öffentlich
  umgestellt → HTTP 403 „Resource not accessible by integration“ trotz `contents: write`. Sichtbarkeit
  nie während eines Release-Laufs ändern; Abhilfe: *Actions › Release › Re-run failed jobs*
  (nur „Release veröffentlichen“ läuft neu, die gebauten Pakete werden wiederverwendet).
- GitHub hängt an jedes Release automatisch *Source code (zip/tar.gz)* an – Nutzer halten das leicht
  für das Programm (der Release-Text weist deshalb darauf hin).
- **Windows 11 „intelligente App-Steuerung“** (Smart App Control) blockiert unsignierte, unbekannte
  EXE/DLL komplett (Setup: „Die Datei konnte nicht im temporären Ordner ausgeführt werden … Fehler
  4551“, Toast „Ein Teil dieser App wurde blockiert“) – kein „Trotzdem ausführen“, keine Ausnahme je
  App. SmartScreen-Hinweise im README reichten nicht. Einzige saubere Lösung: Signatur.
- Inno **prüft nach jedem SignTool-Aufruf**, ob die Datei eine Signatur trägt („returned an exit code
  of 0, but the file does not have a digital signature“) → ein „Sammel-SignTool“ geht nicht; für
  externe Dienste den eingebauten Zwei-Durchlauf-Mechanismus `SignedUninstallerDir` nutzen. Der
  Dateiname enthält einen Hash (Inno-Version, Icons, Versionsinfo) → jede Version neu signieren.
- signpath.org und jrsoftware.org sind aus dem Container gesperrt (Egress) → Inno-Hilfe lokal aus
  `ISetup.chm` lesen (`apt-get install libchm-bin`, `extract_chmLib`), Inno-Quelltext unter
  github.com/jrsoftware/issrc.

## 6. Teststrategie

- `tests/test_audio.py`: Formate (WAV/FLAC/OGG/MP3/AIFF via libsndfile, M4A/Opus via FFmpeg),
  Resampling, WSOLA (Länge, Tonhöhe, Streaming), Cache, Rendern, Engine (Fade, Loop, Limiter, Vorschau).
- `tests/test_project.py`: Anlegen/Öffnen/Speichern, Sicherung bei beschädigter Datei, Import/
  Duplikate, Speichern unter, ZIP-Export/-Import inkl. Zip-Slip-Schutz, Zwischenstand.
- `tests/test_ui.py`: komplette Oberfläche mit Backend; Belegen, DnD, Cover (PNG/ICO), Abspielen,
  Bearbeiten/Rendern, Absturz-Wiederherstellung, Raster, Löschen/Rückgängig, Export,
  **echte Maus-/Touch-Ereignisse** (QTest) inkl. Langdrücken und Show-Modus, Theme-Umschaltung
  (auch per Klick in den Einstellungen), Update-Hinweis/-Dialog, Zustimmungsfrage (Show-Modus).
- `tests/test_update.py`: Versionen, Release-Auswahl (Beta, Übersprungen), lokaler Fake-GitHub-Server
  (Weiterleitung, Digest, SHA256SUMS), falsche Prüfsumme/Abbruch, Installationsart, Installer-
  Argumente, Konsistenz .iss ↔ Programm, Linux-Ordnertausch inkl. `execv`-Neustart, UpdateController.
- `tests/test_purge.py`: Löschen nur eigener Daten (fremde Dateien, geschützte Orte bleiben), CLI.
- `tests/test_signing.py`: Signatur-Erkennung (PE32/PE32+), Sammeln/Einsetzen/Prüfen mit künstlichen
  PE-Dateien, Konsistenz SignPath-Konfiguration ↔ Workflow.
- CI (`build.yml`): Tests Linux+Windows; Windows: EXE + Smoke-Test, kompletter Signierablauf mit
  Test-Zertifikat (2 Inno-Durchläufe, Smoke-Test der signierten EXE), Installer bauen und mit
  `tools/test_windows_installer.ps1` **echt installieren, updaten (bei laufendem Programm) und
  deinstallieren (mit Datenlöschung)**; Linux (ubuntu-22.04): Paket bauen + `test_linux_package.sh`.
- Neue Features immer mit Test + Screenshot-Kontrolle.

## 7. Neue Version veröffentlichen

1. `__version__` in `launchpad_pro_tab/__init__.py` erhöhen, `CHANGELOG.md` → Abschnitt
   `## [Unveröffentlicht]` in `## [X.Y.Z] – Datum` umbenennen (wird Release-Text und erscheint im
   Update-Dialog; `release_notes.py` sucht genau `## [X.Y.Z]`).
2. Commit + Push, CI grün abwarten.
3. `git tag vX.Y.Z && git push origin vX.Y.Z` → `release.yml` baut/testet alles, erzeugt
   `SHA256SUMS.txt` und das Release (Buchstaben in der Version → Vorabversion).
   Ohne lokales git: GitHub › *Releases › Draft a new release* → Tag `vX.Y.Z` neu anlegen, *Target* =
   Zweig mit dem Code, *Publish release* → `release.yml` hängt Assets + Versionshinweise an.
   **Claude-Code-Web-Sitzungen dürfen nur den Entwicklungszweig pushen** (Tag-Push → HTTP 403;
   `Run workflow` für `release.yml` → 404, solange die Datei nicht im Standardzweig liegt) → den Tag
   setzt dann der Nutzer.
4. Assets: `LaunchpadProTAB-Setup-X.Y.Z.exe`, `LaunchpadProTAB-X.Y.Z-linux-x86_64.tar.gz`, `SHA256SUMS.txt`.
5. Repository muss **öffentlich** sein, sonst liefert die GitHub-API 404 („Keine veröffentlichten Versionen“).
6. Signatur: Ist `SIGNPATH_ORGANIZATION_ID` (Repository-Variable) gesetzt, schickt der Release-Lauf
   zwei Anfragen an SignPath, die der Nutzer per E-Mail/SignPath freigeben muss (Wartezeit je 2 h);
   sonst unsigniert. Einrichtung und Variablen: `docs/SIGNPATH.md`.

## 8. Stand der Prüfungen

- v1.0: siehe Git-Historie (CI grün, EXE-Smoke-Test).
- v1.1 (lokal, Linux-Container): 84 Tests grün, `--smoke-test` grün (Quellcode + Linux-Paket),
  `tools/test_linux_package.sh` grün (Installation, Update-Tausch, Deinstallation mit Datenlöschung),
  mitgeliefertes PortAudio lädt ohne System-PortAudio, gepacktes Programm hart beendet → keine
  verwaisten Worker; Installer mit Inno Setup 7.1 unter Wine kompiliert, still installiert/
  deinstalliert, Wartungsseite, Lösch-Dialog und Warten auf freie Programmdatei geprüft.
- v1.1 (GitHub Actions, Commit fc13153): Tests Linux + Windows grün; Windows-Installer echt geprüft
  (Installation nach `C:\Program Files`, Verknüpfungen, Registry, Smoke-Test der installierten EXE,
  Update bei laufendem Programm inkl. `LPTABREADY`, Worker enden nach hartem Beenden, Neustart,
  Deinstallation mit Datenlöschung); Linux-Paket auf Ubuntu 22.04 grün.
- Release v1.1.0 (25.09.2026): Workflow grün (Tests, Windows-Installer-E2E, Linux-Paket); Assets
  `LaunchpadProTAB-Setup-1.1.0.exe`, `LaunchpadProTAB-1.1.0-linux-x86_64.tar.gz`, `SHA256SUMS.txt`.
  Update-Prüfung gegen das echte Release geprüft: installiert 1.1.0 → „aktuell“, 1.0.0 → Angebot
  1.1.0 mit passendem Paket und Prüfsumme (GitHub-Digest = SHA256SUMS).
- Nach Release 1.1.0: Nutzer-PC (Windows 11) blockiert den unsignierten Installer (intelligente
  App-Steuerung, Fehler 4551) → Zustimmungsfrage, MIT-Lizenz und SignPath-Signierung vorbereitet.
  Lokal: Zwei-Durchlauf-Signatur unter Wine mit Test-Zertifikat komplett geprüft (sammeln → signieren
  → einsetzen → 2. Durchlauf übernimmt Deinstaller-Signatur → Setup signiert → Installation, Dateien
  signiert, fremd signierte behalten ihre Signatur). SignPath-Antrag stellt der Nutzer
  (`docs/SIGNPATH.md`); Signatur mit echtem Zertifikat noch ungetestet.
- Nicht automatisch prüfbar (auf echter Hardware testen!): tatsächliche Ausgabelatenz mit WASAPI,
  Windows-Systemlautstärke per pycaw auf einem Rechner mit Audiogerät, Touch-Bedienung auf einem
  echten Touchscreen, native Datei-Dialoge, UAC-Abfrage beim Update (CI-Runner hat keine UAC),
  Titelleisten-Farbe im hellen Modus unter Windows 11.

## 9. Ideen / mögliche nächste Schritte

- MIDI-Eingang (physisches Launchpad als Fernbedienung) – Schnittstelle: `backend.triggerTile(i)`.
- Tastatur-Belegung für Kacheln, Cue-Liste/Szenenfolge, Fade-in/Fade-out-Regler je Kachel,
  „Exklusiv“-Gruppen (Kachel stoppt andere), zweiter Ausgang zum Vorhören (Kopfhörer).
- Projekt-Aufräumen (unbenutzte Audiokopien löschen) mit Rückfrage.
- Lock-Datei gegen gleichzeitiges Öffnen desselben Projekts auf zwei Rechnern.
- Streaming-Dekodierung für sehr lange Dateien (> 30 min), aktuell wird komplett dekodiert.
- Delta-Updates statt Komplettpaket.
