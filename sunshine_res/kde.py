import json
from subprocess import check_call
from subprocess import check_output
from typing import TypedDict
from typing import cast
from typing import override

from sunshine_res.errors import CurrentModeNotFound
from sunshine_res.errors import OutputNotFound
from sunshine_res.resolution_manager import MonitorInfo
from sunshine_res.resolution_manager import MonitorMode
from sunshine_res.resolution_manager import ResolutionManager
from sunshine_res.resolution_manager import ScreenSize


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

        output: KScreenOutput
        for o in screen_info["outputs"]:
            if self.target_output is None or o["name"] == self.target_output:
                output = o
                break
        else:
            raise OutputNotFound("kscreen-doctor", self.target_output)

        # Get current mode info for restoring
        modes: list[MonitorMode] = []
        current_mode: MonitorMode | None = None
        current_mode_id = output["currentModeId"]
        for mode in output["modes"]:
            new_mode = MonitorMode(
                id=mode["id"] or mode["name"],
                width=mode["size"]["width"],
                height=mode["size"]["height"],
                fps=mode["refreshRate"],
            )
            if mode["id"] == current_mode_id:
                current_mode = new_mode
            modes.append(new_mode)

        if not current_mode:
            raise CurrentModeNotFound("kscreen-doctor", output["name"])

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
