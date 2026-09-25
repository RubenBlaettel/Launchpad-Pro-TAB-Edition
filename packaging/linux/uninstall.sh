#!/bin/sh
# Launchpad Pro TAB Edition deinstallieren.
#   ./uninstall.sh                 fragt, ob auch Projekte und Einstellungen gelöscht werden sollen
#   ./uninstall.sh --purge --yes   inkl. aller Projekte und Einstellungen, ohne Rückfrage
DIR=$(cd "$(dirname "$0")" && pwd)
exec "$DIR/install.sh" --uninstall --target "$DIR" "$@"
