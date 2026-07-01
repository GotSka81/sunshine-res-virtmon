import re
from subprocess import check_call
from subprocess import check_output
from typing import override

from sunshine_res.errors import CurrentModeNotFound
from sunshine_res.errors import OutputNotFound
from sunshine_res.resolution_manager import MonitorInfo
from sunshine_res.resolution_manager import MonitorMode
from sunshine_res.resolution_manager import ResolutionManager


class GnomeRandr(ResolutionManager):
    """Designed to work with gnome-randr-rust."""

    def parse_randr(self, out: str) -> MonitorInfo:
        monitors: list[MonitorInfo] = []
        current_monitor: MonitorInfo | None = None

        empty_mode = MonitorMode(id="", width=0, height=0, fps=0)

        for line in out.split("\n"):
            line = line.rstrip()

            if not line:
                continue

            if output := re.match(r"^([A-Z][a-zA-Z]+-[0-9]+)", line):
                # We have a new monitor output
                current_monitor = MonitorInfo(
                    output_name=output.group(1),
                    modes=[],
                    # Set some values to be overwritten later
                    hdr=False,
                    current_mode=empty_mode,
                )
                monitors.append(current_monitor)

            elif mode := re.match(
                r"^[ \t]+([0-9]+x[0-9]+@[0-9]+[\.[0-9]+]?)[ \t]+([0-9]+)x([0-9]+)[ \t]+([0-9]+[\.[0-9]+]?)([+*]?)",
                line,
            ):
                if not current_monitor:
                    raise ValueError(
                        "Could not parse gnome-randr. Found a mode before we found an output"
                    )

                this_mode = MonitorMode(
                    id=mode.group(1),
                    width=int(mode.group(2)),
                    height=int(mode.group(3)),
                    fps=round(float(mode.group(4))),
                )
                current_monitor["modes"].append(this_mode)
                if "*" in mode.group(5):
                    current_monitor["current_mode"] = this_mode

        for monitor in monitors:
            if (
                self.target_output is None
                or self.target_output == monitor["output_name"]
            ):
                if monitor["current_mode"] == empty_mode:
                    raise CurrentModeNotFound("gnome-randr", monitor["output_name"])

                return monitor
        else:
            raise OutputNotFound("gnome-randr", self.target_output)

    @override
    def query_monitor_info(self) -> MonitorInfo:
        out = check_output(["gnome-randr", "query"])
        randr_info = self.parse_randr(out.decode())
        return randr_info

    @override
    def apply_mode(
        self, output_name: str, mode: MonitorMode, hdr: bool = False
    ) -> None:
        # gnome-rander modes should all have an ID
        assert mode["id"], "Expected an ID for the selected mode"

        _ = check_call(
            [
                "gnome-randr",
                "modify",
                output_name,
                "--mode",
                mode["id"],
            ]
        )
