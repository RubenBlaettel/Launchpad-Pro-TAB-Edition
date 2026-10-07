# Code-Signatur mit SignPath einrichten

**Warum?** Windows 11 blockiert mit der *intelligenten App-Steuerung* (Smart App Control) jedes
Programm, das nicht digital signiert ist und das Microsoft noch nicht kennt – beim Installer von
Launchpad Pro erscheint dann „Fehler 4551: Eine Anwendungssteuerungsrichtlinie hat diese Datei
blockiert“. Eine Ausnahme für einzelne Programme gibt es nicht. Mit einer Signatur laufen Installer
und Programm auf allen PCs ohne Umstellung.

Launchpad Pro nutzt dafür das kostenlose Angebot der **SignPath Foundation** für Open-Source-Projekte.
Der Release-Workflow ist fertig vorbereitet – er signiert automatisch, sobald die Schritte unten
erledigt sind. Bis dahin werden Releases wie bisher unsigniert veröffentlicht.

---

## 1. Antrag bei der SignPath Foundation

Voraussetzungen (alle bereits erfüllt):

| Voraussetzung | Wo |
|---|---|
| Open-Source-Lizenz (OSI) | [`LICENSE`](../LICENSE) – MIT, © 2026 TAB Theater |
| Öffentliches Repository | https://github.com/RubenBlaettel/Launchpad-Pro-TAB-Edition |
| Build auf einem vertrauenswürdigen CI-System | GitHub Actions (GitHub-gehostete Runner), `.github/workflows/release.yml` |
| Code-Signing-Richtlinie mit Rollen | README › [Code-Signatur](../README.md#code-signatur) |
| Datenschutzerklärung | README › [Datenschutz](../README.md#datenschutz) – das Programm sendet nur nach ausdrücklicher Zustimmung Daten (Update-Suche) |

So geht's:

1. Für GitHub und später auch für SignPath die **Zwei-Faktor-Anmeldung** einschalten (wird verlangt).
2. Auf **signpath.org** den Antrag für Open-Source-Projekte stellen (*Apply*). Vorschlag für die
   Angaben (auf Englisch):
   - **Project name:** Launchpad Pro TAB Edition
   - **Repository:** `https://github.com/RubenBlaettel/Launchpad-Pro-TAB-Edition`
   - **License:** MIT
   - **Description:** *Touch-optimized soundboard (launchpad) for theater productions: assign audio
     files to a grid of tiles and play them with low latency. Python/Qt application packaged with
     PyInstaller and an Inno Setup installer; all release builds run on GitHub Actions.*
   - **Artifacts to sign:** Windows installer (`LaunchpadProTAB-Setup-x.y.z.exe`), the program
     executable and the bundled open-source libraries without a publisher signature
     (see `THIRD_PARTY_NOTICES.md`)
   - **Code signing policy:** `https://github.com/RubenBlaettel/Launchpad-Pro-TAB-Edition#code-signatur`
   - **Privacy policy:** `https://github.com/RubenBlaettel/Launchpad-Pro-TAB-Edition#datenschutz`
   - **Team:** RubenBlaettel (Committer, Reviewer, Approver)
3. Die Prüfung dauert in der Regel einige Tage; SignPath meldet sich per E-Mail. Fragt SignPath nach
   Änderungen (z. B. an der Richtlinie im README), kann Claude diese direkt umsetzen.

## 2. Nach der Zusage: Projekt in SignPath

Meist richtet SignPath Organisation und Projekt mit ein. Zu prüfen bzw. zu ergänzen:

1. **Projekt** mit dem Slug `Launchpad-Pro-TAB-Edition` und der Repository-URL.
2. **Trusted Build System** *GitHub.com* mit dem Projekt verknüpfen (damit SignPath prüfen kann, dass
   die Dateien wirklich aus diesem Repository gebaut wurden).
3. **Artifact Configuration** mit dem Slug `windows` anlegen und den Inhalt von
   [`packaging/signpath/artifact-configuration.xml`](../packaging/signpath/artifact-configuration.xml)
   einfügen.
4. **Signing Policy** `release-signing` (vorgegeben): Jede Anfrage muss von einem *Approver*
   freigegeben werden.
5. Einen **CI-Benutzer** anlegen (*Users › Add CI user*), ihm im Projekt die Rolle *Submitter* geben
   und ein **API-Token** erzeugen.

## 3. GitHub einrichten

Im Repository unter *Settings › Secrets and variables › Actions*:

| Art | Name | Wert |
|---|---|---|
| Secret | `SIGNPATH_API_TOKEN` | API-Token des CI-Benutzers |
| Variable | `SIGNPATH_ORGANIZATION_ID` | Organisations-ID (SignPath › *Organization settings*) |
| Variable (optional) | `SIGNPATH_PROJECT_SLUG` | nur falls abweichend von `Launchpad-Pro-TAB-Edition` |
| Variable (optional) | `SIGNPATH_POLICY_SLUG` | nur falls abweichend von `release-signing` |
| Variable (optional) | `SIGNPATH_ARTIFACT_CONFIGURATION_SLUG` | nur falls abweichend von `windows` |
| Variable (optional) | `SIGNIEREN_NUR_EIGENE_DATEIEN` | `true`, falls nur `LaunchpadProTAB.exe` (plus Installer/Deinstaller) signiert werden soll |

Sobald `SIGNPATH_ORGANIZATION_ID` gesetzt ist, signiert jeder Release-Lauf.

## 4. Release mit Signatur

1. Version erhöhen und Release anlegen wie in der README beschrieben (Tag `vX.Y.Z`).
2. Der Workflow **Release** schickt zwei Signaturanfragen an SignPath – zuerst die Programmdateien
   samt Deinstaller, danach den fertigen Installer. Zu jeder kommt eine E-Mail: in SignPath
   **Approve** klicken. Der Workflow wartet bis zu zwei Stunden je Anfrage.
3. Danach prüft der Workflow jede Signatur (`Get-AuthenticodeSignature` muss *Valid* melden),
   installiert, aktualisiert und deinstalliert testweise und veröffentlicht erst dann.

## Was wird signiert – und wie?

- **Programmdateien:** alle EXE/DLL/PYD im Programmordner ohne Signatur – das eigene Programm
  (`LaunchpadProTAB.exe`) und mitgelieferte Open-Source-Bibliotheken (z. B. FFmpeg, libsndfile,
  PortAudio, NumPy). Die App-Steuerung prüft auch jede geladene DLL. Bereits signierte Dateien
  (Qt, Python, Microsoft-Laufzeit) behalten die Signatur ihres Herstellers.
- **Deinstaller** `unins000.exe` – dieselbe Datei führt Setup während der Installation im
  Temp-Ordner aus (`LaunchpadProTAB-Setup-x.y.z.tmp`, genau diese wurde bei 1.1.0 blockiert).
  Inno Setup legt sie im ersten Durchlauf unsigniert ab (`build/inno-signiert/uninst-*.e64`), nach
  der Signatur übernimmt der zweite Durchlauf sie (Inno prüft dabei, dass der Inhalt identisch ist).
- **Installer** `LaunchpadProTAB-Setup-x.y.z.exe`.

`tools/signing.py` sammelt die Dateien durchnummeriert (`0001.dll`, `0002.exe` …), setzt sie nach
der Signatur wieder ein und prüft das Ergebnis.

## Testen ohne SignPath

- **Jeder CI-Lauf** spielt den kompletten Ablauf mit einem selbst erstellten Test-Zertifikat durch
  (`tools/test_sign.ps1`) – inklusive Smoke-Test der signierten EXE und Test-Installation. Diese
  Signatur ist nicht vertrauenswürdig; CI-Artefakte helfen daher nicht gegen die App-Steuerung.
- **Eigenes Zertifikat** (lokal unter Windows): Programmdateien mit `signtool` signieren, dann
  `python tools/build_installer.py --sign-tool "signtool sign /a /fd sha256 /tr http://timestamp.digicert.com /td sha256 $f"`
  – signiert Installer und Deinstaller direkt beim Bauen.
