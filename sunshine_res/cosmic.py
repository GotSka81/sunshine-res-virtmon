import re
from subprocess import check_call
from subprocess import check_output
from typing import override

from sunshine_res.errors import CurrentModeNotFound
from sunshine_res.errors import OutputNotFound
from sunshine_res.resolution_manager import MonitorInfo
from sunshine_res.resolution_manager import MonitorMode
from sunshine_res.resolution_manager import ResolutionManager


class CosmicRandr(ResolutionManager):

    def parse_kdl(self, kdl_str: str) -> MonitorInfo:
        monitors: list[MonitorInfo] = []
        current_monitor: MonitorInfo | None = None

        empty_mode = MonitorMode(id="", width=0, height=0, fps=0)

        for line in kdl_str.split("\n"):
            line = line.strip()

            if not line:
                continue

            if output := re.match(r'output\s+"(.+)"', line):
                # We have a new monitor output
                current_monitor = MonitorInfo(
                    output_name=output.group(1),
                    modes=[],
                    # Set some values to be overwritten later
                    hdr=False,
                    current_mode=empty_mode,
                )
                monitors.append(current_monitor)

            elif mode := re.match(r"mode\s+(\d+)\s+(\d+)\s+(\d+)", line):
                if not current_monitor:
                    raise ValueError(
                        "Could not parse KDL. Found a mode before we found an output"
                    )

                # We've found a mode for the current monitor
                this_mode = MonitorMode(
                    id=None,
                    width=int(mode.group(1)),
                    height=int(mode.group(2)),
                    fps=int(mode.group(3)) / 1000,
                )
                current_monitor["modes"].append(this_mode)
                if "current=#true" in line:
                    current_monitor["current_mode"] = this_mode

        for monitor in monitors:
            if (
                self.target_output is None
                or self.target_output == monitor["output_name"]
            ):
                if monitor["current_mode"] == empty_mode:
                    raise CurrentModeNotFound("cosmic-randr", monitor["output_name"])

                return monitor
        else:
            raise OutputNotFound("cosmic-randr", self.target_output)

    @override
    def query_monitor_info(self) -> MonitorInfo:
        out = check_output(["cosmic-randr", "list", "--kdl"])
        cosmic_info = self.parse_kdl(out.decode())
        return cosmic_info

    @override
    def apply_mode(
        self, output_name: str, mode: MonitorMode, hdr: bool = False
    ) -> None:
        _ = check_call(
            [
                "cosmic-randr",
                "mode",
                output_name,
                str(mode["width"]),
                str(mode["height"]),
                "--refresh",
                str(mode["fps"]),
            ]
        )
