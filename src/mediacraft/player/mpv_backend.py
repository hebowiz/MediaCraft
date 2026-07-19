import importlib
import logging
import os
from pathlib import Path
import sys
from types import ModuleType
from collections.abc import Callable
from typing import Any

from mediacraft.player.player_backend import (
    BackendError,
    BackendUnavailableError,
    PlayerBackend,
)

logger = logging.getLogger(__name__)


class MpvBackend(PlayerBackend):
    def __init__(self) -> None:
        self._mpv_module: ModuleType | None = None
        self._player: Any | None = None
        self._dll_directory: Any | None = None

    def initialize(self, window_id: int) -> None:
        if self._player is not None:
            return

        try:
            self._configure_dll_search_path()
            self._mpv_module = importlib.import_module("mpv")
            self._player = self._mpv_module.MPV(
                wid=str(window_id),
                idle="yes",
                keep_open="yes",
                osc=False,
                input_default_bindings=False,
                input_vo_keyboard=False,
                hwdec="auto-safe",
                log_handler=self._log_message,
                loglevel="warn",
            )
        except (ImportError, OSError) as exc:
            raise BackendUnavailableError(
                "libmpvを読み込めません。libmpv-2.dllの配置を確認してください。"
            ) from exc
        except Exception as exc:
            raise BackendError(f"libmpvの初期化に失敗しました: {exc}") from exc

    def load(self, path: Path) -> None:
        player = self._require_player()
        try:
            player.command("loadfile", str(path), "replace")
            player.pause = False
        except Exception as exc:
            raise BackendError(f"動画を読み込めませんでした: {exc}") from exc

    def play(self) -> None:
        self._perform("再生を開始できませんでした", lambda player: setattr(player, "pause", False))

    def pause(self) -> None:
        self._perform("一時停止できませんでした", lambda player: setattr(player, "pause", True))

    def stop(self) -> None:
        def stop_player(player: Any) -> None:
            player.pause = True
            player.command("seek", 0, "absolute", "exact")

        self._perform("停止できませんでした", stop_player)

    def seek_absolute(self, seconds: float) -> None:
        self._perform(
            "シークできませんでした",
            lambda player: player.command("seek", max(0.0, seconds), "absolute", "exact"),
        )

    def seek_relative(self, seconds: float) -> None:
        self._perform(
            "シークできませんでした",
            lambda player: player.command("seek", seconds, "relative", "exact"),
        )

    def set_speed(self, speed: float) -> None:
        self._perform("再生速度を変更できませんでした", lambda player: setattr(player, "speed", speed))

    def set_volume(self, volume: int) -> None:
        self._perform("音量を変更できませんでした", lambda player: setattr(player, "volume", volume))

    def set_mute(self, muted: bool) -> None:
        self._perform("ミュートを変更できませんでした", lambda player: setattr(player, "mute", muted))

    def position(self) -> float:
        return self._number_property("time_pos")

    def duration(self) -> float:
        return self._number_property("duration")

    def is_paused(self) -> bool:
        player = self._require_player()
        try:
            return bool(player.pause)
        except Exception:
            return True

    def shutdown(self) -> None:
        if self._player is None:
            return
        try:
            self._player.terminate()
        except Exception:
            logger.exception("Failed to terminate libmpv cleanly")
        finally:
            self._player = None

    def _number_property(self, name: str) -> float:
        player = self._require_player()
        try:
            value = getattr(player, name)
            return max(0.0, float(value)) if value is not None else 0.0
        except Exception:
            return 0.0

    def _require_player(self) -> Any:
        if self._player is None:
            raise BackendUnavailableError("libmpvが初期化されていません。")
        return self._player

    def _perform(self, message: str, operation: Callable[[Any], Any]) -> Any:
        player = self._require_player()
        try:
            return operation(player)
        except Exception as exc:
            raise BackendError(f"{message}: {exc}") from exc

    def _configure_dll_search_path(self) -> None:
        if os.name != "nt":
            return

        project_root = Path(__file__).resolve().parents[3]
        candidates = (
            project_root / "vendor" / "mpv",
            Path(sys.executable).resolve().parent,
            Path(sys.executable).resolve().parent / "mpv",
        )
        for directory in candidates:
            if not (directory / "libmpv-2.dll").is_file():
                continue
            directory_text = str(directory.resolve())
            path_entries = os.environ.get("PATH", "").split(os.pathsep)
            if directory_text not in path_entries:
                os.environ["PATH"] = directory_text + os.pathsep + os.environ.get("PATH", "")
            if hasattr(os, "add_dll_directory"):
                self._dll_directory = os.add_dll_directory(directory_text)
            return

    @staticmethod
    def _log_message(level: str, component: str, message: str) -> None:
        log_method = logger.warning if level in {"warn", "error", "fatal"} else logger.debug
        log_method("mpv[%s]: %s", component, message.rstrip())
