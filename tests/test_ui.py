"""Rooktest van de vensters (draait zonder scherm via QT_QPA_PLATFORM=offscreen)."""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
QtWidgets = pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtCore import QDate  # noqa: E402

from mijnarchief.archive import Archive  # noqa: E402
from mijnarchief.ui import dialogs  # noqa: E402
from mijnarchief.ui.main_window import MainWindow  # noqa: E402
from mijnarchief.ui.style import apply_style  # noqa: E402


@pytest.fixture(scope="module")
def app():
    a = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    apply_style(a)
    return a


@pytest.fixture
def window(app, tmp_path, monkeypatch):
    monkeypatch.setattr(dialogs, "ask", lambda *a, **k: True)
    monkeypatch.setattr("mijnarchief.ui.main_window.ask", lambda *a, **k: True)
    archive = Archive(tmp_path / "archief")
    win = MainWindow(archive)
    win.show()
    yield win
    win.close()


def make_file(tmp_path, name="kassabon_gamma.txt", text="Gamma muurverf 87,30"):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def test_empty_state(window):
    assert window.list.count() == 0
    assert window.detail.empty_title.text() == "Nog geen documenten"


def test_add_edit_search_delete(window, tmp_path, monkeypatch):
    archive = window.archive
    bonnetjes = next(c.id for c in archive.categories() if c.name == "Bonnetjes")

    dlg = dialogs.DocumentDialog(archive, window, file=make_file(tmp_path), category_id=bonnetjes)
    assert dlg.title.text() == "Kassabon gamma"
    dlg.amount.setText("87,3")
    dlg.desc.setPlainText("Verf voor de slaapkamer")
    dlg.has_warranty.setChecked(True)
    dlg._set_warranty_years(2)
    dlg._save()
    assert dlg.result() == QtWidgets.QDialog.Accepted
    doc = dlg.result_doc
    assert doc.amount == 87.3 and doc.category_id == bonnetjes and doc.warranty_until

    window.refresh_all()
    assert window.list.count() == 1
    assert window.detail.title.text() == "Kassabon gamma"

    # Fout bedrag geeft een melding en sluit het venster niet
    bad = dialogs.DocumentDialog(archive, window, doc=doc)
    bad.amount.setText("twaalf")
    bad._save()
    assert not bad.error.isHidden()

    edit = dialogs.DocumentDialog(archive, window, doc=doc)
    edit.title.setText("Verf slaapkamer")
    edit.date.setDate(QDate(2025, 5, 1))
    edit._save()
    assert archive.document(doc.id).file_path.startswith("documenten/2025/")

    window.search.setText("slaapkamer")
    window.refresh_documents()
    assert window.list.count() == 1
    window.search.setText("koelkast")
    window.refresh_documents()
    assert window.list.count() == 0
    assert window.detail.empty_title.text() == "Niets gevonden"
    window.search.setText("")
    window.refresh_documents()

    window.list.setCurrentRow(0)
    window.delete_document()
    assert window.list.count() == 0
    assert (archive.root / "prullenbak").exists()


def test_category_dialog(window):
    archive = window.archive
    dlg = dialogs.CategoryDialog(archive, window)
    dlg.name.setText("Bonnetjes")  # bestaat al
    dlg._save()
    assert not dlg.error.isHidden()
    dlg.name.setText("Huisdieren")
    dlg.desc.setText("Dierenarts en verzekering")
    dlg._save()
    assert dlg.result() == QtWidgets.QDialog.Accepted
    window.filter_key = ("cat", dlg.category_id)
    window.refresh_all()
    assert window.sidebar.currentItem().text(0) == "Huisdieren"

    window.delete_category(dlg.category_id)
    assert all(c.name != "Huisdieren" for c in archive.categories())


def test_folder_choice_and_move(window, tmp_path):
    used = tmp_path / "gebruikt"
    used.mkdir()
    (used / "foto.jpg").write_text("x")
    assert dialogs.resolve_archive_folder(used) == used / "Mijn Archief"
    assert dialogs.resolve_archive_folder(tmp_path / "nieuw") == tmp_path / "nieuw"

    welcome = dialogs.WelcomeDialog(tmp_path / "start")
    welcome.field.edit.setText(str(used))
    welcome._accept()
    assert welcome.folder == used / "Mijn Archief"

    move = dialogs.MoveDialog(window.archive.root, window)
    assert move.field.path() == dialogs.Path(dialogs.NETWORK_EXAMPLE)
    move.field.edit.setText("")
    move._accept()
    assert not move.error.isHidden()
