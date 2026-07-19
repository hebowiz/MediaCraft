import logging
from pathlib import Path

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QAction, QCloseEvent, QKeySequence, QShortcut, QShowEvent
from PySide6.QtWidgets import QFileDialog, QMainWindow, QVBoxLayout, QWidget

from mediacraft.app.settings import AppSettings
from mediacraft.player.mpv_backend import MpvBackend
from mediacraft.player.player_backend import PlayerBackend
from mediacraft.player.player_controller import PlayerController
from mediacraft.ui.control_bar import ControlBar
from mediacraft.ui.video_widget import VideoWidget

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self, backend: PlayerBackend | None = None) -> None:
        super().__init__()
        self.setWindowTitle("MediaCraft")
        self.resize(1100, 700)
        self.setMinimumSize(720, 480)

        self._settings = AppSettings()
        self._controller = PlayerController(backend or MpvBackend(), self)
        self._player_initialized = False
        self._shortcuts: list[QShortcut] = []

        self.video_widget = VideoWidget()
        self.control_bar = ControlBar()

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.video_widget, 1)
        layout.addWidget(self.control_bar)
        self.setCentralWidget(central)

        self._create_menu()
        self._connect_signals()
        self._create_shortcuts()
        self._restore_settings()
        self.statusBar().showMessage("ファイルを開くか、動画をドロップしてください。")

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        if not self._player_initialized:
            QTimer.singleShot(0, self._initialize_player)

    def closeEvent(self, event: QCloseEvent) -> None:
        self._save_settings()
        self._controller.shutdown()
        event.accept()

    def open_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "動画ファイルを開く",
            self._settings.last_directory(),
            "メディアファイル (*.mp4 *.mkv *.avi *.mov *.wmv *.webm *.mpeg *.mpg *.mts *.m2ts *.ts *.flv);;すべてのファイル (*)",
        )
        if path:
            self._load_file(path)

    def toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self.showNormal()
            self.control_bar.fullscreen_button.setText("全画面")
        else:
            self.showFullScreen()
            self.control_bar.fullscreen_button.setText("全画面解除")

    def leave_fullscreen(self) -> None:
        if self.isFullScreen():
            self.toggle_fullscreen()

    def _initialize_player(self) -> None:
        if self._player_initialized:
            return
        self._player_initialized = self._controller.initialize(int(self.video_widget.winId()))
        if self._player_initialized:
            self.statusBar().showMessage("再生エンジンを初期化しました。", 3000)

    def _load_file(self, path: str) -> None:
        if not self._player_initialized:
            self._show_error("再生エンジンが利用できないため、ファイルを開けません。")
            return
        if self._controller.load_file(path):
            media_path = Path(path)
            self._settings.set_last_directory(str(media_path.parent))
            self.video_widget.set_media_loaded(True)
            self.setWindowTitle(f"{media_path.name} - MediaCraft")
            self.statusBar().showMessage(str(media_path), 5000)

    def _load_dropped_files(self, paths: list[str]) -> None:
        if paths:
            self._load_file(paths[0])
            if len(paths) > 1:
                self.statusBar().showMessage(
                    "Phase 1では先頭の1ファイルのみ読み込みます。", 5000
                )

    def _create_menu(self) -> None:
        file_menu = self.menuBar().addMenu("ファイル")
        open_action = QAction("開く", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)

        file_menu.addSeparator()
        exit_action = QAction("終了", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        view_menu = self.menuBar().addMenu("表示")
        fullscreen_action = QAction("フルスクリーン", self)
        fullscreen_action.setShortcut(QKeySequence("F"))
        fullscreen_action.triggered.connect(self.toggle_fullscreen)
        view_menu.addAction(fullscreen_action)

    def _connect_signals(self) -> None:
        controls = self.control_bar
        controls.open_requested.connect(self.open_file)
        controls.play_pause_requested.connect(self._controller.toggle_play_pause)
        controls.stop_requested.connect(self._controller.stop)
        controls.seek_requested.connect(self._controller.seek_absolute)
        controls.volume_requested.connect(self._controller.set_volume)
        controls.mute_requested.connect(self._controller.toggle_mute)
        controls.speed_requested.connect(self._controller.set_speed)
        controls.fullscreen_requested.connect(self.toggle_fullscreen)

        self.video_widget.files_dropped.connect(self._load_dropped_files)
        self.video_widget.clicked.connect(self._controller.toggle_play_pause)
        self.video_widget.double_clicked.connect(self.toggle_fullscreen)
        self.video_widget.volume_wheel.connect(
            lambda steps: self._controller.adjust_volume(steps * 5)
        )
        self.video_widget.speed_wheel.connect(
            lambda steps: self._controller.adjust_speed(steps * 0.05)
        )

        self._controller.position_changed.connect(controls.set_position)
        self._controller.playback_changed.connect(controls.set_playing)
        self._controller.volume_changed.connect(controls.set_volume)
        self._controller.speed_changed.connect(controls.set_speed)
        self._controller.error_occurred.connect(self._show_error)

    def _create_shortcuts(self) -> None:
        bindings = (
            ("Space", self._controller.toggle_play_pause),
            ("Return", self._controller.toggle_play_pause),
            ("S", self._controller.stop),
            ("Left", lambda: self._controller.seek_relative(-5)),
            ("Right", lambda: self._controller.seek_relative(5)),
            ("Shift+Left", lambda: self._controller.seek_relative(-30)),
            ("Shift+Right", lambda: self._controller.seek_relative(30)),
            ("M", self._controller.toggle_mute),
            ("Up", lambda: self._controller.adjust_volume(5)),
            ("Down", lambda: self._controller.adjust_volume(-5)),
            ("[", lambda: self._controller.adjust_speed(-0.05)),
            ("]", lambda: self._controller.adjust_speed(0.05)),
            ("Backspace", lambda: self._controller.set_speed(1.0)),
            ("Escape", self.leave_fullscreen),
        )
        for key, callback in bindings:
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
            shortcut.activated.connect(callback)
            self._shortcuts.append(shortcut)

    def _restore_settings(self) -> None:
        geometry = self._settings.window_geometry()
        if not geometry.isEmpty():
            self.restoreGeometry(geometry)
        self._controller.set_volume(self._settings.volume())
        self._controller.set_mute(self._settings.muted())
        self._controller.set_speed(self._settings.speed())

    def _save_settings(self) -> None:
        self._settings.set_window_geometry(self.saveGeometry())
        self._settings.set_volume(self._controller.volume)
        self._settings.set_muted(self._controller.muted)
        self._settings.set_speed(self._controller.speed)

    def _show_error(self, message: str) -> None:
        logger.error(message)
        self.statusBar().showMessage(message, 10_000)
