from collections.abc import Generator
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from sunshine_res.errors import CurrentModeNotFound
from sunshine_res.errors import OutputNotFound
from sunshine_res.gnome import GnomeRandr
from sunshine_res.resolution_manager import MonitorMode


@pytest.fixture
def mock_check_output() -> Generator[MagicMock, None, None]:
    with patch("sunshine_res.gnome.check_output") as mock:
        yield mock


@pytest.fixture
def mock_check_call() -> Generator[MagicMock, None, None]:
    with patch("sunshine_res.gnome.check_call") as mock:
        yield mock


@pytest.fixture
def manager() -> GnomeRandr:
    return GnomeRandr(client_width=1920, client_height=1080, client_fps=60)


def test_query_monitor_info(manager: GnomeRandr, mock_check_output: MagicMock) -> None:
    mock_check_output.return_value = b"""
supports-mirroring: true
layout-mode: physical
supports-changing-layout-mode: false
global-scale-required: false
legacy-ui-scaling-factor: 1

logical monitor 0:
x: 0, y: 0, scale: 1, rotation: normal, primary: yes
associated physical monitors:
    HDMI-1 DEL Inspiron 5348 0x002206f2

HDMI-1 DEL Inspiron 5348 0x002206f2
                  1920x1080@60	    1920x1080 	60.00*+   	[x1.00+, x2.00]
                   1280x720@59.99	1280x720  	59.99     	[x1.00+]
is-builtin: false
display-name: "Dell Inc. 23\""
    """
    monitor_info = manager.query_monitor_info()

    assert monitor_info["output_name"] == "HDMI-1"
    assert len(monitor_info["modes"]) == 2
    assert monitor_info["current_mode"]["width"] == 1920
    assert monitor_info["current_mode"]["height"] == 1080
    assert monitor_info["current_mode"]["fps"] == 60.0


def test_query_monitor_info_display_not_found(
    manager: GnomeRandr, mock_check_output: MagicMock
) -> None:
    mock_check_output.return_value = b"""
supports-mirroring: true
layout-mode: physical
supports-changing-layout-mode: false
global-scale-required: false
legacy-ui-scaling-factor: 1

logical monitor 0:
x: 0, y: 0, scale: 1, rotation: normal, primary: yes
associated physical monitors:
    HDMI-1 DEL Inspiron 5348 0x002206f2

HDMI-1 DEL Inspiron 5348 0x002206f2
                  1920x1080@60	    1920x1080 	60.00*+   	[x1.00+, x2.00]
                   1280x720@59.99	1280x720  	59.99     	[x1.00+]
is-builtin: false
display-name: "Dell Inc. 23\""
    """
    with pytest.raises(
        OutputNotFound, match="Could not find output named HDMI-2. Check gnome-randr"
    ):
        manager.target_output = "HDMI-2"
        _ = manager.query_monitor_info()


def test_query_monitor_info_multi_monitor_default(
    manager: GnomeRandr, mock_check_output: MagicMock
) -> None:
    mock_check_output.return_value = b"""
supports-mirroring: true
layout-mode: physical
supports-changing-layout-mode: false
global-scale-required: false
legacy-ui-scaling-factor: 1

logical monitor 0:
x: 0, y: 0, scale: 1, rotation: normal, primary: yes
associated physical monitors:
    HDMI-1 DEL Inspiron 5348 0x002206f2
    HDMI-2 DEL Inspiron 5348 0x002206f2

HDMI-1 DEL Inspiron 5348 0x002206f2
                  1920x1080@60	1920x1080 	60.00*+   	[x1.00+, x2.00]
is-builtin: false
display-name: "Dell Inc. 23\""

HDMI-2 DEL Inspiron 5348 0x002206f2
                  1920x1080@60	1920x1080 	60.00*+   	[x1.00+, x2.00]
                   1280x720@59.99	1280x720  	59.99     	[x1.00+]
is-builtin: false
display-name: "Dell Inc. 23\""
    """
    monitor_info = manager.query_monitor_info()

    assert monitor_info["output_name"] == "HDMI-1"
    assert len(monitor_info["modes"]) == 1
    assert monitor_info["current_mode"]["width"] == 1920
    assert monitor_info["current_mode"]["height"] == 1080
    assert monitor_info["current_mode"]["fps"] == 60.0


def test_query_monitor_info_multi_monitor_specified(
    manager: GnomeRandr, mock_check_output: MagicMock
) -> None:
    mock_check_output.return_value = b"""
supports-mirroring: true
layout-mode: physical
supports-changing-layout-mode: false
global-scale-required: false
legacy-ui-scaling-factor: 1

logical monitor 0:
x: 0, y: 0, scale: 1, rotation: normal, primary: yes
associated physical monitors:
    HDMI-1 DEL Inspiron 5348 0x002206f2
    HDMI-2 DEL Inspiron 5348 0x002206f2

HDMI-1 DEL Inspiron 5348 0x002206f2
                   1280x720@59.99	1280x720  	59.99     	[x1.00+]
is-builtin: false
display-name: "Dell Inc. 23\""

HDMI-2 DEL Inspiron 5348 0x002206f2
                  1920x1080@60	1920x1080 	60.00*+   	[x1.00+, x2.00]
                   1280x720@59.99	1280x720  	59.99     	[x1.00+]
is-builtin: false
display-name: "Dell Inc. 23\""
    """
    manager.target_output = "HDMI-2"
    monitor_info = manager.query_monitor_info()

    assert monitor_info["output_name"] == "HDMI-2"
    assert len(monitor_info["modes"]) == 2
    assert monitor_info["current_mode"]["width"] == 1920
    assert monitor_info["current_mode"]["height"] == 1080
    assert monitor_info["current_mode"]["fps"] == 60.0


def test_query_monitor_info_no_current(
    manager: GnomeRandr, mock_check_output: MagicMock
) -> None:
    mock_check_output.return_value = b"""
supports-mirroring: true
layout-mode: physical
supports-changing-layout-mode: false
global-scale-required: false
legacy-ui-scaling-factor: 1

logical monitor 0:
x: 0, y: 0, scale: 1, rotation: normal, primary: yes
associated physical monitors:
    HDMI-1 DEL Inspiron 5348 0x002206f2

HDMI-1 DEL Inspiron 5348 0x002206f2
                  1920x1080@60	1920x1080 	60.00+   	[x1.00+, x2.00]
is-builtin: false
display-name: "Dell Inc. 23\""
    """
    with pytest.raises(
        CurrentModeNotFound,
        match="Could not identify current mode for output named HDMI-1. Check gnome-randr",
    ):
        _ = manager.query_monitor_info()


@pytest.mark.parametrize(
    "mode,hdr,expected",
    [
        pytest.param(
            {
                "id": "1920x1080@60",
                "width": 1920,
                "height": 1080,
                "fps": 60.0,
            },
            False,
            [
                "gnome-randr",
                "modify",
                "HDMI-1",
                "--mode",
                "1920x1080@60",
            ],
            id="standard mode",
        ),
        pytest.param(
            {
                "id": "1920x1080@60",
                "width": 1920,
                "height": 1080,
                "fps": 60.0,
            },
            True,
            [
                "gnome-randr",
                "modify",
                "HDMI-1",
                "--mode",
                "1920x1080@60",
            ],
            id="hdr mode (noop)",
        ),
    ],
)
def test_apply_mode(
    manager: GnomeRandr,
    mock_check_call: MagicMock,
    mode: MonitorMode,
    hdr: bool,
    expected: list[str],
) -> None:
    manager.apply_mode("HDMI-1", mode, hdr=hdr)
    mock_check_call.assert_called_once_with(expected)
