"""Tekst uit documenten halen, zodat je ook op de inhoud kunt zoeken.

Alles gebeurt lokaal. Voor PDF's wordt de ingebedde tekst gelezen. Voor foto's
en scans wordt tekstherkenning (OCR) gebruikt als Tesseract op de computer is
geïnstalleerd; zonder Tesseract worden foto's gewoon opgeslagen zonder tekst.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

log = logging.getLogger(__name__)

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff", ".webp", ".heic"}
TEXT_EXTS = {".txt", ".csv", ".md"}
MAX_CHARS = 200_000


def find_tesseract() -> str | None:
    found = shutil.which("tesseract")
    if found:
        return found
    if sys.platform == "win32":
        for base in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)"),
                     os.environ.get("LOCALAPPDATA")):
            if base:
                candidate = Path(base) / "Tesseract-OCR" / "tesseract.exe"
                if candidate.exists():
                    return str(candidate)
    return None


def _pdf_text(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    parts: list[str] = []
    total = 0
    for page in reader.pages[:100]:
        text = page.extract_text() or ""
        parts.append(text)
        total += len(text)
        if total > MAX_CHARS:
            break
    return "\n".join(parts)


def _ocr(path: Path) -> str:
    exe = find_tesseract()
    if not exe:
        return ""
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    for lang in ("nld+eng", "eng"):
        try:
            result = subprocess.run(
                [exe, str(path), "stdout", "-l", lang],
                capture_output=True, timeout=120, creationflags=flags,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            log.warning("OCR mislukt voor %s: %s", path, exc)
            return ""
        if result.returncode == 0:
            return result.stdout.decode("utf-8", errors="replace")
    return ""


def extract_text(path: Path) -> str:
    """Geeft de doorzoekbare tekst van een bestand terug (of een lege string)."""
    ext = path.suffix.lower()
    try:
        if ext == ".pdf":
            text = _pdf_text(path)
            if len(text.strip()) < 20:
                # Gescande PDF zonder tekstlaag: probeer OCR als dat kan.
                text = text + "\n" + _ocr(path)
        elif ext in IMAGE_EXTS:
            text = _ocr(path)
        elif ext in TEXT_EXTS:
            text = path.read_text(encoding="utf-8", errors="replace")
        else:
            text = ""
    except Exception as exc:  # een kapot bestand mag het programma niet stoppen
        log.warning("Kon geen tekst lezen uit %s: %s", path, exc)
        text = ""
    return " ".join(text.split())[:MAX_CHARS]
