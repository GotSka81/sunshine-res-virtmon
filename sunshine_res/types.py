"""Common type definitions for monitor and screen information."""

import json
from math import floor
from math import gcd
from pathlib import Path
from typing import NamedTuple
from typing import TypedDict
from typing import cast


class MonitorMode(TypedDict):
    """Generic abstraction for a monitor mode."""

    id: str | None
    width: int
    height: int
    fps: float


class MonitorInfo(TypedDict):
    """Generic a abstraction of a monitor."""

    output_name: str
    hdr: bool
    modes: list[MonitorMode]
    current_mode: MonitorMode


class ScreenSize(TypedDict):
    """Size of a screen."""

    width: int
    height: int


class ResolutionManager:
    """
    Base class for managing display resolution and HDR settings.

    This class serves as a blueprint for platform-specific resolution managers. Subclasses
    must implement `query_monitor_info` and `apply_mode` to interface with the display server.
    """

    def __init__(
        self,
        client_width: int,
        client_height: int,
        client_fps: int,
        client_hdr: bool = False,
        supersample_scale: float = 1.0,
    ) -> None:
        self.client_aspect_by_nine: int = floor(client_width / client_height * 9)
        # NOTE: Using floor here because we match to greater-than-or-equal resolutions later
        self.client_width: int = floor(client_width * supersample_scale)
        self.client_height: int = floor(client_height * supersample_scale)
        self.client_fps: int = client_fps
        self.client_hdr: bool = client_hdr
        self.last_mode: Path = Path("~/.config/sunshine/last_mode.json").expanduser()

    def query_monitor_info(self) -> MonitorInfo:  # pragma: no cover
        raise NotImplementedError()

    def apply_mode(
        self, output_name: str, mode: MonitorMode, hdr: bool = False
    ) -> None:  # pragma: no cover
        raise NotImplementedError()

    def do(self) -> None:
        monitor_info = self.query_monitor_info()
        if (
            monitor_info["current_mode"]["width"],
            monitor_info["current_mode"]["height"],
        ) == (self.client_width, self.client_height):
            print("Resolution already matches.")
            return

        # Filter modes to matching resolution
        matched_modes = [
            mode
            for mode in monitor_info["modes"]
            if (
                mode["height"] == self.client_height
                and mode["width"] == self.client_width
            )
        ]

        if not matched_modes:
            # No exact modes, so look for the nearest match with the same aspect larger than the target resolution
            acceptable_resolution: None | ScreenSize = None
            for mode in monitor_info["modes"]:
                if (
                    floor(mode["width"] / mode["height"] * 9)
                    != self.client_aspect_by_nine
                ):
                    continue
                if (
                    mode["width"] >= self.client_width
                    and mode["height"] >= self.client_height
                ):
                    if acceptable_resolution is None or (
                        mode["width"] < acceptable_resolution["width"]
                        and mode["height"] < acceptable_resolution["height"]
                    ):
                        acceptable_resolution = {
                            "width": mode["width"],
                            "height": mode["height"],
                        }

            if acceptable_resolution is not None:
                matched_modes = [
                    mode
                    for mode in monitor_info["modes"]
                    if (
                        mode["height"] == acceptable_resolution["height"]
                        and mode["width"] == acceptable_resolution["width"]
                    )
                ]

        if not matched_modes:
            raise ValueError(
                f"Did not find mode matching {self.client_width}x{self.client_height} at {monitor_info['output_name']}"
            )

        # Sort by fps
        matched_modes.sort(key=lambda m: m["fps"])

        # Get the mode with the closest refreshrate but not below
        # Eg. if 25 is requested, and 20 and 30 are offered, return 30
        select_mode: MonitorMode = matched_modes[-1]
        for mode in matched_modes:
            select_mode = mode
            if mode["fps"] >= self.client_fps:
                break

        self.apply_mode(monitor_info["output_name"], select_mode, hdr=self.client_hdr)

        # Save original monitor info to file
        if not self.last_mode.parent.exists():
            self.last_mode.parent.mkdir(parents=True, exist_ok=True)

        _ = self.last_mode.write_text(json.dumps(monitor_info))

    def undo(self) -> None:
        # Check previous mode
        if not self.last_mode.exists():
            return

        info: MonitorInfo = cast(MonitorInfo, json.loads(self.last_mode.read_text()))

        # Set the new display mode
        self.apply_mode(info["output_name"], info["current_mode"], hdr=info["hdr"])

        # Clean up file
        self.last_mode.unlink()

    def toggle(self) -> None:
        if self.last_mode.exists():
            self.undo()
        else:
            self.do()
