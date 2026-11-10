"""Losse onderdelen van het hoofdscherm: zijbalk, documentlijst en voorbeeld."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QRect, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QImage, QImageReader, QPainter, QPixmap
from PySide6.QtWidgets import QLabel, QStyle, QStyledItemDelegate, QStyleOptionViewItem

from ..extract import IMAGE_EXTS
from ..formatting import format_amount, format_date_short
from . import style

ROLE_KEY = Qt.UserRole + 1     # ("all", None) / ("cat", id) / ("special", naam) / ("header", None)
ROLE_COUNT = Qt.UserRole + 2
ROLE_COLOR = Qt.UserRole + 3
ROLE_DOC = Qt.UserRole + 4


class SidebarDelegate(QStyledItemDelegate):
    """Tekent een categorie als: gekleurd blokje · naam · aantal."""

    def sizeHint(self, option, index):
        key = index.data(ROLE_KEY)
        if key and key[0] == "header":
            return QSize(option.rect.width(), 34)
        return QSize(option.rect.width(), 34)

    def paint(self, p: QPainter, option: QStyleOptionViewItem, index) -> None:
        p.save()
        p.setRenderHint(QPainter.Antialiasing)
        key = index.data(ROLE_KEY) or ("", None)
        r = option.rect
        if key[0] == "header":
            f = QFont(option.font)
            f.setPointSizeF(option.font.pointSizeF() * 0.8)
            f.setBold(True)
            f.setLetterSpacing(QFont.AbsoluteSpacing, 1.0)
            p.setFont(f)
            p.setPen(QColor(style.MUTED))
            p.drawText(r.adjusted(10, 8, -6, 0), Qt.AlignLeft | Qt.AlignVCenter, index.data().upper())
            p.restore()
            return
        selected = bool(option.state & QStyle.State_Selected)
        hover = bool(option.state & QStyle.State_MouseOver)
        bg = r.adjusted(2, 1, -4, -1)
        if selected:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(style.ACCENT_SOFT))
            p.drawRoundedRect(bg, 6, 6)
        elif hover:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#e8ecf2"))
            p.drawRoundedRect(bg, 6, 6)
        color = index.data(ROLE_COLOR) or style.MUTED
        sw = QRectF(r.left() + 10, r.center().y() - 5, 10, 10)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(color))
        if key[0] == "special":
            p.drawEllipse(sw)
        else:
            p.drawRoundedRect(sw, 3, 3)
        f = QFont(option.font)
        f.setBold(selected)
        p.setFont(f)
        p.setPen(QColor(style.FG))
        count = index.data(ROLE_COUNT)
        count_w = 34 if count is not None else 0
        text_rect = QRect(r.left() + 28, r.top(), r.width() - 28 - count_w - 8, r.height())
        text = p.fontMetrics().elidedText(index.data() or "", Qt.ElideRight, text_rect.width())
        p.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, text)
        if count is not None:
            f2 = QFont(option.font)
            f2.setPointSizeF(option.font.pointSizeF() * 0.9)
            p.setFont(f2)
            p.setPen(QColor(style.MUTED))
            p.drawText(QRect(r.right() - count_w - 8, r.top(), count_w, r.height()),
                       Qt.AlignRight | Qt.AlignVCenter, str(count))
        p.restore()


class DocumentDelegate(QStyledItemDelegate):
    """Tekent een document in de lijst: kleurstreep, titel, afzender · omschrijving,
    datum en bedrag."""

    ROW_HEIGHT = 62

    def __init__(self, color_for, parent=None):
        super().__init__(parent)
        self.color_for = color_for

    def sizeHint(self, option, index):
        return QSize(option.rect.width(), self.ROW_HEIGHT)

    def paint(self, p: QPainter, option: QStyleOptionViewItem, index) -> None:
        doc = index.data(ROLE_DOC)
        if doc is None:
            return
        p.save()
        p.setRenderHint(QPainter.Antialiasing)
        r = option.rect
        selected = bool(option.state & QStyle.State_Selected)
        hover = bool(option.state & QStyle.State_MouseOver)
        if selected:
            p.fillRect(r, QColor(style.ACCENT_SOFT))
        elif hover:
            p.fillRect(r, QColor(style.SURFACE_2))
        p.setPen(QColor(style.LINE))
        p.drawLine(r.bottomLeft(), r.bottomRight())
        # Kleurstreep van de categorie
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(self.color_for(doc.category_id)))
        p.drawRoundedRect(QRectF(r.left(), r.top() + 10, 4, r.height() - 20), 2, 2)

        base = option.font
        small = QFont(base)
        small.setPointSizeF(base.pointSizeF() * 0.92)
        bold = QFont(base)
        bold.setBold(True)

        right_w = 100
        left = r.left() + 16
        text_w = r.width() - 16 - right_w - 14
        # Rechts: datum en bedrag
        p.setFont(small)
        p.setPen(QColor(style.FG))
        p.drawText(QRect(r.right() - right_w - 10, r.top() + 10, right_w, 20),
                   Qt.AlignRight | Qt.AlignVCenter, format_date_short(doc.doc_date))
        p.setPen(QColor(style.MUTED))
        p.drawText(QRect(r.right() - right_w - 10, r.top() + 31, right_w, 20),
                   Qt.AlignRight | Qt.AlignVCenter, format_amount(doc.amount))
        # Titel
        p.setFont(bold)
        p.setPen(QColor(style.FG))
        title = p.fontMetrics().elidedText(doc.title, Qt.ElideRight, text_w)
        p.drawText(QRect(left, r.top() + 10, text_w, 20), Qt.AlignLeft | Qt.AlignVCenter, title)
        # Afzender · omschrijving
        p.setFont(small)
        p.setPen(QColor(style.MUTED))
        sub = " · ".join(x for x in (doc.sender, " ".join(doc.description.split())) if x) or "Geen omschrijving"
        sub = p.fontMetrics().elidedText(sub, Qt.ElideRight, text_w)
        p.drawText(QRect(left, r.top() + 31, text_w, 20), Qt.AlignLeft | Qt.AlignVCenter, sub)
        p.restore()


class StatusBadge(QLabel):
    def set_status(self, status: tuple[str, str] | None) -> None:
        if not status:
            self.hide()
            return
        kind, text = status
        fg, bg = style.STATUS_COLORS[kind]
        self.setText(text)
        self.setStyleSheet(
            f"background:{bg}; color:{fg}; border-radius:10px; padding:3px 10px; font-weight:600; font-size:9pt;")
        self.show()


def render_preview(path: Path, target: QSize, dpr: float = 1.0) -> QPixmap | None:
    """Maakt een voorbeeldafbeelding van de eerste pagina (PDF) of van een foto."""
    if not path.exists():
        return None
    ext = path.suffix.lower()
    w, h = int(target.width() * dpr), int(target.height() * dpr)
    image: QImage | None = None
    if ext == ".pdf":
        from PySide6.QtPdf import QPdfDocument

        pdf = QPdfDocument()
        if pdf.load(str(path)) != QPdfDocument.Error.None_ or pdf.pageCount() < 1:
            return None
        page = pdf.pagePointSize(0)
        if page.width() <= 0 or page.height() <= 0:
            return None
        scale = min(w / page.width(), h / page.height())
        image = pdf.render(0, QSize(max(1, int(page.width() * scale)), max(1, int(page.height() * scale))))
        pdf.close()
    elif ext in IMAGE_EXTS:
        reader = QImageReader(str(path))
        reader.setAutoTransform(True)
        size = reader.size()
        if size.isValid() and (size.width() > w * 2 or size.height() > h * 2):
            reader.setScaledSize(size.scaled(w * 2, h * 2, Qt.KeepAspectRatio))
        image = reader.read()
    if image is None or image.isNull():
        return None
    pm = QPixmap.fromImage(image).scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    pm.setDevicePixelRatio(dpr)
    return pm
