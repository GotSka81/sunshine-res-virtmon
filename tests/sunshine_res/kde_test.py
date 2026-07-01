from collections.abc import Generator
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from sunshine_res.errors import CurrentModeNotFound
from sunshine_res.errors import OutputNotFound
from sunshine_res.kde import KscreenDoctor
from sunshine_res.resolution_manager import MonitorMode


@pytest.fixture
def mock_check_output() -> Generator[MagicMock, None, None]:
    with patch("sunshine_res.kde.check_output") as mock:
        yield mock


@pytest.fixture
def mock_check_call() -> Generator[MagicMock, None, None]:
    with patch("sunshine_res.kde.check_call") as mock:
        yield mock


@pytest.fixture
def manager() -> KscreenDoctor:
    return KscreenDoctor(client_width=1920, client_height=1080, client_fps=60)


def test_query_monitor_info(
    manager: KscreenDoctor, mock_check_output: MagicMock
) -> None:
    mock_check_output.return_value = b"""
    {
        "outputs": [
            {
                "id": 0,
                "name": "HDMI-1",
                "modes": [
                    {
                        "id": 1,
                        "name": "1920x1080",
                        "size": {"width": 1920, "height": 1080},
                        "refreshRate": 60.0
                    },
                    {
                        "id": 2,
                        "name": "1280x720",
                        "size": {"width": 1280, "height": 720},
                        "refreshRate": 60.0
                    }
                ],
                "currentModeId": 1,
                "hdr": false
            }
        ],
        "screen": {
            "id": 0,
            "name": "Screen 1"
        }
    }
    """
    monitor_info = manager.query_monitor_info()

    assert monitor_info["output_name"] == "HDMI-1"
    assert len(monitor_info["modes"]) == 2
    assert monitor_info["current_mode"]["width"] == 1920
    assert monitor_info["current_mode"]["height"] == 1080
    assert monitor_info["current_mode"]["fps"] == 60.0


def test_query_monitor_info_missing_target(
    manager: KscreenDoctor, mock_check_output: MagicMock
) -> None:
    mock_check_output.return_value = b"""
    {
        "outputs": [
            {
                "id": 0,
                "name": "HDMI-1",
                "modes": [
                    {
                        "id": 1,
                        "name": "1920x1080",
                        "size": {"width": 1920, "height": 1080},
                        "refreshRate": 60.0
                    },
                    {
                        "id": 2,
                        "name": "1280x720",
                        "size": {"width": 1280, "height": 720},
                        "refreshRate": 60.0
                    }
                ],
                "currentModeId": 1,
                "hdr": false
            }
        ],
        "screen": {
            "id": 0,
            "name": "Screen 1"
        }
    }
    """
    manager.target_output = "HDMI-2"
    with pytest.raises(
        OutputNotFound, match="Could not find output named HDMI-2. Check kscreen-doctor"
    ):
        monitor_info = manager.query_monitor_info()


def test_query_monitor_info_multi_output(
    manager: KscreenDoctor, mock_check_output: MagicMock
) -> None:
    mock_check_output.return_value = b"""
    {
        "outputs": [
            {
                "id": 0,
                "name": "HDMI-1",
                "modes": [
                    {
                        "id": 1,
                        "name": "1920x1080",
                        "size": {"width": 1920, "height": 1080},
                        "refreshRate": 60.0
                    },
                    {
                        "id": 2,
                        "name": "1280x720",
                        "size": {"width": 1280, "height": 720},
                        "refreshRate": 60.0
                    }
                ],
                "currentModeId": 1,
                "hdr": false
            },
            {
                "id": 0,
                "name": "HDMI-2",
                "modes": [
                    {
                        "id": 1,
                        "name": "1920x1080",
                        "size": {"width": 1920, "height": 1080},
                        "refreshRate": 60.0
                    },
                    {
                        "id": 2,
                        "name": "1280x720",
                        "size": {"width": 1280, "height": 720},
                        "refreshRate": 60.0
                    }
                ],
                "currentModeId": 2,
                "hdr": false
            }
        ],
        "screen": {
            "id": 0,
            "name": "Screen 1"
        }
    }
    """
    monitor_info = manager.query_monitor_info()

    assert monitor_info["output_name"] == "HDMI-1"
    assert len(monitor_info["modes"]) == 2
    assert monitor_info["current_mode"]["width"] == 1920
    assert monitor_info["current_mode"]["height"] == 1080
    assert monitor_info["current_mode"]["fps"] == 60.0


def test_query_monitor_info_multi_output_target_name(
    manager: KscreenDoctor, mock_check_output: MagicMock
) -> None:
    mock_check_output.return_value = b"""
    {
        "outputs": [
            {
                "id": 0,
                "name": "HDMI-1",
                "modes": [
                    {
                        "id": 1,
                        "name": "1920x1080",
                        "size": {"width": 1920, "height": 1080},
                        "refreshRate": 60.0
                    },
                    {
                        "id": 2,
                        "name": "1280x720",
                        "size": {"width": 1280, "height": 720},
                        "refreshRate": 60.0
                    }
                ],
                "currentModeId": 1,
                "hdr": false
            },
            {
                "id": 0,
                "name": "HDMI-2",
                "modes": [
                    {
                        "id": 1,
                        "name": "1920x1080",
                        "size": {"width": 1920, "height": 1080},
                        "refreshRate": 60.0
                    },
                    {
                        "id": 2,
                        "name": "1280x720",
                        "size": {"width": 1280, "height": 720},
                        "refreshRate": 60.0
                    }
                ],
                "currentModeId": 2,
                "hdr": false
            }
        ],
        "screen": {
            "id": 0,
            "name": "Screen 1"
        }
    }
    """
    manager.target_output = "HDMI-2"
    monitor_info = manager.query_monitor_info()

    assert monitor_info["output_name"] == "HDMI-2"
    assert len(monitor_info["modes"]) == 2
    assert monitor_info["current_mode"]["width"] == 1280
    assert monitor_info["current_mode"]["height"] == 720
    assert monitor_info["current_mode"]["fps"] == 60.0


def test_query_monitor_info_no_current_mode(
    manager: KscreenDoctor, mock_check_output: MagicMock
) -> None:
    mock_check_output.return_value = b"""
    {
        "outputs": [
            {
                "id": 0,
                "name": "HDMI-1",
                "modes": [
                    {
                        "id": 1,
                        "name": "1920x1080",
                        "size": {"width": 1920, "height": 1080},
                        "refreshRate": 60.0
                    }
                ],
                "currentModeId": 2,
                "hdr": false
            }
        ],
        "screen": {
            "id": 0,
            "name": "Screen 1"
        }
    }
    """
    with pytest.raises(
        CurrentModeNotFound,
        match="Could not identify current mode for output named HDMI-1. Check kscreen-doctor",
    ):
        _ = manager.query_monitor_info()


@pytest.mark.parametrize(
    "mode,hdr,expected",
    [
        pytest.param(
            {
                "id": "1920x1080",
                "width": 1920,
                "height": 1080,
                "fps": 60.0,
            },
            False,
            [
                "kscreen-doctor",
                "output.HDMI-1.mode.1920x1080",
                "output.HDMI-1.hdr.disable",
            ],
            id="standard mode",
        ),
        pytest.param(
            {
                "id": "1920x1080",
                "width": 1920,
                "height": 1080,
                "fps": 60.0,
            },
            True,
            [
                "kscreen-doctor",
                "output.HDMI-1.mode.1920x1080",
                "output.HDMI-1.hdr.enable",
            ],
            id="hdr mode",
        ),
    ],
)
def test_apply_mode(
    manager: KscreenDoctor,
    mock_check_call: MagicMock,
    mode: MonitorMode,
    hdr: bool,
    expected: list[str],
) -> None:
    manager.apply_mode("HDMI-1", mode, hdr=hdr)
    mock_check_call.assert_called_once_with(expected)
