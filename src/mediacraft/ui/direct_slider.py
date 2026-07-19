from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QSlider, QStyle, QStyleOptionSlider


class DirectSlider(QSlider):
    """A slider that jumps to the pointer and keeps dragging from there."""

    interaction_started = Signal()
    value_committed = Signal(int)

    def __init__(self, orientation: Qt.Orientation, parent=None) -> None:
        super().__init__(orientation, parent)
        self._pointer_active = False

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return

        self._pointer_active = True
        self.setSliderDown(True)
        self.interaction_started.emit()
        self._set_value_from_pointer(event)
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if not self._pointer_active:
            super().mouseMoveEvent(event)
            return
        self._set_value_from_pointer(event)
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton or not self._pointer_active:
            super().mouseReleaseEvent(event)
            return

        self._set_value_from_pointer(event)
        self._pointer_active = False
        self.setSliderDown(False)
        self.value_committed.emit(self.value())
        event.accept()

    def _set_value_from_pointer(self, event: QMouseEvent) -> None:
        option = QStyleOptionSlider()
        self.initStyleOption(option)
        style = self.style()
        groove = style.subControlRect(
            QStyle.ComplexControl.CC_Slider,
            option,
            QStyle.SubControl.SC_SliderGroove,
            self,
        )
        handle = style.subControlRect(
            QStyle.ComplexControl.CC_Slider,
            option,
            QStyle.SubControl.SC_SliderHandle,
            self,
        )

        if self.orientation() == Qt.Orientation.Horizontal:
            slider_min = groove.x()
            slider_max = groove.right() - handle.width() + 1
            pointer_position = round(event.position().x() - handle.width() / 2)
        else:
            slider_min = groove.y()
            slider_max = groove.bottom() - handle.height() + 1
            pointer_position = round(event.position().y() - handle.height() / 2)

        value = QStyle.sliderValueFromPosition(
            self.minimum(),
            self.maximum(),
            pointer_position - slider_min,
            max(1, slider_max - slider_min),
            option.upsideDown,
        )
        self.setValue(value)
