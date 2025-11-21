import re
from subprocess import check_call
from subprocess import check_output
from typing import override

from sunshine_res.types import MonitorInfo
from sunshine_res.types import MonitorMode
from sunshine_res.types import ResolutionManager


class GnomeRandr(ResolutionManager):
    """Designed to work with gnome-randr-rust."""

    def parse_randr(self, out: str) -> MonitorInfo:
        output_name = ""
        modes: list[MonitorMode] = []
        current_mode: MonitorMode | None = None

        for line in out.split("\n"):
            line = line.rstrip()

            if not line:
                continue

            if output := re.match(r"^([A-Z][a-zA-Z]+-[0-9]+)", line):
                print("detected output", output.group(1))
                if output_name and output_name != output.group(1):
                    raise ValueError(
                        "Detected multiple output names. Check gnome-randr."
                    )
                output_name = output.group(1)
            elif mode := re.match(
                r"^[ \t]+([0-9]+x[0-9]+@[0-9]+[\.[0-9]+]?)[ \t]+([0-9]+)x([0-9]+)[ \t]+([0-9]+[\.[0-9]+]?)([+*]?)",
                line,
            ):
                this_mode = MonitorMode(
                    id=mode.group(1),
                    width=int(mode.group(2)),
                    height=int(mode.group(3)),
                    fps=round(float(mode.group(4))),
                )
                print("MODE: ", this_mode)
                modes.append(this_mode)
                if "*" in mode.group(5):
                    current_mode = this_mode
            else:
                print("unparsed:", line)

        if not current_mode:
            raise ValueError("Could not identify current mode. Check gnome-randr.")

        print("Current mode", current_mode)

        return MonitorInfo(
            output_name=output_name,
            hdr=False,
            modes=modes,
            current_mode=current_mode,
        )

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
