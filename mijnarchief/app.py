"""Start van het programma."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtCore import QLibraryInfo, QLocale, QTranslator
from PySide6.QtWidgets import QApplication, QDialog

from . import APP_NAME
from .archive import Archive
from .config import Settings, default_archive_dir, settings_dir
from .ui.dialogs import WelcomeDialog, inform
from .ui.icon import app_icon
from .ui.main_window import MainWindow
from .ui.style import apply_style


def _setup_logging() -> None:
    try:
        folder = settings_dir()
        folder.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(filename=str(folder / "logboek.txt"), level=logging.WARNING,
                            format="%(asctime)s %(levelname)s %(name)s: %(message)s", encoding="utf-8")
    except OSError:
        logging.basicConfig(level=logging.WARNING)


def _open_archive(folder: Path) -> Archive | None:
    try:
        return Archive(folder)
    except Exception as exc:
        logging.exception("Archief openen mislukt")
        inform(None, "Archief openen mislukt",
               f"De archiefmap kon niet worden geopend:\n{folder}\n\n{exc}", error=True)
        return None


def choose_archive(settings: Settings, message: str | None = None, start: Path | None = None) -> Archive | None:
    while True:
        dlg = WelcomeDialog(start or settings.archive_dir or default_archive_dir(), message=message)
        dlg.setWindowIcon(app_icon())
        if dlg.exec() != QDialog.Accepted:
            return None
        archive = _open_archive(dlg.folder)
        if archive:
            settings.archive_dir = dlg.folder
            return archive


def _windows_taskbar_identity() -> None:
    """Zorgt dat Windows de taakbalk toont als 'Mijn Archief' met het eigen
    pictogram, in plaats van als Python."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("MijnArchief.Programma")
    except Exception:
        pass


def main(argv: list[str] | None = None) -> int:
    _setup_logging()
    _windows_taskbar_identity()
    app = QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("MijnArchief")
    app.setWindowIcon(app_icon())
    QLocale.setDefault(QLocale(QLocale.Dutch, QLocale.Netherlands))
    translator = QTranslator(app)
    if translator.load(QLocale(QLocale.Dutch), "qtbase", "_", QLibraryInfo.path(QLibraryInfo.TranslationsPath)):
        app.installTranslator(translator)
    apply_style(app)

    settings = Settings()
    folder = settings.archive_dir
    archive: Archive | None = None
    if folder is None:
        archive = choose_archive(settings)
    elif not (folder / "archief.db").exists():
        archive = choose_archive(
            settings,
            message=(f"Je archiefmap is niet gevonden:<br><b>{folder}</b><br><br>Staat het archief op een "
                     f"USB-stick of externe schijf? Sluit die dan aan en klik op Starten. Je kunt ook een "
                     f"andere map kiezen."),
            start=folder,
        )
    else:
        archive = _open_archive(folder)
        if archive is None:
            archive = choose_archive(settings)
    if archive is None:
        return 0

    holder: dict = {}

    def change_folder() -> None:
        new = choose_archive(settings, message="Kies de map van het archief dat je wilt openen, of een lege "
                                               "map voor een nieuw archief.")
        if new:
            old = holder["window"]
            win = MainWindow(new, change_folder)
            holder["window"] = win
            win.show()
            old.close()

    window = MainWindow(archive, change_folder)
    holder["window"] = window
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
