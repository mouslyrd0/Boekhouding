"""Kleuren, lettertypen en stijl van ontwerp A."""

from __future__ import annotations

from PySide6.QtGui import QColor, QFont, QFontDatabase, QPalette
from PySide6.QtWidgets import QApplication

BG = "#eef1f5"
SURFACE = "#ffffff"
SURFACE_2 = "#f5f7fa"
LINE = "#d9dee6"
FG = "#1b2330"
MUTED = "#5d6878"
ACCENT = "#2b4c7e"
ACCENT_HOVER = "#223d66"
ACCENT_SOFT = "#e2e9f4"
OK, OK_SOFT = "#2f7a4f", "#e1f1e7"
WARN, WARN_SOFT = "#a8620a", "#fbefdc"
BAD, BAD_SOFT = "#b23b3b", "#f7e3e3"

STATUS_COLORS = {"ok": (OK, OK_SOFT), "warn": (WARN, WARN_SOFT), "bad": (BAD, BAD_SOFT)}


def pick_family(*candidates: str) -> str:
    families = set(QFontDatabase.families())
    for name in candidates:
        if name in families:
            return name
    return QApplication.font().family()


def apply_style(app: QApplication) -> None:
    app.setStyle("Fusion")
    family = pick_family("Segoe UI", "Inter", "IBM Plex Sans", "Noto Sans", "DejaVu Sans")
    font = QFont(family, 10)
    app.setFont(font)

    pal = QPalette()
    pal.setColor(QPalette.Window, QColor(BG))
    pal.setColor(QPalette.WindowText, QColor(FG))
    pal.setColor(QPalette.Base, QColor(SURFACE))
    pal.setColor(QPalette.AlternateBase, QColor(SURFACE_2))
    pal.setColor(QPalette.Text, QColor(FG))
    pal.setColor(QPalette.Button, QColor(SURFACE))
    pal.setColor(QPalette.ButtonText, QColor(FG))
    pal.setColor(QPalette.Highlight, QColor(ACCENT))
    pal.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    pal.setColor(QPalette.ToolTipBase, QColor(SURFACE))
    pal.setColor(QPalette.ToolTipText, QColor(FG))
    pal.setColor(QPalette.PlaceholderText, QColor(MUTED))
    pal.setColor(QPalette.Link, QColor(ACCENT))
    for role in (QPalette.Text, QPalette.WindowText, QPalette.ButtonText):
        pal.setColor(QPalette.Disabled, role, QColor("#9aa3b0"))
    app.setPalette(pal)
    app.setStyleSheet(STYLESHEET + _arrow_rules())


def _arrow_rules() -> str:
    """Tekent een klein pijltje voor keuzelijsten en datumvelden."""
    import tempfile
    from pathlib import Path

    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QPainter, QPen, QPixmap

    pm = QPixmap(24, 24)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(MUTED), 2.6)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    p.drawPolyline([QPointF(6, 9), QPointF(12, 15), QPointF(18, 9)])
    p.end()
    path = Path(tempfile.gettempdir()) / "mijnarchief-pijl.png"
    try:
        pm.save(str(path), "PNG")
    except Exception:
        return ""
    url = path.as_posix()
    return f"""
QComboBox::drop-down, QDateEdit::drop-down {{ subcontrol-origin: padding; subcontrol-position: center right;
    width: 26px; border: none; background: transparent; }}
QComboBox::down-arrow, QDateEdit::down-arrow {{ image: url("{url}"); width: 12px; height: 12px; }}
QComboBox::down-arrow:disabled, QDateEdit::down-arrow:disabled {{ image: none; }}
"""


STYLESHEET = f"""
QMainWindow, QDialog {{ background: {SURFACE}; }}
QToolTip {{ background: {SURFACE}; color: {FG}; border: 1px solid {LINE}; padding: 4px 6px; }}

QWidget#toolbar {{ background: {SURFACE}; border-bottom: 1px solid {LINE}; }}
QLineEdit#search {{
    background: {SURFACE_2}; border: 1px solid {LINE}; border-radius: 7px;
    padding: 7px 10px; font-size: 11pt;
}}
QLineEdit#search:focus {{ border-color: {ACCENT}; background: {SURFACE}; }}

QPushButton {{
    background: {SURFACE}; color: {FG}; border: 1px solid {LINE}; border-radius: 7px;
    padding: 7px 14px;
}}
QPushButton:hover {{ border-color: {ACCENT}; }}
QPushButton:pressed {{ background: {ACCENT_SOFT}; }}
QPushButton:disabled {{ color: #9aa3b0; border-color: {LINE}; }}
QPushButton#primary {{ background: {ACCENT}; color: white; border-color: {ACCENT}; font-weight: 600; }}
QPushButton#primary:hover {{ background: {ACCENT_HOVER}; border-color: {ACCENT_HOVER}; }}
QPushButton#danger {{ color: {BAD}; }}
QPushButton#danger:hover {{ border-color: {BAD}; }}
QPushButton#link {{ border: none; background: transparent; color: {ACCENT}; text-align: left; padding: 6px 12px; }}
QPushButton#link:hover {{ text-decoration: underline; }}
QPushButton#swatch {{ border-radius: 6px; padding: 0; min-width: 26px; max-width: 26px; min-height: 26px; max-height: 26px; border: 2px solid transparent; }}
QPushButton#swatch:checked {{ border: 2px solid {FG}; }}

QTreeWidget#sidebar {{
    background: {SURFACE_2}; border: none; border-right: 1px solid {LINE}; outline: 0; padding: 6px 4px;
}}
QWidget#sidebarPanel {{ background: {SURFACE_2}; border-right: 1px solid {LINE}; }}
QListWidget#doclist {{ background: {SURFACE}; border: none; border-right: 1px solid {LINE}; outline: 0; }}

QScrollArea#detail, QWidget#detailInner {{ background: {SURFACE}; border: none; }}
QLabel#detailTitle {{ font-size: 15pt; font-weight: 700; color: {FG}; }}
QLabel#muted, QLabel#metaKey {{ color: {MUTED}; }}
QLabel#eyebrow {{ color: {MUTED}; font-size: 8pt; letter-spacing: 1px; font-weight: 600; }}
QFrame#descBox {{ background: {SURFACE_2}; border: 1px solid {LINE}; border-radius: 6px; }}
QFrame#preview {{ background: {SURFACE_2}; border: 1px solid {LINE}; border-radius: 6px; }}
QLabel#chip {{ background: {SURFACE_2}; border: 1px solid {LINE}; border-radius: 10px; padding: 2px 9px; font-size: 9pt; }}
QLabel#emptyTitle {{ font-size: 13pt; font-weight: 700; }}
QLabel#error {{ color: {BAD}; }}
QLabel#dialogTitle {{ font-size: 14pt; font-weight: 700; }}
QLabel#fieldLabel {{ font-weight: 600; }}
QLabel#hint {{ color: {MUTED}; font-size: 9pt; }}
QFrame#dropZone {{ border: 2px dashed {LINE}; border-radius: 8px; background: {SURFACE_2}; }}

QLineEdit, QPlainTextEdit, QComboBox, QDateEdit {{
    background: {SURFACE_2}; border: 1px solid {LINE}; border-radius: 6px; padding: 6px 8px; color: {FG};
    selection-background-color: {ACCENT};
}}
QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QDateEdit:focus {{ border-color: {ACCENT}; background: {SURFACE}; }}
QLineEdit:disabled, QDateEdit:disabled {{ color: #9aa3b0; }}
QComboBox QAbstractItemView {{ background: {SURFACE}; border: 1px solid {LINE}; selection-background-color: {ACCENT_SOFT}; selection-color: {FG}; }}

QStatusBar {{ background: {SURFACE_2}; color: {MUTED}; border-top: 1px solid {LINE}; }}
QStatusBar QLabel {{ color: {MUTED}; padding: 0 6px; }}
QMenuBar {{ background: {SURFACE_2}; border-bottom: 1px solid {LINE}; }}
QMenuBar::item:selected {{ background: {ACCENT_SOFT}; }}
QMenu {{ background: {SURFACE}; border: 1px solid {LINE}; padding: 4px; }}
QMenu::item {{ padding: 6px 22px; border-radius: 4px; }}
QMenu::item:selected {{ background: {ACCENT_SOFT}; color: {FG}; }}
QMenu::separator {{ height: 1px; background: {LINE}; margin: 4px 6px; }}
QSplitter::handle {{ background: {LINE}; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #c4cbd6; border-radius: 4px; min-height: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QCheckBox {{ spacing: 8px; }}
"""
