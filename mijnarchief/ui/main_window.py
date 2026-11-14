"""Het hoofdscherm (ontwerp A): categorieën · documentlijst · details."""

from __future__ import annotations

import subprocess
import sys
from datetime import date
from pathlib import Path

from PySide6.QtCore import QSize, Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QDesktopServices, QKeySequence, QPixmap
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow,
    QMenu, QPushButton, QScrollArea, QSplitter, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from .. import APP_NAME, __version__
from ..archive import (
    FILTER_EXPIRING, FILTER_UNCATEGORIZED, FILTER_WARRANTY, Archive, ArchiveError, Document,
)
from ..extract import find_tesseract
from ..formatting import format_amount, format_date_long, warranty_status
from . import style
from .dialogs import AboutBox, CategoryDialog, DocumentDialog, MoveDialog, ask, inform
from .icon import app_icon
from .widgets import (
    ROLE_COLOR, ROLE_COUNT, ROLE_DOC, ROLE_KEY, DocumentDelegate, SidebarDelegate, StatusBadge, render_preview,
)

PREVIEW_SIZE = QSize(460, 320)


class FlowChips(QWidget):
    """Een rij labels die netjes doorloopt naar een volgende regel."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.lay = QGridLayout(self)
        self.lay.setContentsMargins(0, 0, 0, 0)
        self.lay.setHorizontalSpacing(5)
        self.lay.setVerticalSpacing(5)

    def set_items(self, items: list[str]) -> None:
        while self.lay.count():
            w = self.lay.takeAt(0).widget()
            if w:
                w.hide()
                w.setParent(None)
                w.deleteLater()
        if not items:
            lbl = QLabel("—")
            self.lay.addWidget(lbl, 0, 0, Qt.AlignLeft)
            return
        per_row = 4
        for i, text in enumerate(items):
            chip = QLabel(text)
            chip.setObjectName("chip")
            self.lay.addWidget(chip, i // per_row, i % per_row, Qt.AlignLeft)
        self.lay.setColumnStretch(per_row, 1)


class DetailPanel(QScrollArea):
    def __init__(self, window: "MainWindow"):
        super().__init__()
        self.main = window
        self.setObjectName("detail")
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        inner = QWidget()
        inner.setObjectName("detailInner")
        self.setWidget(inner)
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(20, 18, 20, 18)
        lay.setSpacing(14)

        # Lege toestand
        self.empty = QWidget()
        el = QVBoxLayout(self.empty)
        el.setContentsMargins(0, 40, 0, 0)
        self.empty_title = QLabel("Nog geen documenten")
        self.empty_title.setObjectName("emptyTitle")
        self.empty_text = QLabel()
        self.empty_text.setWordWrap(True)
        self.empty_text.setObjectName("muted")
        el.addWidget(self.empty_title)
        el.addWidget(self.empty_text)
        el.addStretch(1)
        lay.addWidget(self.empty)

        # Inhoud
        self.content = QWidget()
        cl = QVBoxLayout(self.content)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(14)

        self.preview_frame = QFrame()
        self.preview_frame.setObjectName("preview")
        self.preview_frame.setMinimumHeight(PREVIEW_SIZE.height() + 24)
        self.preview_frame.setCursor(Qt.PointingHandCursor)
        self.preview_frame.setToolTip("Dubbelklik om het bestand te openen")
        pl = QVBoxLayout(self.preview_frame)
        pl.setContentsMargins(10, 10, 10, 8)
        self.preview = QLabel()
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setMinimumHeight(PREVIEW_SIZE.height())
        self.preview_info = QLabel()
        self.preview_info.setObjectName("muted")
        pl.addWidget(self.preview, 1)
        pl.addWidget(self.preview_info)
        self.preview_frame.mouseDoubleClickEvent = lambda e: self.main.open_document()
        cl.addWidget(self.preview_frame)

        head = QHBoxLayout()
        head.setSpacing(10)
        self.title = QLabel()
        self.title.setObjectName("detailTitle")
        self.title.setWordWrap(True)
        self.title.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.badge = StatusBadge()
        head.addWidget(self.title, 1)
        head.addWidget(self.badge, 0, Qt.AlignTop)
        cl.addLayout(head)

        self.desc_box = QFrame()
        self.desc_box.setObjectName("descBox")
        dl = QVBoxLayout(self.desc_box)
        dl.setContentsMargins(12, 10, 12, 10)
        dl.setSpacing(2)
        eyebrow = QLabel("OMSCHRIJVING")
        eyebrow.setObjectName("eyebrow")
        self.desc = QLabel()
        self.desc.setWordWrap(True)
        self.desc.setTextInteractionFlags(Qt.TextSelectableByMouse)
        dl.addWidget(eyebrow)
        dl.addWidget(self.desc)
        cl.addWidget(self.desc_box)

        meta = QGridLayout()
        meta.setHorizontalSpacing(16)
        meta.setVerticalSpacing(8)
        meta.setColumnStretch(1, 1)
        self.meta: dict[str, QLabel] = {}
        row = 0
        for key in ("Categorie", "Van", "Datum", "Bedrag", "Garantie tot", "Labels", "Bestand"):
            k = QLabel(key)
            k.setObjectName("metaKey")
            meta.addWidget(k, row, 0, Qt.AlignTop)
            if key == "Labels":
                self.chips = FlowChips()
                meta.addWidget(self.chips, row, 1)
            else:
                v = QLabel()
                v.setWordWrap(True)
                v.setTextInteractionFlags(Qt.TextSelectableByMouse)
                self.meta[key] = v
                meta.addWidget(v, row, 1)
            row += 1
        cl.addLayout(meta)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        self.btn_open = QPushButton("Openen")
        self.btn_open.setObjectName("primary")
        self.btn_folder = QPushButton("Toon in map")
        self.btn_edit = QPushButton("Bewerken")
        self.btn_delete = QPushButton("Verwijderen")
        self.btn_delete.setObjectName("danger")
        self.btn_open.clicked.connect(self.main.open_document)
        self.btn_folder.clicked.connect(self.main.show_in_folder)
        self.btn_edit.clicked.connect(self.main.edit_document)
        self.btn_delete.clicked.connect(self.main.delete_document)
        for b in (self.btn_open, self.btn_folder, self.btn_edit):
            actions.addWidget(b)
        actions.addStretch(1)
        actions.addWidget(self.btn_delete)
        cl.addLayout(actions)
        cl.addStretch(1)
        lay.addWidget(self.content)
        self.show_document(None)

    def show_empty(self, title: str, text: str) -> None:
        self.empty_title.setText(title)
        self.empty_text.setText(text)
        self.empty.show()
        self.content.hide()

    def show_document(self, doc: Document | None) -> None:
        if doc is None:
            self.content.hide()
            self.empty.show()
            return
        archive = self.main.archive
        self.empty.hide()
        self.content.show()
        path = archive.file_of(doc)
        pm = render_preview(path, PREVIEW_SIZE, self.devicePixelRatioF())
        if pm:
            self.preview.setPixmap(pm)
            self.preview.setText("")
        else:
            self.preview.setPixmap(QPixmap())
            self.preview.setText("Bestand niet gevonden" if not path.exists()
                                 else f"Geen voorbeeld beschikbaar\nvoor {path.suffix.upper().lstrip('.')}-bestanden")
        ext = path.suffix.upper().lstrip(".") or "BESTAND"
        size = f"{path.stat().st_size / 1024:,.0f} kB".replace(",", ".") if path.exists() else "ontbreekt"
        self.preview_info.setText(f"{ext} · {size}")

        self.title.setText(doc.title)
        self.badge.set_status(warranty_status(doc.warranty_until))
        self.desc.setText(doc.description or "Geen omschrijving. Klik op Bewerken om er een toe te voegen.")
        cat = archive.category(doc.category_id)
        color = cat.color if cat else style.MUTED
        cat_text = archive.category_path(doc.category_id) or "Zonder categorie"
        self.meta["Categorie"].setText(
            f"<span style='color:{color}; font-size:12pt'>●</span>&nbsp; {escape(cat_text)}")
        self.meta["Van"].setText(doc.sender or "—")
        self.meta["Datum"].setText(format_date_long(doc.doc_date))
        self.meta["Bedrag"].setText(format_amount(doc.amount))
        self.meta["Garantie tot"].setText(format_date_long(doc.warranty_until) if doc.warranty_until else "Geen garantie")
        self.meta["Bestand"].setText(f"<span style='color:{style.MUTED}'>{escape(doc.file_path)}</span>")
        self.chips.set_items(doc.tags)


def escape(text: str) -> str:
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class MainWindow(QMainWindow):
    def __init__(self, archive: Archive, change_folder=None, switch_to=None):
        super().__init__()
        self.archive = archive
        self.change_folder_cb = change_folder
        self.switch_to_cb = switch_to
        self.filter_key: tuple = ("all", None)
        self.docs: list[Document] = []
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(app_icon())
        self.resize(1360, 860)
        self.setMinimumSize(900, 560)
        self.setAcceptDrops(True)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Werkbalk
        bar = QWidget()
        bar.setObjectName("toolbar")
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(12, 10, 12, 10)
        bl.setSpacing(8)
        self.search = QLineEdit()
        self.search.setObjectName("search")
        self.search.setPlaceholderText("Zoek in alles, bijv. wasmachine, Eneco, garantie, 2025…   (Ctrl+F)")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(lambda: self._search_timer.start())
        bl.addWidget(self.search, 1)
        btn_cat = QPushButton("+ Categorie")
        btn_cat.clicked.connect(lambda: self.new_category())
        btn_add = QPushButton("+ Document toevoegen")
        btn_add.setObjectName("primary")
        btn_add.clicked.connect(lambda: self.add_documents())
        bl.addWidget(btn_cat)
        bl.addWidget(btn_add)
        root.addWidget(bar)

        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(150)
        self._search_timer.timeout.connect(self.refresh_documents)

        # Drie kolommen
        split = QSplitter(Qt.Horizontal)
        split.setHandleWidth(1)
        split.setChildrenCollapsible(False)

        side_panel = QWidget()
        side_panel.setObjectName("sidebarPanel")
        sl = QVBoxLayout(side_panel)
        sl.setContentsMargins(0, 0, 0, 6)
        sl.setSpacing(0)
        self.sidebar = QTreeWidget()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setHeaderHidden(True)
        self.sidebar.setRootIsDecorated(False)
        self.sidebar.setIndentation(16)
        self.sidebar.setItemDelegate(SidebarDelegate(self.sidebar))
        self.sidebar.setMouseTracking(True)
        self.sidebar.setContextMenuPolicy(Qt.CustomContextMenu)
        self.sidebar.customContextMenuRequested.connect(self._sidebar_menu)
        self.sidebar.itemSelectionChanged.connect(self._on_sidebar_select)
        self.sidebar.itemDoubleClicked.connect(self._on_sidebar_double)
        self.sidebar.setStyleSheet("QTreeWidget#sidebar { border-right: none; }")
        sl.addWidget(self.sidebar, 1)
        new_cat = QPushButton("+ Nieuwe categorie")
        new_cat.setObjectName("link")
        new_cat.clicked.connect(lambda: self.new_category())
        sl.addWidget(new_cat)
        split.addWidget(side_panel)

        self.list = QListWidget()
        self.list.setObjectName("doclist")
        self.list.setItemDelegate(DocumentDelegate(self._color_for, self.list))
        self.list.setMouseTracking(True)
        self.list.setUniformItemSizes(True)
        self.list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self._list_menu)
        self.list.currentItemChanged.connect(self._on_doc_select)
        self.list.itemDoubleClicked.connect(lambda _: self.open_document())
        split.addWidget(self.list)

        self.detail = DetailPanel(self)
        split.addWidget(self.detail)
        split.setSizes([240, 520, 600])
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        split.setStretchFactor(2, 1)
        root.addWidget(split, 1)

        # Statusbalk
        self.status_count = QLabel()
        self.status_folder = QLabel()
        offline = QLabel(f"<span style='color:{style.OK}'>●</span> Offline · lokaal opgeslagen")
        self.statusBar().addWidget(self.status_count)
        self.statusBar().addWidget(self.status_folder, 1)
        self.statusBar().addPermanentWidget(offline)
        self.statusBar().setSizeGripEnabled(True)

        self._build_menu()
        self.refresh_all()

    # -------------------------------------------------------------- menu's
    def _build_menu(self) -> None:
        m = self.menuBar().addMenu("&Bestand")
        self._action(m, "Document toevoegen…", self.add_documents, QKeySequence.New)
        self._action(m, "Nieuwe categorie…", self.new_category, "Ctrl+Shift+N")
        m.addSeparator()
        self._action(m, "Back-up maken…", self.make_backup, "Ctrl+B")
        self._action(m, "Archiefmap openen in Verkenner", self.open_archive_folder)
        if self.change_folder_cb:
            self._action(m, "Ander archief openen…", self.change_folder_cb)
        if self.switch_to_cb:
            self._action(m, "Archief verhuizen (bijv. naar Raspberry Pi)…", self.move_archive)
        m.addSeparator()
        self._action(m, "Afsluiten", self.close, "Ctrl+Q")

        d = self.menuBar().addMenu("&Document")
        self.act_open = self._action(d, "Openen", self.open_document, "Ctrl+O")
        self.act_folder = self._action(d, "Toon in map", self.show_in_folder)
        self.act_edit = self._action(d, "Bewerken…", self.edit_document, "Ctrl+E")
        d.addSeparator()
        self.act_delete = self._action(d, "Verwijderen", self.delete_document, QKeySequence.Delete)

        h = self.menuBar().addMenu("&Help")
        self._action(h, "Over Mijn Archief", self.show_about)

        find = QAction(self)
        find.setShortcut(QKeySequence.Find)
        find.triggered.connect(lambda: (self.search.setFocus(), self.search.selectAll()))
        self.addAction(find)
        esc = QAction(self)
        esc.setShortcut(Qt.Key_Escape)
        esc.triggered.connect(lambda: self.search.clear())
        self.addAction(esc)

    def _action(self, menu: QMenu, text: str, slot, shortcut=None) -> QAction:
        act = menu.addAction(text)
        act.triggered.connect(lambda checked=False: slot())
        if shortcut:
            act.setShortcut(QKeySequence(shortcut))
        return act

    # -------------------------------------------------------- vernieuwen
    def refresh_all(self) -> None:
        self.refresh_sidebar()
        self.refresh_documents()

    def _color_for(self, category_id: int | None) -> str:
        return self._colors.get(category_id, style.MUTED)

    def refresh_sidebar(self) -> None:
        cats = self.archive.categories()
        self._colors = {c.id: c.color for c in cats}
        counts = self.archive.counts()
        per = counts["per_category"]
        ids = {c.id for c in cats}
        children: dict[int | None, list] = {}
        for c in cats:
            children.setdefault(c.parent_id if c.parent_id in ids else None, []).append(c)

        def total(cid: int) -> int:
            return per.get(cid, 0) + sum(total(ch.id) for ch in children.get(cid, []))

        self.sidebar.blockSignals(True)
        self.sidebar.clear()

        def item(parent, text, key, color=None, count=None, tooltip=""):
            it = QTreeWidgetItem(parent, [text])
            it.setData(0, ROLE_KEY, key)
            it.setData(0, ROLE_COLOR, color)
            it.setData(0, ROLE_COUNT, count)
            if tooltip:
                it.setToolTip(0, tooltip)
            if key[0] == "header":
                it.setFlags(Qt.ItemIsEnabled)
            return it

        item(self.sidebar, "Archief", ("header", None))
        item(self.sidebar, "Alle documenten", ("all", None), style.MUTED, counts["total"])
        item(self.sidebar, "Categorieën", ("header", None))

        def add(parent, parent_id):
            for c in children.get(parent_id, []):
                it = item(parent, c.name, ("cat", c.id), c.color, total(c.id), c.description)
                add(it, c.id)

        add(self.sidebar, None)
        if per.get(None):
            item(self.sidebar, "Zonder categorie", ("special", FILTER_UNCATEGORIZED), "#9aa3b0", per[None])
        item(self.sidebar, "Garantie", ("header", None))
        item(self.sidebar, "Garantie loopt nog", ("special", FILTER_WARRANTY), style.OK, counts["warranty"])
        item(self.sidebar, "Verloopt binnenkort", ("special", FILTER_EXPIRING), style.WARN,
             counts["expiring"], "Garantie verloopt binnen 3 maanden")
        self.sidebar.expandAll()

        # Selectie herstellen
        target = None
        it_iter = [self.sidebar.topLevelItem(i) for i in range(self.sidebar.topLevelItemCount())]
        while it_iter:
            it = it_iter.pop(0)
            if it.data(0, ROLE_KEY) == self.filter_key:
                target = it
                break
            it_iter.extend(it.child(i) for i in range(it.childCount()))
        if target is None:
            self.filter_key = ("all", None)
            target = self.sidebar.topLevelItem(1)
        self.sidebar.setCurrentItem(target)
        self.sidebar.blockSignals(False)

    def refresh_documents(self, select_id: int | None = None) -> None:
        if select_id is None:
            cur = self.list.currentItem()
            select_id = cur.data(ROLE_DOC).id if cur else None
        kind, value = self.filter_key
        self.docs = self.archive.search(
            self.search.text(),
            category_id=value if kind == "cat" else None,
            special=value if kind == "special" else None,
        )
        self.list.blockSignals(True)
        self.list.clear()
        select_row = 0
        for i, doc in enumerate(self.docs):
            it = QListWidgetItem()
            it.setData(ROLE_DOC, doc)
            it.setToolTip(doc.title)
            self.list.addItem(it)
            if doc.id == select_id:
                select_row = i
        self.list.blockSignals(False)
        if self.docs:
            self.list.setCurrentRow(select_row)
            self.list.scrollToItem(self.list.currentItem())
        self._on_doc_select()

        n = len(self.docs)
        total = self.archive.counts()["total"]
        self.status_count.setText(f"{n} van {total} documenten" if n != total else
                                  f"{total} {'document' if total == 1 else 'documenten'}")
        self.status_folder.setText(f"Archiefmap: {self.archive.root}")

    # ----------------------------------------------------------- selectie
    def _on_sidebar_select(self) -> None:
        it = self.sidebar.currentItem()
        if not it:
            return
        key = it.data(0, ROLE_KEY)
        if key[0] == "header":
            return
        self.filter_key = key
        self.refresh_documents()

    def _on_sidebar_double(self, it: QTreeWidgetItem) -> None:
        key = it.data(0, ROLE_KEY)
        if key and key[0] == "cat":
            self.edit_category(key[1])

    def current_document(self) -> Document | None:
        it = self.list.currentItem()
        return it.data(ROLE_DOC) if it else None

    def _on_doc_select(self, *_args) -> None:
        doc = self.current_document()
        for act in (self.act_open, self.act_folder, self.act_edit, self.act_delete):
            act.setEnabled(doc is not None)
        if doc:
            self.detail.show_document(doc)
        elif self.archive.counts()["total"] == 0:
            self.detail.show_empty(
                "Nog geen documenten",
                "Klik op ‘+ Document toevoegen’ of sleep een PDF, foto of scan naar dit venster. "
                "Het bestand wordt als kopie in je archief bewaard.")
        elif self.search.text().strip():
            self.detail.show_empty(
                "Niets gevonden",
                f"Er is geen document met “{self.search.text().strip()}”. Probeer een ander woord, "
                "of zoek op winkel, bedrag of jaartal.")
        else:
            self.detail.show_empty("Geen documenten hier", "In deze categorie staan nog geen documenten.")

    # ----------------------------------------------------- contextmenu's
    def _sidebar_menu(self, pos) -> None:
        it = self.sidebar.itemAt(pos)
        key = it.data(0, ROLE_KEY) if it else None
        menu = QMenu(self)
        if key and key[0] == "cat":
            menu.addAction("Bewerken…", lambda: self.edit_category(key[1]))
            menu.addAction("Subcategorie toevoegen…", lambda: self.new_category(parent_id=key[1]))
            menu.addAction("Document toevoegen in deze categorie…", lambda: self.add_documents(category_id=key[1]))
            menu.addSeparator()
            menu.addAction("Verwijderen…", lambda: self.delete_category(key[1]))
        else:
            menu.addAction("Nieuwe categorie…", lambda: self.new_category())
        menu.exec(self.sidebar.viewport().mapToGlobal(pos))

    def _list_menu(self, pos) -> None:
        it = self.list.itemAt(pos)
        if not it:
            return
        self.list.setCurrentItem(it)
        menu = QMenu(self)
        menu.addAction("Openen", self.open_document)
        menu.addAction("Toon in map", self.show_in_folder)
        menu.addAction("Bewerken…", self.edit_document)
        menu.addSeparator()
        menu.addAction("Verwijderen…", self.delete_document)
        menu.exec(self.list.viewport().mapToGlobal(pos))

    # ------------------------------------------------------------ acties
    def _selected_category(self) -> int | None:
        return self.filter_key[1] if self.filter_key[0] == "cat" else None

    def new_category(self, parent_id: int | None = None) -> None:
        dlg = CategoryDialog(self.archive, self, parent_id=parent_id)
        if dlg.exec():
            self.filter_key = ("cat", dlg.category_id)
            self.refresh_all()

    def edit_category(self, category_id: int) -> None:
        if CategoryDialog(self.archive, self, category_id=category_id).exec():
            self.refresh_all()

    def delete_category(self, category_id: int) -> None:
        cat = self.archive.category(category_id)
        if not cat:
            return
        n = len(self.archive.search(category_id=category_id))
        extra = (f"\n\nDe {n} {'document' if n == 1 else 'documenten'} in deze categorie blijven bewaard en "
                 f"komen onder ‘Zonder categorie’." if n else "")
        if ask(self, "Categorie verwijderen", f"Categorie “{cat.name}” verwijderen?{extra}",
               "Verwijderen", danger=True):
            self.archive.delete_category(category_id)
            self.filter_key = ("all", None)
            self.refresh_all()

    def add_documents(self, files: list[Path] | None = None, category_id: int | None = None) -> None:
        category_id = category_id if category_id is not None else self._selected_category()
        files = files or [None]
        last = None
        for f in files:
            dlg = DocumentDialog(self.archive, self, file=f, category_id=category_id)
            if len(files) > 1:
                dlg.setWindowTitle(f"Document toevoegen ({files.index(f) + 1} van {len(files)})")
            if not dlg.exec():
                if len(files) > 1 and not ask(self, "Doorgaan?", "Wil je de overige bestanden nog toevoegen?",
                                               "Doorgaan", "Stoppen"):
                    break
                continue
            last = dlg.result_doc
        if last:
            self.search.blockSignals(True)
            self.search.clear()
            self.search.blockSignals(False)
            if self.filter_key[0] != "all" and not (self.filter_key == ("cat", last.category_id)):
                self.filter_key = ("all", None)
            self.refresh_sidebar()
            self.refresh_documents(select_id=last.id)
            self.statusBar().showMessage(f"“{last.title}” is opgeslagen in je archief.", 5000)

    def edit_document(self) -> None:
        doc = self.current_document()
        if not doc:
            return
        dlg = DocumentDialog(self.archive, self, doc=doc)
        if dlg.exec():
            self.refresh_sidebar()
            self.refresh_documents(select_id=doc.id)
            self.statusBar().showMessage("Wijzigingen opgeslagen.", 4000)

    def delete_document(self) -> None:
        doc = self.current_document()
        if not doc:
            return
        if not ask(self, "Document verwijderen",
                   f"“{doc.title}” verwijderen uit je archief?\n\nHet bestand wordt verplaatst naar de map "
                   f"‘prullenbak’ in je archiefmap, zodat je het altijd nog terug kunt halen.",
                   "Verwijderen", danger=True):
            return
        row = self.list.currentRow()
        try:
            self.archive.delete_document(doc.id)
        except ArchiveError as exc:
            inform(self, "Verwijderen lukt niet", str(exc), error=True)
            return
        self.refresh_sidebar()
        nxt = self.docs[row + 1].id if row + 1 < len(self.docs) else (self.docs[row - 1].id if row > 0 else None)
        self.refresh_documents(select_id=nxt)
        self.statusBar().showMessage(f"“{doc.title}” is verplaatst naar de prullenbak-map.", 5000)

    def open_document(self) -> None:
        doc = self.current_document()
        if not doc:
            return
        path = self.archive.file_of(doc)
        if not path.exists():
            inform(self, "Bestand niet gevonden",
                   f"Het bestand staat niet meer op de verwachte plek:\n{path}", error=True)
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def show_in_folder(self) -> None:
        doc = self.current_document()
        if not doc:
            return
        path = self.archive.file_of(doc)
        reveal(path if path.exists() else path.parent)

    def open_archive_folder(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.archive.root)))

    def move_archive(self) -> None:
        dlg = MoveDialog(self.archive.root, self)
        while dlg.exec():
            self.setCursor(Qt.WaitCursor)
            self.statusBar().showMessage("Bezig met kopiëren… dit kan even duren.")
            QApplication.processEvents()
            try:
                n = self.archive.copy_to(dlg.folder)
            except ArchiveError as exc:
                self.unsetCursor()
                self.statusBar().clearMessage()
                dlg.show_error(str(exc))
                continue
            self.unsetCursor()
            self.statusBar().clearMessage()
            old = self.archive.root
            if self.switch_to_cb(dlg.folder):
                inform(None, "Archief verhuisd",
                       f"{n} {'document is' if n == 1 else 'documenten zijn'} gekopieerd naar:\n{dlg.folder}\n\n"
                       f"Mijn Archief werkt vanaf nu met deze map. Je oude archief staat nog op:\n{old}\n"
                       f"Als alles goed werkt, kun je die map later zelf verwijderen.")
            return

    def make_backup(self) -> None:
        name = f"Mijn Archief back-up {date.today().isoformat()}.zip"
        path, _ = QFileDialog.getSaveFileName(self, "Back-up opslaan", str(Path.home() / name),
                                              "Zip-bestand (*.zip)")
        if not path:
            return
        if not path.lower().endswith(".zip"):
            path += ".zip"
        self.setCursor(Qt.WaitCursor)
        try:
            out = self.archive.backup(Path(path))
        except (ArchiveError, OSError) as exc:
            self.unsetCursor()
            inform(self, "Back-up mislukt", str(exc), error=True)
            return
        self.unsetCursor()
        inform(self, "Back-up gemaakt",
               f"Je back-up is opgeslagen als:\n{out}\n\nBewaar dit bestand bij voorkeur op een USB-stick of "
               f"externe schijf. Terugzetten: pak het zip-bestand uit en kies de map via "
               f"Bestand › Ander archief openen.")

    def show_about(self) -> None:
        tesseract = find_tesseract()
        ocr = ("Tekstherkenning voor foto's en scans: <b>aan</b> (Tesseract gevonden)." if tesseract else
               "Tekstherkenning voor foto's en scans: <b>uit</b>. Installeer Tesseract-OCR om ook te zoeken op "
               "tekst in foto's en gescande documenten. PDF's met tekst zijn altijd doorzoekbaar.")
        AboutBox(
            f"<h3 style='margin:0'>{APP_NAME} {__version__}</h3>"
            f"<p>Een eigen digitaal archief voor bonnetjes, garantiebewijzen, facturen en brieven.</p>"
            f"<p><b>Volledig offline.</b> Dit programma maakt nooit verbinding met internet. Al je documenten "
            f"en gegevens staan in je archiefmap:<br><span style='color:{style.MUTED}'>{escape(str(self.archive.root))}"
            f"</span></p><p>{ocr}</p>"
            f"<p style='color:{style.MUTED}'>Sneltoetsen: Ctrl+N toevoegen · Ctrl+F zoeken · Ctrl+E bewerken · "
            f"Ctrl+O openen · Delete verwijderen · Ctrl+B back-up</p>", self).exec()

    # ------------------------------------------------------- slepen
    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls() and any(u.isLocalFile() for u in event.mimeData().urls()):
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        files = [Path(u.toLocalFile()) for u in event.mimeData().urls() if u.isLocalFile()]
        files = [f for f in files if f.is_file()]
        if files:
            event.acceptProposedAction()
            QTimer.singleShot(0, lambda: self.add_documents(files))

    def closeEvent(self, event) -> None:
        self.archive.close()
        super().closeEvent(event)


def reveal(path: Path) -> None:
    """Opent de Verkenner met het bestand geselecteerd."""
    if sys.platform == "win32" and path.is_file():
        subprocess.Popen(["explorer", "/select,", str(path)])
    elif sys.platform == "darwin" and path.is_file():
        subprocess.Popen(["open", "-R", str(path)])
    else:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path if path.is_dir() else path.parent)))
