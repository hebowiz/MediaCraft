from collections.abc import Callable
import logging
from pathlib import Path
from time import monotonic
from typing import Any

from PySide6.QtCore import QTimer, Qt

from mediacraft.media.avi_info import inspect_avi
from mediacraft.player.player_backend import BackendError, BackendUnavailableError, PlayerBackend


logger = logging.getLogger(__name__)


class WindowsMediaBackend(PlayerBackend):
    """AMV4 playback through the Windows Media Player DirectShow/VfW path."""

    PLAYING = 3
    STOPPED = 1
    MEDIA_ENDED = 8

    def __init__(self, control_factory: Callable[[], Any]) -> None:
        self._control_factory = control_factory
        self._player: Any | None = None
        self._controls: Any | None = None
        self._fps = 0.0
        self._duration = 0.0
        self._ab_loop: tuple[float, float] | None = None
        self._last_position = 0.0
        self._was_playing = False
        self._ended = False
        self._speed = 1.0
        self._play_requested = False
        self._rate_playing = False
        self._rate_last_clock: float | None = None
        self._rate_target_position = 0.0
        self._rate_timer = QTimer()
        self._rate_timer.setInterval(16)
        self._rate_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._rate_timer.timeout.connect(self._advance_rate_playback)

    def initialize(self, window_id: int) -> None:
        del window_id
        if self._player is not None:
            return
        try:
            self._player = self._control_factory()
            self._controls = self._player.querySubObject("controls")
        except Exception as exc:
            raise BackendUnavailableError(
                "Windows Media Playerを初期化できませんでした。"
            ) from exc
        if self._player is None or self._player.isNull() or self._controls is None:
            self._player = None
            self._controls = None
            raise BackendUnavailableError(
                "AMV4再生に必要なWindows Media Playerを利用できません。"
            )

    def load(self, path: Path) -> None:
        player = self._require_player()
        info = inspect_avi(path)
        self._fps = info.frame_rate if info is not None else 0.0
        self._duration = info.duration if info is not None else 0.0
        self._ab_loop = None
        self._last_position = 0.0
        self._was_playing = False
        self._ended = False
        self._play_requested = True
        self._stop_rate_playback()
        try:
            self._set_properties(
                player,
                URL=str(path),
                uiMode="none",
                autoStart=False,
                stretchToFit=True,
                enableContextMenu=False,
            )
            self._controls = player.querySubObject("controls")
            self._require_controls().dynamicCall("play()")
            self._set_native_rate(1.0)
            player.show()
            player.raise_()
        except Exception as exc:
            raise BackendError(f"AMV4動画を開けませんでした: {exc}") from exc

    def play(self) -> None:
        self._ended = False
        self._play_requested = True
        self._update_rate_mode()

    def pause(self) -> None:
        self._play_requested = False
        self._stop_rate_playback()
        self._perform(lambda: self._require_controls().dynamicCall("pause()"))

    def stop(self) -> None:
        self._ended = False
        self._play_requested = False
        self._stop_rate_playback()
        self._was_playing = False

        def operation() -> None:
            self._require_controls().dynamicCall("stop()")
            self.seek_absolute(0.0)

        self._perform(operation)

    def clear_media(self) -> None:
        if self._player is None:
            return
        self._perform(lambda: self._require_controls().dynamicCall("stop()"))
        self._set_properties(self._player, URL="")
        self._player.hide()
        self._fps = 0.0
        self._duration = 0.0
        self._ab_loop = None
        self._last_position = 0.0
        self._was_playing = False
        self._ended = False
        self._play_requested = False
        self._stop_rate_playback()

    def seek_absolute(self, seconds: float) -> None:
        controls = self._require_controls()
        target = max(0.0, float(seconds))
        if not controls.setProperty("currentPosition", target):
            raise BackendError("AMV4動画をシークできませんでした。")
        self._last_position = target
        self._ended = False
        self._rate_last_clock = monotonic() if self._rate_playing else None
        self._rate_target_position = target

    def seek_relative(self, seconds: float) -> None:
        self.seek_absolute(self.position() + seconds)

    def set_speed(self, speed: float) -> None:
        self._speed = max(0.1, min(4.0, float(speed)))
        # The AMV4 VfW path rejects WMP's native rate setting and silently
        # remains at 1.0x. Keep WMP at its stable native rate and drive its
        # supported frame-step operation from a precise timer instead.
        self._set_native_rate(1.0)
        self._update_rate_mode()

    def set_volume(self, volume: int) -> None:
        player = self._require_player()
        settings = player.querySubObject("settings")
        if settings is not None and not settings.setProperty(
            "volume", max(0, min(100, int(volume)))
        ):
            raise BackendError("AMV4動画の音量を変更できませんでした。")

    def set_mute(self, muted: bool) -> None:
        player = self._require_player()
        settings = player.querySubObject("settings")
        if settings is not None and not settings.setProperty("mute", bool(muted)):
            raise BackendError("AMV4動画のミュート状態を変更できませんでした。")

    def set_ab_loop(self, start: float | None, end: float | None) -> None:
        self._ab_loop = (
            (max(0.0, start), max(0.0, end))
            if start is not None and end is not None
            else None
        )

    def save_screenshot(self, path: Path, include_subtitles: bool = False) -> None:
        del include_subtitles
        player = self._require_player()
        if not player.grab().save(str(path)):
            raise BackendError("AMV4動画のスクリーンショットを保存できませんでした。")

    def frame_step(self, count: int) -> None:
        if count == 0:
            return
        if count < 0:
            if self._fps <= 0:
                raise BackendError(
                    "AMV4動画のフレームレートを取得できないため、フレーム戻しできません。"
                )
            self.seek_absolute(self.position() + count / self._fps)
            return
        controls = self._require_controls()
        for _ in range(count):
            controls.dynamicCall("step(int)", 1)

    def position(self) -> float:
        position = self._raw_position()
        state = int(self._require_player().dynamicCall("playState") or 0)
        if state == self.PLAYING:
            self._was_playing = True
            if self._play_requested and self._speed != 1.0 and not self._rate_playing:
                self._update_rate_mode()
        elif self._rate_playing:
            self._was_playing = True
        elif self._play_requested and self._speed != 1.0:
            # Loading is asynchronous. Start frame-clock playback once WMP
            # reports that the media is ready to play.
            self._update_rate_mode()
        if position > 0:
            self._last_position = position
        if self._ab_loop is not None and position >= self._ab_loop[1]:
            self.seek_absolute(self._ab_loop[0])
            return self._ab_loop[0]
        return position

    def duration(self) -> float:
        player = self._require_player()
        media = player.querySubObject("currentMedia")
        if media is not None:
            try:
                value = float(media.dynamicCall("duration") or 0.0)
                if value > 0:
                    self._duration = value
            except (TypeError, ValueError):
                pass
        return self._duration

    def is_paused(self) -> bool:
        return not self._play_requested

    def estimated_frame_number(self) -> int | None:
        return round(self._last_position * self._fps) if self._fps > 0 else None

    def frame_rate(self) -> float:
        return self._fps

    def has_ended(self) -> bool:
        if self._ended:
            return True
        state = int(self._require_player().dynamicCall("playState") or 0)
        if state == self.MEDIA_ENDED:
            self._ended = True
        elif (
            state == self.STOPPED
            and self._was_playing
            and self._duration > 0
            and self._last_position >= self._duration - self._end_tolerance()
        ):
            self._ended = True
        return self._ended

    def shutdown(self) -> None:
        self._stop_rate_playback()
        if self._player is None:
            return
        try:
            if self._controls is not None:
                self._controls.dynamicCall("stop()")
            self._player.clear()
        except Exception:
            logger.exception("Failed to shut down Windows Media Player cleanly")
        finally:
            self._controls = None
            self._player = None

    def _require_player(self) -> Any:
        if self._player is None:
            raise BackendUnavailableError("Windows Media Playerが初期化されていません。")
        return self._player

    def _require_controls(self) -> Any:
        if self._controls is None:
            raise BackendUnavailableError("Windows Media Playerの操作機能を利用できません。")
        return self._controls

    def _end_tolerance(self) -> float:
        return max(0.1, 2.0 / self._fps) if self._fps > 0 else 0.25

    def _raw_position(self) -> float:
        value = self._require_controls().dynamicCall("currentPosition")
        try:
            return max(0.0, float(value or 0.0))
        except (TypeError, ValueError):
            return 0.0

    def _set_control_position(self, seconds: float) -> None:
        if not self._require_controls().setProperty(
            "currentPosition", max(0.0, float(seconds))
        ):
            raise BackendError("AMV4動画をシークできませんでした。")

    def _set_native_rate(self, rate: float) -> None:
        settings = self._require_player().querySubObject("settings")
        if settings is not None and not settings.setProperty("rate", float(rate)):
            raise BackendError("AMV4動画の再生速度を初期化できませんでした。")

    def _update_rate_mode(self) -> None:
        if not self._play_requested:
            self._stop_rate_playback()
            return
        controls = self._require_controls()
        if self._speed == 1.0:
            self._stop_rate_playback()
            controls.dynamicCall("play()")
            return
        if self._fps <= 0:
            raise BackendError(
                "AMV4動画のフレームレートを取得できないため、速度変更できません。"
            )
        state = int(self._require_player().dynamicCall("playState") or 0)
        if state not in {self.PLAYING, 2} and not self._rate_playing:
            return
        controls.dynamicCall("pause()")
        if not self._rate_playing:
            self._rate_playing = True
            self._rate_last_clock = monotonic()
            self._rate_target_position = self._raw_position()
            self._rate_timer.start()

    def _stop_rate_playback(self) -> None:
        self._rate_timer.stop()
        self._rate_playing = False
        self._rate_last_clock = None

    def _advance_rate_playback(self) -> None:
        if not self._rate_playing or not self._play_requested:
            self._stop_rate_playback()
            return
        now = monotonic()
        if self._rate_last_clock is None:
            self._rate_last_clock = now
            return
        elapsed = max(0.0, now - self._rate_last_clock)
        self._rate_last_clock = now
        self._rate_target_position += elapsed * self._speed
        frame_number = int(self._rate_target_position * self._fps)
        target = frame_number / self._fps
        if target <= self._last_position:
            return

        final_frame = (
            max(0.0, self._duration - 1.0 / self._fps)
            if self._duration > 0
            else None
        )
        if final_frame is not None and target >= final_frame:
            self._set_control_position(final_frame)
            self._last_position = final_frame
            self._ended = True
            self._play_requested = False
            self._stop_rate_playback()
            return
        self._set_control_position(target)
        self._last_position = target

    @staticmethod
    def _set_properties(target: Any, **updates: object) -> None:
        properties = target.propertyBag()
        properties.update(updates)
        target.setPropertyBag(properties)

    @staticmethod
    def _perform(operation: Callable[[], None]) -> None:
        try:
            operation()
        except BackendError:
            raise
        except Exception as exc:
            raise BackendError(f"AMV4再生操作に失敗しました: {exc}") from exc
