import ast
import zipfile
from datetime import date
from pathlib import Path

import pytest

from mijnarchief.archive import (
    FILTER_EXPIRING, FILTER_UNCATEGORIZED, FILTER_WARRANTY, Archive, ArchiveError, build_fts_query,
    safe_name,
)

TODAY = date(2026, 11, 10)


@pytest.fixture
def archive(tmp_path):
    a = Archive(tmp_path / "Mijn Archief")
    yield a
    a.close()


@pytest.fixture
def src(tmp_path):
    def make(name="bon.txt", text="Bosch wasmachine WGG244 serienummer 123"):
        p = tmp_path / "inbox" / name
        p.parent.mkdir(exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return p
    return make


def cat_id(archive, name):
    return next(c.id for c in archive.categories() if c.name == name)


def test_default_categories(archive):
    names = {c.name for c in archive.categories()}
    assert {"Bonnetjes", "Garantiebewijzen", "Facturen", "Brieven"} <= names


def test_add_document_copies_file_with_clear_name(archive, src):
    source = src()
    doc = archive.add_document(source, "Wasmachine Bosch", cat_id(archive, "Garantiebewijzen"), "2026-09-03",
                               amount=649.0, sender="MediaMarkt", warranty_until="2031-09-03",
                               description="5 jaar garantie", tags="huishouden, witgoed, Huishouden")
    assert doc.file_path == "documenten/2026/2026-09-03_Garantiebewijzen_Wasmachine-Bosch.txt"
    assert archive.file_of(doc).read_text(encoding="utf-8").startswith("Bosch")
    assert source.exists(), "het origineel blijft staan"
    assert doc.tags == ["huishouden", "witgoed"]
    assert "WGG244" in doc.content


def test_duplicate_names_get_number(archive, src):
    a = archive.add_document(src(), "Bon", None, "2026-01-01")
    b = archive.add_document(src(), "Bon", None, "2026-01-01")
    assert a.file_path != b.file_path
    assert b.file_path.endswith("(2).txt")


@pytest.mark.parametrize("query, expected", [
    ("wasm", True),             # begin van een woord
    ("mediamarkt", True),       # afzender
    ("garantie huishouden", True),  # meerdere woorden
    ("WGG244", True),           # tekst in het bestand
    ("september", True),        # maandnaam van de datum
    ("2026", True),             # jaartal
    ("649", True),              # bedrag
    ("649,00", True),
    ("garantiebewijzen", True),  # categorienaam
    ("koelkast", False),
    ("wasmachine koelkast", False),
])
def test_search(archive, src, query, expected):
    archive.add_document(src(), "Wasmachine Bosch", cat_id(archive, "Garantiebewijzen"), "2026-09-03",
                         amount=649.0, sender="MediaMarkt", description="5 jaar garantie", tags="huishouden")
    assert bool(archive.search(query)) is expected


def test_search_ignores_accents_and_odd_characters(archive, src):
    archive.add_document(src(), "Café-rekening", None, "2026-01-01", description="Privé uitje")
    assert archive.search("cafe")
    assert archive.search("prive")
    assert archive.search('"(prive*') , "vreemde tekens mogen geen fout geven"
    assert archive.search("") and archive.search("   ")


def test_subcategories_and_filter(archive, src):
    huis = archive.add_category("Huis", "Alles rond het huis", "#2b4c7e")
    energie = archive.add_category("Energie", "", "#2f7a4f", parent_id=huis)
    archive.add_document(src(), "Jaarafrekening", energie, "2026-10-14")
    archive.add_document(src(), "Bon", cat_id(archive, "Bonnetjes"), "2026-10-15")
    assert [d.title for d in archive.search(category_id=huis)] == ["Jaarafrekening"]
    assert archive.category_path(energie) == "Huis › Energie"
    assert archive.search("huis energie")


def test_category_validation(archive):
    with pytest.raises(ArchiveError):
        archive.add_category("  ")
    with pytest.raises(ArchiveError):
        archive.add_category("bonnetjes")  # bestaat al (hoofdletters tellen niet)
    a = archive.add_category("A")
    b = archive.add_category("B", parent_id=a)
    with pytest.raises(ArchiveError):
        archive.update_category(a, "A", "", "#000000", parent_id=b)  # kringverwijzing


def test_rename_category_updates_search_and_filename(archive, src):
    auto = archive.add_category("Auto")
    doc = archive.add_document(src(), "APK", auto, "2026-06-11")
    archive.update_category(auto, "Vervoer", "", "#1f7a85", None)
    assert archive.search("vervoer")
    assert not archive.search("auto")
    # Na bewerken krijgt het bestand de nieuwe naam.
    doc = archive.update_document(doc.id, "APK", auto, "2026-06-11", None, "", None, "", "")
    assert doc.file_path == "documenten/2026/2026-06-11_Vervoer_APK.txt"
    assert archive.file_of(doc).exists()


def test_delete_category_keeps_documents(archive, src):
    huis = archive.add_category("Huis")
    energie = archive.add_category("Energie", parent_id=huis)
    doc = archive.add_document(src(), "Rekening", huis, "2026-01-01")
    archive.delete_category(huis)
    assert archive.document(doc.id).category_id is None
    assert archive.category(energie).parent_id is None
    assert [d.id for d in archive.search(special=FILTER_UNCATEGORIZED)] == [doc.id]


def test_update_moves_file_when_date_changes(archive, src):
    doc = archive.add_document(src(), "Brief", None, "2025-12-02")
    old = archive.file_of(doc)
    doc = archive.update_document(doc.id, "Brief belasting", cat_id(archive, "Brieven"), "2026-01-05",
                                  12.5, "Belastingdienst", None, "nieuw", "belasting")
    assert not old.exists()
    assert not old.parent.exists(), "lege jaarmap wordt opgeruimd"
    assert archive.file_of(doc).exists()
    assert doc.file_path.startswith("documenten/2026/")
    assert archive.search("belastingdienst nieuw")


def test_update_keeps_file_when_name_unchanged(archive, src):
    archive.add_document(src(), "Bon", None, "2026-01-01")
    doc2 = archive.add_document(src(), "Bon", None, "2026-01-01")  # krijgt (2)
    doc2 = archive.update_document(doc2.id, "Bon", None, "2026-01-01", 3.0, "", None, "", "")
    assert doc2.file_path.endswith("(2).txt")


def test_delete_moves_to_trash(archive, src):
    doc = archive.add_document(src(), "Weg ermee", None, "2026-01-01")
    trashed = archive.delete_document(doc.id)
    assert trashed and trashed.exists() and trashed.parent.name == "prullenbak"
    assert archive.document(doc.id) is None
    assert not archive.search("ermee")


def test_warranty_filters(archive, src):
    archive.add_document(src(), "Laptop", None, "2025-03-18", warranty_until="2027-03-18")
    archive.add_document(src(), "Koptelefoon", None, "2024-12-20", warranty_until="2026-12-20")
    archive.add_document(src(), "Oude tv", None, "2020-01-01", warranty_until="2022-01-01")
    assert {d.title for d in archive.search(special=FILTER_WARRANTY, today=TODAY)} == {"Laptop", "Koptelefoon"}
    assert [d.title for d in archive.search(special=FILTER_EXPIRING, today=TODAY)] == ["Koptelefoon"]
    c = archive.counts(today=TODAY)
    assert (c["total"], c["warranty"], c["expiring"]) == (3, 2, 1)


def test_validation(archive, src):
    with pytest.raises(ArchiveError):
        archive.add_document(src(), "", None, "2026-01-01")
    with pytest.raises(ArchiveError):
        archive.add_document(src(), "x", None, "geen datum")
    with pytest.raises(ArchiveError):
        archive.add_document(Path("bestaat-niet.pdf"), "x", None, "2026-01-01")


def test_backup_contains_everything(archive, src, tmp_path):
    doc = archive.add_document(src(), "Bon", None, "2026-01-01")
    zip_path = archive.backup(tmp_path / "backup.zip")
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
    assert "archief.db" in names and doc.file_path in names
    with pytest.raises(ArchiveError):
        archive.backup(archive.root / "backup.zip")


def test_reopen_keeps_data(tmp_path, src):
    a = Archive(tmp_path / "A")
    a.add_document(src(), "Blijft", None, "2026-01-01")
    a.close()
    b = Archive(tmp_path / "A")
    assert [d.title for d in b.search("blijft")] == ["Blijft"]
    assert len([c for c in b.categories() if c.name == "Bonnetjes"]) == 1
    b.close()


def test_safe_name():
    assert safe_name('Factuur: "Eneco" 2026/10?') == "Factuur-Eneco-2026-10"
    assert safe_name("...") == "document"
    assert len(safe_name("x" * 300)) <= 80


def test_build_fts_query():
    assert build_fts_query('wasm "AND" -x') == '"wasm"* "AND"* "x"*'
    assert build_fts_query("  ") == ""


def test_program_never_uses_network():
    """Het programma mag geen netwerkcode bevatten."""
    forbidden = {"socket", "urllib", "http", "requests", "ftplib", "smtplib", "ssl", "websocket",
                 "PySide6.QtNetwork", "PySide6.QtWebEngineWidgets", "PySide6.QtWebEngineCore"}
    pkg = Path(__file__).resolve().parent.parent / "mijnarchief"
    for py in pkg.rglob("*.py"):
        tree = ast.parse(py.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module] + [f"{node.module}.{a.name}" for a in node.names]
            for name in names:
                assert name.split(".")[0] not in forbidden and name not in forbidden, f"{py.name}: {name}"


def test_lock_other_computer(archive, monkeypatch):
    import json
    assert archive.lock_owner() is None
    archive.acquire_lock()
    assert archive.lock_owner() is None, "eigen computer telt niet als 'in gebruik'"
    (archive.root / "in-gebruik.json").write_text(json.dumps({"computer": "LAPTOP-WOONKAMER", "pid": 1}))
    assert archive.lock_owner()["computer"] == "LAPTOP-WOONKAMER"
    archive.release_lock()  # niet van ons: blijft staan
    assert (archive.root / "in-gebruik.json").exists()


def test_lock_released_on_close(tmp_path):
    a = Archive(tmp_path / "A")
    a.acquire_lock()
    assert (tmp_path / "A" / "in-gebruik.json").exists()
    a.close()
    assert not (tmp_path / "A" / "in-gebruik.json").exists()


def test_journal_mode_works_on_network_shares(archive):
    assert archive.conn.execute("PRAGMA journal_mode").fetchone()[0] == "delete"


def test_copy_to_new_location(archive, src, tmp_path):
    huis = archive.add_category("Huis")
    doc = archive.add_document(src(), "Jaarafrekening", huis, "2026-10-14", description="Eneco")
    gone = archive.add_document(src(), "Weg", None, "2026-01-01")
    archive.delete_document(gone.id)
    dest = tmp_path / "raspberry" / "MijnArchief"
    assert archive.copy_to(dest) == 1
    assert archive.file_of(doc).exists(), "het origineel blijft staan"
    copy = Archive(dest)
    assert [d.title for d in copy.search("eneco")] == ["Jaarafrekening"]
    assert copy.file_of(copy.document(doc.id)).exists()
    assert any((dest / "prullenbak").iterdir())
    assert copy.category_path(copy.document(doc.id).category_id) == "Huis"
    copy.close()


def test_copy_to_refuses_bad_targets(archive, tmp_path):
    full = tmp_path / "vol"
    full.mkdir()
    (full / "iets.txt").write_text("x")
    with pytest.raises(ArchiveError):
        archive.copy_to(full)
    with pytest.raises(ArchiveError):
        archive.copy_to(archive.root)
    with pytest.raises(ArchiveError):
        archive.copy_to(archive.root / "binnenin")
