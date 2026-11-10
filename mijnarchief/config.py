"""Instellingen van het programma (alleen lokaal)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def settings_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "MijnArchief"


def default_archive_dir() -> Path:
    docs = Path.home() / "Documents"
    if not docs.exists():
        alt = Path.home() / "Documenten"
        docs = alt if alt.exists() else Path.home()
    return docs / "Mijn Archief"


class Settings:
    """Klein JSON-bestand met o.a. de gekozen archiefmap."""

    def __init__(self, path: Path | None = None):
        self.path = path or settings_dir() / "instellingen.json"
        self.data: dict = {}
        try:
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.data = {}

    def get(self, key: str, default=None):
        return self.data.get(key, default)

    def set(self, key: str, value) -> None:
        self.data[key] = value
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.path)

    @property
    def archive_dir(self) -> Path | None:
        value = self.get("archiefmap")
        return Path(value) if value else None

    @archive_dir.setter
    def archive_dir(self, path: Path) -> None:
        self.set("archiefmap", str(path))
