from collections.abc import Generator
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from sunshine_res.cosmic import CosmicRandr
from sunshine_res.errors import CurrentModeNotFound
from sunshine_res.errors import OutputNotFound
from sunshine_res.types import MonitorMode


@pytest.fixture
def mock_check_output() -> Generator[MagicMock, None, None]:
    with patch("sunshine_res.cosmic.check_output") as mock:
        yield mock


@pytest.fixture
def mock_check_call() -> Generator[MagicMock, None, None]:
    with patch("sunshine_res.cosmic.check_call") as mock:
        yield mock


@pytest.fixture
def manager() -> CosmicRandr:
    return CosmicRandr(client_width=1920, client_height=1080, client_fps=60)


def test_parse_kdl_happy(manager: CosmicRandr, mock_check_output: MagicMock) -> None:
    kdl_input = """
    output "HDMI-1"
        mode 1920 1080 60000 current=#true
        mode 1280 720 60000
    """
    monitor_info = manager.parse_kdl(kdl_input)

    assert monitor_info["output_name"] == "HDMI-1"
    assert len(monitor_info["modes"]) == 2
    assert monitor_info["current_mode"]["width"] == 1920
    assert monitor_info["current_mode"]["height"] == 1080
    assert monitor_info["current_mode"]["fps"] == 60.0


def test_parse_kdl_no_current(
    manager: CosmicRandr, mock_check_output: MagicMock
) -> None:
    kdl_input = """
    output "HDMI-1"
        mode 1920 1080 60000
        mode 1280 720 60000
    """
    with pytest.raises(
        CurrentModeNotFound,
        match="Could not identify current mode for output named HDMI-1. Check cosmic-randr",
    ):
        _ = manager.parse_kdl(kdl_input)


def test_parse_kdl_display_not_found(
    manager: CosmicRandr, mock_check_output: MagicMock
) -> None:
    kdl_input = """
    output "HDMI-1"
        mode 1920 1080 60000 current=#true
        mode 1280 720 60000
    """
    manager.target_output = "HDMI-2"
    with pytest.raises(
        OutputNotFound, match="Could not find output named HDMI-2. Check cosmic-randr"
    ):
        _ = manager.parse_kdl(kdl_input)


def test_query_monitor_info(manager: CosmicRandr, mock_check_output: MagicMock) -> None:
    mock_check_output.return_value = b"""
    output "HDMI-1"
        mode 1920 1080 60000 current=#true
        mode 1280 720 60000
    """
    monitor_info = manager.query_monitor_info()

    assert monitor_info["output_name"] == "HDMI-1"
    assert len(monitor_info["modes"]) == 2
    assert monitor_info["current_mode"]["width"] == 1920
    assert monitor_info["current_mode"]["height"] == 1080
    assert monitor_info["current_mode"]["fps"] == 60.0


def test_parse_kdl_dual_display_default(
    manager: CosmicRandr, mock_check_output: MagicMock
) -> None:
    mock_check_output.return_value = b"""
    output "HDMI-1"
        mode 1920 1080 60000 current=#true
        mode 1280 720 60000
    output "HDMI-2"
        mode 1920 1080 60000
        mode 1280 720 60000 current=#true
    """
    monitor_info = manager.query_monitor_info()

    assert monitor_info["output_name"] == "HDMI-1"
    assert len(monitor_info["modes"]) == 2
    assert monitor_info["current_mode"]["width"] == 1920
    assert monitor_info["current_mode"]["height"] == 1080
    assert monitor_info["current_mode"]["fps"] == 60.0


def test_parse_kdl_dual_display_specified(
    manager: CosmicRandr, mock_check_output: MagicMock
) -> None:
    mock_check_output.return_value = b"""
    output "HDMI-1"
        mode 1920 1080 60000 current=#true
        mode 1280 720 60000
    output "HDMI-2"
        mode 1920 1080 60000
        mode 1280 720 60000 current=#true
    """
    manager.target_output = "HDMI-2"
    monitor_info = manager.query_monitor_info()

    assert monitor_info["output_name"] == "HDMI-2"
    assert len(monitor_info["modes"]) == 2
    assert monitor_info["current_mode"]["width"] == 1280
    assert monitor_info["current_mode"]["height"] == 720
    assert monitor_info["current_mode"]["fps"] == 60.0


@pytest.mark.parametrize(
    "mode,hdr,expected",
    [
        pytest.param(
            {
                "id": None,
                "width": 1920,
                "height": 1080,
                "fps": 60.0,
            },
            False,
            [
                "cosmic-randr",
                "mode",
                "HDMI-1",
                "1920",
                "1080",
                "--refresh",
                "60.0",
            ],
            id="standard mode",
        ),
        pytest.param(
            {
                "id": None,
                "width": 1920,
                "height": 1080,
                "fps": 60.0,
            },
            True,
            [
                "cosmic-randr",
                "mode",
                "HDMI-1",
                "1920",
                "1080",
                "--refresh",
                "60.0",
            ],
            id="standard mode (HDR is noop)",
        ),
    ],
)
def test_apply_mode(
    manager: CosmicRandr,
    mock_check_call: MagicMock,
    mode: MonitorMode,
    hdr: bool,
    expected: list[str],
) -> None:
    manager.apply_mode("HDMI-1", mode, hdr=hdr)
    mock_check_call.assert_called_once_with(expected)
