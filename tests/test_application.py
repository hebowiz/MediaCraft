from uuid import uuid4

import pytest
from PySide6.QtGui import QIcon

from mediacraft.app.application import APP_ICON_PATH
from mediacraft.app.single_instance import SingleInstance, command_line_paths


def test_application_icon_contains_all_windows_sizes() -> None:
    icon = QIcon(str(APP_ICON_PATH))

    assert APP_ICON_PATH.is_file()
    assert not icon.isNull()
    assert [size.width() for size in icon.availableSizes()] == [
        16,
        24,
        32,
        48,
        64,
        128,
        256,
    ]


def test_command_line_paths_keeps_existing_files(tmp_path) -> None:
    media_file = tmp_path / "日本語 file.mp4"
    media_file.touch()

    assert command_line_paths(["--ignored", str(media_file)]) == [
        str(media_file.resolve())
    ]


def test_instance_lock_allows_only_one_primary(tmp_path) -> None:
    server_name = f"MediaCraft.Test.{uuid4()}"
    lock_path = tmp_path / "instance.lock"
    primary = SingleInstance(server_name=server_name, lock_path=str(lock_path))
    secondary = SingleInstance(server_name=server_name, lock_path=str(lock_path))

    if not primary.acquire_or_notify([]):
        pytest.skip("この実行環境ではQtローカルIPCを作成できません")
    assert not secondary._lock.tryLock(0)
    primary.close()
    assert secondary.acquire_or_notify([])
    secondary.close()
