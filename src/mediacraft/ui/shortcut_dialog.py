from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QFont
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)


@dataclass(frozen=True)
class ShortcutHelpEntry:
    category: str
    key: str
    normal_action: str
    inspection_action: str = "同じ"


class ShortcutDialog(QDialog):
    def __init__(self, entries: list[ShortcutHelpEntry], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("キーボードショートカット")
        self.resize(760, 620)
        self.shortcut_count = len(entries)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(3)
        self.tree.setHeaderLabels(
            ("キー", "通常モード", "フレーム確認モード")
        )
        self.tree.setRootIsDecorated(True)
        self.tree.setAlternatingRowColors(False)
        self.tree.setStyleSheet(
            """
            QTreeWidget::item:selected {
                background: #454b57;
                color: #ffffff;
            }
            """
        )

        category_items: dict[str, QTreeWidgetItem] = {}
        for entry in entries:
            category_item = category_items.get(entry.category)
            if category_item is None:
                category_item = QTreeWidgetItem(self.tree, (entry.category, "", ""))
                category_item.setFirstColumnSpanned(True)
                category_item.setFlags(
                    category_item.flags() & ~Qt.ItemFlag.ItemIsSelectable
                )
                category_item.setBackground(0, QBrush(QColor("#30343d")))
                category_font = QFont(category_item.font(0))
                category_font.setBold(True)
                category_item.setFont(0, category_font)
                category_items[entry.category] = category_item
            QTreeWidgetItem(
                category_item,
                (
                    self._display_key(entry.key),
                    entry.normal_action,
                    entry.inspection_action,
                ),
            )

        self.tree.expandAll()
        header = self.tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self.tree, 1)
        layout.addWidget(buttons)

    @staticmethod
    def _display_key(key: str) -> str:
        names = {
            "Left": "←",
            "Right": "→",
            "Up": "↑",
            "Down": "↓",
            "Return": "Enter",
            "Escape": "Esc",
            "PgUp": "PageUp",
            "PgDown": "PageDown",
        }
        parts = key.split("+")
        parts[-1] = names.get(parts[-1], parts[-1])
        return "+".join(parts)
