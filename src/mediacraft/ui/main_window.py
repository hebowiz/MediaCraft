import logging
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QPoint, QSignalBlocker, QTimer, Qt
from PySide6.QtGui import (
    QAction,
    QCloseEvent,
    QDragEnterEvent,
    QDropEvent,
    QImage,
    QKeySequence,
    QResizeEvent,
    QShortcut,
    QShowEvent,
)
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QMainWindow,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from mediacraft.app.settings import AppSettings
from mediacraft.frame.frame_controller import FrameController
from mediacraft.frame.media_probe import MediaProbe
from mediacraft.player.adaptive_backend import AdaptiveBackend
from mediacraft.player.player_backend import PlayerBackend
from mediacraft.player.player_controller import PlayerController
from mediacraft.player.playback_state import PlaybackState
from mediacraft.playlist.playlist_controller import PlaylistController
from mediacraft.playlist.metadata_probe import PlaylistMetadataProbe
from mediacraft.repeat.ab_repeat_controller import ABRepeatController
from mediacraft.screenshot.file_naming import build_screenshot_path
from mediacraft.thumbnail.thumbnail_provider import ThumbnailProvider
from mediacraft.ui.control_bar import ControlBar
from mediacraft.ui.fullscreen_overlay import FullscreenOverlay
from mediacraft.ui.playlist_panel import PlaylistPanel
from mediacraft.ui.settings_dialog import SettingsDialog
from mediacraft.ui.shortcut_dialog import ShortcutDialog, ShortcutHelpEntry
from mediacraft.ui.thumbnail_preview import ThumbnailPreview
from mediacraft.ui.toast_notification import ToastNotification
from mediacraft.ui.video_widget import VideoWidget
from mediacraft.utils.drop_paths import local_drop_paths

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    MEDIA_FILTER = (
        "メディアファイル (*.mp4 *.mkv *.avi *.mov *.wmv *.webm *.mpeg *.mpg "
        "*.mts *.m2ts *.ts *.flv);;すべてのファイル (*)"
    )
    MEDIA_EXTENSIONS = {
        ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".webm", ".mpeg", ".mpg",
        ".mts", ".m2ts", ".ts", ".flv",
    }

    def __init__(self, backend: PlayerBackend | None = None) -> None:
        super().__init__()
        self.setWindowTitle("MediaCraft")
        self.setAcceptDrops(True)
        self.resize(1100, 700)
        self.setMinimumSize(720, 480)

        self._settings = AppSettings()
        self.video_widget = VideoWidget()
        selected_backend = backend or AdaptiveBackend(self.video_widget.windows_media_control)
        self._controller = PlayerController(selected_backend, self)
        self._frame_controller = FrameController(self._controller, self)
        self._playlist_controller = PlaylistController(self)
        self._ab_repeat_controller = ABRepeatController(self._controller, self)
        self._playlist_metadata_probe = PlaylistMetadataProbe(self)
        self._media_probe = MediaProbe(self)
        self._thumbnail_provider = ThumbnailProvider(self)
        self._player_initialized = False
        self._playback_active = False
        self._shortcuts: list[QShortcut] = []
        self._shortcut_by_key: dict[str, QShortcut] = {}
        self._shortcut_help_entries: list[ShortcutHelpEntry] = []
        self._playlist_was_visible = True
        self._thumbnail_hover_time = 0.0
        self._thumbnail_hover_position: QPoint | None = None
        self._thumbnail_request_key: int | None = None
        self._media_fps = 0.0
        self._media_variable_rate: bool | None = None
        self._thumbnail_preload_enabled = self._settings.thumbnail_preload_enabled()

        self.control_bar = ControlBar()
        self.playlist_panel = PlaylistPanel()
        self.playlist_panel.setMinimumWidth(250)

        self._content_splitter = QSplitter(Qt.Orientation.Horizontal)
        self._content_splitter.setChildrenCollapsible(False)
        self._content_splitter.addWidget(self.video_widget)
        self._content_splitter.addWidget(self.playlist_panel)
        self._content_splitter.setStretchFactor(0, 1)
        self._content_splitter.setStretchFactor(1, 0)
        self._content_splitter.setSizes([820, 280])

        central = QWidget()
        self._main_layout = QVBoxLayout(central)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)
        self._main_layout.addWidget(self._content_splitter, 1)
        self._main_layout.addWidget(self.control_bar)
        self.setCentralWidget(central)

        self._fullscreen_overlay = FullscreenOverlay(self)
        self._toast = ToastNotification(self)
        self._thumbnail_preview = ThumbnailPreview()
        self._thumbnail_timer = QTimer(self)
        self._thumbnail_timer.setSingleShot(True)
        self._thumbnail_timer.setInterval(50)
        self._thumbnail_timer.timeout.connect(self._request_thumbnail)
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
        self._thumbnail_timer.stop()
        self._thumbnail_preview.close()
        self._fullscreen_overlay.hide()
        self._set_fullscreen_cursor_hidden(False)
        self._toast.stop()
        self._save_settings()
        self._media_probe.shutdown()
        self._thumbnail_provider.shutdown()
        self._playlist_metadata_probe.shutdown()
        self._controller.shutdown()
        event.accept()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if self.isFullScreen() and self._fullscreen_overlay.isVisible():
            self._fullscreen_overlay.update_position(self)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if local_drop_paths(event.mimeData()):
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        paths = local_drop_paths(event.mimeData())
        if paths:
            self._replace_playlist_from_drop(paths)
            event.acceptProposedAction()
            return
        super().dropEvent(event)

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

    def open_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "ファイルを開く",
            self._settings.last_directory(),
            self.MEDIA_FILTER,
        )
        if paths:
            self._add_paths(paths, play_first=True, replace=True)

    def add_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "動画ファイルをプレイリストへ追加",
            self._settings.last_directory(),
            self.MEDIA_FILTER,
        )
        if paths:
            self._add_paths(paths, play_first=self._controller.current_file is None)

    def add_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self,
            "動画フォルダをプレイリストへ追加",
            self._settings.last_directory(),
        )
        if path:
            self._add_paths([path], play_first=self._controller.current_file is None)

    def take_screenshot(self) -> None:
        media_path = self._controller.current_file
        if media_path is None:
            return
        directory_text = self._settings.screenshot_directory()
        directory = Path(directory_text) if directory_text else media_path.parent / "MediaCraft"
        try:
            directory.mkdir(parents=True, exist_ok=True)
            output_path = build_screenshot_path(
                directory,
                media_path,
                self._controller.frame_number,
                self._settings.screenshot_format(),
            )
        except (OSError, ValueError) as exc:
            self._show_error(f"スクリーンショットの保存先を準備できませんでした: {exc}")
            return

        if not self._controller.save_screenshot(output_path, include_subtitles=False):
            return
        logger.info("Screenshot requested: %s", output_path)
        self._show_toast(f"スクリーンショットを保存しました\n{output_path.name}")

    def toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self._leave_fullscreen()
        else:
            self._enter_fullscreen()

    def leave_fullscreen(self) -> None:
        if self.isFullScreen():
            self._leave_fullscreen()

    def _enter_fullscreen(self) -> None:
        self._playlist_was_visible = self.playlist_panel.isVisible()
        self._set_playlist_toggle_enabled(False)
        self.playlist_panel.hide()
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
        self._set_fullscreen_cursor_hidden(False)
        control_bar = self._fullscreen_overlay.detach_control_bar()
        if control_bar is not None:
            self._main_layout.addWidget(control_bar)
        self.menuBar().show()
        self.statusBar().show()
        self.showNormal()
        if self._playlist_was_visible:
            self.playlist_panel.show()
        self._set_playlist_toggle_enabled(True)
        self.control_bar.set_fullscreen(False)

    def _show_fullscreen_overlay(self) -> None:
        if not self.isFullScreen():
            return
        self._set_fullscreen_cursor_hidden(False)
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
            self._set_fullscreen_cursor_hidden(True)

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
        self._playlist_controller.add_files([path])
        requested_index = self._playlist_controller.index_for_path(path)
        if self._controller.load_file(path):
            media_path = Path(path)
            self._settings.set_last_directory(str(media_path.parent))
            self.video_widget.set_media_loaded(True)
            self.setWindowTitle(f"{media_path.name} - MediaCraft")
            self.statusBar().showMessage(str(media_path), 5000)
        elif requested_index + 1 < len(self._playlist_controller.entries):
            QTimer.singleShot(
                0,
                lambda index=requested_index + 1: self._playlist_controller.request_play(index),
            )

    def _load_dropped_files(self, paths: list[str]) -> None:
        if paths:
            self._replace_playlist_from_drop(paths)

    def _replace_playlist_from_drop(self, paths: list[str]) -> None:
        self._add_paths(paths, play_first=True, replace=True)

    def _append_playlist_from_drop(self, paths: list[str]) -> None:
        self._add_paths(paths, play_first=False)

    def _add_paths(
        self,
        paths: list[str],
        *,
        play_first: bool,
        replace: bool = False,
    ) -> None:
        files: list[Path] = []
        for value in paths:
            path = Path(value).expanduser().resolve()
            if path.is_file():
                files.append(path)
            elif path.is_dir():
                files.extend(
                    sorted(
                        (
                            child
                            for child in path.iterdir()
                            if child.is_file() and child.suffix.lower() in self.MEDIA_EXTENSIONS
                        ),
                        key=lambda child: child.name.casefold(),
                    )
                )
        if replace and files:
            self._playlist_controller.clear()
        first_added = self._playlist_controller.add_files(files)
        if files:
            self._settings.set_last_directory(str(files[0].parent))
        if files and play_first:
            self._playlist_controller.request_play(
                self._playlist_controller.index_for_path(files[0])
            )
        elif first_added >= 0:
            self.statusBar().showMessage(f"{len(files)}件をプレイリストへ追加しました。", 3000)

    def _create_menu(self) -> None:
        file_menu = self.menuBar().addMenu("ファイル")
        open_action = QAction("ファイルを開く\tCtrl+O", self)
        open_action.triggered.connect(self.open_files)
        file_menu.addAction(open_action)

        add_folder_action = QAction("フォルダを追加", self)
        add_folder_action.triggered.connect(self.add_folder)
        file_menu.addAction(add_folder_action)

        file_menu.addSeparator()
        self.screenshot_action = QAction("スクリーンショットを保存\tCtrl+S", self)
        self.screenshot_action.setEnabled(False)
        self.screenshot_action.triggered.connect(self.take_screenshot)
        file_menu.addAction(self.screenshot_action)

        file_menu.addSeparator()
        exit_action = QAction("終了", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        settings_menu = self.menuBar().addMenu("設定")
        preferences_action = QAction("MediaCraftの設定...", self)
        preferences_action.triggered.connect(self.open_settings)
        settings_menu.addAction(preferences_action)

        playback_menu = self.menuBar().addMenu("再生")
        self.set_a_action = QAction("A点を設定\tA", self)
        self.set_a_action.triggered.connect(self._ab_repeat_controller.set_point_a)
        playback_menu.addAction(self.set_a_action)

        self.set_b_action = QAction("B点を設定\tB", self)
        self.set_b_action.triggered.connect(self._ab_repeat_controller.set_point_b)
        playback_menu.addAction(self.set_b_action)

        self.ab_repeat_action = QAction("A-Bリピート\tR", self)
        self.ab_repeat_action.setCheckable(True)
        self.ab_repeat_action.triggered.connect(self._ab_repeat_controller.set_enabled)
        playback_menu.addAction(self.ab_repeat_action)

        playback_menu.addSeparator()
        self.seek_a_action = QAction("A点へ移動", self)
        self.seek_a_action.triggered.connect(self._ab_repeat_controller.seek_to_a)
        playback_menu.addAction(self.seek_a_action)

        self.seek_b_action = QAction("B点へ移動", self)
        self.seek_b_action.triggered.connect(self._ab_repeat_controller.seek_to_b)
        playback_menu.addAction(self.seek_b_action)

        playback_menu.addSeparator()
        self.clear_a_action = QAction("A点を解除\tShift+A", self)
        self.clear_a_action.triggered.connect(self._ab_repeat_controller.clear_point_a)
        playback_menu.addAction(self.clear_a_action)
        self.clear_b_action = QAction("B点を解除\tShift+B", self)
        self.clear_b_action.triggered.connect(self._ab_repeat_controller.clear_point_b)
        playback_menu.addAction(self.clear_b_action)
        clear_ab_action = QAction("A-B設定をすべて解除", self)
        clear_ab_action.triggered.connect(self._ab_repeat_controller.clear)
        playback_menu.addAction(clear_ab_action)

        self._ab_media_actions = (
            self.set_a_action,
            self.set_b_action,
            self.ab_repeat_action,
            self.seek_a_action,
            self.seek_b_action,
            self.clear_a_action,
            self.clear_b_action,
            clear_ab_action,
        )
        for action in self._ab_media_actions:
            action.setEnabled(False)

        view_menu = self.menuBar().addMenu("表示")
        self.playlist_action = QAction("プレイリスト\tCtrl+L", self)
        self.playlist_action.setCheckable(True)
        self.playlist_action.setChecked(True)
        self.playlist_action.triggered.connect(self._set_playlist_visible)
        view_menu.addAction(self.playlist_action)
        view_menu.addSeparator()

        self.frame_inspection_action = QAction("フレーム確認モード\tI", self)
        self.frame_inspection_action.setCheckable(True)
        self.frame_inspection_action.setEnabled(False)
        self.frame_inspection_action.triggered.connect(
            self._frame_controller.set_inspection_mode
        )
        view_menu.addAction(self.frame_inspection_action)
        view_menu.addSeparator()

        self.fullscreen_action = QAction("フルスクリーン\tF", self)
        self.fullscreen_action.triggered.connect(self.toggle_fullscreen)
        view_menu.addAction(self.fullscreen_action)

        help_menu = self.menuBar().addMenu("ヘルプ")
        self.shortcut_help_action = QAction("キーボードショートカット...", self)
        self.shortcut_help_action.triggered.connect(self.show_shortcut_help)
        help_menu.addAction(self.shortcut_help_action)

    def _connect_signals(self) -> None:
        controls = self.control_bar
        controls.previous_requested.connect(self._play_previous)
        controls.play_pause_requested.connect(self._play_selected_or_toggle)
        controls.stop_requested.connect(self._controller.stop)
        controls.next_requested.connect(self._play_next)
        controls.shuffle_requested.connect(self._playlist_controller.toggle_shuffle)
        controls.repeat_requested.connect(self._playlist_controller.cycle_repeat_mode)
        controls.frame_back_requested.connect(lambda: self._frame_controller.request_step(-1))
        controls.frame_forward_requested.connect(lambda: self._frame_controller.request_step(1))
        controls.seek_requested.connect(self._controller.seek_absolute)
        controls.volume_requested.connect(self._controller.set_volume)
        controls.mute_requested.connect(self._controller.toggle_mute)
        controls.speed_requested.connect(self._controller.set_speed)
        controls.fullscreen_requested.connect(self.toggle_fullscreen)
        controls.seek_hovered.connect(self._on_seek_hovered)
        controls.seek_hover_left.connect(self._hide_thumbnail_preview)

        self.video_widget.files_dropped.connect(self._load_dropped_files)
        self.video_widget.clicked.connect(self._controller.toggle_play_pause)
        self.video_widget.double_clicked.connect(self.toggle_fullscreen)
        self.video_widget.volume_wheel.connect(
            lambda steps: self._controller.adjust_volume(steps * 5)
        )
        self.video_widget.speed_wheel.connect(
            lambda steps: self._controller.adjust_speed(steps * 0.05)
        )

        self.playlist_panel.add_files_requested.connect(self.add_files)
        self.playlist_panel.add_folder_requested.connect(self.add_folder)
        self.playlist_panel.remove_requested.connect(self._playlist_controller.remove_indices)
        self.playlist_panel.clear_requested.connect(self._playlist_controller.clear)
        self.playlist_panel.play_requested.connect(self._playlist_controller.request_play)
        self.playlist_panel.order_changed.connect(self._playlist_controller.reorder)
        self.playlist_panel.files_dropped.connect(self._append_playlist_from_drop)
        self._playlist_controller.play_requested.connect(self._load_file)
        self._playlist_controller.playlist_changed.connect(self.playlist_panel.set_entries)
        self._playlist_controller.playlist_changed.connect(self._probe_playlist_metadata)
        self._playlist_controller.current_index_changed.connect(
            self.playlist_panel.set_current_index
        )
        self._playlist_controller.current_item_removed.connect(
            self._on_current_playlist_item_removed
        )
        self._playlist_controller.cleared.connect(self._reset_media_view)
        self._playlist_controller.shuffle_changed.connect(controls.set_shuffle)
        self._playlist_controller.repeat_mode_changed.connect(controls.set_repeat_mode)
        self._playlist_metadata_probe.duration_ready.connect(
            self._playlist_controller.update_duration
        )

        self._controller.position_changed.connect(controls.set_position)
        self._controller.position_changed.connect(self._start_thumbnail_preload)
        self._controller.position_changed.connect(
            lambda _position, duration: self._playlist_controller.update_current_duration(duration)
        )
        self._controller.playback_changed.connect(self._on_playback_changed)
        self._controller.state_changed.connect(self._sync_playback_icon)
        self._controller.volume_changed.connect(controls.set_volume)
        self._controller.speed_changed.connect(controls.set_speed)
        self._controller.file_changed.connect(self._media_probe.probe)
        self._controller.file_changed.connect(self._on_thumbnail_media_changed)
        self._controller.file_changed.connect(self._playlist_controller.set_current_path)
        self._controller.file_changed.connect(
            lambda _path: self.frame_inspection_action.setEnabled(True)
        )
        self._controller.file_changed.connect(
            lambda _path: self._set_ab_actions_enabled(True)
        )
        self._controller.file_changed.connect(
            lambda _path: self.screenshot_action.setEnabled(True)
        )
        self._controller.error_occurred.connect(self._show_error)
        self._controller.media_ended.connect(self._on_media_ended)
        self._frame_controller.inspection_mode_changed.connect(controls.set_frame_inspection)
        self._frame_controller.inspection_mode_changed.connect(
            self.frame_inspection_action.setChecked
        )
        self._frame_controller.frame_display_changed.connect(controls.set_frame_info)
        self._media_probe.analysis_ready.connect(self._on_media_analysis)
        self._thumbnail_provider.thumbnail_ready.connect(self._on_thumbnail_ready)
        self._thumbnail_provider.coarse_thumbnail_ready.connect(
            self._on_coarse_thumbnail_ready
        )
        self._ab_repeat_controller.state_changed.connect(self._sync_ab_repeat_ui)
        self._ab_repeat_controller.message.connect(
            lambda message: self.statusBar().showMessage(message, 4000)
        )

    def _create_shortcuts(self) -> None:
        bindings = (
            ("ファイル・表示", "Ctrl+O", "ファイルを開く", "同じ", self.open_files),
            ("ファイル・表示", "Ctrl+S", "現在フレームを保存", "同じ", self.take_screenshot),
            ("ファイル・表示", "Ctrl+L", "プレイリスト表示切り替え", "同じ", self.playlist_action.trigger),
            ("ファイル・表示", "F", "フルスクリーン切り替え", "同じ", self.fullscreen_action.trigger),
            ("ファイル・表示", "Esc", "フルスクリーン解除", "確認モード解除", self._handle_escape),
            ("再生", "Space", "再生／一時停止", "同じ", self._controller.toggle_play_pause),
            ("再生", "Return", "選択項目を再生／一時停止", "同じ", self._play_selected_or_toggle),
            ("再生", "S", "停止して先頭へ戻る", "同じ", self._controller.stop),
            ("再生", "PgUp", "前のファイル", "同じ", self._play_previous),
            ("再生", "PgDown", "次のファイル", "同じ", self._play_next),
            ("シーク・フレーム", "Left", "5秒戻る", "1フレーム戻る", lambda: self._seek_or_step(-1, -5)),
            ("シーク・フレーム", "Right", "5秒進む", "1フレーム進む", lambda: self._seek_or_step(1, 5)),
            ("シーク・フレーム", "Shift+Left", "30秒戻る", "10フレーム戻る", lambda: self._seek_or_step(-10, -30)),
            ("シーク・フレーム", "Shift+Right", "30秒進む", "10フレーム進む", lambda: self._seek_or_step(10, 30)),
            ("シーク・フレーム", "Ctrl+Left", "—", "100フレーム戻る", lambda: self._inspection_step(-100)),
            ("シーク・フレーム", "Ctrl+Right", "—", "100フレーム進む", lambda: self._inspection_step(100)),
            ("シーク・フレーム", ",", "1フレーム戻る", "同じ", lambda: self._frame_controller.request_step(-1)),
            ("シーク・フレーム", ".", "1フレーム進む", "同じ", lambda: self._frame_controller.request_step(1)),
            ("シーク・フレーム", "I", "確認モード切り替え", "確認モード解除", self.frame_inspection_action.trigger),
            ("音量・速度", "M", "ミュート切り替え", "同じ", self._controller.toggle_mute),
            ("音量・速度", "Up", "音量を5%上げる", "同じ", lambda: self._controller.adjust_volume(5)),
            ("音量・速度", "Down", "音量を5%下げる", "同じ", lambda: self._controller.adjust_volume(-5)),
            ("音量・速度", "[", "再生速度を0.05x下げる", "同じ", lambda: self._controller.adjust_speed(-0.05)),
            ("音量・速度", "]", "再生速度を0.05x上げる", "同じ", lambda: self._controller.adjust_speed(0.05)),
            ("音量・速度", "Backspace", "再生速度を1.00xへ戻す", "同じ", lambda: self._controller.set_speed(1.0)),
            ("A-Bリピート", "A", "A点を設定", "同じ", self.set_a_action.trigger),
            ("A-Bリピート", "B", "B点を設定", "同じ", self.set_b_action.trigger),
            ("A-Bリピート", "R", "A-Bリピート切り替え", "同じ", self.ab_repeat_action.trigger),
            ("A-Bリピート", "Shift+A", "A点を解除", "同じ", self.clear_a_action.trigger),
            ("A-Bリピート", "Shift+B", "B点を解除", "同じ", self.clear_b_action.trigger),
        )
        self._shortcut_help_entries = [
            ShortcutHelpEntry(category, key, normal, inspection)
            for category, key, normal, inspection, _callback in bindings
        ]
        for _category, key, _normal, _inspection, callback in bindings:
            shortcut = self._register_shortcut(key, callback)
            if key == "Ctrl+S":
                self.screenshot_shortcut = shortcut

    def show_shortcut_help(self) -> None:
        ShortcutDialog(self._shortcut_help_entries, self).exec()

    def _register_shortcut(self, key: str, callback) -> QShortcut:
        sequence = QKeySequence(key)
        normalized_key = sequence.toString(QKeySequence.SequenceFormat.PortableText)
        if sequence.isEmpty():
            raise ValueError(f"ショートカットを解釈できません: {key}")
        if normalized_key in self._shortcut_by_key:
            raise ValueError(f"ショートカットが重複しています: {normalized_key}")
        shortcut = QShortcut(sequence, self)
        shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
        shortcut.activated.connect(callback)
        self._shortcut_by_key[normalized_key] = shortcut
        self._shortcuts.append(shortcut)
        return shortcut

    def _play_previous(self) -> None:
        if not self._playlist_controller.play_previous():
            self.statusBar().showMessage("前のファイルはありません。", 2000)

    def _play_selected_or_toggle(self) -> None:
        selected_index = self.playlist_panel.selected_index()
        current_index = self._playlist_controller.current_index
        if (
            self._controller.state is not PlaybackState.PLAYING
            and selected_index >= 0
            and selected_index != current_index
            and self._playlist_controller.request_play(selected_index)
        ):
            return
        self._controller.toggle_play_pause()

    def _play_next(self) -> None:
        if not self._playlist_controller.play_next():
            self.statusBar().showMessage("プレイリストの末尾です。", 2000)

    def _on_media_ended(self, _path: str) -> None:
        if self._playlist_controller.play_next(automatic=True):
            return
        if self._playlist_controller.entries:
            self._playlist_controller.request_play(0)
            self._controller.stop()
            self.statusBar().showMessage("プレイリストの再生が終了しました。", 3000)

    def _sync_playback_icon(self, state: PlaybackState) -> None:
        self.control_bar.set_playing(state is PlaybackState.PLAYING)
        if state is PlaybackState.NO_MEDIA:
            self._set_ab_actions_enabled(False)
            self.screenshot_action.setEnabled(False)

    def _sync_ab_repeat_ui(self, start: float, end: float, enabled: bool) -> None:
        self.control_bar.set_ab_points(start, end, enabled)
        blocker = QSignalBlocker(self.ab_repeat_action)
        self.ab_repeat_action.setChecked(enabled)
        del blocker

    def _set_ab_actions_enabled(self, enabled: bool) -> None:
        for action in self._ab_media_actions:
            action.setEnabled(enabled)

    def _on_current_playlist_item_removed(self, replacement_path: str) -> None:
        self._load_file(replacement_path)
        self._controller.stop()

    def _reset_media_view(self) -> None:
        if not self._controller.clear_media():
            return
        self.video_widget.set_media_loaded(False)
        self._thumbnail_provider.set_media(None)
        self._hide_thumbnail_preview()
        self.frame_inspection_action.setEnabled(False)
        self.screenshot_action.setEnabled(False)
        self.setWindowTitle("MediaCraft")
        self.statusBar().showMessage("ファイルを開くか、動画をドロップしてください。")

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
        self._media_fps = fps
        self._media_variable_rate = variable_rate
        self._frame_controller.set_frame_rate_analysis(fps, variable_rate)

    def _on_thumbnail_media_changed(self, path: str) -> None:
        self._thumbnail_timer.stop()
        self._thumbnail_preview.hide()
        self._thumbnail_request_key = None
        self._media_fps = 0.0
        self._media_variable_rate = None
        self._thumbnail_provider.set_media(path)

    def _on_seek_hovered(self, timestamp: float, global_position: QPoint) -> None:
        self._thumbnail_hover_time = timestamp
        self._thumbnail_hover_position = global_position
        self._thumbnail_request_key = None
        key, image = self._thumbnail_provider.cached(timestamp)
        if image is None:
            self._thumbnail_preview.show_pending(
                timestamp,
                self._thumbnail_frame_text(timestamp),
                global_position,
            )
        else:
            self._thumbnail_request_key = key
            self._thumbnail_preview.show_thumbnail(
                image,
                timestamp,
                self._thumbnail_frame_text(timestamp),
                global_position,
            )
        self._thumbnail_timer.start()

    def _request_thumbnail(self) -> None:
        if self._thumbnail_hover_position is None:
            return
        key, image = self._thumbnail_provider.request(self._thumbnail_hover_time)
        self._thumbnail_request_key = key
        if image is not None:
            self._thumbnail_preview.show_thumbnail(
                image,
                self._thumbnail_hover_time,
                self._thumbnail_frame_text(self._thumbnail_hover_time),
                self._thumbnail_hover_position,
            )

    def _start_thumbnail_preload(self, _position: float, duration: float) -> None:
        if self._thumbnail_preload_enabled:
            self._thumbnail_provider.start_preload(duration)

    def _on_thumbnail_ready(
        self,
        _path: str,
        key: int,
        _actual_timestamp: float,
        image: QImage,
    ) -> None:
        if (
            self._thumbnail_hover_position is None
            or key != self._thumbnail_request_key
            or not self._thumbnail_preview.isVisible()
        ):
            return
        self._thumbnail_preview.show_thumbnail(
            image,
            self._thumbnail_hover_time,
            self._thumbnail_frame_text(self._thumbnail_hover_time),
            self._thumbnail_hover_position,
        )

    def _on_coarse_thumbnail_ready(
        self,
        _path: str,
        _timestamp: float,
        _image: QImage,
    ) -> None:
        if (
            self._thumbnail_hover_position is None
            or not self._thumbnail_preview.isVisible()
        ):
            return
        _key, cached = self._thumbnail_provider.cached(self._thumbnail_hover_time)
        if cached is None:
            return
        self._thumbnail_preview.show_thumbnail(
            cached,
            self._thumbnail_hover_time,
            self._thumbnail_frame_text(self._thumbnail_hover_time),
            self._thumbnail_hover_position,
        )

    def _hide_thumbnail_preview(self) -> None:
        self._thumbnail_timer.stop()
        self._thumbnail_hover_position = None
        self._thumbnail_request_key = None
        self._thumbnail_preview.hide()

    def _thumbnail_frame_text(self, timestamp: float) -> str:
        if self._media_fps <= 0:
            return "Frame: --"
        frame_number = max(0, round(timestamp * self._media_fps))
        suffix = " (推定)" if self._media_variable_rate is True else ""
        return f"Frame: {frame_number:,}{suffix}"

    def _probe_playlist_metadata(self, entries: object) -> None:
        self._playlist_metadata_probe.probe(
            [str(entry.path) for entry in entries if entry.duration is None]
        )

    def _set_playlist_visible(self, visible: bool) -> None:
        self.playlist_panel.setVisible(visible)
        self.playlist_action.setChecked(visible)

    def _set_playlist_toggle_enabled(self, enabled: bool) -> None:
        self.playlist_action.setEnabled(enabled)
        shortcut = self._shortcut_by_key.get("Ctrl+L")
        if shortcut is not None:
            shortcut.setEnabled(enabled)

    def open_settings(self) -> None:
        dialog = SettingsDialog(
            self._settings.screenshot_directory(),
            self._settings.screenshot_format(),
            self._thumbnail_preload_enabled,
            self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self._settings.set_screenshot_directory(dialog.screenshot_directory)
        self._settings.set_screenshot_format(dialog.screenshot_format)
        self._settings.set_thumbnail_preload_enabled(dialog.thumbnail_preload_enabled)
        self._thumbnail_preload_enabled = dialog.thumbnail_preload_enabled

        if self._thumbnail_preload_enabled:
            self._thumbnail_provider.start_preload(self._controller.duration)
        else:
            self._thumbnail_provider.cancel_preload()
        self.statusBar().showMessage("設定を保存しました。", 3000)

    def _set_fullscreen_cursor_hidden(self, hidden: bool) -> None:
        if hidden:
            cursor = Qt.CursorShape.BlankCursor
            self.setCursor(cursor)
            self.video_widget.setCursor(cursor)
            self._fullscreen_overlay.setCursor(cursor)
            return
        self.unsetCursor()
        self.video_widget.unsetCursor()
        self._fullscreen_overlay.unsetCursor()

    def _show_toast(self, message: str) -> None:
        bottom_margin = (
            self.control_bar.sizeHint().height() + 20 if self.isFullScreen() else 24
        )
        self._toast.show_message(
            message,
            self,
            bottom_margin=bottom_margin,
        )

    def _restore_settings(self) -> None:
        geometry = self._settings.window_geometry()
        if not geometry.isEmpty():
            self.restoreGeometry(geometry)
        state = self._settings.playlist_splitter_state()
        if not state.isEmpty():
            self._content_splitter.restoreState(state)
        self._set_playlist_visible(self._settings.playlist_visible())
        self._controller.set_volume(self._settings.volume())
        self._controller.set_mute(self._settings.muted())
        self._controller.set_speed(self._settings.speed())

    def _save_settings(self) -> None:
        self._settings.set_window_geometry(self.saveGeometry())
        self._settings.set_playlist_splitter_state(self._content_splitter.saveState())
        self._settings.set_playlist_visible(self.playlist_action.isChecked())
        self._settings.set_volume(self._controller.volume)
        self._settings.set_muted(self._controller.muted)
        self._settings.set_speed(self._controller.speed)

    def _show_error(self, message: str) -> None:
        logger.error(message)
        self.statusBar().showMessage(message, 10_000)
