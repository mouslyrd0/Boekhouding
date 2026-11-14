"""Vensters voor categorieën, documenten, de eerste start en meldingen."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QCheckBox, QComboBox, QDateEdit, QDialog, QFileDialog, QFrame, QGridLayout,
    QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPlainTextEdit, QPushButton, QVBoxLayout,
)

from ..archive import CATEGORY_COLORS, Archive, ArchiveError, Document
from ..formatting import format_amount_plain, parse_amount

FILE_FILTER = ("Documenten (*.pdf *.jpg *.jpeg *.png *.heic *.tif *.tiff *.bmp *.gif *.webp *.txt "
               "*.doc *.docx *.xls *.xlsx *.odt *.eml *.msg);;Alle bestanden (*)")
DATE_FORMAT = "d MMMM yyyy"
NETWORK_EXAMPLE = r"\\raspberrypi\MijnArchief"
UNREACHABLE = ("Het archief is niet bereikbaar. Staat het archief op je Raspberry Pi of een andere schijf? "
               "Controleer of die aanstaat en verbonden is, en probeer het opnieuw.")


# ----------------------------------------------------------------- meldingen
def ask(parent, title: str, text: str, yes: str, no: str = "Annuleren", danger: bool = False) -> bool:
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setIcon(QMessageBox.Warning if danger else QMessageBox.Question)
    box.setText(text)
    yes_btn = box.addButton(yes, QMessageBox.AcceptRole)
    no_btn = box.addButton(no, QMessageBox.RejectRole)
    if danger:
        yes_btn.setObjectName("danger")
    box.setDefaultButton(no_btn if danger else yes_btn)
    box.exec()
    return box.clickedButton() is yes_btn


def inform(parent, title: str, text: str, error: bool = False) -> None:
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setIcon(QMessageBox.Critical if error else QMessageBox.Information)
    box.setText(text)
    box.addButton("OK", QMessageBox.AcceptRole)
    box.exec()


def _label(text: str, name: str = "fieldLabel") -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName(name)
    return lbl


def _buttons(ok_text: str, dialog: QDialog) -> tuple[QHBoxLayout, QPushButton]:
    row = QHBoxLayout()
    row.addStretch(1)
    cancel = QPushButton("Annuleren")
    cancel.clicked.connect(dialog.reject)
    ok = QPushButton(ok_text)
    ok.setObjectName("primary")
    ok.setDefault(True)
    row.addWidget(cancel)
    row.addWidget(ok)
    return row, ok


def fill_category_combo(combo: QComboBox, archive: Archive, none_text: str,
                        exclude: set[int] | None = None, select: int | None = None) -> None:
    """Vult een keuzelijst met categorieën, subcategorieën ingesprongen."""
    combo.clear()
    combo.addItem(none_text, None)
    cats = archive.categories()
    children: dict[int | None, list] = {}
    for c in cats:
        children.setdefault(c.parent_id if c.parent_id in {x.id for x in cats} else None, []).append(c)

    def add(parent_id, depth):
        for c in children.get(parent_id, []):
            if exclude and c.id in exclude:
                continue
            combo.addItem("      " * depth + c.name, c.id)
            add(c.id, depth + 1)

    add(None, 0)
    idx = combo.findData(select)
    combo.setCurrentIndex(max(0, idx))


# ---------------------------------------------------------------- categorie
class CategoryDialog(QDialog):
    def __init__(self, archive: Archive, parent=None, category_id: int | None = None,
                 parent_id: int | None = None):
        super().__init__(parent)
        self.archive = archive
        self.category_id = category_id
        cat = archive.category(category_id) if category_id else None
        self.setWindowTitle("Categorie bewerken" if cat else "Nieuwe categorie")
        self.setMinimumWidth(440)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 20, 22, 18)
        lay.setSpacing(8)
        lay.addWidget(_label(self.windowTitle(), "dialogTitle"))
        lay.addSpacing(6)

        lay.addWidget(_label("Naam"))
        self.name = QLineEdit(cat.name if cat else "")
        self.name.setPlaceholderText("bijv. Huisdieren")
        self.name.setMaxLength(60)
        lay.addWidget(self.name)

        lay.addWidget(_label("Omschrijving"))
        self.desc = QLineEdit(cat.description if cat else "")
        self.desc.setPlaceholderText("bijv. Dierenarts, verzekering en chipregistratie")
        lay.addWidget(self.desc)

        lay.addWidget(_label("Kleur"))
        row = QHBoxLayout()
        row.setSpacing(8)
        self.colors = QButtonGroup(self)
        current = cat.color if cat else CATEGORY_COLORS[len(archive.categories()) % len(CATEGORY_COLORS)]
        for i, color in enumerate(CATEGORY_COLORS):
            b = QPushButton()
            b.setObjectName("swatch")
            b.setCheckable(True)
            b.setAccessibleName(f"Kleur {i + 1}")
            b.setStyleSheet(f"background:{color};")
            b.setProperty("color", color)
            b.setChecked(color.lower() == current.lower())
            self.colors.addButton(b)
            row.addWidget(b)
        if not self.colors.checkedButton():
            self.colors.buttons()[0].setChecked(True)
        row.addStretch(1)
        lay.addLayout(row)

        lay.addWidget(_label("Onderdeel van"))
        self.parent_combo = QComboBox()
        exclude = archive.descendants(category_id) if category_id else None
        fill_category_combo(self.parent_combo, archive, "Geen (hoofdcategorie)", exclude,
                            cat.parent_id if cat else parent_id)
        lay.addWidget(self.parent_combo)
        lay.addWidget(_label("Kies een categorie om hier een subcategorie van te maken, bijv. Huis › Energie.",
                             "hint"))

        self.error = _label("", "error")
        self.error.setWordWrap(True)
        self.error.hide()
        lay.addSpacing(4)
        lay.addWidget(self.error)
        buttons, ok = _buttons("Opslaan" if cat else "Categorie aanmaken", self)
        ok.clicked.connect(self._save)
        lay.addLayout(buttons)
        self.name.setFocus()

    def _save(self) -> None:
        color = self.colors.checkedButton().property("color")
        try:
            if self.category_id:
                self.archive.update_category(self.category_id, self.name.text(), self.desc.text(), color,
                                             self.parent_combo.currentData())
            else:
                self.category_id = self.archive.add_category(self.name.text(), self.desc.text(), color,
                                                             self.parent_combo.currentData())
        except ArchiveError as exc:
            self.error.setText(str(exc))
            self.error.show()
            return
        self.accept()


# ----------------------------------------------------------------- document
def title_from_filename(path: Path) -> str:
    stem = re.sub(r"[_\-]+", " ", path.stem)
    stem = re.sub(r"\s+", " ", stem).strip()
    return stem[:1].upper() + stem[1:] if stem else ""


class DocumentDialog(QDialog):
    """Document toevoegen (met bestand) of de gegevens van een document bewerken."""

    def __init__(self, archive: Archive, parent=None, doc: Document | None = None, file: Path | None = None,
                 category_id: int | None = None):
        super().__init__(parent)
        self.archive = archive
        self.doc = doc
        self.file = Path(file) if file else None
        self.result_doc: Document | None = None
        self.setWindowTitle("Document bewerken" if doc else "Document toevoegen")
        self.setMinimumWidth(560)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 20, 22, 18)
        lay.setSpacing(8)
        lay.addWidget(_label(self.windowTitle(), "dialogTitle"))
        lay.addSpacing(4)

        # Bestand
        file_box = QFrame()
        file_box.setObjectName("dropZone")
        fl = QHBoxLayout(file_box)
        fl.setContentsMargins(12, 10, 12, 10)
        self.file_label = QLabel()
        self.file_label.setWordWrap(True)
        fl.addWidget(self.file_label, 1)
        if not doc:
            choose = QPushButton("Bestand kiezen…")
            choose.clicked.connect(self._choose_file)
            fl.addWidget(choose)
        lay.addWidget(file_box)

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(6)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        grid.addWidget(_label("Titel"), 0, 0, 1, 2)
        self.title = QLineEdit(doc.title if doc else "")
        self.title.setPlaceholderText("bijv. Stofzuiger Dyson V12")
        self.title.setMaxLength(120)
        grid.addWidget(self.title, 1, 0, 1, 2)

        grid.addWidget(_label("Categorie"), 2, 0)
        grid.addWidget(_label("Datum"), 2, 1)
        self.category = QComboBox()
        fill_category_combo(self.category, archive, "Zonder categorie", None,
                            doc.category_id if doc else category_id)
        grid.addWidget(self.category, 3, 0)
        self.date = QDateEdit()
        self.date.setCalendarPopup(True)
        self.date.setDisplayFormat(DATE_FORMAT)
        self.date.setDate(QDate.fromString(doc.doc_date, Qt.ISODate) if doc else QDate.currentDate())
        grid.addWidget(self.date, 3, 1)

        grid.addWidget(_label("Bedrag (€)"), 4, 0)
        grid.addWidget(_label("Van (winkel, bedrijf of instantie)"), 4, 1)
        self.amount = QLineEdit(format_amount_plain(doc.amount) if doc else "")
        self.amount.setPlaceholderText("0,00")
        grid.addWidget(self.amount, 5, 0)
        self.sender = QLineEdit(doc.sender if doc else "")
        self.sender.setPlaceholderText("bijv. Coolblue")
        grid.addWidget(self.sender, 5, 1)
        lay.addLayout(grid)

        # Garantie
        lay.addSpacing(2)
        self.has_warranty = QCheckBox("Dit document geeft garantie tot")
        lay.addWidget(self.has_warranty)
        wrow = QHBoxLayout()
        self.warranty = QDateEdit()
        self.warranty.setCalendarPopup(True)
        self.warranty.setDisplayFormat(DATE_FORMAT)
        wrow.addWidget(self.warranty, 1)
        self._quick = []
        for years in (1, 2, 3, 5):
            b = QPushButton(f"{years} jaar")
            b.setToolTip(f"Garantie tot {years} jaar na de datum van het document")
            b.clicked.connect(lambda _=False, y=years: self._set_warranty_years(y))
            wrow.addWidget(b)
            self._quick.append(b)
        lay.addLayout(wrow)
        if doc and doc.warranty_until:
            self.has_warranty.setChecked(True)
            self.warranty.setDate(QDate.fromString(doc.warranty_until, Qt.ISODate))
        else:
            self.warranty.setDate(self.date.date().addYears(2))
        self.has_warranty.toggled.connect(self._sync_warranty)
        self._sync_warranty()

        lay.addWidget(_label("Omschrijving"))
        self.desc = QPlainTextEdit(doc.description if doc else "")
        self.desc.setPlaceholderText("In je eigen woorden, bijv. ‘Gekocht voor de zolder, doos bewaard, "
                                     "serienummer staat onderop.’")
        self.desc.setTabChangesFocus(True)
        self.desc.setFixedHeight(84)
        lay.addWidget(self.desc)

        lay.addWidget(_label("Labels"))
        self.tags = QLineEdit(", ".join(doc.tags) if doc else "")
        self.tags.setPlaceholderText("bijv. huishouden, zolder")
        lay.addWidget(self.tags)
        lay.addWidget(_label("Scheid labels met een komma. Je kunt later op elk label zoeken.", "hint"))

        self.error = _label("", "error")
        self.error.setWordWrap(True)
        self.error.hide()
        lay.addWidget(self.error)
        buttons, ok = _buttons("Wijzigingen opslaan" if doc else "Opslaan in archief", self)
        ok.clicked.connect(self._save)
        lay.addLayout(buttons)

        self._update_file_label()
        if self.file and not self.title.text():
            self.title.setText(title_from_filename(self.file))
        self.title.setFocus()
        self.title.selectAll()

    def _update_file_label(self) -> None:
        if self.doc:
            self.file_label.setText(f"<b>Bestand:</b> {Path(self.doc.file_path).name}")
        elif self.file:
            self.file_label.setText(f"<b>{self.file.name}</b><br><span style='color:#5d6878'>"
                                    f"Er wordt een kopie in je archief bewaard. Het origineel blijft staan.</span>")
        else:
            self.file_label.setText("Kies een PDF, foto of scan. Je kunt bestanden ook direct "
                                    "naar het hoofdvenster slepen.")

    def _choose_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Bestand kiezen", str(Path.home()), FILE_FILTER)
        if path:
            self.file = Path(path)
            if not self.title.text().strip():
                self.title.setText(title_from_filename(self.file))
            self._update_file_label()

    def _sync_warranty(self) -> None:
        on = self.has_warranty.isChecked()
        self.warranty.setEnabled(on)
        for b in self._quick:
            b.setEnabled(on)

    def _set_warranty_years(self, years: int) -> None:
        self.warranty.setDate(self.date.date().addYears(years))

    def _show_error(self, text: str) -> None:
        self.error.setText(text)
        self.error.show()

    def _save(self) -> None:
        try:
            amount = parse_amount(self.amount.text())
        except ValueError:
            self._show_error("Het bedrag klopt niet. Typ bijvoorbeeld 12,50 of 1.149,00.")
            self.amount.setFocus()
            return
        warranty = self.warranty.date().toString(Qt.ISODate) if self.has_warranty.isChecked() else None
        values = dict(title=self.title.text(), category_id=self.category.currentData(),
                      doc_date=self.date.date().toString(Qt.ISODate), amount=amount, sender=self.sender.text(),
                      warranty_until=warranty, description=self.desc.toPlainText(), tags=self.tags.text())
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            if self.doc:
                self.result_doc = self.archive.update_document(self.doc.id, **values)
            else:
                if not self.file:
                    raise ArchiveError("Kies eerst een bestand.")
                self.result_doc = self.archive.add_document(self.file, **values)
        except ArchiveError as exc:
            QApplication.restoreOverrideCursor()
            self._show_error(str(exc))
            return
        except (sqlite3.Error, OSError):
            QApplication.restoreOverrideCursor()
            self._show_error(UNREACHABLE)
            return
        QApplication.restoreOverrideCursor()
        self.accept()


# ------------------------------------------------------------ eerste start
def resolve_archive_folder(chosen: Path) -> Path:
    """Een lege map of bestaande archiefmap gebruiken we direct; staat er al iets
    anders in, dan maken we er de submap 'Mijn Archief' in."""
    try:
        if chosen.exists() and not (chosen / "archief.db").exists() and any(chosen.iterdir()):
            return chosen / "Mijn Archief"
    except OSError:
        pass
    return chosen


class FolderField(QHBoxLayout):
    """Invoerveld voor een map, met knop 'Bladeren…'. Je kunt ook een
    netwerkadres typen, zoals NETWORK_EXAMPLE."""

    def __init__(self, dialog: QDialog, start: Path | None, title: str):
        super().__init__()
        self.dialog = dialog
        self.title = title
        self.edit = QLineEdit(str(start) if start else "")
        self.edit.setPlaceholderText(f"bijv. {NETWORK_EXAMPLE}")
        browse = QPushButton("Bladeren…")
        browse.clicked.connect(self._browse)
        self.addWidget(self.edit, 1)
        self.addWidget(browse)

    def _browse(self) -> None:
        current = self.path()
        start = str(current.parent if current else Path.home())
        path = QFileDialog.getExistingDirectory(self.dialog, self.title, start)
        if path:
            self.edit.setText(str(resolve_archive_folder(Path(path))))

    def path(self) -> Path | None:
        text = self.edit.text().strip().strip('"')
        return Path(text) if text else None


class WelcomeDialog(QDialog):
    """Bij de eerste start (of via 'Ander archief openen'): kies waar het archief staat."""

    def __init__(self, default_dir: Path, parent=None, message: str | None = None,
                 ok_text: str = "Starten"):
        super().__init__(parent)
        self.setWindowTitle("Welkom bij Mijn Archief")
        self.setMinimumWidth(560)
        self.folder = default_dir
        lay = QVBoxLayout(self)
        lay.setContentsMargins(26, 24, 26, 20)
        lay.setSpacing(10)
        lay.addWidget(_label("Welkom bij Mijn Archief", "dialogTitle"))
        intro = QLabel(message or (
            "Hier bewaar je bonnetjes, garantiebewijzen, facturen en brieven. Het programma maakt nooit "
            "verbinding met internet.<br><br>"
            "Kies de map waarin je archief komt. Dat kan een map op deze computer zijn, of een gedeelde map "
            "op je Raspberry Pi in je eigen thuisnetwerk."))
        intro.setWordWrap(True)
        intro.setTextFormat(Qt.RichText)
        lay.addWidget(intro)
        lay.addSpacing(4)
        lay.addWidget(_label("Archiefmap"))
        self.field = FolderField(self, default_dir, "Archiefmap kiezen")
        lay.addLayout(self.field)
        lay.addWidget(_label(f"Archief op je Raspberry Pi? Typ het netwerkadres, bijvoorbeeld "
                             f"{NETWORK_EXAMPLE}. Kies je een bestaande archiefmap, dan wordt die gewoon "
                             f"geopend.", "hint"))
        self.error = _label("", "error")
        self.error.setWordWrap(True)
        self.error.hide()
        lay.addWidget(self.error)
        lay.addSpacing(8)
        buttons, ok = _buttons(ok_text, self)
        ok.clicked.connect(self._accept)
        lay.addLayout(buttons)

    def _accept(self) -> None:
        path = self.field.path()
        if not path:
            self.error.setText("Kies of typ eerst een map.")
            self.error.show()
            return
        if str(path).startswith("\\\\") and not path.exists():
            self.error.setText(
                f"Het netwerkadres {path} is niet bereikbaar. Staat de Raspberry Pi aan? Open het adres "
                f"eerst één keer in de Verkenner en log in met je Raspberry Pi-gebruikersnaam en "
                f"-wachtwoord (vink ‘Referenties onthouden’ aan).")
            self.error.show()
            return
        self.folder = resolve_archive_folder(path)
        self.accept()


class MoveDialog(QDialog):
    """Het hele archief kopiëren naar een andere map, zoals de Raspberry Pi."""

    def __init__(self, current: Path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Archief verhuizen")
        self.setMinimumWidth(560)
        self.folder: Path | None = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(26, 24, 26, 20)
        lay.setSpacing(10)
        lay.addWidget(_label("Archief verhuizen", "dialogTitle"))
        intro = QLabel(
            "Alle documenten, categorieën en omschrijvingen worden gekopieerd naar een nieuwe map, "
            "bijvoorbeeld de gedeelde map op je Raspberry Pi. Daarna werkt het programma met de nieuwe map."
            f"<br><br>Je huidige archief blijft staan op:<br><span style='color:#5d6878'>{current}</span><br>"
            "Als alles goed werkt, kun je die map later zelf verwijderen.")
        intro.setWordWrap(True)
        intro.setTextFormat(Qt.RichText)
        lay.addWidget(intro)
        lay.addWidget(_label("Nieuwe archiefmap"))
        self.field = FolderField(self, None, "Nieuwe archiefmap kiezen")
        self.field.edit.setText(NETWORK_EXAMPLE)
        lay.addLayout(self.field)
        lay.addWidget(_label("Kies een lege map. Op de Raspberry Pi is dat meestal "
                             f"{NETWORK_EXAMPLE}.", "hint"))
        self.error = _label("", "error")
        self.error.setWordWrap(True)
        self.error.hide()
        lay.addWidget(self.error)
        buttons, ok = _buttons("Kopiëren en overstappen", self)
        ok.clicked.connect(self._accept)
        lay.addLayout(buttons)

    def show_error(self, text: str) -> None:
        self.error.setText(text)
        self.error.show()

    def _accept(self) -> None:
        path = self.field.path()
        if not path:
            self.show_error("Kies of typ eerst een map.")
            return
        if str(path).startswith("\\\\") and not path.exists():
            self.show_error(f"Het netwerkadres {path} is niet bereikbaar. Staat de Raspberry Pi aan? Open het "
                            f"adres eerst één keer in de Verkenner en log in.")
            return
        self.folder = path
        self.accept()


class AboutBox(QDialog):
    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Over Mijn Archief")
        self.setMinimumWidth(460)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 22, 24, 18)
        body = QLabel(text)
        body.setWordWrap(True)
        body.setTextFormat(Qt.RichText)
        body.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lay.addWidget(body)
        row = QHBoxLayout()
        row.addStretch(1)
        ok = QPushButton("Sluiten")
        ok.setObjectName("primary")
        ok.clicked.connect(self.accept)
        row.addWidget(ok)
        lay.addLayout(row)

