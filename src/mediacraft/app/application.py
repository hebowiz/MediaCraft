import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from mediacraft.app.logging_config import configure_logging, install_exception_hook
from mediacraft.app.single_instance import SingleInstance, command_line_paths
from mediacraft.ui.main_window import MainWindow


DARK_STYLESHEET = """
QWidget {
    background-color: #181a1f;
    color: #e8e8e8;
    font-size: 13px;
}
QMainWindow, QMenuBar, QMenu, QStatusBar {
    background-color: #20232a;
}
#videoWidget {
    background-color: #08090b;
    border: none;
}
QPushButton, QComboBox {
    background-color: #30343d;
    border: 1px solid #454b57;
    border-radius: 4px;
    padding: 5px 9px;
}
QPushButton:hover, QComboBox:hover {
    background-color: #3a404b;
}
QPushButton:pressed {
    background-color: #4776a8;
}
QPushButton:checked {
    background-color: #4776a8;
    border-color: #6ca6dc;
}
QSlider::groove:horizontal {
    background: #3a3f49;
    height: 5px;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #6ca6dc;
    width: 14px;
    margin: -5px 0;
    border-radius: 7px;
}
QSlider::sub-page:horizontal {
    background: #477eae;
}
"""

APP_ICON_PATH = Path(__file__).resolve().parents[1] / "assets" / "mediacraft.ico"


def create_application(argv: list[str] | None = None) -> QApplication:
    app = QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName("MediaCraft")
    app.setApplicationDisplayName("MediaCraft")
    app.setOrganizationName("MediaCraft")
    app.setWindowIcon(QIcon(str(APP_ICON_PATH)))
    app.setStyle("Fusion")
    app.setStyleSheet(DARK_STYLESHEET)
    return app


def run(argv: list[str] | None = None) -> int:
    actual_argv = argv if argv is not None else sys.argv
    app = create_application(actual_argv)
    configure_logging()
    install_exception_hook()
    startup_paths = command_line_paths(actual_argv[1:])
    single_instance = SingleInstance(app)
    if not single_instance.acquire_or_notify(startup_paths):
        return 0
    window = MainWindow()
    single_instance.paths_received.connect(window.open_paths_from_shell)
    window.show()
    if startup_paths:
        window.open_paths_from_shell(startup_paths)
    return app.exec()
