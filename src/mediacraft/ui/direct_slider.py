from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPaintEvent, QPainter, QPen
from PySide6.QtWidgets import QSlider, QStyle, QStyleOptionSlider


class DirectSlider(QSlider):
    """A slider that jumps to the pointer and keeps dragging from there."""

    interaction_started = Signal()
    value_committed = Signal(int)

    def __init__(self, orientation: Qt.Orientation, parent=None) -> None:
        super().__init__(orientation, parent)
        self._pointer_active = False
        self._ab_start: float | None = None
        self._ab_end: float | None = None
        self._ab_duration = 0.0
        self._ab_enabled = False

    def set_ab_points(
        self,
        start: float | None,
        end: float | None,
        duration: float,
        enabled: bool,
    ) -> None:
        self._ab_start = start
        self._ab_end = end
        self._ab_duration = max(0.0, duration)
        self._ab_enabled = enabled
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        if self.orientation() != Qt.Orientation.Horizontal or self._ab_duration <= 0:
            return

        option = QStyleOptionSlider()
        self.initStyleOption(option)
        groove = self.style().subControlRect(
            QStyle.ComplexControl.CC_Slider,
            option,
            QStyle.SubControl.SC_SliderGroove,
            self,
        )
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        start_x = self._point_x(self._ab_start, groove)
        end_x = self._point_x(self._ab_end, groove)
        if self._ab_enabled and start_x is not None and end_x is not None:
            fill = QColor(240, 180, 41, 210)
            painter.fillRect(start_x, groove.top(), max(1, end_x - start_x), groove.height(), fill)
        if start_x is not None:
            painter.setPen(QPen(QColor("#61d287"), 2))
            painter.drawLine(start_x, 1, start_x, self.height() - 2)
        if end_x is not None:
            painter.setPen(QPen(QColor("#f2a65a"), 2))
            painter.drawLine(end_x, 1, end_x, self.height() - 2)

        handle = self.style().subControlRect(
            QStyle.ComplexControl.CC_Slider,
            option,
            QStyle.SubControl.SC_SliderHandle,
            self,
        )
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#6ca6dc"))
        painter.drawEllipse(handle)
        painter.end()

    def _point_x(self, point: float | None, groove) -> int | None:
        if point is None:
            return None
        ratio = max(0.0, min(1.0, point / self._ab_duration))
        return groove.left() + round(ratio * groove.width())

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
