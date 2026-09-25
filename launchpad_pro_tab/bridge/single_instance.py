"""Nur eine laufende Instanz pro Benutzer.

Wird Launchpad Pro ein zweites Mal gestartet (Doppelklick auf das Symbol, eine
Projektdatei im Explorer …), übergibt die neue Instanz ihren Auftrag an die laufende und
beendet sich. Die laufende Instanz holt ihr Fenster nach vorne und öffnet ggf. das Projekt.
So laufen nie zwei Audio-Engines gleichzeitig auf demselben Bühnenrechner.

Protokoll: eine JSON-Zeile pro Auftrag; die laufende Instanz bestätigt mit ``ok``.
"""

from __future__ import annotations

import getpass
import hashlib
import json
import logging
import sys

from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket

from .. import __app_id__

log = logging.getLogger(__name__)

ACK = b"ok\n"


def server_name() -> str:
    try:
        user = getpass.getuser()
    except Exception:  # noqa: BLE001
        user = "user"
    return f"{__app_id__}-{hashlib.sha1(user.encode('utf-8')).hexdigest()[:10]}"


class SingleInstance(QObject):
    messageReceived = Signal(dict)

    def __init__(self, name: str | None = None, parent: QObject | None = None):
        super().__init__(parent)
        self._name = name or server_name()
        self._server: QLocalServer | None = None
        self._buffers: dict[QLocalSocket, bytes] = {}

    @property
    def name(self) -> str:
        return self._name

    # ------------------------------------------------------------------
    # Zweite Instanz
    # ------------------------------------------------------------------
    def forward(self, payload: dict, timeout_ms: int = 3000) -> bool:
        """Auftrag an eine laufende Instanz senden. ``True`` = es läuft bereits eine."""
        sock = QLocalSocket()
        sock.connectToServer(self._name)
        if not sock.waitForConnected(timeout_ms):
            return False
        if sys.platform == "win32":
            # Der laufenden Instanz erlauben, ihr Fenster in den Vordergrund zu holen
            try:
                import ctypes

                ctypes.windll.user32.AllowSetForegroundWindow(0xFFFFFFFF)   # ASFW_ANY
            except Exception:  # noqa: BLE001
                pass
        sock.write((json.dumps(payload) + "\n").encode("utf-8"))
        sock.flush()
        sock.waitForBytesWritten(timeout_ms)
        # Auf die Bestätigung warten, damit der Auftrag sicher angekommen ist, bevor sich
        # dieser Prozess beendet (unter Windows gehen sonst ungelesene Daten verloren).
        if not sock.waitForReadyRead(timeout_ms):
            log.warning("Laufende Instanz hat den Auftrag nicht bestätigt.")
        sock.disconnectFromServer()
        if sock.state() != QLocalSocket.LocalSocketState.UnconnectedState:
            sock.waitForDisconnected(1000)
        return True     # verbunden = es läuft bereits eine Instanz

    # ------------------------------------------------------------------
    # Laufende Instanz
    # ------------------------------------------------------------------
    def listen(self) -> bool:
        server = QLocalServer(self)
        server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
        if not server.listen(self._name):
            # Verwaiste Socket-Datei nach einem Absturz (Linux/macOS) entfernen und erneut
            QLocalServer.removeServer(self._name)
            if not server.listen(self._name):
                log.warning("Einzelinstanz-Server nicht verfügbar: %s", server.errorString())
                return False
        server.newConnection.connect(self._on_connection)
        self._server = server
        return True

    def close(self) -> None:
        if self._server is not None:
            self._server.close()
            self._server = None

    def _on_connection(self) -> None:
        assert self._server is not None
        while self._server.hasPendingConnections():
            sock = self._server.nextPendingConnection()
            self._buffers[sock] = b""
            sock.readyRead.connect(lambda s=sock: self._read(s))
            sock.disconnected.connect(lambda s=sock: self._finish(s))
            # Daten können schon angekommen sein, bevor die Signale verbunden waren
            if sock.bytesAvailable() > 0:
                self._read(sock)
            if sock.state() == QLocalSocket.LocalSocketState.UnconnectedState:
                self._finish(sock)

    def _read(self, sock: QLocalSocket) -> None:
        if sock not in self._buffers:
            return
        data = self._buffers[sock] + bytes(sock.readAll())
        *lines, rest = data.split(b"\n")
        self._buffers[sock] = rest
        for line in lines:
            payload = self._parse(line)
            if payload is None:
                continue
            if sock.state() == QLocalSocket.LocalSocketState.ConnectedState:
                sock.write(ACK)          # zuerst bestätigen – das Öffnen eines Projekts dauert
                sock.flush()
            self.messageReceived.emit(payload)

    def _finish(self, sock: QLocalSocket) -> None:
        if sock not in self._buffers:
            return
        rest = self._buffers.pop(sock) + bytes(sock.readAll())
        for line in rest.split(b"\n"):
            payload = self._parse(line)
            if payload is not None:
                self.messageReceived.emit(payload)
        sock.deleteLater()

    @staticmethod
    def _parse(line: bytes) -> dict | None:
        if not line.strip():
            return None
        try:
            payload = json.loads(line.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            return None
        return payload if isinstance(payload, dict) else None
