import re
from subprocess import check_call
from subprocess import check_output
from typing import override

from sunshine_res.types import MonitorInfo
from sunshine_res.types import MonitorMode
from sunshine_res.types import ResolutionManager


class CosmicRandr(ResolutionManager):

    def parse_kdl(self, kdl_str: str) -> MonitorInfo:
        output_name = ""
        modes: list[MonitorMode] = []
        current_mode: MonitorMode | None = None

        for line in kdl_str.split("\n"):
            line = line.strip()

            if not line:
                continue

            if output := re.match(r'output\s+"(.+)"', line):
                if output_name and output_name != output.group(1):
                    raise ValueError(
                        "Detected multiple output names. Check cosmic-randr."
                    )
                output_name = output.group(1)
            elif mode := re.match(r"mode\s+(\d+)\s+(\d+)\s+(\d+)", line):
                this_mode = MonitorMode(
                    id=None,
                    width=int(mode.group(1)),
                    height=int(mode.group(2)),
                    fps=int(mode.group(3)) / 1000,
                )
                modes.append(this_mode)
                if "current=#true" in line:
                    current_mode = this_mode

        if not current_mode:
            raise ValueError("Could not identify current mode. Check cosmic-randr.")

        return MonitorInfo(
            output_name=output_name,
            hdr=False,
            modes=modes,
            current_mode=current_mode,
        )

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
