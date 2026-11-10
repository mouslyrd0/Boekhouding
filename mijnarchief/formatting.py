"""Nederlandse notatie van bedragen en datums."""

from __future__ import annotations

import re
from datetime import date

MAANDEN = [
    "januari", "februari", "maart", "april", "mei", "juni", "juli",
    "augustus", "september", "oktober", "november", "december",
]

_THOUSANDS_DOT = re.compile(r"^\d{1,3}(\.\d{3})+$")


def parse_amount(text: str) -> float | None:
    """Zet een ingetypt bedrag om naar een getal.

    Accepteert onder meer ``12,50``, ``1.149,00``, ``1149.5`` en ``€ 87,30``.
    Geeft ``None`` terug bij een leeg veld. Gooit ``ValueError`` bij onzin.
    """
    s = (text or "").strip().replace("€", "").replace(" ", "").replace(" ", "")
    if not s:
        return None
    negative = s.startswith("-")
    s = s.lstrip("+-")
    if "," in s and "." in s:
        # De laatste scheidingsteken is het decimaalteken.
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    elif "." in s and _THOUSANDS_DOT.match(s):
        s = s.replace(".", "")
    if not re.fullmatch(r"\d+(\.\d+)?", s):
        raise ValueError(f"Ongeldig bedrag: {text!r}")
    value = round(float(s), 2)
    return -value if negative else value


def format_amount(value: float | None) -> str:
    """``1149.0`` → ``€ 1.149,00``; ``None`` → ``—``."""
    if value is None:
        return "—"
    sign = "-" if value < 0 else ""
    whole, frac = f"{abs(value):,.2f}".split(".")
    return f"€ {sign}{whole.replace(',', '.')},{frac}"


def format_amount_plain(value: float | None) -> str:
    """Bedrag zoals je het in een invoerveld typt: ``1149,00``."""
    if value is None:
        return ""
    return f"{value:.2f}".replace(".", ",")


def parse_iso(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def format_date_long(s: str | None) -> str:
    d = parse_iso(s)
    if not d:
        return "—"
    return f"{d.day} {MAANDEN[d.month - 1]} {d.year}"


def format_date_short(s: str | None, today: date | None = None) -> str:
    """``3 sep`` binnen het huidige jaar, anders ``3 sep 2025``."""
    d = parse_iso(s)
    if not d:
        return ""
    today = today or date.today()
    base = f"{d.day} {MAANDEN[d.month - 1][:3]}"
    return base if d.year == today.year else f"{base} {d.year}"


def warranty_status(until: str | None, today: date | None = None) -> tuple[str, str] | None:
    """Geeft (soort, tekst) terug. Soort is ``ok``, ``warn`` of ``bad``."""
    end = parse_iso(until)
    if not end:
        return None
    today = today or date.today()
    days = (end - today).days
    if days < 0:
        return "bad", "Garantie verlopen"
    if days < 90:
        return "warn", f"Garantie nog {days} {'dag' if days == 1 else 'dagen'}"
    return "ok", f"Garantie t/m {MAANDEN[end.month - 1]} {end.year}"
