from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QDragEnterEvent, QDragMoveEvent, QDropEvent, QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from mediacraft.playlist.playlist_controller import PlaylistEntry
from mediacraft.utils.drop_paths import local_drop_paths
from mediacraft.utils.time_format import format_time


class PlaylistListWidget(QListWidget):
    files_dropped = Signal(list)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if local_drop_paths(event.mimeData()):
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        if local_drop_paths(event.mimeData()):
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        paths = local_drop_paths(event.mimeData())
        if paths:
            self.files_dropped.emit(paths)
            event.acceptProposedAction()
            return
        super().dropEvent(event)


class PlaylistPanel(QWidget):
    add_files_requested = Signal()
    add_folder_requested = Signal()
    remove_requested = Signal(list)
    clear_requested = Signal()
    play_requested = Signal(int)
    order_changed = Signal(list)
    files_dropped = Signal(list)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._current_index = -1
        self._rebuilding = False

        self.list_widget = PlaylistListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.list_widget.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.list_widget.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.list_widget.setAlternatingRowColors(False)
        self.list_widget.setStyleSheet(
            """
            QListWidget {
                background-color: #181a1f;
                border: 1px solid #30343d;
            }
            QListWidget::item {
                background-color: #181a1f;
                border-bottom: 1px solid #2b2f37;
                padding: 6px 5px;
            }
            QListWidget::item:hover {
                background-color: #252932;
            }
            QListWidget::item:selected {
                background-color: #343a46;
                color: #ffffff;
            }
            """
        )
        self.list_widget.itemDoubleClicked.connect(self._play_item)
        self.list_widget.model().rowsMoved.connect(self._rows_moved)
        self.list_widget.files_dropped.connect(self.files_dropped.emit)

        self.add_button = QPushButton("追加")
        self.folder_button = QPushButton("フォルダ")
        self.remove_button = QPushButton("削除")
        self.clear_button = QPushButton("全消去")
        for button, width in (
            (self.add_button, 50),
            (self.folder_button, 64),
            (self.remove_button, 50),
            (self.clear_button, 60),
        ):
            button.setFixedWidth(width)
        self.add_button.clicked.connect(self.add_files_requested.emit)
        self.folder_button.clicked.connect(self.add_folder_requested.emit)
        self.remove_button.clicked.connect(self._remove_selected)
        self.clear_button.clicked.connect(self.clear_requested.emit)

        button_row = QHBoxLayout()
        button_row.setSpacing(4)
        button_row.addWidget(self.add_button)
        button_row.addWidget(self.folder_button)
        button_row.addStretch(1)
        button_row.addWidget(self.remove_button)
        button_row.addWidget(self.clear_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(self.list_widget, 1)
        layout.addLayout(button_row)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if local_drop_paths(event.mimeData()):
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        if local_drop_paths(event.mimeData()):
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        paths = local_drop_paths(event.mimeData())
        if paths:
            self.files_dropped.emit(paths)
            event.acceptProposedAction()
            return
        super().dropEvent(event)

    def set_entries(self, entries: tuple[PlaylistEntry, ...]) -> None:
        self._rebuilding = True
        self.list_widget.clear()
        for entry in entries:
            duration = format_time(entry.duration) if entry.duration is not None else "--:--:--"
            item = QListWidgetItem(f"{entry.path.name}\n{duration}")
            item.setData(Qt.ItemDataRole.UserRole, str(entry.path))
            item.setToolTip(str(entry.path))
            self.list_widget.addItem(item)
        self._rebuilding = False
        self.set_current_index(self._current_index)

    def set_current_index(self, index: int) -> None:
        self._current_index = index
        for row in range(self.list_widget.count()):
            item = self.list_widget.item(row)
            is_current = row == index
            font = QFont(item.font())
            font.setBold(is_current)
            item.setFont(font)
            item.setForeground(QColor("#ffffff") if is_current else QColor("#d5d8de"))
            prefix = "▶ " if is_current else ""
            lines = item.text().removeprefix("▶ ").splitlines()
            item.setText(prefix + "\n".join(lines))
        if 0 <= index < self.list_widget.count():
            self.list_widget.setCurrentRow(index)
            self.list_widget.scrollToItem(self.list_widget.item(index))
        else:
            self.list_widget.clearSelection()
            self.list_widget.setCurrentRow(-1)

    def _play_item(self, item: QListWidgetItem) -> None:
        self.play_requested.emit(self.list_widget.row(item))

    def _remove_selected(self) -> None:
        rows = sorted({self.list_widget.row(item) for item in self.list_widget.selectedItems()})
        if rows:
            self.remove_requested.emit(rows)

    def _rows_moved(self, *_args) -> None:
        if self._rebuilding:
            return
        paths = [
            self.list_widget.item(row).data(Qt.ItemDataRole.UserRole)
            for row in range(self.list_widget.count())
        ]
        self.order_changed.emit(paths)
