import logging
import sys

from PySide6.QtWidgets import QMessageBox

from mediacraft.app.logging_config import configure_logging, install_exception_hook


def test_logging_writes_to_rotating_file(tmp_path) -> None:
    log_path = configure_logging(tmp_path)

    logging.getLogger("mediacraft.test").warning("log-file-check")
    for handler in logging.getLogger().handlers:
        handler.flush()

    assert log_path == tmp_path / "mediacraft.log"
    assert "log-file-check" in log_path.read_text(encoding="utf-8")


def test_unhandled_exception_is_logged_and_reported(monkeypatch) -> None:
    reports: list[tuple[object, str, str]] = []
    original_hook = sys.excepthook
    monkeypatch.setattr(
        QMessageBox,
        "critical",
        lambda parent, title, message: reports.append((parent, title, message)),
    )
    try:
        install_exception_hook()
        error = RuntimeError("test-error")
        sys.excepthook(RuntimeError, error, error.__traceback__)
    finally:
        sys.excepthook = original_hook

    assert reports
    assert reports[0][1] == "MediaCraft - エラー"
