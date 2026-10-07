# Launchpad Pro im Microsoft Store veröffentlichen

**Warum?** Windows 11 blockiert mit der *intelligenten App-Steuerung* (Smart App Control) jedes
Programm, das nicht mit einem vertrauenswürdigen Zertifikat signiert ist. Eine Ausnahme für einzelne
Programme gibt es nicht, und selbst erstellte Zertifikate erkennt sie nicht an. Ein MSIX-Paket aus dem
**Microsoft Store** signiert Microsoft selbst – kostenlos. Damit lässt sich Launchpad Pro auf
jedem Windows-PC installieren, und der Store hält es automatisch aktuell.

Im Repository ist dafür alles vorbereitet:

| Baustein | Wo |
|---|---|
| Store-Paket bauen (Manifest, Kachel-Bilder, Dateizuordnung `.lptab`) | `tools/build_msix.py`, `packaging/msix/` |
| Bei jedem CI-Lauf: Paket bauen, testweise installieren, starten, deinstallieren | `.github/workflows/build.yml`, `tools/test_msix.ps1` |
| Programm erkennt die Store-Fassung → keine eigene Update-Suche, Hinweis auf den Store | `update/install.py` (`InstallKind.MS_STORE`), `bridge/updater.py` |
| Installer weist auf PCs mit App-Steuerung auf die Store-Fassung hin | `packaging/windows/LaunchpadProTAB.iss` |

Was nur du selbst erledigen kannst: Konto anlegen, App-Namen reservieren, Paket hochladen.

---

## 1. Entwicklerkonto anlegen (einmalig, kostenlos)

1. **https://storedeveloper.microsoft.com** öffnen und mit einem **persönlichen Microsoft-Konto**
   anmelden.
2. Als **Einzelperson** (Individual) registrieren. Für Einzelpersonen kostet das nichts.
3. **Identität bestätigen:** Personalausweis oder Reisepass scannen und ein Selfie aufnehmen – das
   Formular führt Schritt für Schritt durch.
4. Danach steht das **Partner Center** bereit: https://partner.microsoft.com/dashboard

## 2. App-Namen reservieren

1. Partner Center › **Apps und Spiele** › **Neues Produkt** › **MSIX- oder PWA-App**.
2. Name: **Launchpad Pro TAB Edition** › *Verfügbarkeit prüfen* › *Produktnamen reservieren*.
   - Ist der Name vergeben, einen anderen wählen (z. B. „Launchpad Pro TAB Edition – Theater-Soundboard“)
     und ihn genauso in `packaging/msix/store.json` bei `display_name` eintragen – Manifest und
     Reservierung müssen exakt übereinstimmen.

## 3. Paket-Identität übernehmen

Partner Center › die App › **Produktverwaltung › Produktidentität**. Dort stehen vier Werte, die in
[`packaging/msix/store.json`](../packaging/msix/store.json) gehören:

| Partner Center | `store.json` | Beispiel |
|---|---|---|
| `Package/Identity/Name` | `identity_name` | `12345RubenBlaettel.LaunchpadProTABEdition` |
| `Package/Identity/Publisher` | `publisher` | `CN=A1B2C3D4-0000-0000-0000-000000000000` |
| `Package/Properties/PublisherDisplayName` | `publisher_display_name` | `Ruben Blättel` |
| Store-ID | `store_id` | `9NXXXXXXXXXX` (12 Zeichen) |

Die Werte genau so übernehmen (Groß-/Kleinschreibung!), committen und pushen – oder sie einfach
Claude geben. Der nächste CI-Lauf baut dann das Paket mit der echten Identität (die Warnung
„TEST-Identität“ verschwindet), und der Installer verweist mit der Store-ID direkt auf die Store-Seite.

## 4. Store-Paket herunterladen

GitHub › **Actions** › **CI** › den neuesten grünen Lauf öffnen › unten bei *Artifacts*
**LaunchpadProTAB-Microsoft-Store** herunterladen und entpacken → `LaunchpadProTAB-<Version>.msix`.
(Bei einem Release liegt es genauso im Lauf des Workflows *Release*; GitHub bewahrt es 90 Tage auf.)

Mit der GitHub-Kommandozeile geht es auch so:

```bash
gh run download --repo RubenBlaettel/Launchpad-Pro-TAB-Edition --name LaunchpadProTAB-Microsoft-Store
```

Das Paket ist **absichtlich unsigniert** – der Store signiert es. Per Doppelklick lässt es sich
deshalb nicht installieren; das ist normal.

## 5. Erste Einreichung

Partner Center › die App › **Übermittlung starten**. Die Abschnitte:

### Preise und Verfügbarkeit

- **Märkte:** alle oder nur Deutschland/Österreich/Schweiz.
- **Sichtbarkeit:**
  - *Öffentlich* – jeder findet die App im Store.
  - *Nicht auffindbar, nur per direktem Link* – passend, wenn nur der Verein die App nutzen soll.
- **Preis:** Kostenlos.

### Eigenschaften

- **Kategorie:** Musik (alternativ Produktivität).
- **Datenschutzrichtlinie:** `https://github.com/RubenBlaettel/Launchpad-Pro-TAB-Edition#datenschutz`
- **Website:** `https://github.com/RubenBlaettel/Launchpad-Pro-TAB-Edition`
- **Supportkontakt:** `https://github.com/RubenBlaettel/Launchpad-Pro-TAB-Edition/issues` oder eine E-Mail-Adresse.
- **Systemanforderungen** (optional): Touchscreen *empfohlen*, Arbeitsspeicher mind. 4 GB.

### Altersfreigaben

Fragebogen (IARC) ausfüllen: App-Typ *alle anderen App-Typen*; keine Gewalt, keine Kommunikation
zwischen Nutzern, keine Käufe, keine Standortdaten → Freigabe ab 0 Jahren (USK 0).

### Pakete

`LaunchpadProTAB-<Version>.msix` hineinziehen. Partner Center prüft sofort, ob Name, Herausgeber
und Version passen. Gerätefamilie: **Desktop**.

### Store-Einträge (Deutsch)

Vorschläge zum Einfügen:

- **Beschreibung:**

  > Launchpad Pro TAB Edition ist ein touch-optimiertes Soundboard für den Theaterbetrieb. Audiodateien
  > werden auf farbige Kacheln gelegt und per Fingertipp oder Mausklick mit sehr geringer Verzögerung
  > abgespielt – wie mit einem Hardware-Launchpad. Mehrere Kacheln laufen gleichzeitig, jede auf Wunsch
  > in Schleife; „ALLES STOPPEN“ beendet alles mit einem Tipp.
  >
  > Eine eingebaute Schnittfunktion zeigt die Wellenform, setzt Anfang und Ende, ändert die
  > Geschwindigkeit ohne Tonhöhenänderung und passt die Lautstärke an – nicht-destruktiv und
  > jederzeit änderbar. Projekte speichern sich automatisch, mehrere Projekte sind gleichzeitig in
  > Registerkarten geöffnet, und der Show-Modus sperrt während der Vorstellung alle Bearbeitungen.
  >
  > Open Source (MIT-Lizenz), ohne Werbung, ohne Telemetrie.

- **Funktionen** (je eine Zeile): Kachel-Raster 3×3 bis 7×7 mit Farben und Coverbildern ·
  Mehrere Kacheln gleichzeitig, Schleife je Kachel · Schneiden, Tempo und Lautstärke je Kachel ·
  Projekte in Registerkarten, automatisches Speichern · Show-Modus für die Vorstellung ·
  Master-Fader für die Windows-Lautstärke · Dunkles und helles Design · Optimiert für Touchscreens
- **Screenshots** (1920×1080, aus `docs/images/`): `02_hauptansicht.png`, `08_raster.png`,
  `06_bearbeiten.png`, `12_hauptansicht_hell.png`, `09_show_modus.png`, `03_kachelmenue.png`.
- **Suchbegriffe:** Soundboard, Theater, Launchpad, Bühne, Sound-Effekte, Zuspieler, Touch

### Übermittlungsoptionen

Bei **eingeschränkte Funktionen** (`runFullTrust`) fragt Partner Center nach einer Begründung:

> Launchpad Pro TAB Edition ist eine klassische Desktop-Anwendung (Python/Qt), die als MSIX-Paket
> verteilt wird. runFullTrust ist für jede Win32-Desktop-Anwendung im Paket erforderlich; die App
> spielt Audio über WASAPI ab, liest vom Nutzer gewählte Audiodateien und speichert Projekte im
> Dokumente-Ordner.

**Übermitteln** → die Zertifizierung dauert meist 1–3 Werktage; Partner Center schickt eine E-Mail.

## 6. Nach der Freigabe

- Store-Seite: `https://apps.microsoft.com/detail/<Store-ID>` – diesen Link weitergeben bzw. im
  README eintragen (Abschnitt *Windows: Microsoft Store*).
- Ist `store_id` in `store.json` eingetragen, öffnet der Installer auf PCs mit App-Steuerung direkt
  diese Store-Seite.
- Installation auf einem Fremdrechner: Link öffnen → **Installieren**. Ein Microsoft-Konto ist für
  kostenlose Apps nicht nötig, Administratorrechte auch nicht.

## 7. Updates veröffentlichen

1. Neue Version wie gewohnt vorbereiten (Versionsnummer, CHANGELOG, Push, ggf. Release – siehe
   README *Neue Version veröffentlichen*). Die Versionsnummer muss höher sein als die der letzten
   Store-Übermittlung.
2. Das neue `.msix` aus dem CI- bzw. Release-Lauf herunterladen (Schritt 4).
3. Partner Center › die App › **Update** (neue Übermittlung) › *Pakete*: das alte Paket entfernen, das
   neue hochladen › bei *Store-Einträge* „Neuigkeiten in dieser Version“ ausfüllen (Text aus
   `CHANGELOG.md`) › **Übermitteln**.
4. Nach der Zertifizierung installiert Windows das Update auf allen Rechnern automatisch.

## Häufige Fragen

- **Muss ich etwas signieren oder ein Zertifikat kaufen?** Nein – das erledigt der Store.
- **Gibt es den Installer weiterhin?** Ja, für PCs ohne App-Steuerung (z. B. ältere oder
  aktualisierte Windows-Installationen). Er warnt, wenn die App-Steuerung eingeschaltet ist.
- **Laufen beide Fassungen nebeneinander?** Ja. Sie teilen sich die Projekte (Ordner *Dokumente ›
  Launchpad Pro TAB*); Einstellungen der Store-Fassung verwaltet Windows in einem eigenen Bereich, der
  beim Deinstallieren gelöscht wird. Projekte bleiben immer erhalten.
- **Kann ich das Paket vor der Einreichung testen?** Auf einem PC mit eingeschalteter
  App-Steuerung nicht – dort blockiert Windows jedes testweise signierte Paket. Das übernimmt die CI:
  Sie installiert das Paket bei jedem Lauf mit einem Test-Zertifikat auf einem Windows-Server,
  startet es (Smoke-Test inkl. Audio-Dekodierung) und deinstalliert es wieder.
- **Partner Center meldet „Paketidentität stimmt nicht überein“:** Die Werte in `store.json`
  stimmen nicht exakt mit *Produktidentität* überein (auch `display_name` prüfen).
- **Vorabversionen (Beta)?** Für Versionen mit Buchstaben (z. B. `1.3.0-beta.1`) entsteht kein
  Store-Paket – Betas gibt es nur über die GitHub-Releases.
