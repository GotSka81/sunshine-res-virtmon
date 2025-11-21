import json
import sys
from pathlib import Path
from tempfile import mktemp
from typing import Any

import pytest

# The production code lives in the package `sunshine_res`
from sunshine_res.types import MonitorInfo
from sunshine_res.types import MonitorMode
from sunshine_res.types import ResolutionManager
from sunshine_res.types import ScreenSize


class DummyResolutionManager(ResolutionManager):
    """
    A thin wrapper around :class:`ResolutionManager` that records calls to
    :py:meth:`apply_mode` and returns a pre‑defined monitor description.

    The real implementation is completely platform dependent – we only need
    the algorithm in :py:meth:`do` / :py:meth:`undo` / :py:meth:`toggle`.
    """

    def __init__(
        self, *args, monitor_info: MonitorInfo, last_mode: Path | None = None, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self._monitor_info: MonitorInfo = monitor_info

        # Replace the default config path with a temporary location so that
        # we do not touch the real user configuration.
        self.last_mode: Path = Path(mktemp(".json"))

        self.apply_calls: list[tuple[str, MonitorMode, bool]] = []

    # ----------------------------------------------------------------------
    #  Platform specific hooks
    # ----------------------------------------------------------------------
    def query_monitor_info(self) -> MonitorInfo:
        return self._monitor_info

    def apply_mode(
        self, output_name: str, mode: MonitorMode, hdr: bool = False
    ) -> None:
        self.apply_calls.append((output_name, mode, hdr))


# ----------------------------------------------------------------------
#  Helper utilities
# ----------------------------------------------------------------------
def _build_mode(
    width: int, height: int, fps: float, id_: str | None = None
) -> MonitorMode:
    return {"id": id_, "width": width, "height": height, "fps": fps}


def _build_monitor_info(
    modes: list[MonitorMode],
    current_mode: MonitorMode,
    output_name: str = "HDMI-1",
    hdr: bool = False,
) -> MonitorInfo:
    return {
        "output_name": output_name,
        "hdr": hdr,
        "modes": modes,
        "current_mode": current_mode,
    }


# ----------------------------------------------------------------------
#  Tests
# ----------------------------------------------------------------------
def test_constructor_initialises_attributes():
    mgr = DummyResolutionManager(
        1280,
        720,
        60,
        client_hdr=True,
        monitor_info=_build_monitor_info([], _build_mode(1280, 720, 60)),
    )
    assert mgr.client_width == 1280
    assert mgr.client_height == 720
    assert mgr.client_fps == 60
    assert mgr.client_hdr is True


def test_do_resolution_already_matches_exits(capsys):
    # Current mode matches requested resolution
    current = _build_mode(1920, 1080, 60)
    monitor_info = _build_monitor_info([current], current)
    mgr = DummyResolutionManager(1920, 1080, 60, monitor_info=monitor_info)

    mgr.do()

    out, err = capsys.readouterr()
    assert "Resolution already matches." in out
    assert not mgr.apply_calls  # nothing was applied


def test_do_no_matching_modes_raises_value_error():
    # No mode with the requested resolution
    modes = [_build_mode(1280, 720, 60), _build_mode(800, 600, 60)]
    monitor_info = _build_monitor_info(modes, modes[0])
    mgr = DummyResolutionManager(1920, 1080, 60, monitor_info=monitor_info)

    with pytest.raises(ValueError) as exc:
        mgr.do()

    assert "Did not find mode matching 1920x1080" in str(exc.value)


@pytest.mark.parametrize(
    "fps_requested, available_fps, expected_fps",
    [
        pytest.param(25, [20, 25, 30], 25, id="exact match exists"),
        pytest.param(27, [20, 25, 30], 30, id="first fps >= requested"),
        pytest.param(35, [20, 25, 30], 30, id="none above requested"),
    ],
)
def test_fps_selection(
    tmp_path: Path, fps_requested: int, available_fps: list[int], expected_fps: int
):
    # Build monitor modes that all match the requested resolution
    modes = [_build_mode(1920, 1080, fp) for fp in available_fps]
    current = _build_mode(1280, 720, 60)
    monitor_info = _build_monitor_info(modes, current)

    mgr = DummyResolutionManager(1920, 1080, fps_requested, monitor_info=monitor_info)
    mgr.do()

    # Only one apply_mode call should have been made
    assert len(mgr.apply_calls) == 1
    _, selected_mode, _ = mgr.apply_calls[0]
    assert selected_mode["fps"] == expected_fps


def test_do_writes_last_mode_file(tmp_path: Path):
    modes = [_build_mode(1920, 1080, 60)]
    current = _build_mode(1280, 720, 60)
    monitor_info = _build_monitor_info(modes, current)

    mgr = DummyResolutionManager(1920, 1080, 60, monitor_info=monitor_info)

    mgr.do()

    assert mgr.last_mode.exists()
    data = json.loads(mgr.last_mode.read_text())
    assert data == monitor_info


def test_do_creates_parent_directory_if_missing(tmp_path: Path):
    # Parent directory deliberately missing
    parent = tmp_path / "missing"
    if parent.exists():
        # ensure clean start
        parent.rmdir()
    modes = [_build_mode(1920, 1080, 60)]
    current = _build_mode(1280, 720, 60)
    monitor_info = _build_monitor_info(modes, current)

    mgr = DummyResolutionManager(1920, 1080, 60, monitor_info=monitor_info)
    mgr.last_mode = parent / "last_mode.json"

    mgr.do()

    assert parent.exists()
    assert mgr.last_mode.exists()


def test_undo_applies_stored_mode_and_removes_file(tmp_path: Path):
    modes = [_build_mode(1920, 1080, 60)]
    current = _build_mode(1280, 720, 60)
    monitor_info = _build_monitor_info(modes, current)

    mgr = DummyResolutionManager(1920, 1080, 60, monitor_info=monitor_info)
    # Pretend the file already contains the original monitor info
    mgr.last_mode.write_text(json.dumps(monitor_info))

    mgr.undo()

    # One call to apply_mode with the stored mode
    assert len(mgr.apply_calls) == 1
    output_name, mode, hdr = mgr.apply_calls[0]
    assert mode == monitor_info["current_mode"]
    assert hdr == monitor_info["hdr"]
    # File should be removed
    assert not mgr.last_mode.exists()


def test_undo_no_file_exits_gracefully():
    monitor_info = _build_monitor_info([], _build_mode(1280, 720, 60))
    mgr = DummyResolutionManager(1920, 1080, 60, monitor_info=monitor_info)

    mgr.undo()

    assert not mgr.apply_calls  # nothing was applied


def test_toggle_calls_do_when_no_backup():
    monitor_info = _build_monitor_info([], _build_mode(1280, 720, 60))
    mgr = DummyResolutionManager(1920, 1080, 60, monitor_info=monitor_info)

    called: list[str] = []

    def fake_do():
        called.append("do")

    def fake_undo():
        called.append("undo")

    mgr.do = fake_do  # type: ignore[assignment]
    mgr.undo = fake_undo  # type: ignore[assignment]

    # Ensure no backup file
    if mgr.last_mode.exists():
        mgr.last_mode.unlink()

    mgr.toggle()

    assert called == ["do"]


def test_toggle_calls_undo_when_backup_present(tmp_path: Path):
    monitor_info = _build_monitor_info([], _build_mode(1280, 720, 60))
    mgr = DummyResolutionManager(1920, 1080, 60, monitor_info=monitor_info)

    called: list[str] = []

    def fake_do():
        called.append("do")

    def fake_undo():
        called.append("undo")

    mgr.do = fake_do  # type: ignore[assignment]
    mgr.undo = fake_undo  # type: ignore[assignment]

    # Create a dummy backup file
    mgr.last_mode = tmp_path / "last_mode.json"
    mgr.last_mode.write_text("{}")

    mgr.toggle()

    assert called == ["undo"]
