"""Common type definitions for monitor and screen information."""

import json
import os
import subprocess
from collections.abc import Iterable
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
        target_output: str | None = None,
    ) -> None:
        self.client_aspect_by_nine: int = floor(client_width / client_height * 9)
        # NOTE: Using floor here because we match to greater-than-or-equal resolutions later
        self.client_width: int = floor(client_width * supersample_scale)
        self.client_height: int = floor(client_height * supersample_scale)
        self.client_fps: int = client_fps
        self.client_hdr: bool = client_hdr
        self.target_output: str | None = target_output
        self.last_mode: Path = Path("~/.config/sunshine/last_mode.json").expanduser()

    def query_monitor_info(self) -> MonitorInfo:  # pragma: no cover
        raise NotImplementedError()

    def apply_mode(
        self, output_name: str, mode: MonitorMode, hdr: bool = False
    ) -> None:  # pragma: no cover
        raise NotImplementedError()

    def _filter_aspect(self, modes: Iterable[MonitorMode]) -> list[MonitorMode]:
        """Returns modes from Iterable that match the target aspect ratio."""
        return [
            mode
            for mode in modes
            if floor(mode["width"] / mode["height"] * 9) == self.client_aspect_by_nine
        ]

    def _filter_exact_res(
        self, modes: Iterable[MonitorMode], target_res: ScreenSize | None = None
    ) -> list[MonitorMode]:
        """Returns modes from Iterable that match the target resolution."""
        if target_res:
            height = target_res["height"]
            width = target_res["width"]
        else:
            height = self.client_height
            width = self.client_width

        return [
            mode
            for mode in modes
            if (mode["height"] == height and mode["width"] == width)
        ]

    def _filter_nearest_larger(self, modes: Iterable[MonitorMode]) -> list[MonitorMode]:
        """Returns modes from Iterable that are the nearest larger resolution from target."""
        acceptable_resolution: None | ScreenSize = None

        for mode in modes:
            if (
                mode["width"] >= self.client_width
                and mode["height"] >= self.client_height
            ):
                # Resolution is greater than target
                if acceptable_resolution is None or (
                    mode["width"] < acceptable_resolution["width"]
                    and mode["height"] < acceptable_resolution["height"]
                ):
                    # Less than currently selected acceptable res
                    acceptable_resolution = {
                        "width": mode["width"],
                        "height": mode["height"],
                    }

        if acceptable_resolution is not None:
            return self._filter_exact_res(modes, acceptable_resolution)

        return []

    def _filter_highest_res(self, modes: Iterable[MonitorMode]) -> list[MonitorMode]:
        """Returns modes from Iterable that are the highest resolution from target."""
        acceptable_resolution: None | ScreenSize = None

        for mode in modes:
            if acceptable_resolution is None or (
                mode["width"] > acceptable_resolution["width"]
                and mode["height"] > acceptable_resolution["height"]
            ):
                # Resolution is greater than current
                acceptable_resolution = {
                    "width": mode["width"],
                    "height": mode["height"],
                }

        if acceptable_resolution is not None:
            return self._filter_exact_res(modes, acceptable_resolution)

        return []

    def do(self) -> None:
        monitor_info = self.query_monitor_info()
        if (
            monitor_info["current_mode"]["width"],
            monitor_info["current_mode"]["height"],
        ) == (self.client_width, self.client_height):
            print("Resolution already matches.")
            return

        # Filter modes to matching resolution
        matched_modes = self._filter_exact_res(monitor_info["modes"])

        if not matched_modes:
            aspect_modes = self._filter_aspect(monitor_info["modes"])
            matched_modes = self._filter_nearest_larger(
                aspect_modes
            ) or self._filter_highest_res(aspect_modes)

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


class VirtualDisplayManager:
    """
    Handles the lifecycle of virtual/headless displays across different 
    Linux Wayland compositors for Sunshine streaming.
    """
    def __init__(
        self,
        client_width: int,
        client_height: int,
        client_fps: int,
        client_hdr: bool = False,
    ) -> None:
        self.client_width = client_width
        self.client_height = client_height
        self.client_fps = client_fps
        self.client_hdr = client_hdr
        self.state_file = Path("~/.config/sunshine/virtual_display_state.json").expanduser()
        self.desktop_env = os.getenv("XDG_CURRENT_DESKTOP", "").lower()

    def do(self) -> None:
        """Creates a virtual display matching the Moonlight client's specifications."""
        output_name = None

        if "hyprland" in self.desktop_env:
            output_name = self._create_hyprland_display()
        elif "sway" in self.desktop_env:
            output_name = self._create_sway_display()
        elif "kde" in self.desktop_env or "plasma" in self.desktop_env:
            output_name = self._create_kde_display()
        else:
            print(f"Unsupported DE for Virtual Displays: {self.desktop_env}. Current support is restricted to Hyprland, Sway, and KDE.")
            return

        if output_name:
            self._save_state(output_name)
            print(f"Spawned virtual display {output_name} at {self.client_width}x{self.client_height}@{self.client_fps}Hz (HDR: {self.client_hdr})")

    def undo(self) -> None:
        """Removes the virtual display created during the 'do' phase."""
        state = self._load_state()
        if not state or 'output_name' not in state:
            print("No active virtual display found in state file. Skipping undo.")
            return

        output_name = state['output_name']
        
        if "hyprland" in self.desktop_env:
            subprocess.run(["hyprctl", "output", "remove", output_name], check=False)
        elif "sway" in self.desktop_env:
            subprocess.run(["swaymsg", "output", output_name, "unplug"], check=False)
        elif "kde" in self.desktop_env or "plasma" in self.desktop_env:
            subprocess.run(["killall", "krfb-virtualmonitor"], check=False)
        
        self._clear_state()
        print(f"Removed virtual display: {output_name}")

    def toggle(self) -> None:
        if self.state_file.exists():
            self.undo()
        else:
            self.do()

    def _create_hyprland_display(self) -> str:
        # Spawn the headless output
        result = subprocess.run(["hyprctl", "output", "create", "headless"], capture_output=True, text=True)
        # Parse output to capture the display name
        output_name = "HEADLESS-1" if "HEADLESS-1" in result.stdout else "HEADLESS-2"
        
        # Configure resolution, refresh rate, and scale
        monitor_cmd = f"{output_name},{self.client_width}x{self.client_height}@{self.client_fps},auto,1"
        
        # Inject HDR 10-bit color space if requested
        if self.client_hdr:
            monitor_cmd += ",bitdepth,10"
            
        subprocess.run(["hyprctl", "keyword", "monitor", monitor_cmd], check=True)
        return output_name

    def _create_sway_display(self) -> str:
        subprocess.run(["swaymsg", "create_output"], check=True)
        output_name = "HEADLESS-1"
        subprocess.run(["swaymsg", "output", output_name, "resolution", f"{self.client_width}x{self.client_height}@{self.client_fps}Hz"], check=True)
        return output_name

    def _create_kde_display(self) -> str:
        import time
        
        # 1. Spawn the virtual monitor process in the background
        # krfb-virtualmonitor requires password and port arguments even when not utilizing VNC
        subprocess.Popen([
            "krfb-virtualmonitor", 
            "--name", "sunshine-vm", 
            "--resolution", f"{self.client_width}x{self.client_height}",
            "--password", "moonlight", 
            "--port", "5905"
        ])
        
        # Give KWin a moment to initialize the display
        time.sleep(2)
        
        # 2. KDE prepends "Virtual-" to the assigned name
        output_name = "Virtual-sunshine-vm"
        
        # 3. Add custom mode and set refresh rate (unit is mHz for addCustomMode)
        mhz = int(self.client_fps * 1000)
        subprocess.run([
            "kscreen-doctor", 
            f"output.{output_name}.addCustomMode.{self.client_width}.{self.client_height}.{mhz}.full"
        ], check=False)
        
        # 4. Apply the exact mode and HDR state
        hdr_state = "enable" if self.client_hdr else "disable"
        subprocess.run([
            "kscreen-doctor", 
            f"output.{output_name}.mode.{self.client_width}x{self.client_height}@{self.client_fps}",
            f"output.{output_name}.hdr.{hdr_state}"
        ], check=False)
        
        return output_name

    def _save_state(self, output_name: str) -> None:
        if not self.state_file.parent.exists():
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps({'output_name': output_name}))

    def _load_state(self) -> dict | None:
        if self.state_file.exists():
            return json.loads(self.state_file.read_text())
        return None

    def _clear_state(self) -> None:
        if self.state_file.exists():
            self.state_file.unlink()
