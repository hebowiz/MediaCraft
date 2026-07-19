import logging
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QTimer, Qt
from PySide6.QtGui import QAction, QCloseEvent, QKeySequence, QResizeEvent, QShortcut, QShowEvent
from PySide6.QtWidgets import QApplication, QFileDialog, QMainWindow, QVBoxLayout, QWidget

from mediacraft.app.settings import AppSettings
from mediacraft.frame.frame_controller import FrameController
from mediacraft.frame.media_probe import MediaProbe
from mediacraft.player.mpv_backend import MpvBackend
from mediacraft.player.player_backend import PlayerBackend
from mediacraft.player.player_controller import PlayerController
from mediacraft.ui.control_bar import ControlBar
from mediacraft.ui.fullscreen_overlay import FullscreenOverlay
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
        self._frame_controller = FrameController(self._controller, self)
        self._media_probe = MediaProbe(self)
        self._player_initialized = False
        self._playback_active = False
        self._shortcuts: list[QShortcut] = []

        self.video_widget = VideoWidget()
        self.control_bar = ControlBar()

        central = QWidget()
        self._main_layout = QVBoxLayout(central)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)
        self._main_layout.addWidget(self.video_widget, 1)
        self._main_layout.addWidget(self.control_bar)
        self.setCentralWidget(central)

        self._fullscreen_overlay = FullscreenOverlay(self)
        self._overlay_hide_timer = QTimer(self)
        self._overlay_hide_timer.setSingleShot(True)
        self._overlay_hide_timer.setInterval(2000)
        self._overlay_hide_timer.timeout.connect(self._hide_fullscreen_overlay)

        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

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
        app = QApplication.instance()
        if app is not None:
            app.removeEventFilter(self)
        self._overlay_hide_timer.stop()
        self._fullscreen_overlay.hide()
        self._save_settings()
        self._media_probe.shutdown()
        self._controller.shutdown()
        event.accept()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if self.isFullScreen() and self._fullscreen_overlay.isVisible():
            self._fullscreen_overlay.update_position(self)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        mouse_events = {
            QEvent.Type.MouseMove,
            QEvent.Type.MouseButtonPress,
            QEvent.Type.MouseButtonDblClick,
            QEvent.Type.Wheel,
        }
        if self.isFullScreen() and event.type() in mouse_events:
            self._show_fullscreen_overlay()
        return super().eventFilter(watched, event)

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
            self._leave_fullscreen()
        else:
            self._enter_fullscreen()

    def leave_fullscreen(self) -> None:
        if self.isFullScreen():
            self._leave_fullscreen()

    def _enter_fullscreen(self) -> None:
        self._main_layout.removeWidget(self.control_bar)
        self._fullscreen_overlay.attach_control_bar(self.control_bar)
        self.menuBar().hide()
        self.statusBar().hide()
        self.showFullScreen()
        self.control_bar.set_fullscreen(True)
        QTimer.singleShot(0, self._show_fullscreen_overlay)

    def _leave_fullscreen(self) -> None:
        self._overlay_hide_timer.stop()
        self._fullscreen_overlay.hide()
        control_bar = self._fullscreen_overlay.detach_control_bar()
        if control_bar is not None:
            self._main_layout.addWidget(control_bar)
        self.menuBar().show()
        self.statusBar().show()
        self.showNormal()
        self.control_bar.set_fullscreen(False)

    def _show_fullscreen_overlay(self) -> None:
        if not self.isFullScreen():
            return
        self._fullscreen_overlay.update_position(self)
        self._fullscreen_overlay.show()
        self._fullscreen_overlay.raise_()
        if self._playback_active:
            self._overlay_hide_timer.start()
        else:
            self._overlay_hide_timer.stop()

    def _hide_fullscreen_overlay(self) -> None:
        if self.isFullScreen() and self._playback_active:
            self._fullscreen_overlay.hide()

    def _on_playback_changed(self, playing: bool) -> None:
        self._playback_active = playing
        if not self.isFullScreen():
            return
        if playing:
            self._overlay_hide_timer.start()
        else:
            self._show_fullscreen_overlay()

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
        self.frame_inspection_action = QAction("フレーム確認モード", self)
        self.frame_inspection_action.setCheckable(True)
        self.frame_inspection_action.setEnabled(False)
        self.frame_inspection_action.setShortcut(QKeySequence("I"))
        self.frame_inspection_action.setShortcutContext(
            Qt.ShortcutContext.ApplicationShortcut
        )
        self.frame_inspection_action.triggered.connect(
            self._frame_controller.set_inspection_mode
        )
        view_menu.addAction(self.frame_inspection_action)
        view_menu.addSeparator()

        fullscreen_action = QAction("フルスクリーン", self)
        fullscreen_action.setShortcut(QKeySequence("F"))
        fullscreen_action.triggered.connect(self.toggle_fullscreen)
        view_menu.addAction(fullscreen_action)

    def _connect_signals(self) -> None:
        controls = self.control_bar
        controls.play_pause_requested.connect(self._controller.toggle_play_pause)
        controls.stop_requested.connect(self._controller.stop)
        controls.frame_back_requested.connect(lambda: self._frame_controller.request_step(-1))
        controls.frame_forward_requested.connect(lambda: self._frame_controller.request_step(1))
        controls.frame_mode_requested.connect(self._frame_controller.toggle_inspection_mode)
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
        self._controller.playback_changed.connect(self._on_playback_changed)
        self._controller.volume_changed.connect(controls.set_volume)
        self._controller.speed_changed.connect(controls.set_speed)
        self._controller.file_changed.connect(self._media_probe.probe)
        self._controller.file_changed.connect(
            lambda _path: self.frame_inspection_action.setEnabled(True)
        )
        self._controller.error_occurred.connect(self._show_error)
        self._frame_controller.inspection_mode_changed.connect(controls.set_frame_inspection)
        self._frame_controller.inspection_mode_changed.connect(
            self.frame_inspection_action.setChecked
        )
        self._frame_controller.frame_display_changed.connect(controls.set_frame_info)
        self._media_probe.analysis_ready.connect(self._on_media_analysis)

    def _create_shortcuts(self) -> None:
        bindings = (
            ("Space", self._controller.toggle_play_pause),
            ("Return", self._controller.toggle_play_pause),
            ("S", self._controller.stop),
            ("Left", lambda: self._seek_or_step(-1, -5)),
            ("Right", lambda: self._seek_or_step(1, 5)),
            ("Shift+Left", lambda: self._seek_or_step(-10, -30)),
            ("Shift+Right", lambda: self._seek_or_step(10, 30)),
            ("Ctrl+Left", lambda: self._inspection_step(-100)),
            ("Ctrl+Right", lambda: self._inspection_step(100)),
            (",", lambda: self._frame_controller.request_step(-1)),
            (".", lambda: self._frame_controller.request_step(1)),
            ("M", self._controller.toggle_mute),
            ("Up", lambda: self._controller.adjust_volume(5)),
            ("Down", lambda: self._controller.adjust_volume(-5)),
            ("[", lambda: self._controller.adjust_speed(-0.05)),
            ("]", lambda: self._controller.adjust_speed(0.05)),
            ("Backspace", lambda: self._controller.set_speed(1.0)),
            ("Escape", self._handle_escape),
        )
        for key, callback in bindings:
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
            shortcut.activated.connect(callback)
            self._shortcuts.append(shortcut)

    def _seek_or_step(self, frame_count: int, seconds: float) -> None:
        if self._frame_controller.inspection_mode:
            self._frame_controller.request_step(frame_count)
        else:
            self._controller.seek_relative(seconds)

    def _inspection_step(self, frame_count: int) -> None:
        if self._frame_controller.inspection_mode:
            self._frame_controller.request_step(frame_count)

    def _handle_escape(self) -> None:
        if self._frame_controller.inspection_mode:
            self._frame_controller.set_inspection_mode(False)
        else:
            self.leave_fullscreen()

    def _on_media_analysis(self, path: str, fps: float, variable: object) -> None:
        current_file = self._controller.current_file
        if current_file is None or Path(path).resolve() != current_file:
            return
        variable_rate = variable if isinstance(variable, bool) else None
        self._frame_controller.set_frame_rate_analysis(fps, variable_rate)

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
