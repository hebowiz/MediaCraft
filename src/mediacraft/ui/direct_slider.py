from PySide6.QtCore import QRectF, Qt, Signal
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
        self._centered_track = False

    def set_centered_track(self, enabled: bool) -> None:
        self._centered_track = enabled
        self.setStyleSheet(
            """
            QSlider::groove:horizontal,
            QSlider::sub-page:horizontal,
            QSlider::add-page:horizontal,
            QSlider::handle:horizontal {
                background: transparent;
                border: none;
            }
            QSlider::groove:horizontal {
                height: 5px;
            }
            QSlider::handle:horizontal {
                width: 14px;
                margin: -5px 0;
            }
            """
            if enabled
            else ""
        )
        self.update()

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
        if self.orientation() != Qt.Orientation.Horizontal:
            return

        option = QStyleOptionSlider()
        self.initStyleOption(option)
        groove = self.style().subControlRect(
            QStyle.ComplexControl.CC_Slider,
            option,
            QStyle.SubControl.SC_SliderGroove,
            self,
        )
        handle = self.style().subControlRect(
            QStyle.ComplexControl.CC_Slider,
            option,
            QStyle.SubControl.SC_SliderHandle,
            self,
        )
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self._centered_track:
            track_left = self._value_x(
                self.minimum(), groove, handle.width(), option.upsideDown
            )
            track_right = self._value_x(
                self.maximum(), groove, handle.width(), option.upsideDown
            )
            position_x = self._value_x(
                self.value(), groove, handle.width(), option.upsideDown
            )
            track_y = groove.center().y()
            track_color = QColor("#3a3f49")
            progress_color = QColor("#477eae")
            handle_color = QColor("#6ca6dc")
            if not self.isEnabled():
                track_color.setAlpha(115)
                progress_color.setAlpha(115)
                handle_color.setAlpha(115)

            track_pen = QPen(track_color, max(1, groove.height()))
            track_pen.setCapStyle(Qt.PenCapStyle.FlatCap)
            painter.setPen(track_pen)
            painter.drawLine(track_left, track_y, track_right, track_y)

            progress_pen = QPen(progress_color, max(1, groove.height()))
            progress_pen.setCapStyle(Qt.PenCapStyle.FlatCap)
            painter.setPen(progress_pen)
            if option.upsideDown:
                painter.drawLine(position_x, track_y, track_right, track_y)
            else:
                painter.drawLine(track_left, track_y, position_x, track_y)
        else:
            handle_color = QColor("#6ca6dc")

        start_x = (
            self._point_x(self._ab_start, groove, handle.width(), option.upsideDown)
            if self._ab_duration > 0
            else None
        )
        end_x = (
            self._point_x(self._ab_end, groove, handle.width(), option.upsideDown)
            if self._ab_duration > 0
            else None
        )
        if self._ab_enabled and start_x is not None and end_x is not None:
            fill = QColor(240, 180, 41, 210)
            painter.fillRect(start_x, groove.top(), max(1, end_x - start_x), groove.height(), fill)
        if start_x is not None:
            painter.setPen(QPen(QColor("#61d287"), 2))
            painter.drawLine(start_x, 1, start_x, self.height() - 2)
        if end_x is not None:
            painter.setPen(QPen(QColor("#f2a65a"), 2))
            painter.drawLine(end_x, 1, end_x, self.height() - 2)

        if self._centered_track or self._ab_duration > 0:
            handle_center_x = self._value_x(
                self.value(), groove, handle.width(), option.upsideDown
            )
            handle_center_y = handle.y() + handle.height() / 2
            handle_diameter = 9.0
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(handle_color)
            painter.drawEllipse(
                QRectF(
                    handle_center_x - handle_diameter / 2,
                    handle_center_y - handle_diameter / 2,
                    handle_diameter,
                    handle_diameter,
                )
            )
        painter.end()

    def _point_x(
        self,
        point: float | None,
        groove,
        handle_width: int,
        upside_down: bool,
    ) -> int | None:
        if point is None:
            return None
        ratio = max(0.0, min(1.0, point / self._ab_duration))
        point_value = self.minimum() + int(ratio * (self.maximum() - self.minimum()))
        return self._value_x(point_value, groove, handle_width, upside_down)

    def _value_x(
        self,
        value: int,
        groove,
        handle_width: int,
        upside_down: bool,
    ) -> int:
        available = max(0, groove.width() - handle_width)
        handle_position = QStyle.sliderPositionFromValue(
            self.minimum(),
            self.maximum(),
            value,
            available,
            upside_down,
        )
        return groove.left() + handle_position + round(handle_width / 2)

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
