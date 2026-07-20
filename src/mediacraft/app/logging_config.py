import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys

from PySide6.QtCore import QStandardPaths
from PySide6.QtWidgets import QMessageBox


LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def configure_logging(directory: Path | None = None) -> Path:
    if directory is None:
        app_data = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppLocalDataLocation
        )
        directory = Path(app_data or Path.cwd()) / "logs"
    directory.mkdir(parents=True, exist_ok=True)
    log_path = directory / "mediacraft.log"

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    formatter = logging.Formatter(LOG_FORMAT)

    for handler in tuple(root.handlers):
        if getattr(handler, "_mediacraft_handler", False):
            root.removeHandler(handler)
            handler.close()

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=2 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler._mediacraft_handler = True
    root.addHandler(file_handler)

    if sys.stderr is not None:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        stream_handler._mediacraft_handler = True
        root.addHandler(stream_handler)

    logging.captureWarnings(True)
    return log_path


def install_exception_hook() -> None:
    def handle_exception(exc_type, value, traceback) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, value, traceback)
            return
        logging.getLogger("mediacraft.unhandled").critical(
            "Unhandled exception",
            exc_info=(exc_type, value, traceback),
        )
        QMessageBox.critical(
            None,
            "MediaCraft - エラー",
            "予期しないエラーが発生しました。\n"
            "詳細はMediaCraftのログファイルへ記録されました。",
        )

    sys.excepthook = handle_exception
