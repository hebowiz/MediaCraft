from mediacraft.frame.media_probe import MediaProbe, detect_variable_frame_rate


def test_detects_constant_and_variable_frame_intervals() -> None:
    constant = [index / 30 for index in range(20)]
    variable = [0.0]
    for index in range(1, 20):
        interval = 1 / 24 if index % 3 == 0 else 1 / 30
        variable.append(variable[-1] + interval)

    assert detect_variable_frame_rate(constant) is False
    assert detect_variable_frame_rate(variable) is True
    assert detect_variable_frame_rate(constant[:5]) is None


def test_probe_reports_unreadable_media_without_blocking(qtbot, tmp_path) -> None:
    media_file = tmp_path / "empty.mp4"
    media_file.touch()
    probe = MediaProbe()

    with qtbot.waitSignal(probe.analysis_ready) as blocker:
        probe.probe(str(media_file))

    assert blocker.args == [str(media_file), 0.0, None]
    probe.shutdown()
