from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)


class SettingsDialog(QDialog):
    def __init__(
        self,
        screenshot_directory: str,
        screenshot_format: str,
        thumbnail_preload_enabled: bool,
        shell_open_mode: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("設定")
        self.setModal(True)
        self.setMinimumWidth(520)

        self.screenshot_directory_edit = QLineEdit(screenshot_directory)
        browse_button = QPushButton("参照...")
        browse_button.clicked.connect(self._choose_screenshot_directory)
        directory_row = QHBoxLayout()
        directory_row.addWidget(self.screenshot_directory_edit, 1)
        directory_row.addWidget(browse_button)

        self.screenshot_format_combo = QComboBox()
        self.screenshot_format_combo.addItem("PNG", "png")
        self.screenshot_format_combo.addItem("JPEG", "jpeg")
        format_index = self.screenshot_format_combo.findData(screenshot_format)
        self.screenshot_format_combo.setCurrentIndex(max(0, format_index))

        self.thumbnail_preload_checkbox = QCheckBox(
            "動画読み込み後に粗いサムネイルをバックグラウンド生成する"
        )
        self.thumbnail_preload_checkbox.setChecked(thumbnail_preload_enabled)
        self.shell_open_mode_combo = QComboBox()
        self.shell_open_mode_combo.addItem(
            "新規プレイリストとして開く", "replace"
        )
        self.shell_open_mode_combo.addItem(
            "現在のプレイリストへ追加", "append"
        )
        shell_mode_index = self.shell_open_mode_combo.findData(shell_open_mode)
        self.shell_open_mode_combo.setCurrentIndex(max(0, shell_mode_index))
        note = QLabel(
            "無効にすると再生中のCPU・ストレージ負荷を抑えられます。\n"
            "ホバー位置のサムネイルは引き続き生成されます。"
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #aeb5c0;")

        form = QFormLayout()
        form.addRow("スクリーンショット保存先", directory_row)
        form.addRow("スクリーンショット形式", self.screenshot_format_combo)
        form.addRow("サムネイル", self.thumbnail_preload_checkbox)
        form.addRow("", note)
        form.addRow("エクスプローラーから開く", self.shell_open_mode_combo)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addStretch(1)
        layout.addWidget(buttons)

    @property
    def screenshot_directory(self) -> str:
        return self.screenshot_directory_edit.text().strip()

    @property
    def screenshot_format(self) -> str:
        return str(self.screenshot_format_combo.currentData())

    @property
    def thumbnail_preload_enabled(self) -> bool:
        return self.thumbnail_preload_checkbox.isChecked()

    @property
    def shell_open_mode(self) -> str:
        return str(self.shell_open_mode_combo.currentData())

    def _choose_screenshot_directory(self) -> None:
        start = self.screenshot_directory or str(Path.home())
        directory = QFileDialog.getExistingDirectory(
            self,
            "スクリーンショット保存先を選択",
            start,
        )
        if directory:
            self.screenshot_directory_edit.setText(directory)
