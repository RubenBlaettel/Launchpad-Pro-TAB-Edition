#!/bin/sh
# ============================================================================
#  Launchpad Pro TAB Edition – Installation unter Linux
# ============================================================================
#
#  Aus dem entpackten Paket heraus aufrufen:
#      ./install.sh                     interaktiv (Ordner, Menüeintrag, Desktop-Verknüpfung)
#      ./install.sh --yes               ohne Rückfragen mit Standardwerten
#      ./install.sh --prefix DIR --no-desktop --no-menu --no-mime --yes
#
#  Deinstallieren (im Installationsordner):
#      ./uninstall.sh                   fragt, ob Projekte/Einstellungen gelöscht werden sollen
#      ./uninstall.sh --purge --yes     inkl. aller Projekte und Einstellungen, ohne Rückfrage
#
#  Intern (Update mit Administratorrechten über pkexec, vom Programm aufgerufen):
#      install.sh --update --target DIR --source NEUER_ORDNER
#
#  Standard: für den aktuellen Benutzer nach ~/.local/share/launchpad-pro-tab (keine
#  Administratorrechte nötig, Updates laufen automatisch). Als root: /opt/launchpad-pro-tab.
# ============================================================================
set -eu

APP_NAME="Launchpad Pro TAB Edition"
APP_ID="LaunchpadProTAB"            # = QGuiApplication.desktopFileName (Wayland app_id)
EXE="LaunchpadProTAB"
ICON_NAME="launchpad-pro-tab"
MIME_TYPE="application/x-launchpad-pro-tab"
INFO=".install-info"

SRC=$(cd "$(dirname "$0")" && pwd)
MODE="install"
PREFIX=""
TARGET=""
SOURCE=""
ASSUME_YES=0
WANT_MENU=1
WANT_DESKTOP=1
WANT_MIME=1
PURGE=""

say() { printf '%s\n' "$*"; }
die() { printf 'Fehler: %s\n' "$*" >&2; exit 1; }

ask() {  # ask "Frage" Standard(1/0) -> 0=ja, 1=nein
    if [ "$ASSUME_YES" = 1 ] || [ ! -t 0 ]; then
        [ "$2" = 1 ] && return 0 || return 1
    fi
    if [ "$2" = 1 ]; then hint="[J/n]"; else hint="[j/N]"; fi
    printf '%s %s ' "$1" "$hint"
    read -r answer || answer=""
    case "$answer" in
        [JjYy]*) return 0 ;;
        [Nn]*) return 1 ;;
        *) [ "$2" = 1 ] && return 0 || return 1 ;;
    esac
}

while [ $# -gt 0 ]; do
    case "$1" in
        --prefix) PREFIX="$2"; shift ;;
        --target) TARGET="$2"; shift ;;
        --source) SOURCE="$2"; shift ;;
        --update) MODE="update" ;;
        --uninstall) MODE="uninstall" ;;
        --purge) PURGE=1 ;;
        --keep-data) PURGE=0 ;;
        --no-menu) WANT_MENU=0 ;;
        --no-desktop) WANT_DESKTOP=0 ;;
        --no-mime) WANT_MIME=0 ;;
        -y|--yes) ASSUME_YES=1 ;;
        -h|--help) sed -n '2,24p' "$0"; exit 0 ;;
        *) die "Unbekannte Option: $1" ;;
    esac
    shift
done

if [ "$(id -u)" = 0 ]; then
    DEFAULT_PREFIX="/opt/launchpad-pro-tab"
    APPS_DIR="/usr/local/share/applications"
    ICONS_DIR="/usr/local/share/icons/hicolor/256x256/apps"
    MIME_DIR="/usr/local/share/mime"
    BIN_DIR="/usr/local/bin"
    REAL_USER="${SUDO_USER:-${PKEXEC_UID:+$(id -nu "$PKEXEC_UID" 2>/dev/null)}}"
else
    DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
    DEFAULT_PREFIX="$DATA_HOME/launchpad-pro-tab"
    APPS_DIR="$DATA_HOME/applications"
    ICONS_DIR="$DATA_HOME/icons/hicolor/256x256/apps"
    MIME_DIR="$DATA_HOME/mime"
    BIN_DIR="$HOME/.local/bin"
    REAL_USER=""
fi

desktop_dir() {
    user_home="$HOME"
    if [ -n "$REAL_USER" ]; then
        user_home=$(getent passwd "$REAL_USER" | cut -d: -f6)
    fi
    dir=""
    if command -v xdg-user-dir >/dev/null 2>&1; then
        if [ -n "$REAL_USER" ]; then
            dir=$(su "$REAL_USER" -c "xdg-user-dir DESKTOP" 2>/dev/null || true)
        else
            dir=$(xdg-user-dir DESKTOP 2>/dev/null || true)
        fi
    fi
    [ -n "$dir" ] && [ "$dir" != "$user_home" ] || dir="$user_home/Desktop"
    printf '%s' "$dir"
}

refresh_caches() {
    command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database -q "$APPS_DIR" 2>/dev/null || true
    command -v update-mime-database >/dev/null 2>&1 && update-mime-database "$MIME_DIR" >/dev/null 2>&1 || true
    command -v gtk-update-icon-cache >/dev/null 2>&1 && gtk-update-icon-cache -q -t "$(dirname "$(dirname "$(dirname "$ICONS_DIR")")")" 2>/dev/null || true
}

write_desktop_file() {  # write_desktop_file ZIEL PROGRAMMORDNER
    cat > "$1" <<EOF
[Desktop Entry]
Type=Application
Name=$APP_NAME
GenericName=Soundboard
Comment=Touch-optimierte Launchpad-Software für den Theaterbetrieb
Exec="$2/$EXE" %f
TryExec=$2/$EXE
Icon=$ICON_NAME
Terminal=false
Categories=AudioVideo;Audio;Music;
Keywords=Theater;Soundboard;Launchpad;Audio;Kacheln;
MimeType=$MIME_TYPE;
StartupWMClass=$APP_ID
StartupNotify=true
EOF
}

check_libraries() {  # fehlende Systembibliotheken für die Oberfläche melden
    plugin="$1/_internal/PySide6/Qt/plugins/platforms/libqxcb.so"
    [ -f "$plugin" ] || return 0
    missing=$(ldd "$plugin" 2>/dev/null | awk '/not found/ {print $1}' | sort -u | tr '\n' ' ')
    if [ -n "$missing" ]; then
        say ""
        say "Hinweis: Folgende Systembibliotheken fehlen für die Oberfläche: $missing"
        say "  Debian/Ubuntu: sudo apt install libxcb-cursor0 libxkbcommon-x11-0 libegl1"
        say "  Fedora:        sudo dnf install xcb-util-cursor libxkbcommon-x11 mesa-libEGL"
    fi
}

# ---------------------------------------------------------------------------
# Update (vom Programm über pkexec aufgerufen, wenn der Ordner root gehört)
# ---------------------------------------------------------------------------
if [ "$MODE" = "update" ]; then
    [ -n "$TARGET" ] && [ -n "$SOURCE" ] || die "--update braucht --target und --source"
    [ -x "$SOURCE/$EXE" ] || die "Kein Programm in $SOURCE"
    [ -x "$TARGET/$EXE" ] || die "Keine Installation in $TARGET"
    NEW="$TARGET.neu-$$"
    OLD="$TARGET.alt-$$"
    rm -rf "$NEW"
    cp -a "$SOURCE" "$NEW"
    [ -f "$TARGET/$INFO" ] && cp -p "$TARGET/$INFO" "$NEW/$INFO"
    chmod -R a+rX "$NEW"
    mv "$TARGET" "$OLD"
    if mv "$NEW" "$TARGET"; then
        rm -rf "$OLD"
        say "Update installiert: $TARGET"
    else
        mv "$OLD" "$TARGET"
        die "Update fehlgeschlagen – alte Version wiederhergestellt."
    fi
    exit 0
fi

# ---------------------------------------------------------------------------
# Deinstallation
# ---------------------------------------------------------------------------
if [ "$MODE" = "uninstall" ]; then
    DIR="${TARGET:-$SRC}"
    [ -f "$DIR/$INFO" ] || die "In $DIR ist keine Installation von $APP_NAME."
    say "$APP_NAME wird von diesem Computer entfernt ($DIR)."
    if [ -z "$PURGE" ]; then
        say ""
        say "Projekte (Kacheln, Audiodateien, Coverbilder) und Einstellungen bleiben normalerweise erhalten."
        if ask "Alle Projekte und Einstellungen ebenfalls löschen? (kann nicht rückgängig gemacht werden)" 0; then
            PURGE=1
        else
            PURGE=0
        fi
    fi
    [ "$ASSUME_YES" = 1 ] || ask "Jetzt deinstallieren?" 1 || { say "Abgebrochen."; exit 1; }
    if [ "$PURGE" = 1 ]; then
        if [ -n "$REAL_USER" ]; then
            su "$REAL_USER" -c "\"$DIR/$EXE\" --purge-user-data --yes" || true
        else
            "$DIR/$EXE" --purge-user-data --yes || true
        fi
    fi
    # Einträge laut .install-info entfernen
    while IFS='=' read -r key value; do
        case "$key" in
            file) [ -n "$value" ] && rm -f "$value" ;;
        esac
    done < "$DIR/$INFO"
    PARENT_DIR=$(dirname "$DIR")
    BASE_NAME=$(basename "$DIR")
    rm -rf "$DIR"
    # Reste früherer Updates neben dem Programmordner
    for leftover in "$PARENT_DIR/.alt-$BASE_NAME-"* "$PARENT_DIR/.launchpad-update-"*; do
        [ -e "$leftover" ] && rm -rf "$leftover"
    done
    # Zwischenspeicher (Update-Downloads, QML-Cache) immer entfernen
    CACHE_HOME="$HOME"
    [ -n "$REAL_USER" ] && CACHE_HOME=$(getent passwd "$REAL_USER" | cut -d: -f6)
    rm -rf "$CACHE_HOME/.cache/launchpad-pro-tab" "$CACHE_HOME/.cache/TAB Theater/Launchpad Pro TAB Edition"
    rmdir "$CACHE_HOME/.cache/TAB Theater" 2>/dev/null || true
    refresh_caches
    say "$APP_NAME wurde entfernt."
    exit 0
fi

# ---------------------------------------------------------------------------
# Installation
# ---------------------------------------------------------------------------
[ -x "$SRC/$EXE" ] || die "Bitte install.sh aus dem entpackten Programmpaket aufrufen."
VERSION=$("$SRC/$EXE" --version 2>/dev/null | awk '{print $NF}' || true)
say "$APP_NAME ${VERSION:-} – Installation"
say ""

if [ -z "$PREFIX" ]; then
    PREFIX="$DEFAULT_PREFIX"
    if [ "$ASSUME_YES" = 0 ] && [ -t 0 ]; then
        printf 'Installationsordner [%s]: ' "$PREFIX"
        read -r answer || answer=""
        [ -n "$answer" ] && PREFIX="$answer"
    fi
fi
case "$PREFIX" in "~"*) PREFIX="$HOME${PREFIX#\~}" ;; esac
[ "$WANT_MENU" = 1 ] && { ask "Eintrag im Anwendungsmenü anlegen?" 1 || WANT_MENU=0; }
[ "$WANT_DESKTOP" = 1 ] && { ask "Verknüpfung auf dem Desktop anlegen?" 1 || WANT_DESKTOP=0; }
[ "$WANT_MIME" = 1 ] && { ask "Projektdateien (.lptab) per Doppelklick mit Launchpad Pro öffnen?" 1 || WANT_MIME=0; }
say ""
ask "Jetzt nach $PREFIX installieren?" 1 || { say "Abgebrochen."; exit 1; }

# Programmordner kopieren (vorhandene Installation wird ersetzt)
PARENT=$(dirname "$PREFIX")
mkdir -p "$PARENT"
NEW="$PREFIX.neu-$$"
rm -rf "$NEW"
cp -a "$SRC" "$NEW"
rm -f "$NEW/$INFO"
if [ -d "$PREFIX" ]; then
    [ -x "$PREFIX/$EXE" ] || [ -f "$PREFIX/$INFO" ] || die "$PREFIX existiert und ist keine Installation von $APP_NAME."
    rm -rf "$PREFIX.alt-$$"
    mv "$PREFIX" "$PREFIX.alt-$$"
    mv "$NEW" "$PREFIX"
    rm -rf "$PREFIX.alt-$$"
else
    mv "$NEW" "$PREFIX"
fi
chmod 755 "$PREFIX/uninstall.sh" "$PREFIX/install.sh" "$PREFIX/$EXE"

INFO_FILE="$PREFIX/$INFO"
{
    echo "version=${VERSION:-}"
    echo "installed=$(date '+%Y-%m-%d %H:%M')"
} > "$INFO_FILE"

# Symbol (für Menü, Desktop und Projektdateien)
ICON_SRC="$PREFIX/_internal/launchpad_pro_tab/assets/app_icon.png"
if [ -f "$ICON_SRC" ]; then
    mkdir -p "$ICONS_DIR"
    cp "$ICON_SRC" "$ICONS_DIR/$ICON_NAME.png"
    echo "file=$ICONS_DIR/$ICON_NAME.png" >> "$INFO_FILE"
fi

# Befehl im Terminal: launchpad-pro-tab
mkdir -p "$BIN_DIR"
ln -sf "$PREFIX/$EXE" "$BIN_DIR/launchpad-pro-tab"
echo "file=$BIN_DIR/launchpad-pro-tab" >> "$INFO_FILE"

if [ "$WANT_MENU" = 1 ]; then
    mkdir -p "$APPS_DIR"
    write_desktop_file "$APPS_DIR/$APP_ID.desktop" "$PREFIX"
    echo "file=$APPS_DIR/$APP_ID.desktop" >> "$INFO_FILE"
fi

if [ "$WANT_DESKTOP" = 1 ]; then
    DESK=$(desktop_dir)
    if [ -d "$DESK" ]; then
        write_desktop_file "$DESK/$APP_ID.desktop" "$PREFIX"
        chmod 755 "$DESK/$APP_ID.desktop"
        [ -n "$REAL_USER" ] && chown "$REAL_USER" "$DESK/$APP_ID.desktop" 2>/dev/null || true
        # GNOME: Verknüpfung als vertrauenswürdig markieren (sonst „Start nicht erlaubt“)
        command -v gio >/dev/null 2>&1 && gio set "$DESK/$APP_ID.desktop" metadata::trusted true 2>/dev/null || true
        echo "file=$DESK/$APP_ID.desktop" >> "$INFO_FILE"
    else
        say "Hinweis: Desktop-Ordner nicht gefunden – keine Desktop-Verknüpfung angelegt."
    fi
fi

if [ "$WANT_MIME" = 1 ]; then
    mkdir -p "$MIME_DIR/packages"
    cat > "$MIME_DIR/packages/$ICON_NAME.xml" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<mime-info xmlns="http://www.freedesktop.org/standards/shared-mime-info">
  <mime-type type="$MIME_TYPE">
    <comment>Launchpad Pro TAB Projekt</comment>
    <glob pattern="*.lptab"/>
    <icon name="$ICON_NAME"/>
  </mime-type>
</mime-info>
EOF
    echo "file=$MIME_DIR/packages/$ICON_NAME.xml" >> "$INFO_FILE"
fi

refresh_caches
check_libraries "$PREFIX"

say ""
say "Fertig! $APP_NAME ist installiert in: $PREFIX"
[ "$WANT_MENU" = 1 ] && say "  • Start über das Anwendungsmenü: $APP_NAME"
say "  • oder im Terminal: $BIN_DIR/launchpad-pro-tab"
say "  • Deinstallieren: $PREFIX/uninstall.sh"
say "Updates meldet das Programm beim Start selbst und installiert sie auf Wunsch automatisch."
