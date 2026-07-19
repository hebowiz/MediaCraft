from dataclasses import dataclass, replace
from pathlib import Path

from PySide6.QtCore import QObject, Signal


@dataclass(frozen=True, slots=True)
class PlaylistEntry:
    path: Path
    duration: float | None = None


class PlaylistController(QObject):
    playlist_changed = Signal(object)
    current_index_changed = Signal(int)
    play_requested = Signal(str)
    current_item_removed = Signal(str)
    cleared = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._entries: list[PlaylistEntry] = []
        self._current_index = -1
        self._duration_cache: dict[Path, float] = {}

    @property
    def entries(self) -> tuple[PlaylistEntry, ...]:
        return tuple(self._entries)

    @property
    def current_index(self) -> int:
        return self._current_index

    def add_files(self, paths: list[str | Path]) -> int:
        existing = {entry.path for entry in self._entries}
        first_added = -1
        for value in paths:
            path = Path(value).expanduser().resolve()
            if not path.is_file() or path in existing:
                continue
            if first_added < 0:
                first_added = len(self._entries)
            self._entries.append(PlaylistEntry(path, self._duration_cache.get(path)))
            existing.add(path)
        if first_added >= 0:
            self._emit_playlist()
        return first_added

    def remove_indices(self, indices: list[int]) -> None:
        valid = sorted({index for index in indices if 0 <= index < len(self._entries)}, reverse=True)
        if not valid:
            return
        current_path = self._current_path()
        current_removed = self._current_index in valid
        previous_index = self._current_index
        for index in valid:
            del self._entries[index]
        if current_removed and self._entries:
            self._current_index = min(previous_index, len(self._entries) - 1)
        else:
            self._current_index = self._index_of(current_path) if current_path is not None else -1
        self._emit_playlist()
        self.current_index_changed.emit(self._current_index)
        if not self._entries:
            self.cleared.emit()
        elif current_removed:
            self.current_item_removed.emit(str(self._entries[self._current_index].path))

    def clear(self) -> None:
        if not self._entries:
            return
        self._entries.clear()
        self._current_index = -1
        self._emit_playlist()
        self.current_index_changed.emit(-1)
        self.cleared.emit()

    def reorder(self, ordered_paths: list[str | Path]) -> None:
        resolved = [Path(path).expanduser().resolve() for path in ordered_paths]
        if len(resolved) != len(self._entries) or set(resolved) != {
            entry.path for entry in self._entries
        }:
            return
        current_path = self._current_path()
        entries_by_path = {entry.path: entry for entry in self._entries}
        self._entries = [entries_by_path[path] for path in resolved]
        self._current_index = self._index_of(current_path) if current_path is not None else -1
        self._emit_playlist()
        self.current_index_changed.emit(self._current_index)

    def request_play(self, index: int) -> bool:
        if not 0 <= index < len(self._entries):
            return False
        self.play_requested.emit(str(self._entries[index].path))
        return True

    def index_for_path(self, path: str | Path) -> int:
        return self._index_of(Path(path).expanduser().resolve())

    def play_next(self) -> bool:
        next_index = 0 if self._current_index < 0 else self._current_index + 1
        return self.request_play(next_index)

    def play_previous(self) -> bool:
        if self._current_index <= 0:
            return False
        return self.request_play(self._current_index - 1)

    def set_current_path(self, path: str | Path) -> None:
        resolved = Path(path).expanduser().resolve()
        index = self._index_of(resolved)
        if index == self._current_index:
            return
        self._current_index = index
        self.current_index_changed.emit(index)

    def update_current_duration(self, duration: float) -> None:
        if self._current_index < 0 or duration <= 0:
            return
        if self._entries[self._current_index].duration is not None:
            return
        self.update_duration(self._entries[self._current_index].path, duration)

    def update_duration(self, path: str | Path, duration: float) -> None:
        index = self.index_for_path(path)
        if index < 0 or duration <= 0:
            return
        entry = self._entries[index]
        if entry.duration is not None and abs(entry.duration - duration) < 0.01:
            return
        self._duration_cache[entry.path] = duration
        self._entries[index] = replace(entry, duration=duration)
        self._emit_playlist()

    def _current_path(self) -> Path | None:
        if 0 <= self._current_index < len(self._entries):
            return self._entries[self._current_index].path
        return None

    def _index_of(self, path: Path | None) -> int:
        if path is None:
            return -1
        return next(
            (index for index, entry in enumerate(self._entries) if entry.path == path),
            -1,
        )

    def _emit_playlist(self) -> None:
        self.playlist_changed.emit(self.entries)
