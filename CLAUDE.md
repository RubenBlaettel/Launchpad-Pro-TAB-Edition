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
- **Lokaler Arbeitsordner des Nutzers** (Windows 11, `C:\Projekte\Launchpad-Pro-TAB-Edition\
  Launchpad-Pro-TAB-Edition-1.1.0`) ist seit 07.10.2026 eine **Git-Arbeitskopie von `main`** (vorher
  ein entpacktes 1.1.0 ohne git → Änderungen mussten von Hand mit GitHub zusammengeführt werden).
  Auf Auftrag „auf GitHub hochladen“ wird direkt nach `main` gepusht und der Entwicklungszweig
  gleichgezogen. `gh` ist dort angemeldet. Auf diesem PC ist die **intelligente App-Steuerung an** –
  siehe Stolperfallen (blockiert auch neu installierte Python-Binärpakete).

### Entscheidungen aus Rückfragen

| Frage | Entscheidung |
|---|---|
| Technologie (v1.0) | **Python + PySide6 (Qt 6, QML/Qt Quick)** |
| Antippen einer laufenden Kachel (v1.0) | **Start/Stopp-Umschalter**, mehrere Kacheln parallel, Schleife je Kachel, „ALLES STOPPEN“ |
| Tempo-Regler (v1.0) | **Tonhöhe bleibt erhalten** (Time-Stretch), 0,5×–2,0×, Rastpunkt 1,0× – seit v1.2 Phase-Vocoder statt WSOLA (siehe unten) |
| Update-Quelle (v1.1) | Repo war privat → Nutzer macht das **Repository öffentlich**; Updates direkt aus dessen GitHub-Releases (keine Tokens). |
| Erstes Release (v1.1) | **v1.1.0 veröffentlicht** (25.09.2026): Nutzer hat PR #1 nach `main` gemergt und das Release in der GitHub-Oberfläche angelegt; `release.yml` hat die Assets angehängt. |
| Installer von Windows 11 blockiert (intelligente App-Steuerung, Fehler 4551) | ~~Signatur über die SignPath Foundation~~ – **abgelehnt** (07.10.2026, „zu geringe Reichweite“). `docs/SIGNPATH.md` + Signierablauf bleiben für ein späteres Zertifikat. |
| Signatur-Weg nach der SignPath-Ablehnung (07.10.2026) | **Microsoft Store (MSIX)** – kostenlos, Microsoft signiert, Store verteilt Updates. Verworfen: Azure Artifact Signing (Privatpersonen nur USA/Kanada; über den Verein ≈ 10 $/Monat, Verein ≥ 3 Jahre), Certum-OSS-Zertifikat (≈ 50–70 €/Jahr, Signieren lokal per SimplySign). Selbst signierte Zertifikate erkennt die App-Steuerung grundsätzlich nicht an. Inno-Installer + GitHub-Updater bleiben für PCs ohne App-Steuerung. Konto/Einreichung macht der Nutzer: `docs/MICROSOFT_STORE.md`. |
| Release 1.2.0 (07.10.2026) | **Erst veröffentlichen, wenn die Store-Fassung steht** („erst mit Signatur“). `__version__` ist schon 1.2.0 (für das Store-Paket); CHANGELOG-Abschnitt heißt bis dahin „[Unveröffentlicht]“. |
| Lizenz (Voraussetzung SignPath) | **MIT**, Rechteinhaber **TAB Theater** (`LICENSE`). |
| Update-Suche vs. Datenschutzerklärung (SignPath) | **Beim ersten Start einmal fragen**; ohne Zustimmung keine Verbindung ins Netz. |
| Registerkarten: Wiedergabe beim Wechsel (v1.2) | **Weiterspielen** wie ein Browser-Tab; Karte zeigt ▶ + Anzahl; „ALLES STOPPEN“ stoppt alle Karten. |
| Kachel ziehen vs. Maus-Start beim Drücken (v1.2) | Klick startet **weiterhin sofort beim Drücken**; wird daraus ein Ziehen, bricht der gerade gestartete Ton ab (`backend.stopTile`). Touch: Ziehen spielt nichts ab. |
| Fader im hellen Modus (v1.2) | **Alle** Fader-Bahnen (Master + Lautstärke im Editor) hellgrau – ersetzt „Fader-Bahnen bleiben schwarz“. |
| Projekte löschen (v1.2) | In der Projektauswahl/Startseite per Papierkorb-Knopf → **in den Papierkorb des Systems** (nicht endgültig), mit Rückfrage. **Offene Projekte**: speichern, Karte schließen, dann löschen. |
| „Hitboxen hinter Pop-ups“ (v1.2) | Trat bei offenen Dialogen mit Maus **und** Touch auf → Ursache siehe Stolperfallen (TapHandler in Pop-ups). |

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
  Verlauf, **Fader-Bahnen hellgrau** mit dunkler Skala (v1.2, Nutzerwunsch; dunkel: schwarz wie am
  Mischpult), Logo bleibt dunkel.
- **Registerkarten (v1.2):** „Neu“, „Öffnen“ und die Projektauswahl öffnen in einer **neuen** Karte
  (eine leere aktive Karte wird wiederverwendet); ist das Projekt schon offen, wird nur dorthin
  gewechselt. Höchstens **eine leere Karte** (Startseite mit zuletzt geöffneten Projekten), immer
  mindestens eine Karte. Schließen speichert vorher (schlägt das fehl, bleibt die Karte offen) und
  blendet die Kacheln der Karte aus. Offene Karten stehen in `settings.open_projects`, die aktive in
  `last_project`; beim Start stellt `Backend.restore_tabs()` sie wieder her. Show-Modus: nur
  Wechseln, kein Öffnen/Schließen. Eine offene Bearbeitung wird beim Wechsel geparkt
  (`close(keep_session=True)`) und beim Zurückwechseln still wiederhergestellt.
- **Kacheln verschieben (v1.2):** Ziehen auf eine andere Kachel tauscht die Plätze
  (`ProjectData.swap`); laufende Stimmen werden in der Engine umbenannt (`engine.rekey`) und spielen
  weiter, die Bearbeitung zieht mit (`editor.move_key`). Gesperrt im Show-Modus, während eine Kachel
  lädt und während der Editor speichert. Die Drag-Miniatur schwebt **über** dem Finger, damit der
  Hinweis auf der Zielkachel sichtbar bleibt.
- **Projekt löschen (v1.2):** `backend.deleteProject(path)` – nur Ordner mit gültiger
  `projekt.lptab` (`purge.is_project_dir`), nie `purge.protected_dirs()`/Laufwerkswurzel; fehlt der
  Ordner, nur `forgetProject`. Offene Karte → `_close_tab` (speichert, parkt den Editor; schlägt
  das Speichern fehl, wird nicht gelöscht), dann `tab.pcm.clear()`. Papierkorb über
  `qtutil.move_to_trash` (`QFile.moveToTrash`, kein System-Dialog) – austauschbar als
  `backend.move_to_trash` (Tests). Unter Windows scheitert das, solange Dateien des Ordners gemappt
  sind (ausblendende Stimmen, Vorschau, Worker) → bis zu 25 Versuche im Abstand von 200 ms mit
  `gc.collect()`, danach Fehlermeldung. Rückfrage: `Main.qml` `requestDeleteProject()` +
  `deleteProjectDialog`. `ProjectRow` ist deshalb ein `Item` (Zeile + Papierkorb daneben), damit der
  Knopf auch bei ausgegrauten „nicht gefunden“-Zeilen bedienbar bleibt.
- **Kachel in den Editor ziehen (v1.2, Nutzerwunsch):** DropArea über dem ganzen Bereich
  *Bearbeiten & Schneiden* (`EditorSection.qml`, Schlüssel `application/x-lptab-tile`) →
  `backend.editTile(i)` wie der Menüpunkt. Während eine Kachel gezogen wird, ist der Bereich
  umrandet; der Hinweis steht in der Hälfte, die der Zeiger **nicht** belegt (über dem Finger
  schwebt die Miniatur). Dieselbe Kachel erneut ablegen = nichts tun (`editor.editsTile(i)`), eine
  andere ersetzt die offene Bearbeitung (Hinweis warnt), beim Speichern gesperrt. Die DropArea
  nimmt jeden Kachel-Drag an (sonst kein `exited`) und entscheidet erst in `onDropped`.
- **Vollbild (v1.2, Nutzerwunsch):** Schalter unter *Einstellungen › Darstellung › Fenster*,
  gespeichert in `AppSettings.fullscreen` → Start direkt im Vollbild (Kontext-Property
  `startFullscreen`). Quelle der Wahrheit ist das Fenster: `Main.qml` meldet jede Änderung von
  `visibility` (auch F11, Fenstersystem) an `backend.setFullscreen()`; Minimieren/Ausblenden zählt
  nicht. Verlassen → vorheriger Zustand (maximiert/Fenster). `--fullscreen` setzt nur für diesen
  Start (`Backend.start_fullscreen()`), ohne die Einstellung zu ändern. Der Schalter ist
  `checkable: false` (sonst reißt die Bindung an `backend.fullscreen` nach dem ersten Klick ab).
- **Time-Stretch = Phase-Vocoder (v1.2, Nutzerwunsch „Aufnahme wirkt beim Ändern der
  Schnelligkeit verzerrt“):** WSOLA (40-ms-Fenster, alle 20 ms Überblendung) erzeugte bei
  mehrstimmigem Material ~50-Hz-Modulation (rau, „kratzig“). `audio/timestretch.py` →
  `TimeStretcher`: Hann N = 4096 bei 44,1/48 kHz (≈ 85 ms), 75 % Überlappung; Phasenfortschritt
  aus einem zweiten Spektrum genau einen Synthese-Hop früher (kein Unwrapping, auch bei 2×
  eindeutig); Identity Phase Locking; **eine** Phasendrehung für beide Kanäle (Bezug:
  betragsgewichtete Summe, Stereobild bleibt); Transienten (≥ 35 % der Frequenzen +5 dB je Hop):
  Phasen-Reset + 3 Fenster Tempo 1, danach Zeitausgleich (25 %/Fenster). Einsatz nur in einem
  Kanal → nur ansteigende Frequenzen zurücksetzen (sonst leiden Töne im anderen Kanal).
  Messwerte alt → neu (Störanteil abseits der Töne, Akkord mit Bass + Cmaj7): 0,5× −10 → −39 dB,
  0,75× −9 → −44 dB, 1,5× −10 → −42 dB, 2× −10 → −31 dB; Schläge ohne Vorecho (vorher
  verdoppelt bei 0,5×), Stereo-Laufzeit exakt erhalten. Kompromisse: Sprache bei 0,5× etwas
  weicher (Scheitelfaktor 2,26 statt 2,53 bei WSOLA, Original 2,72; ab 0,75× gleichauf), Anschläge sitzen konstant
  bis ≈ 30 ms (0,5×) neben der idealen Stelle (Rhythmus gleichmäßig, ±5 ms), Tempo-Änderungen
  greifen nach 2 Fenstern (≈ 43 ms), CPU Vorschau ≈ 2,6 % statt 1 %. Verworfen: kürzere Fenster
  (Akkorde −15 dB), längere (Anschläge/Sprache schlechter), 87,5 % Überlappung (kein Gewinn,
  doppelte CPU), float32 (kaum schneller, nicht mehr exakt bei 1,0×). Bereits gerenderte
  Bearbeitungen werden nicht automatisch neu berechnet (erneut speichern genügt).
- **Hinweis-Meldungen (v1.2)** fangen Klicks ab (sonst löst die Kachel darunter aus); Antippen
  schließt Meldungen ohne Aktion, Meldungen mit „Rückgängig“/„Anzeigen“ bleiben.
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
- **Microsoft-Store-Fassung (v1.2):** MSIX aus dem unveränderten PyInstaller-Ordner
  (`tools/build_msix.py`, Vorlage `packaging/msix/AppxManifest.xml`, Identität `packaging/msix/store.json`),
  **unsigniert** – der Store signiert. Laufzeit-Erkennung über `GetCurrentPackageFamilyName`
  (`integration.package_family_name()`) → `InstallKind.MS_STORE`: `updater.start()` fragt/sucht nie,
  `check()` tut nichts, `storeManaged` blendet in *Einstellungen › Updates* Suche/Schalter aus und
  zeigt „Updates im Microsoft Store anzeigen“ (`ms-windows-store://downloadsandupdates`); keine
  eigene AppUserModelID im Paket. Manifest: `runFullTrust`, Dateizuordnung `.lptab`, App-Alias
  `LaunchpadProTAB.exe` (CI startet darüber), `de-DE`, MinVersion 10.0.17763. Bilder in Zielgröße
  aus `tools/make_icon.render()`, mit makepri zusätzlich scale-200/targetsize/altform-unplated.
  Vorabversionen → kein Store-Paket. Der **Inno-Installer** prüft `HKLM\SYSTEM\CurrentControlSet\
  Control\CI\Policy\VerifiedAndReputablePolicyState = 1` (App-Steuerung an) und bietet (nicht bei
  stillen Updates) Store bzw. Projektseite an; `StoreId` kommt aus `store.json` (`build_installer.py`).

## 2. Schnellstart für Entwicklung

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
python -m pip install -r requirements-dev.txt
python -m pytest -q                                     # ~90 Tests, ~30 s, ohne Soundkarte/Bildschirm
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
  **Unter Windows** genügt `python tools/make_screenshots.py` – öffnet ~1 min ein echtes Fenster (GPU,
  daher mit Leuchten/Cover-Masken); die Systemlautstärke wird dabei immer simuliert (keine
  Gerätenamen in den Bildern, echte Lautstärke bleibt unberührt).
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
                      settings (AppSettings JSON inkl. theme/fullscreen/update_*), paths (config/cache/projects; Env-
                      Overrides LPTAB_CONFIG_DIR/LPTAB_PROJECTS_DIR/LPTAB_CACHE_DIR), purge, util
    purge.py          „Alle Projekte und Einstellungen löschen“: nur Ordner mit gültiger projekt.lptab,
                      nur eigene Einträge (projekt.lptab, audio, cover, .autosave, .cache), geschützte Orte
  audio/              KEIN Qt! (wird in Worker-Prozessen importiert)
    decoder.py        decode(path, sr) -> float32 (frames,2); soundfile zuerst für WAV/FLAC/OGG/AIFF,
                      sonst PyAV/FFmpeg; soxr-Resampling; to_stereo (5.1-Downmix)
    cache.py          PCM-Cache im Projekt-.cache: <key>.pcm (int16 stereo), <key>.peaks.npy, <key>.json
    dsp.py            Peaks (min/max/rms je 256 Frames), aggregate_peaks, soft_limit, Kantenblenden
    timestretch.py    TimeStretcher (Phase-Vocoder, streaming, Tempo live änderbar, exakt bei 1.0), stretch()
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
    install.py        InstallKind (Windows-Installer/portabel, Microsoft Store, Linux-Paket, Quellcode),
                      is_packaged(), Installer-Argumente,
                      Linux: extract_bundle (tar filter="data"), swap_directories, finish_linux_update, pkexec
  system/volume.py    SystemVolume-Protokoll + Windows(pycaw)/Pulse/WirePlumber/ALSA/macOS/Dummy
  system/integration.py  Windows: Named Mutex (für AppMutex des Installers), AppUserModelID (nicht im MSIX),
                      package_family_name() (MSIX-Erkennung),
                      disable_press_and_hold (Fenster-Eigenschaft MicrosoftTabletPenServiceProperty)
  bridge/             Qt-Brücke
    backend.py        Backend (QML: `backend`) – Registerkarten (tabs/activeTab/activateTab/newTab/
                      closeTab/restore_tabs), Projekte, Kacheln der AKTIVEN Karte, DnD, moveTile,
                      Autosave aller Karten, Tick (30 Hz), Theme, prepare_for_update()
    tabs.py           ProjectTab (Projekt + pcm/tokens/runtime/dirty je Karte, engine_key) und
                      TabsModel (QML: backend.tabs – title/path/dirty/playing/active)
    appearance.py     Farbschema an Qt melden (QStyleHints.setColorScheme → Windows-Titelleiste)
    touch.py          SyntheticRightClickFilter: verwirft System-Rechtsklicks von Finger/Stift
                      (Event-Filter am Fenster, installiert in app._prepare_touch_input)
    updater.py        UpdateController (QML: `updater`) – prüfen, Dialogzustand, Download, Installation
    single_instance.py  QLocalServer/QLocalSocket, Name je Benutzer
    editor.py         EditorController (QML: `editor`) – Bearbeiten & Schneiden
    volume.py         MasterVolumeController (QML: `master`) – eigener Thread
    models.py         TileModel (zeigt die aktive Karte; runtime-dict wird mit ProjectTab geteilt),
                      RecentAudioModel, RecentProjectsModel (Rollen current/open)
    waveform.py       WaveformView (QQuickPaintedItem, `import LaunchpadPro`, Property `dark`)
    covers.py         Cover importieren (ICO: größtes Bild, max. 1024 px)
    tasks.py          TaskRunner: ProcessPool(spawn) + ThreadPool, Ergebnisse per Signal in UI-Thread;
                      BrokenProcessPool -> Thread; stop_processes() vor Updates (keine Dateisperren)
    qtutil.py         rprop()/PropertyObject._set(), to_local_path()
  qml/                Main.qml + Komponenten (flach), Theme.qml (Singleton via qmldir, Farben für
                      BEIDE Modi), UiState.qml (Singleton: modalCount/modalOpen), TabStrip (Karten),
                      ProjectRow (Zeile „zuletzt geöffnet“: Projektauswahl + Startseite), DragProxy
                      (kind "file" | "tile"), SettingsDialog (Reiter), UpdateDialog, UpdateConsentDialog
                      (Zustimmung Update-Suche), ThemePreview, icons/*.svg
packaging/
  launchpad_pro_tab.spec   PyInstaller (Windows + Linux), Laufzeit-Hook pyi_rth_portaudio.py; legt
                           LICENSE.txt + THIRD_PARTY_NOTICES.md neben die EXE
  windows/LaunchpadProTAB.iss  Inno Setup 7 (+ wizard-large.png/wizard-small.png aus tools/make_installer_images.py);
                           Signatur per /DSignToolName (lokal) oder /DSignedUninstallerDir (extern, 2 Durchläufe)
  msix/AppxManifest.xml  Manifest-Vorlage des Store-Pakets ($-Platzhalter, KEIN „--“ in Kommentaren)
  msix/store.json     Paket-Identität aus Partner Center (leer = nur Testpaket) + store_id
  signpath/artifact-configuration.xml  SignPath-Konfiguration „windows“ (SignPath abgelehnt – ruht)
  linux/install.sh, uninstall.sh  (install/--update/--uninstall, .install-info listet angelegte Dateien)
tools/                make_screenshots.py, make_installer_screenshots.py, demo_assets.py, make_icons.py,
                      make_icon.py, make_installer_images.py, build_installer.py (--sign-tool,
                      --signed-uninstaller-dir; Code 3 = „erst signieren“), signing.py (sammeln/
                      einsetzen/pruefen), test_sign.ps1 (CI-Test-Zertifikat), build_linux_package.py,
                      build_msix.py (Store-Paket; --test-identity, --no-pack ohne SDK), test_msix.ps1
                      (CI: Testsignatur, Add-AppxPackage, Smoke-Test über App-Alias, Deinstallation),
                      test_windows_installer.ps1, test_linux_package.sh, release_notes.py
tests/                test_models, test_project, test_audio, test_settings_volume, test_ui (Touch/Maus,
                      Theme, Update-Dialog, Zustimmungsfrage, Registerkarten, Projektauswahl,
                      Kacheln ziehen, Durchklick-Schutz, Fader-Farben), test_update (lokaler
                      Fake-GitHub-Server), test_purge, test_single_instance, test_signing
                      (künstliche PE-Dateien), test_msix (Version, Identität, Manifest, Paketordner)
docs/                 images/ (README-Bilder), MICROSOFT_STORE.md (Konto, Einreichung, Updates im Store),
                      SIGNPATH.md (abgelehnt, für später aufbewahrt)
.github/workflows/    build.yml (wiederverwendbar, Input `sign`; Artefakt LaunchpadProTAB-Microsoft-Store),
                      ci.yml (jeder Push), release.yml (Tag v*)
```

### Datenfluss Kachel antippen

`Tile.qml` (TapHandler) → `backend.triggerTile(i)` (aktive Karte) → `engine.toggle((uid, r, c), pcm, loop)`
(deque) → Audio-Callback entscheidet atomar Start/Stopp → `engine.snapshot` → `Backend._tick()` (30 Hz)
aktualisiert die Laufzeitdaten ALLER Karten, `TileModel.refresh()` nur für die sichtbare → QML zeigt
Leuchten/Restzeit, TabStrip zeigt ▶ + Anzahl je Karte.

### Datenfluss Kachel verschieben

`Tile.qml` (DragHandler, nicht im Show-Modus) → `DragProxy.beginTile()` (Drag.keys
`application/x-lptab-tile`) → DropArea der Zielkachel → `backend.moveTile(von, nach)` →
`ProjectData.swap` + pcm/runtime tauschen + `engine.rekey({alt: neu})` + `editor.move_key()`.
Hat der Maus-Klick die Kachel gestartet (`triggerTile` → True), ruft der Beginn des Ziehens
`backend.stopTile(i)`. Dieselbe Karte, abgelegt auf *Bearbeiten & Schneiden* → DropArea in
`EditorSection.qml` → `backend.editTile(i)` → `editor.open_tile(key)`.

### Datenfluss Belegen

`assignAudio` → Thread: `Project.import_audio` (Kopie) → Prozess: `tasks.prepare` (Dekodieren →
Cache) → UI-Thread: `open_pcm` (memmap) + Kopf vorladen → Kachel bereit. `Backend._current(tab,
project, key, token)` verwirft veraltete Ergebnisse (Karte geschlossen, Projekt ersetzt, neuer Auftrag) –
Ergebnisse für Hintergrund-Karten werden normal übernommen.

### Datenfluss Update

**Store-Fassung (`InstallKind.MS_STORE`): `updater.start()` kehrt sofort zurück – kein Dialog, keine
Verbindung; Updates kommen über den Store.** Sonst:
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

- **Engine-Schlüssel der Kacheln sind `(tab.uid, row, col)`** (`ProjectTab.engine_key`,
  `Backend.engine_key(index)`), nie mehr `(row, col)` – sonst kollidieren Karten. `engine.stop_group(uid)`
  blendet eine Karte aus. Kachel-Slots aus QML gelten immer für die **aktive** Karte; asynchrone
  Ergebnisse tragen ihre Karte + ihr Projekt mit (`_current(...)` prüfen, `_refresh(tab, …)` zeigt nur
  die sichtbare Karte an). `apply_edit(project, …)` bekommt das Projekt, in dem bearbeitet wurde.
- Das `runtime`-dict einer Karte ist dasselbe Objekt wie im `TileModel` → nur leeren (`clear()`),
  nie neu zuweisen.
- **TapHandler in Pop-ups/Dialogen immer mit `gesturePolicy: TapHandler.ReleaseWithinBounds`**
  (siehe Stolperfallen), neue modale Pop-ups zählen `UiState.modalCount` (siehe AppDialog).
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
  (Update-Suche erst nach „Ja“ bzw. per Knopf; Store-Fassung nie). Die Datenschutzerklärung im
  README (`#datenschutz`) ist die Datenschutzrichtlinie der Store-Seite – neue Netzfunktionen immer
  mit Zustimmung + README-Abschnitt „Datenschutz“.
- **Store-Paket:** Identität (`identity_name`, `publisher`, `publisher_display_name`) und
  `display_name` in `packaging/msix/store.json` müssen **exakt** Partner Center entsprechen.
  MSIX-Version = `__version__` + `.0` (Store verlangt 0 an vierter Stelle, muss je Übermittlung
  steigen). Das Paket immer aus dem **unsignierten** PyInstaller-Ordner bauen (in `build.yml` vor den
  Test-Signatur-Schritten) und nie selbst signiert hochladen. Die Store-Fassung darf keine eigene
  Update-Installation anstoßen (Store-Richtlinie + schreibgeschützter `WindowsApps`-Ordner).
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
- Offscreen-Plattform im Test: Bildschirm nur 800×800 → kleiner als die Mindestgröße des Fensters;
  Meldungen werden dann so hoch, dass sie Kacheln überdecken. `tests/test_ui.py` stellt das Fenster
  deshalb auf 1440×900 (`visibility` Windowed + setWidth/setHeight).
- **Qt 6.11: Mausklick auf einen `TapHandler` mit Standard-`gesturePolicy` (DragThreshold) in einem
  modalen Pop-up erreicht zusätzlich die Pointer-Handler HINTER dem Pop-up** (Kachel startete beim
  Klick auf einen Farbkreis im Kachel-Menü). Eine MouseArea im Dialog-Hintergrund hilft NICHT.
  Abhilfe: TapHandler in Pop-ups mit `ReleaseWithinBounds` (exklusiver Grab); zusätzlich ignorieren
  Kacheln Eingaben, solange `UiState.modalOpen`. Klicks auf leere Dialogflächen, den abgedunkelten
  Hintergrund, Touch, Stift, Hover, Mausrad und Datei-Drops blockt Qt korrekt (getestet).
- **Windows: „Gedrückt halten“ mit Finger/Stift erzeugt beim Loslassen einen Rechtsklick** an der
  Fingerposition (Qt reicht ihn als Maus-Rechtsklick mit `source != NotSynthesized` weiter). Er lag
  neben dem gerade per langem Drücken geöffneten Kachel-Menü → `CloseOnPressOutside` schloss es
  sofort wieder. Offscreen nicht sichtbar (reine Touch-Ereignisse schließen nichts). Abhilfe doppelt:
  `integration.disable_press_and_hold()` schaltet es fürs Fenster ab (auch den Windows-Ring), und
  `bridge/touch.py` filtert solche Rechtsklicks auf allen Systemen (Test:
  `test_long_press_menu_survives_system_right_click`).
- **`TapHandler.acceptedButtons` filtert Touch nicht** (ein Finger hat keine Maustaste): Der
  Mittelklick-Handler der Registerkarten (`acceptedButtons: Qt.MiddleButton`) schloss bei *jedem*
  Antippen am Touchmonitor das Projekt. Handler, die nur für eine bestimmte Maustaste gedacht sind,
  brauchen `acceptedDevices: PointerDevice.Mouse` (Test: `test_tabs_by_touch`).
- Items ohne Eingabe (Rectangle/Text, z. B. Meldungen) lassen Klicks an die Kacheln darunter durch →
  `MouseArea { acceptedButtons: Qt.AllButtons; hoverEnabled: true }` hineinlegen (blockt auch Handler).
- QML-Funktionen (z. B. `openFor`) aus Python per `QMetaObject.invokeMethod(obj, "openFor",
  Q_ARG("QVariant", i))` aufrufen, nicht als Attribut.
- Nach einem Kartenwechsel (Modell-Reset) sind die Kachelpositionen erst nach einem Durchlauf der
  Ereignisschleife gültig (Grid-Polish) – in Skripten/Tests vor `mapToScene` kurz `processEvents`.
- Ein Modell-Reset zerstört die Kachel-Delegates – auch die gerade gezogene samt DragHandler; dann
  käme nie `finish()` und die Drag-Miniatur bliebe hängen. Daher: DragProxy bricht bei
  `backend.tabsChanged` ab, Tile setzt in `Component.onDestruction` `dragging = false`.
- **Deadlock in Skripten mit echtem Fenster (Windows, threaded Render-Loop):** `QTest.mouseRelease`
  u. ä. behalten die Python-Sperre (GIL) und synchronisieren dabei mit dem Render-Thread. Muss der
  dann ein Python-`QQuickPaintedItem` zeichnen (`WaveformView.paint`, z. B. nach Ablegen einer
  Kachel im Editor), wartet er ewig auf die GIL → Fenster „Keine Rückmeldung“. Betrifft nur
  Skripte (`tools/make_screenshots.py`), nicht die App (Ereignisse kommen aus `app.exec()`, GIL
  frei) und nicht die Tests (offscreen = Basic-Render-Loop). Abhilfe im Skript: solche Ereignisse
  per `QCoreApplication.postEvent(win, QMouseEvent(...))` einstellen und mit `processEvents`
  warten. In der App nie `processEvents`/Warteschleifen in Slots aufrufen.
- **Dauerschleifen in Threads: Schleifenvariablen halten Objekte fest.** `for v in …` im
  Vorlade-Thread ließ `v` nach der Schleife an die zuletzt gespielte Stimme gebunden → deren memmap
  blieb offen und Windows sperrte den Projektordner (Projekt löschen scheiterte). Deshalb liegt der
  Durchgang in `AudioEngine._prefetch_once()` (Test: `test_engine_prefetch_releases_finished_voices`).
  Offene memmaps findet man mit `gc.get_objects()` + `gc.get_referrers()` und `sys._current_frames()`.
- **Phase-Vocoder (timestretch.py):** Der harte Schnitt am **Ende** des Bereichs sah für die
  Transienten-Erkennung wie ein Einsatz aus → Tempo-1-Sperre kurz vor Schluss, der Zeitausgleich
  hatte keinen Platz mehr, die Länge stimmte um bis zu 40 ms nicht. Daher keine Erkennung, sobald
  das Fenster über `end` hinausragt. Der **Vorlauf** (Fenster vor dem ersten Ausgabe-Sample) muss
  mit Tempo 1 laufen, sonst beginnt die Ausgabe verschmiert statt exakt mit dem ersten Sample.
  Phasen-Resets ohne Tempo-1-Sperre helfen Schlägen kaum (Vorecho −9 … −18 dB, Spitze halbiert).
  Einsatz-Schwelle **+5 dB**, nicht +3 dB: Bei Rauschen (Gewitter, MP3-Ausklang) steigt zufällig
  ~1/3 der Frequenzen um 3 dB → Fehlalarme knapp über 35 % (Gewitter 12 statt 2 Einsätze, Klingel
  0,1 s zu kurz). +6 dB macht Sprache weicher.
  Neue Qualitätstests immer auch gegen das alte Verfahren laufen lassen: Ein reiner Dur-Dreiklang
  ist fast periodisch – daran scheitert nicht einmal WSOLA.
- `tools/demo_assets.py`: MP3 schreiben (LAME in libsndfile) sprengt unter Windows den 1-MB-Stack
  des Hauptthreads (STATUS_STACK_OVERFLOW 0xC00000FD) → läuft in einem Thread mit 64 MB Stack.
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
- **Intelligente App-Steuerung auf dem Nutzer-PC** (Ereignisanzeige: *Microsoft-Windows-
  CodeIntegrity/Operational*, Ereignis 3077 „did not meet the Enterprise signing level
  requirements“; Status: Registry `…\Control\CI\Policy\VerifiedAndReputablePolicyState`, 1 = an)
  blockiert nicht nur Launchpad Pro, sondern auch **frisch per pip installierte Binärpakete**:
  `pip install av==19.0.1` in die `.venv` → „DLL load failed … Eine Anwendungssteuerungsrichtlinie
  hat diese Datei blockiert“. In der Nutzer-`.venv` keine Binärpakete aktualisieren (ggf. sofort
  die alte Version zurückinstallieren, z. B. `av==18.1.0`); neue Bibliotheksversionen in der CI
  prüfen. Ein testweise signiertes MSIX lässt sich dort ebenfalls nicht installieren → CI.
- **PyAV 19** hat `av.open(..., metadata_errors=…)` entfernt (Metadaten jetzt immer UTF-8 mit
  `surrogateescape`) → TypeError, MP3/M4A ließen sich nicht mehr laden. CI installiert immer die
  neueste Version, lokal lief noch 18.1 → erst in der CI aufgefallen. Abhilfe `decoder._av_open()`
  (mit Parameter versuchen, bei TypeError ohne); Test `test_decode_with_pyav_19_open_signature`.
- **MSIX: `PATH` gilt nicht für DLLs.** Im Paket lud die Oberfläche nicht („Cannot load library
  …\qml\QtQuick\Controls\Basic\qtquickcontrols2basicstyleplugin.dll: The specified module could not
  be found“) – Qt-Plugins finden ihre Qt6*.dll in `_internal\PySide6` außerhalb des Pakets über PATH
  (PyInstaller/PySide6), im Paket ignoriert Windows PATH. Abhilfe im Manifest:
  `uap6:LoaderSearchPathOverride` mit `_internal\PySide6` und `_internal` (max. 5 Einträge, gilt für
  alle Prozesse des Pakets inkl. Worker). Fehlertext liefert der Smoke-Test-Bericht (`problems`).
- XML-Kommentare dürfen kein `--` enthalten (z. B. `--fullscreen` im Manifest-Kommentar → makeappx/
  ElementTree „not well-formed“). `string.Template` in `build_msix.py`: kein `$` mit geschweiften
  Klammern in Kommentaren der Vorlage.
- Python-Skripte per Bash-Heredoc an `python -` mit `\n` in Ersetzungstexten: Escape-Sequenzen
  verwirren sich leicht → solche Änderungen mit dem Edit-Werkzeug machen.

## 6. Teststrategie

- `tests/test_audio.py`: Formate (WAV/FLAC/OGG/MP3/AIFF via libsndfile, M4A/Opus via FFmpeg),
  Resampling, Time-Stretch (exakt bei 1,0×, Länge, Tonhöhe, Streaming, Mehrstimmigkeit ohne Rauigkeit,
  Transienten ohne Vorecho/gleichmäßiger Rhythmus, Stereobild, Tempo-Regler live), Cache, Rendern,
  Engine (Fade, Loop, Limiter, Vorschau).
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
- `tests/test_msix.py`: MSIX-Version (Vorabversionen → kein Paket), Identität aus `store.json`
  (Pflichtfelder, Test-Identität nur mit Schalter), Manifest (Identität, runFullTrust, `.lptab`,
  App-Alias, alle Bilder vorhanden, XML-Maskierung), Paketordner ohne SDK, Bildvarianten, Store-ID
  für den Installer, Reihenfolge im Workflow (Store-Paket vor Test-Signatur), ASCII-Skript.
  `test_update.py`/`test_ui.py`: Store-Fassung fragt/sucht nie, Einstellungen zeigen den Store.
- CI (`build.yml`, Windows): Store-Paket bauen → `tools/test_msix.ps1` (Kopie mit Test-Zertifikat
  signieren, `Add-AppxPackage`, Alias + `resources.pri` prüfen, `--smoke-test` im Paket mit
  `LPTAB_SMOKE_REPORT` → `install_kind == microsoft-store`, Deinstallation) → Artefakt
  **LaunchpadProTAB-Microsoft-Store** (90 Tage).
- CI (`build.yml`): Tests Linux+Windows; Windows: EXE + Smoke-Test, kompletter Signierablauf mit
  Test-Zertifikat (2 Inno-Durchläufe, Smoke-Test der signierten EXE), Installer bauen und mit
  `tools/test_windows_installer.ps1` **echt installieren, updaten (bei laufendem Programm) und
  deinstallieren (mit Datenlöschung)**; Linux (ubuntu-22.04): Paket bauen + `test_linux_package.sh`.
- `test_ui.py` (v1.2): Registerkarten (Hintergrund-Wiedergabe, Wechsel, Schließen, leere Karte,
  Wiederherstellen, per Touch antippen ohne zu schließen), Projekt löschen (offen + spielend,
  Fremdordner/Benutzerordner abgelehnt, nicht gefunden, Show-Modus, Klickweg mit Rückfrage; mit
  Ersatz-Papierkorb im Temp-Ordner), Kachel-Menü nach langem Drücken übersteht
  den System-Rechtsklick, Projektauswahl per Klick, Kacheln tauschen (Backend, echte Maus inkl. Ton-Abbruch,
  Touch, Show-Modus gesperrt), Kachel in den Editor ziehen (Maus/Touch, dieselbe Kachel, Wechsel mit
  Hinweis), Durchklick-Schutz (Farbkreis per Maus/Touch, Meldung antippen),
  Fader-Farben hell/dunkel, Vollbild-Schalter (Klick, F11, Fenstersystem, `--fullscreen` ohne Speichern).
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
6. Signatur: SignPath wurde abgelehnt → Releases sind unsigniert (die Variable
   `SIGNPATH_ORGANIZATION_ID` ist nicht gesetzt). Signiert wird über den **Microsoft Store**:
   Artefakt *LaunchpadProTAB-Microsoft-Store* des Release-Laufs in Partner Center als neue
   Übermittlung hochladen (`docs/MICROSOFT_STORE.md`). Voraussetzung: echte Identität in
   `packaging/msix/store.json` (sonst baut die CI nur ein Testpaket mit Warnung).

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
  signiert, fremd signierte behalten ihre Signatur). CI #13 (3d44501, Windows, `SIGNATUR=test`):
  kompletter Ablauf grün – signierte PyInstaller-EXE startet (Smoke-Test), Installer-E2E meldet
  „Signatur: LaunchpadProTAB.exe/unins000.exe“, Update + Deinstallation ok. SignPath-Antrag stellt der
  Nutzer (`docs/SIGNPATH.md`); Signatur mit echtem Zertifikat und die SignPath-Action selbst sind
  noch ungetestet (Eingaben der Action aus dem Gedächtnis – beim ersten echten Lauf prüfen).
- v1.2 (unveröffentlicht, lokal Windows 11, Python 3.13, PySide6 6.11.2): 96 Tests grün (3 Linux-Tests
  übersprungen), `--smoke-test` grün, README-Bilder unter Windows neu erzeugt (inkl.
  18_projektauswahl, 19_kachel_verschieben, 20_kachel_bearbeiten, 21_projekt_loeschen,
  11_einstellungen mit Vollbild-Schalter); Vollbild-Start
  (Einstellung bzw. `--fullscreen`) im echten Windows-Fenster geprüft. Kachel-in-den-Editor-Ziehen im
  echten Fenster mit echter Audioausgabe geprüft (Ereignisse über die Ereignisschleife);
  `QFile.moveToTrash` mit echtem Windows-Papierkorb geprüft (gemappte Datei → `False` ohne Dialog,
  danach Erfolg). (Entstanden in einem Arbeitsordner ohne git auf Basis von v1.1.0; am 07.10.2026
  mit dem GitHub-Stand – Zustimmungsfrage, MIT-Lizenz, SignPath – zusammengeführt: 111 Tests grün,
  `--smoke-test` grün, README-Bilder unter Windows neu erzeugt, Frage-Bild heißt jetzt `22_update_frage.png`.)
- Phase-Vocoder (v1.2, lokal Windows 11): 103 Tests grün, `--smoke-test` grün; neue Time-Stretch-Tests
  schlagen mit dem alten WSOLA fehl (7 von 13). Gemessen mit synthetischen Signalen, Windows-Sprachausgabe
  (SAPI „Hedda“) und den Testdateien des Nutzers (Türklingel: Rauigkeit wie im Original statt +6 … +10 dB).
  Hörprobe durch den Nutzer steht noch aus.
- Microsoft-Store-Fassung (07.10.2026, lokal Windows 11): 135 Tests grün, `--smoke-test` inkl.
  `LPTAB_SMOKE_REPORT` grün, Paketordner + alle 30 Bildvarianten lokal erzeugt und angesehen,
  `test_msix.ps1` mit dem Parser von Windows PowerShell 5.1 geprüft. Paketbau mit makeappx/makepri
  und Installation des Pakets laufen nur in der CI (lokal kein Windows SDK, App-Steuerung an).
  CI 1392d8b (GitHub Actions, windows-latest) komplett grün: MSIX (108 MB) gebaut, testsigniert
  installiert, Alias + Dateizuordnung + resources.pri vorhanden, Smoke-Test im Paket (inkl.
  Worker-Prozesse) meldet `microsoft-store` + Paketfamilie, Deinstallation sauber; Inno-Installer mit
  App-Steuerungs-Hinweis kompiliert, Installations-/Update-/Deinstallationstest grün; Tests Linux +
  Windows mit PyAV 19 grün. Store-Konto, Namensreservierung und erste Einreichung macht der Nutzer.
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
- Store-Übermittlung automatisieren (Microsoft Store Developer CLI `msstore` bzw. Submission-API in
  `release.yml`; braucht eine Entra-ID-App mit Zugriff auf Partner Center).
