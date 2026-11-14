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
from .ui.dialogs import UNREACHABLE, WelcomeDialog, ask, inform
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


NOT_FOUND = ("Je archief is niet gevonden:<br><b>{folder}</b><br><br>Staat het archief op je Raspberry Pi, "
             "een USB-stick of externe schijf? Controleer of die aanstaat en verbonden is, en klik dan op "
             "<b>Opnieuw proberen</b>. Je kunt ook een andere map kiezen.")


def _claim(archive: Archive) -> bool:
    """Controleert of het archief niet al op een andere computer open is."""
    owner = archive.lock_owner()
    if owner and not ask(
            None, "Archief is al in gebruik",
            f"Dit archief is geopend op de computer “{owner.get('computer', 'onbekend')}”.\n\n"
            f"Gebruik het archief op één computer tegelijk, anders kunnen wijzigingen verloren gaan. "
            f"Sluit Mijn Archief eerst op die computer.\n\n"
            f"Is die computer uit of vastgelopen? Dan kun je het archief toch openen.",
            "Toch openen", "Annuleren", danger=True):
        archive.conn.close()
        return False
    archive.acquire_lock()
    return True


def _open_archive(folder: Path) -> Archive | None:
    try:
        archive = Archive(folder)
    except Exception as exc:
        logging.exception("Archief openen mislukt")
        inform(None, "Archief openen mislukt",
               f"De archiefmap kon niet worden geopend:\n{folder}\n\n{exc}", error=True)
        return None
    return archive if _claim(archive) else None


def choose_archive(settings: Settings, message: str | None = None, start: Path | None = None,
                   ok_text: str = "Starten") -> Archive | None:
    while True:
        dlg = WelcomeDialog(start or settings.archive_dir or default_archive_dir(), message=message,
                            ok_text=ok_text)
        dlg.setWindowIcon(app_icon())
        if dlg.exec() != QDialog.Accepted:
            return None
        archive = _open_archive(dlg.folder)
        if archive:
            settings.archive_dir = dlg.folder
            return archive
        start = dlg.folder


def _install_error_handler() -> None:
    """Toont een begrijpelijke melding in plaats van te crashen, bijvoorbeeld als
    de Raspberry Pi tijdens het werken onbereikbaar wordt."""
    import sqlite3

    def handler(exc_type, exc, tb):
        logging.error("Onverwachte fout", exc_info=(exc_type, exc, tb))
        if issubclass(exc_type, (sqlite3.Error, OSError)):
            text = UNREACHABLE
        else:
            text = f"Er ging iets mis: {exc}\n\nDe details staan in het logboek:\n{settings_dir() / 'logboek.txt'}"
        try:
            inform(QApplication.activeWindow(), "Er ging iets mis", text, error=True)
        except Exception:
            pass

    sys.excepthook = handler


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

    _install_error_handler()
    settings = Settings()
    folder = settings.archive_dir
    archive: Archive | None = None
    if folder is None:
        archive = choose_archive(settings)
    elif not (folder / "archief.db").exists():
        archive = choose_archive(settings, message=NOT_FOUND.format(folder=folder), start=folder,
                                 ok_text="Opnieuw proberen")
    else:
        archive = _open_archive(folder)
        if archive is None:
            archive = choose_archive(settings)
    if archive is None:
        return 0

    holder: dict = {}

    def show(new: Archive) -> None:
        old = holder.get("window")
        win = MainWindow(new, change_folder, switch_to)
        holder["window"] = win
        win.show()
        if old:
            old.close()

    def change_folder() -> None:
        new = choose_archive(settings, message="Kies de map van het archief dat je wilt openen, of een lege "
                                               "map voor een nieuw archief. Dat kan ook een gedeelde map op je "
                                               "Raspberry Pi zijn.", ok_text="Openen")
        if new:
            show(new)

    def switch_to(folder: Path) -> bool:
        new = _open_archive(folder)
        if not new:
            return False
        settings.archive_dir = folder
        show(new)
        return True

    show(archive)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
