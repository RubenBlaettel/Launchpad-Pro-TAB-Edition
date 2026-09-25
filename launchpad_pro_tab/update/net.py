"""HTTP(S)-Zugriff für die Update-Funktion (nur Standardbibliothek).

* Zertifikate werden immer geprüft: zuerst mit dem Zertifikatsspeicher des Systems
  (unter Windows auch Firmen-Proxys mit eigener Stammzertifizierung), bei einem
  Prüffehler zusätzlich mit dem Mozilla-Bundle aus ``certifi``.
* Nur ``https://`` – ``http://`` ist ausschließlich für ``localhost`` erlaubt (Tests).
* Proxy-Einstellungen aus der Umgebung (``HTTPS_PROXY``) werden übernommen.
"""

from __future__ import annotations

import json
import logging
import socket
import ssl
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import urlsplit

from .. import __app_id__, __version__

log = logging.getLogger(__name__)

USER_AGENT = f"{__app_id__}/{__version__} (+https://github.com)"


class NetworkError(Exception):
    """Verständliche Fehlermeldung für die Oberfläche."""


def check_url(url: str) -> None:
    parts = urlsplit(url)
    if parts.scheme == "https":
        return
    if parts.scheme == "http" and parts.hostname in ("127.0.0.1", "localhost", "::1"):
        return
    raise NetworkError(f"Unsichere Adresse abgelehnt: {url}")


def _contexts() -> list[ssl.SSLContext]:
    contexts = [ssl.create_default_context()]
    try:
        import certifi

        contexts.append(ssl.create_default_context(cafile=certifi.where()))
    except Exception:  # noqa: BLE001 – certifi ist optional
        pass
    return contexts


class _SafeRedirect(urllib.request.HTTPRedirectHandler):
    """Weiterleitungen (GitHub -> Download-Server) nur zu https bzw. localhost."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D102
        check_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def open_url(url: str, *, timeout: float = 15.0, accept: str = "*/*"):
    """Öffnet ``url`` und liefert die Antwort (Kontextmanager, streamfähig)."""
    check_url(url)
    headers = {"User-Agent": USER_AGENT, "Accept": accept}
    if "api.github.com" in url:
        headers["X-GitHub-Api-Version"] = "2022-11-28"
    last_ssl: Exception | None = None
    for ctx in _contexts():
        opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx), _SafeRedirect())
        try:
            return opener.open(urllib.request.Request(url, headers=headers), timeout=timeout)
        except urllib.error.HTTPError as exc:
            raise NetworkError(_http_message(exc)) from exc
        except urllib.error.URLError as exc:
            reason = exc.reason
            if isinstance(reason, ssl.SSLCertVerificationError):
                last_ssl = reason
                continue          # nächsten Zertifikatsspeicher versuchen
            raise NetworkError(_url_message(reason)) from exc
        except ssl.SSLCertVerificationError as exc:
            last_ssl = exc
            continue
        except (TimeoutError, socket.timeout) as exc:
            raise NetworkError("Zeitüberschreitung – der Update-Server antwortet nicht.") from exc
        except OSError as exc:
            raise NetworkError(_url_message(exc)) from exc
    raise NetworkError(f"Sichere Verbindung fehlgeschlagen (Zertifikat nicht vertrauenswürdig): {last_ssl}")


def get_json(url: str, *, timeout: float = 15.0) -> Any:
    with open_url(url, timeout=timeout, accept="application/vnd.github+json") as resp:
        raw = resp.read(8 * 1024 * 1024)
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise NetworkError("Unerwartete Antwort vom Update-Server.") from exc


def get_text(url: str, *, timeout: float = 15.0, limit: int = 1024 * 1024) -> str:
    with open_url(url, timeout=timeout) as resp:
        return resp.read(limit).decode("utf-8", errors="replace")


def _http_message(exc: urllib.error.HTTPError) -> str:
    if exc.code in (403, 429) and exc.headers.get("X-RateLimit-Remaining") == "0":
        return "GitHub-Abfragelimit erreicht – bitte in einer Stunde erneut versuchen."
    if exc.code == 404:
        return "Keine veröffentlichten Versionen gefunden (Repository privat oder noch kein Release)."
    return f"Update-Server meldet Fehler {exc.code} ({exc.reason})."


def _url_message(reason: object) -> str:
    if isinstance(reason, socket.gaierror):
        return "Keine Internetverbindung (Server nicht gefunden)."
    if isinstance(reason, (TimeoutError, socket.timeout)):
        return "Zeitüberschreitung – der Update-Server antwortet nicht."
    if isinstance(reason, ConnectionRefusedError):
        return "Verbindung abgelehnt."
    return f"Keine Verbindung zum Update-Server ({reason})."
