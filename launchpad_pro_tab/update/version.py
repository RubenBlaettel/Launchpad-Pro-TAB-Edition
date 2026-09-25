"""Versionsnummern vergleichen (``1.2.0``, ``v1.2.0``, ``1.3.0-beta.1``, ``1.3.0b1`` …)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_RE = re.compile(
    r"^\s*v?(\d+)(?:\.(\d+))?(?:\.(\d+))?"
    r"(?:[-_.]?(dev|alpha|a|beta|b|preview|pre|rc|c)[-_.]?(\d+)?)?\s*$",
    re.IGNORECASE,
)
_STAGES = {"dev": 0, "alpha": 1, "a": 1, "beta": 2, "b": 2, "preview": 2, "pre": 2, "rc": 3, "c": 3}
FINAL = 9


@dataclass(frozen=True, order=True)
class Version:
    major: int
    minor: int
    patch: int
    stage: int = FINAL        # Vorabversionen sind kleiner als die fertige Version
    number: int = 0
    text: str = field(default="", compare=False)

    @property
    def is_prerelease(self) -> bool:
        return self.stage != FINAL

    def __str__(self) -> str:
        return self.text or f"{self.major}.{self.minor}.{self.patch}"


def parse_version(text: str | None) -> Version | None:
    if not text:
        return None
    m = _RE.match(str(text))
    if not m:
        return None
    major, minor, patch, stage, number = m.groups()
    clean = str(text).strip()
    if clean[:1] in "vV":
        clean = clean[1:]
    return Version(
        int(major), int(minor or 0), int(patch or 0),
        _STAGES[stage.lower()] if stage else FINAL,
        int(number or 0),
        clean,
    )


def is_newer(candidate: str | None, current: str | None) -> bool:
    """Ist ``candidate`` neuer als ``current``? Unlesbare Angaben gelten nie als neuer."""
    a, b = parse_version(candidate), parse_version(current)
    if a is None:
        return False
    if b is None:
        return True
    return a > b
