"""Het archief: lokale bestanden plus een SQLite-database met zoekindex.

Opbouw van de archiefmap::

    Mijn Archief/
    ├── archief.db           categorieën, gegevens, omschrijvingen en zoekindex
    ├── documenten/
    │   └── 2026/
    │       └── 2026-09-03_Garantiebewijzen_Wasmachine-Bosch.pdf
    └── prullenbak/          verwijderde documenten (voor de zekerheid bewaard)

De documenten zijn gewone bestanden met een duidelijke naam. Ze blijven ook
zonder dit programma leesbaar.
"""

from __future__ import annotations

import re
import shutil
import sqlite3
import tempfile
import zipfile
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable

from .extract import extract_text
from .formatting import MAANDEN, format_amount_plain

SCHEMA_VERSION = 1
DB_NAME = "archief.db"
DOCS_DIR = "documenten"
TRASH_DIR = "prullenbak"

CATEGORY_COLORS = ["#2b4c7e", "#2f7a4f", "#a8620a", "#7b3f8c", "#1f7a85", "#b23b3b", "#59606b", "#8a6d1f"]

DEFAULT_CATEGORIES = [
    ("Bonnetjes", "Kassabonnen van winkels en aankopen", "#a8620a"),
    ("Garantiebewijzen", "Aankoopbewijzen met garantie", "#2f7a4f"),
    ("Facturen", "Rekeningen, afschriften en nota's", "#2b4c7e"),
    ("Brieven", "Post van instanties, bedrijven en personen", "#7b3f8c"),
]

# Speciale filters in de zijbalk.
FILTER_WARRANTY = "garantie"
FILTER_EXPIRING = "binnenkort"
FILTER_UNCATEGORIZED = "zonder"

EXPIRING_DAYS = 90


@dataclass
class Category:
    id: int
    name: str
    description: str = ""
    color: str = "#59606b"
    parent_id: int | None = None


@dataclass
class Document:
    id: int
    title: str
    category_id: int | None
    doc_date: str
    amount: float | None = None
    sender: str = ""
    warranty_until: str | None = None
    description: str = ""
    tags: list[str] = field(default_factory=list)
    file_path: str = ""
    original_name: str = ""
    content: str = ""
    added_at: str = ""
    updated_at: str = ""


class ArchiveError(Exception):
    """Fout die als begrijpelijke melding aan de gebruiker getoond kan worden."""


_INVALID_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]+')


def safe_name(text: str, limit: int = 80) -> str:
    """Maakt van vrije tekst een veilige, leesbare stukje bestandsnaam."""
    s = _INVALID_CHARS.sub(" ", text or "")
    s = re.sub(r"[\s›]+", "-", s.strip())
    s = re.sub(r"-{2,}", "-", s).strip("-. ")
    return s[:limit].rstrip("-. ") or "document"


def parse_tags(text: str | Iterable[str]) -> list[str]:
    items = text.split(",") if isinstance(text, str) else list(text)
    seen: list[str] = []
    for item in items:
        tag = " ".join(str(item).split())
        if tag and tag.lower() not in (t.lower() for t in seen):
            seen.append(tag)
    return seen


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    n = 2
    while True:
        candidate = path.with_name(f"{path.stem} ({n}){path.suffix}")
        if not candidate.exists():
            return candidate
        n += 1


def build_fts_query(text: str) -> str:
    """Zet zoektekst om naar een FTS5-zoekvraag: alle woorden moeten voorkomen,
    en elk woord mag het begin van een langer woord zijn (``wasm`` vindt
    ``wasmachine``)."""
    words = re.findall(r"\w+", text or "", flags=re.UNICODE)
    return " ".join(f'"{w}"*' for w in words)


class Archive:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / DOCS_DIR).mkdir(exist_ok=True)
        self.db_path = self.root / DB_NAME
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._migrate()

    # ------------------------------------------------------------------ setup
    def _migrate(self) -> None:
        version = self.conn.execute("PRAGMA user_version").fetchone()[0]
        if version >= SCHEMA_VERSION:
            return
        with self.conn:
            self.conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS categories (
                    id          INTEGER PRIMARY KEY,
                    name        TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    color       TEXT NOT NULL DEFAULT '#59606b',
                    parent_id   INTEGER REFERENCES categories(id) ON DELETE SET NULL
                );
                CREATE TABLE IF NOT EXISTS documents (
                    id             INTEGER PRIMARY KEY,
                    title          TEXT NOT NULL,
                    category_id    INTEGER REFERENCES categories(id) ON DELETE SET NULL,
                    doc_date       TEXT NOT NULL,
                    amount         REAL,
                    sender         TEXT NOT NULL DEFAULT '',
                    warranty_until TEXT,
                    description    TEXT NOT NULL DEFAULT '',
                    tags           TEXT NOT NULL DEFAULT '',
                    file_path      TEXT NOT NULL,
                    original_name  TEXT NOT NULL DEFAULT '',
                    content        TEXT NOT NULL DEFAULT '',
                    added_at       TEXT NOT NULL,
                    updated_at     TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_documents_date ON documents(doc_date);
                CREATE INDEX IF NOT EXISTS idx_documents_category ON documents(category_id);
                CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
                    title, description, sender, tags, category, content, extra,
                    tokenize = "unicode61 remove_diacritics 2"
                );
                """
            )
            if not self.conn.execute("SELECT 1 FROM categories LIMIT 1").fetchone():
                for name, desc, color in DEFAULT_CATEGORIES:
                    self.conn.execute(
                        "INSERT INTO categories(name, description, color) VALUES (?, ?, ?)",
                        (name, desc, color),
                    )
            self.conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")

    def close(self) -> None:
        self.conn.close()

    # ------------------------------------------------------------- categories
    @staticmethod
    def _row_to_category(row: sqlite3.Row) -> Category:
        return Category(row["id"], row["name"], row["description"], row["color"], row["parent_id"])

    def categories(self) -> list[Category]:
        rows = self.conn.execute("SELECT * FROM categories ORDER BY name COLLATE NOCASE")
        return [self._row_to_category(r) for r in rows]

    def category(self, category_id: int | None) -> Category | None:
        if category_id is None:
            return None
        row = self.conn.execute("SELECT * FROM categories WHERE id = ?", (category_id,)).fetchone()
        return self._row_to_category(row) if row else None

    def category_path(self, category_id: int | None, sep: str = " › ") -> str:
        names: list[str] = []
        seen: set[int] = set()
        cat = self.category(category_id)
        while cat and cat.id not in seen:
            seen.add(cat.id)
            names.append(cat.name)
            cat = self.category(cat.parent_id)
        return sep.join(reversed(names))

    def descendants(self, category_id: int) -> set[int]:
        """De categorie zelf plus alle subcategorieën (op elk niveau)."""
        children: dict[int | None, list[int]] = {}
        for c in self.categories():
            children.setdefault(c.parent_id, []).append(c.id)
        result, stack = set(), [category_id]
        while stack:
            cid = stack.pop()
            if cid in result:
                continue
            result.add(cid)
            stack.extend(children.get(cid, []))
        return result

    def _check_category(self, name: str, parent_id: int | None, exclude_id: int | None = None) -> str:
        name = " ".join((name or "").split())
        if not name:
            raise ArchiveError("Geef de categorie een naam.")
        if len(name) > 60:
            raise ArchiveError("De naam van de categorie mag maximaal 60 tekens lang zijn.")
        if parent_id is not None and self.category(parent_id) is None:
            raise ArchiveError("De gekozen bovenliggende categorie bestaat niet meer.")
        row = self.conn.execute(
            "SELECT id FROM categories WHERE name = ? COLLATE NOCASE AND parent_id IS ? AND id IS NOT ?",
            (name, parent_id, exclude_id),
        ).fetchone()
        if row:
            raise ArchiveError(f"Er bestaat al een categorie met de naam “{name}” op deze plek.")
        return name

    def add_category(self, name: str, description: str = "", color: str = "#59606b",
                     parent_id: int | None = None) -> int:
        name = self._check_category(name, parent_id)
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO categories(name, description, color, parent_id) VALUES (?, ?, ?, ?)",
                (name, (description or "").strip(), color, parent_id),
            )
        return cur.lastrowid

    def update_category(self, category_id: int, name: str, description: str, color: str,
                        parent_id: int | None) -> None:
        if parent_id is not None and parent_id in self.descendants(category_id):
            raise ArchiveError("Een categorie kan niet onder zichzelf of onder een eigen subcategorie vallen.")
        name = self._check_category(name, parent_id, exclude_id=category_id)
        with self.conn:
            self.conn.execute(
                "UPDATE categories SET name = ?, description = ?, color = ?, parent_id = ? WHERE id = ?",
                (name, (description or "").strip(), color, parent_id, category_id),
            )
        self._reindex_categories(self.descendants(category_id))

    def delete_category(self, category_id: int) -> None:
        """Verwijdert een categorie. Subcategorieën schuiven een niveau omhoog;
        documenten blijven bewaard en komen bij 'Zonder categorie'."""
        cat = self.category(category_id)
        if not cat:
            return
        affected = self.descendants(category_id)
        with self.conn:
            self.conn.execute("UPDATE categories SET parent_id = ? WHERE parent_id = ?",
                              (cat.parent_id, category_id))
            self.conn.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        self._reindex_categories(affected | {None})

    def _reindex_categories(self, category_ids: set[int | None]) -> None:
        for doc in self.all_documents():
            if doc.category_id in category_ids or doc.category_id is None:
                self._index(doc)
        self.conn.commit()

    # -------------------------------------------------------------- documents
    @staticmethod
    def _row_to_document(row: sqlite3.Row) -> Document:
        return Document(
            id=row["id"], title=row["title"], category_id=row["category_id"], doc_date=row["doc_date"],
            amount=row["amount"], sender=row["sender"], warranty_until=row["warranty_until"],
            description=row["description"], tags=parse_tags(row["tags"]), file_path=row["file_path"],
            original_name=row["original_name"], content=row["content"], added_at=row["added_at"],
            updated_at=row["updated_at"],
        )

    def document(self, doc_id: int) -> Document | None:
        row = self.conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
        return self._row_to_document(row) if row else None

    def all_documents(self) -> list[Document]:
        rows = self.conn.execute("SELECT * FROM documents ORDER BY doc_date DESC, id DESC")
        return [self._row_to_document(r) for r in rows]

    def file_of(self, doc: Document) -> Path:
        return self.root / Path(doc.file_path)

    def _target_path(self, title: str, category_id: int | None, doc_date: str, suffix: str) -> Path:
        year = doc_date[:4] if re.match(r"\d{4}", doc_date or "") else "zonder-datum"
        cat = self.category_path(category_id, sep=" ") or "Zonder-categorie"
        name = f"{doc_date}_{safe_name(cat, 40)}_{safe_name(title)}{suffix.lower()}"
        return self.root / DOCS_DIR / year / name

    @staticmethod
    def _validate(title: str, doc_date: str, warranty_until: str | None) -> str:
        title = " ".join((title or "").split())
        if not title:
            raise ArchiveError("Geef het document een titel.")
        try:
            date.fromisoformat(doc_date)
        except (TypeError, ValueError):
            raise ArchiveError("De datum van het document is ongeldig.") from None
        if warranty_until:
            try:
                date.fromisoformat(warranty_until)
            except ValueError:
                raise ArchiveError("De garantiedatum is ongeldig.") from None
        return title

    def add_document(self, source: Path, title: str, category_id: int | None, doc_date: str,
                     amount: float | None = None, sender: str = "", warranty_until: str | None = None,
                     description: str = "", tags: str | Iterable[str] = "",
                     content: str | None = None) -> Document:
        source = Path(source)
        if not source.is_file():
            raise ArchiveError(f"Het bestand “{source.name}” is niet gevonden.")
        title = self._validate(title, doc_date, warranty_until)
        target = _unique_path(self._target_path(title, category_id, doc_date, source.suffix))
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(source, target)
        except OSError as exc:
            raise ArchiveError(f"Kon het bestand niet naar het archief kopiëren: {exc}") from exc
        if content is None:
            content = extract_text(target)
        now = _now()
        try:
            with self.conn:
                cur = self.conn.execute(
                    """INSERT INTO documents(title, category_id, doc_date, amount, sender, warranty_until,
                       description, tags, file_path, original_name, content, added_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (title, category_id, doc_date, amount, (sender or "").strip(), warranty_until or None,
                     (description or "").strip(), ", ".join(parse_tags(tags)),
                     target.relative_to(self.root).as_posix(), source.name, content or "", now, now),
                )
                doc = self.document(cur.lastrowid)
                self._index(doc)
        except Exception:
            target.unlink(missing_ok=True)
            raise
        return doc

    def update_document(self, doc_id: int, title: str, category_id: int | None, doc_date: str,
                        amount: float | None, sender: str, warranty_until: str | None,
                        description: str, tags: str | Iterable[str]) -> Document:
        doc = self.document(doc_id)
        if not doc:
            raise ArchiveError("Dit document bestaat niet meer.")
        title = self._validate(title, doc_date, warranty_until)
        current = self.file_of(doc)
        file_path = doc.file_path
        desired = self._target_path(title, category_id, doc_date, current.suffix)
        same_name = (current.parent == desired.parent and
                     re.fullmatch(re.escape(desired.stem) + r"( \(\d+\))?", current.stem))
        moved_to: Path | None = None
        if current.exists() and not same_name:
            moved_to = _unique_path(desired)
            moved_to.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.move(str(current), str(moved_to))
            except OSError as exc:
                raise ArchiveError(
                    f"Kon het bestand niet hernoemen. Is het nog geopend in een ander programma? ({exc})"
                ) from exc
            file_path = moved_to.relative_to(self.root).as_posix()
        try:
            with self.conn:
                self.conn.execute(
                    """UPDATE documents SET title = ?, category_id = ?, doc_date = ?, amount = ?, sender = ?,
                       warranty_until = ?, description = ?, tags = ?, file_path = ?, updated_at = ?
                       WHERE id = ?""",
                    (title, category_id, doc_date, amount, (sender or "").strip(), warranty_until or None,
                     (description or "").strip(), ", ".join(parse_tags(tags)), file_path, _now(), doc_id),
                )
                doc = self.document(doc_id)
                self._index(doc)
        except Exception:
            if moved_to is not None:
                shutil.move(str(moved_to), str(current))
            raise
        self._remove_empty_dirs(current.parent)
        return doc

    def delete_document(self, doc_id: int) -> Path | None:
        """Verwijdert het document uit het archief. Het bestand gaat naar de
        prullenbak-map, zodat je het altijd nog terug kunt halen."""
        doc = self.document(doc_id)
        if not doc:
            return None
        src = self.file_of(doc)
        trashed: Path | None = None
        if src.exists():
            trash = self.root / TRASH_DIR
            trash.mkdir(exist_ok=True)
            trashed = _unique_path(trash / src.name)
            try:
                shutil.move(str(src), str(trashed))
            except OSError as exc:
                raise ArchiveError(
                    f"Kon het bestand niet verplaatsen. Is het nog geopend in een ander programma? ({exc})"
                ) from exc
        with self.conn:
            self.conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
            self.conn.execute("DELETE FROM documents_fts WHERE rowid = ?", (doc_id,))
        self._remove_empty_dirs(src.parent)
        return trashed

    def _remove_empty_dirs(self, folder: Path) -> None:
        docs_root = (self.root / DOCS_DIR).resolve()
        try:
            folder = folder.resolve()
            if folder != docs_root and docs_root in folder.parents and not any(folder.iterdir()):
                folder.rmdir()
        except OSError:
            pass

    # ----------------------------------------------------------------- search
    def _index(self, doc: Document) -> None:
        d = None
        try:
            d = date.fromisoformat(doc.doc_date)
        except ValueError:
            pass
        extra = [doc.doc_date, doc.original_name]
        if d:
            extra += [str(d.year), MAANDEN[d.month - 1]]
        if doc.amount is not None:
            extra += [format_amount_plain(doc.amount), str(int(doc.amount))]
        if doc.warranty_until:
            extra.append("garantie")
        self.conn.execute("DELETE FROM documents_fts WHERE rowid = ?", (doc.id,))
        self.conn.execute(
            """INSERT INTO documents_fts(rowid, title, description, sender, tags, category, content, extra)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (doc.id, doc.title, doc.description, doc.sender, " ".join(doc.tags),
             self.category_path(doc.category_id, sep=" "), doc.content, " ".join(extra)),
        )

    def rebuild_index(self) -> None:
        with self.conn:
            self.conn.execute("DELETE FROM documents_fts")
            for doc in self.all_documents():
                self._index(doc)

    def search(self, text: str = "", category_id: int | None = None, special: str | None = None,
               today: date | None = None) -> list[Document]:
        """Zoekt documenten. Alle woorden moeten ergens voorkomen: in de titel,
        omschrijving, afzender, labels, categorie, tekst in het bestand, datum
        of bedrag."""
        today = today or date.today()
        sql = "SELECT d.* FROM documents d"
        where: list[str] = []
        params: list = []
        fts = build_fts_query(text)
        if fts:
            sql += " JOIN documents_fts f ON f.rowid = d.id"
            where.append("documents_fts MATCH ?")
            params.append(fts)
        if category_id is not None:
            ids = sorted(self.descendants(category_id))
            where.append(f"d.category_id IN ({','.join('?' * len(ids))})")
            params.extend(ids)
        if special == FILTER_WARRANTY:
            where.append("d.warranty_until >= ?")
            params.append(today.isoformat())
        elif special == FILTER_EXPIRING:
            where.append("d.warranty_until >= ? AND d.warranty_until <= ?")
            params += [today.isoformat(), (today + timedelta(days=EXPIRING_DAYS)).isoformat()]
        elif special == FILTER_UNCATEGORIZED:
            where.append("d.category_id IS NULL")
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY d.doc_date DESC, d.id DESC"
        return [self._row_to_document(r) for r in self.conn.execute(sql, params)]

    def counts(self, today: date | None = None) -> dict:
        """Aantallen voor de zijbalk."""
        today = today or date.today()
        per_cat: dict[int | None, int] = {}
        for row in self.conn.execute("SELECT category_id, COUNT(*) n FROM documents GROUP BY category_id"):
            per_cat[row["category_id"]] = row["n"]
        total = sum(per_cat.values())
        warranty = self.conn.execute(
            "SELECT COUNT(*) FROM documents WHERE warranty_until >= ?", (today.isoformat(),)).fetchone()[0]
        expiring = self.conn.execute(
            "SELECT COUNT(*) FROM documents WHERE warranty_until >= ? AND warranty_until <= ?",
            (today.isoformat(), (today + timedelta(days=EXPIRING_DAYS)).isoformat())).fetchone()[0]
        return {"per_category": per_cat, "total": total, "warranty": warranty, "expiring": expiring}

    # ----------------------------------------------------------------- backup
    def backup(self, dest_zip: Path) -> Path:
        """Maakt één zip-bestand met de database en alle documenten."""
        dest_zip = Path(dest_zip)
        root = self.root.resolve()
        if root == dest_zip.resolve().parent or root in dest_zip.resolve().parents:
            raise ArchiveError("Sla de back-up op buiten de archiefmap, bijvoorbeeld op een USB-stick.")
        with tempfile.TemporaryDirectory() as tmp:
            snapshot = Path(tmp) / DB_NAME
            target = sqlite3.connect(str(snapshot))
            try:
                self.conn.backup(target)
            finally:
                target.close()
            tmp_zip = dest_zip.with_name(dest_zip.name + ".deel")
            with zipfile.ZipFile(tmp_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                zf.write(snapshot, DB_NAME)
                for sub in (DOCS_DIR, TRASH_DIR):
                    base = self.root / sub
                    if base.exists():
                        for path in sorted(base.rglob("*")):
                            if path.is_file():
                                zf.write(path, path.relative_to(self.root).as_posix())
            tmp_zip.replace(dest_zip)
        return dest_zip
