"""Het programmapictogram, getekend in code (geen losse bestanden nodig)."""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPixmap

from . import style


def icon_pixmap(size: int) -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    s = size / 64.0
    # Achtergrond
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(style.ACCENT))
    p.drawRoundedRect(QRectF(2 * s, 2 * s, 60 * s, 60 * s), 13 * s, 13 * s)
    # Map met tabblad
    folder = QPainterPath()
    folder.moveTo(12 * s, 22 * s)
    folder.lineTo(26 * s, 22 * s)
    folder.lineTo(30 * s, 26 * s)
    folder.lineTo(52 * s, 26 * s)
    folder.lineTo(52 * s, 50 * s)
    folder.lineTo(12 * s, 50 * s)
    folder.closeSubpath()
    p.setBrush(QColor("#9db6dc"))
    p.drawPath(folder)
    # Document dat uit de map steekt
    p.setBrush(QColor("#ffffff"))
    p.drawRoundedRect(QRectF(19 * s, 14 * s, 26 * s, 26 * s), 2 * s, 2 * s)
    p.setBrush(QColor(style.ACCENT))
    for i, w in enumerate((16, 12, 14)):
        p.drawRect(QRectF(23 * s, (19 + i * 5) * s, w * s, 2 * s))
    # Voorkant van de map
    p.setBrush(QColor("#c9d8ee"))
    p.drawRoundedRect(QRectF(12 * s, 31 * s, 40 * s, 19 * s), 2 * s, 2 * s)
    p.end()
    return pm


def app_icon() -> QIcon:
    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        icon.addPixmap(icon_pixmap(size))
    return icon
