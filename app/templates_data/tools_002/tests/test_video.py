from vadana.video import _static_silent


def test_static_silent_lone_frame_no_audio():
    # one still frame, no audio, no screen-share -> can't be built (would be ~0s)
    assert _static_silent([(0.0, "a")], None, False)


def test_static_silent_needs_no_audio():
    assert not _static_silent([(0.0, "a")], "master.m4a", False)   # audio holds the frame


def test_static_silent_spanning_frames_ok():
    assert not _static_silent([(0.0, "a"), (30.0, "b")], None, False)  # motion over time


def test_static_silent_screenshare_ok():
    assert not _static_silent([(0.0, "a")], None, True)            # screen-share carries it


def test_static_silent_empty_handled_elsewhere():
    assert not _static_silent([], None, False)


def test_make_full_video_new_style_returns_none(tmp_path):
    import io, zipfile
    from vadana.video import make_full_video
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("mainstream.flv", "x")
        z.writestr("cameraVoip_0_3.flv", "x")
    buf.seek(0)
    zf = zipfile.ZipFile(buf)
    assert make_full_video(zf, str(tmp_path), str(tmp_path / "o.mp4")) is None
