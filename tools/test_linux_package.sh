#!/bin/sh
# Prüft das Linux-Programmpaket von vorne bis hinten (im CI und lokal nutzbar):
#   Installation mit install.sh, Start (--smoke-test), Update-Tausch über den
#   Hilfsprozess der neuen Version, Deinstallation inkl. Projekte und Einstellungen.
#
#   sh tools/test_linux_package.sh dist/LaunchpadProTAB-<version>-linux-x86_64.tar.gz
#
# Als normaler Benutzer ausführen (root installiert nach /opt). Benutzt einen eigenen,
# temporären Benutzerordner – echte Einstellungen und Projekte bleiben unberührt.
set -eu

if [ "$(id -u)" = 0 ]; then
    echo "Bitte als normaler Benutzer ausführen (root installiert nach /opt)." >&2
    exit 2
fi

PKG=$(cd "$(dirname "$1")" && pwd)/$(basename "$1")
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

export HOME="$WORK/home"
export XDG_DATA_HOME="$HOME/.local/share" XDG_CONFIG_HOME="$HOME/.config" XDG_CACHE_HOME="$HOME/.cache"
export QT_QPA_PLATFORM=offscreen LPTAB_UPDATE_URL=http://127.0.0.1:9/keine-updates
unset LPTAB_CONFIG_DIR LPTAB_PROJECTS_DIR LPTAB_CACHE_DIR
mkdir -p "$HOME/Desktop" "$HOME/Documents"

must() {  # must "Beschreibung" befehl [argumente …] – bricht bei Fehlschlag ab
    desc=$1
    shift
    if "$@"; then
        printf '  ok: %s\n' "$desc"
    else
        printf 'FEHLER: %s\n' "$desc" >&2
        exit 1
    fi
}
absent() { [ ! -e "$1" ]; }
no_leftovers() { [ -z "$(find "$XDG_DATA_HOME" -maxdepth 1 \( -name '.alt-*' -o -name '.launchpad-update-*' \))" ]; }

echo "== Installation"
tar -xzf "$PKG" -C "$WORK"
SRC=$(find "$WORK" -maxdepth 1 -type d -name "LaunchpadProTAB-*-linux-x86_64" | head -n 1)
"$SRC/install.sh" --yes
APP="$XDG_DATA_HOME/launchpad-pro-tab"
must "Programm installiert" test -x "$APP/LaunchpadProTAB"
must "Deinstallationsskript vorhanden" test -x "$APP/uninstall.sh"
must "Menüeintrag" test -f "$XDG_DATA_HOME/applications/LaunchpadProTAB.desktop"
must "Desktop-Verknüpfung" test -f "$HOME/Desktop/LaunchpadProTAB.desktop"
must "Dateizuordnung .lptab" test -f "$XDG_DATA_HOME/mime/packages/launchpad-pro-tab.xml"

echo "== Start"
must "Smoke-Test" "$HOME/.local/bin/launchpad-pro-tab" --smoke-test

echo "== Update (Ordnertausch + Neustart)"
STAGE=$(mktemp -d "$XDG_DATA_HOME/.launchpad-update-XXXXXX")
tar -xzf "$PKG" -C "$STAGE"
NEW=$(find "$STAGE" -maxdepth 1 -type d -name "LaunchpadProTAB-*" | head -n 1)
echo neu > "$NEW/_internal/UPDATE-MARKER"
sleep 2 &
OLD_PID=$!
must "neue Version gestartet" "$NEW/LaunchpadProTAB" --finish-update "$APP" --wait-pid "$OLD_PID" -- --smoke-test
must "Programmordner ersetzt" test -f "$APP/_internal/UPDATE-MARKER"
must "Installationsdaten übernommen" test -f "$APP/.install-info"
must "Update-Zwischenordner entfernt" absent "$STAGE"

echo "== Deinstallation inkl. Projekte und Einstellungen"
mkdir -p "$HOME/Documents/Launchpad Pro TAB/CI-Projekt/audio"
printf '{"format": "launchpad-pro-tab", "version": 1}' > "$HOME/Documents/Launchpad Pro TAB/CI-Projekt/projekt.lptab"
"$APP/uninstall.sh" --purge --yes
must "Programm entfernt" absent "$APP"
must "keine Update-Reste" no_leftovers
must "Menüeintrag entfernt" absent "$XDG_DATA_HOME/applications/LaunchpadProTAB.desktop"
must "Desktop-Verknüpfung entfernt" absent "$HOME/Desktop/LaunchpadProTAB.desktop"
must "Befehl entfernt" absent "$HOME/.local/bin/launchpad-pro-tab"
must "Projekte gelöscht" absent "$HOME/Documents/Launchpad Pro TAB"
must "Einstellungen gelöscht" absent "$XDG_CONFIG_HOME/launchpad-pro-tab"
echo "Linux-Paket-Test erfolgreich."
