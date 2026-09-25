"""GitHub-Releases abfragen und die passende neue Version auswählen."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .. import __repository__
from .net import NetworkError, get_json, get_text
from .version import Version, is_newer, parse_version

CHECKSUM_NAMES = ("SHA256SUMS.txt", "SHA256SUMS", "sha256sums.txt")
_HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")


@dataclass
class Asset:
    name: str
    url: str
    size: int = 0
    sha256: str | None = None       # aus dem GitHub-Feld "digest" oder SHA256SUMS.txt


@dataclass
class Release:
    version: Version
    tag: str
    title: str
    notes: str
    html_url: str
    published: datetime | None
    prerelease: bool
    assets: list[Asset] = field(default_factory=list)

    def asset(self, pattern: str) -> Asset | None:
        rx = re.compile(pattern, re.IGNORECASE)
        return next((a for a in self.assets if rx.search(a.name)), None)

    @property
    def checksums(self) -> Asset | None:
        return next((a for a in self.assets if a.name in CHECKSUM_NAMES), None)


def releases_url(repo: str | None = None) -> str:
    """API-Adresse; für Tests über ``LPTAB_UPDATE_URL`` bzw. ``LPTAB_UPDATE_REPO`` änderbar."""
    override = os.environ.get("LPTAB_UPDATE_URL")
    if override:
        return override
    repo = repo or os.environ.get("LPTAB_UPDATE_REPO") or __repository__
    return f"https://api.github.com/repos/{repo}/releases?per_page=20"


def releases_page(repo: str | None = None) -> str:
    repo = repo or os.environ.get("LPTAB_UPDATE_REPO") or __repository__
    return f"https://github.com/{repo}/releases"


def _parse_time(text: Any) -> datetime | None:
    if not isinstance(text, str) or not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _digest(value: Any) -> str | None:
    if isinstance(value, str) and value.lower().startswith("sha256:"):
        hexpart = value.split(":", 1)[1].strip()
        if _HEX64.match(hexpart):
            return hexpart.lower()
    return None


def parse_release(raw: dict[str, Any]) -> Release | None:
    """Ein Release aus der API-Antwort; ``None`` für Entwürfe oder unlesbare Tags."""
    if not isinstance(raw, dict) or raw.get("draft"):
        return None
    tag = str(raw.get("tag_name") or "")
    version = parse_version(tag)
    if version is None:
        return None
    assets = []
    for a in raw.get("assets") or []:
        if not isinstance(a, dict) or not a.get("name") or not a.get("browser_download_url"):
            continue
        try:
            size = int(a.get("size") or 0)
        except (TypeError, ValueError):
            size = 0
        assets.append(Asset(str(a["name"]), str(a["browser_download_url"]), size, _digest(a.get("digest"))))
    return Release(
        version=version,
        tag=tag,
        title=str(raw.get("name") or f"Version {version}"),
        notes=str(raw.get("body") or ""),
        html_url=str(raw.get("html_url") or ""),
        published=_parse_time(raw.get("published_at")),
        prerelease=bool(raw.get("prerelease")) or version.is_prerelease,
        assets=assets,
    )


def fetch_releases(url: str | None = None, *, timeout: float = 12.0) -> list[Release]:
    data = get_json(url or releases_url(), timeout=timeout)
    if not isinstance(data, list):
        raise NetworkError("Unerwartete Antwort vom Update-Server.")
    return [r for r in (parse_release(item) for item in data) if r is not None]


def pick_update(releases: list[Release], current: str, *, include_prereleases: bool = False,
                skipped: str | None = None) -> Release | None:
    """Neueste Version, sofern neuer als ``current``.

    Wurde diese (oder eine neuere) Version übersprungen, wird erst die nächste neuere
    Version wieder angeboten.
    """
    candidates = [r for r in releases if include_prereleases or not r.prerelease]
    if not candidates:
        return None
    newest = max(candidates, key=lambda r: r.version)
    if not is_newer(str(newest.version), current):
        return None
    skipped_version = parse_version(skipped)
    if skipped_version is not None and skipped_version >= newest.version:
        return None
    return newest


def parse_checksums(text: str) -> dict[str, str]:
    """``sha256sum``-Format: ``<hex>  <dateiname>`` (auch ``*dateiname``)."""
    out: dict[str, str] = {}
    for line in text.splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) == 2 and _HEX64.match(parts[0]):
            out[parts[1].strip().lstrip("*")] = parts[0].lower()
    return out


def resolve_checksum(release: Release, asset: Asset, *, timeout: float = 12.0) -> str | None:
    """SHA-256 des Pakets: GitHub-Digest bevorzugt, sonst aus SHA256SUMS.txt."""
    if asset.sha256:
        return asset.sha256
    sums = release.checksums
    if sums is None:
        return None
    return parse_checksums(get_text(sums.url, timeout=timeout)).get(asset.name)
