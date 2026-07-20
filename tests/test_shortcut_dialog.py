from mediacraft.ui.shortcut_dialog import ShortcutDialog, ShortcutHelpEntry


def test_shortcut_dialog_groups_and_displays_mode_specific_actions(qtbot) -> None:
    entries = [
        ShortcutHelpEntry("再生", "Space", "再生／一時停止"),
        ShortcutHelpEntry("シーク", "Left", "5秒戻る", "1フレーム戻る"),
        ShortcutHelpEntry("シーク", "Ctrl+Right", "—", "100フレーム進む"),
    ]
    dialog = ShortcutDialog(entries)
    qtbot.addWidget(dialog)

    assert dialog.shortcut_count == 3
    assert not dialog.tree.alternatingRowColors()
    assert dialog.tree.topLevelItemCount() == 2
    seek_group = dialog.tree.topLevelItem(1)
    assert seek_group.text(0) == "シーク"
    assert seek_group.childCount() == 2
    assert seek_group.child(0).text(0) == "←"
    assert seek_group.child(0).text(1) == "5秒戻る"
    assert seek_group.child(0).text(2) == "1フレーム戻る"
    assert seek_group.child(1).text(0) == "Ctrl+→"
