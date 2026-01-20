import json
from subprocess import check_call
from subprocess import check_output
from typing import TypedDict
from typing import cast
from typing import override

from sunshine_res.types import MonitorInfo
from sunshine_res.types import MonitorMode
from sunshine_res.types import ResolutionManager
from sunshine_res.types import ScreenSize


class KScreenMode(TypedDict):
    """Screen mode from kscreen-doctor."""

    id: str
    name: str
    refreshRate: float
    size: ScreenSize


class KScreenOutput(TypedDict):
    """Output device info from kscreen-doctor."""

    connected: bool
    currentModeId: str
    enabled: bool
    hdr: bool
    id: int
    modes: list[KScreenMode]
    name: str
    size: ScreenSize
    sizeMM: ScreenSize


class KScreenInfo(TypedDict):
    """Screen information from kscreen-doctor."""

    currentSize: ScreenSize
    id: int
    maxActiveOutputsCount: int
    maxSize: ScreenSize
    minSize: ScreenSize


class KScreenResult(TypedDict):
    """Result returned from kscreen-doctor."""

    outputs: list[KScreenOutput]
    screen: KScreenInfo


class KscreenDoctor(ResolutionManager):

    @override
    def query_monitor_info(self) -> MonitorInfo:
        out = check_output(["kscreen-doctor", "--json"])
        screen_info = cast(KScreenResult, json.loads(out))

        screen_id = screen_info["screen"]["id"]
        output = screen_info["outputs"][screen_id]

        # Get current mode info for restoring
        modes: list[MonitorMode] = []
        current_mode: MonitorMode | None = None
        current_mode_id = output["currentModeId"]
        for mode in output["modes"]:
            new_mode = MonitorMode(
                id=mode["name"],
                width=mode["size"]["width"],
                height=mode["size"]["height"],
                fps=mode["refreshRate"],
            )
            if mode["id"] == current_mode_id:
                current_mode = new_mode
            modes.append(new_mode)

        if not current_mode:
            raise ValueError(
                "Could not determine the current monitor mode. Check kscreen-doctor."
            )

        return MonitorInfo(
            output_name=output["name"],
            current_mode=current_mode,
            modes=modes,
            hdr=output.get("hdr", False),
        )

    @override
    def apply_mode(
        self, output_name: str, mode: MonitorMode, hdr: bool = False
    ) -> None:
        # Set the new display mode
        _ = check_call(
            [
                "kscreen-doctor",
                f"output.{output_name}.mode.{mode['id']}",
                f"output.{output_name}.hdr.{'enable' if hdr else 'disable'}",
            ]
        )
