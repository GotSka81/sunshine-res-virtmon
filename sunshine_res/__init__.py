"""
Resolution Management Module

This module provides a system to dynamically adjust display resolution and HDR settings
based on the user's desktop environment (KDE or Cosmic). It supports command-line
operations to 'do' (apply a resolution), 'undo' (revert to original), or 'auto' (toggle
between modes). The module uses platform-specific tools (kscreen-doctor for KDE,
cosmic-randr for Cosmic) to interface with the display server.

Key Features:
- Auto-detects desktop environment (KDE/Cosmic)
- Manages resolution and HDR settings
- Persistent state tracking for 'undo' operations
- Supports dynamic virtual display creation

Usage:
sunshine-res [do/undo/auto] [--virtual]
"""

import argparse
import os
import sys
from argparse import Namespace
from typing import NamedTuple
from typing import cast

from sunshine_res.cosmic import CosmicRandr
from sunshine_res.gnome import GnomeRandr
from sunshine_res.kde import KscreenDoctor
from sunshine_res.resolution_manager import ResolutionManager
from sunshine_res.resolution_manager import VirtualDisplayManager

SUNSHINE_CLIENT_WIDTH = int(os.getenv("SUNSHINE_CLIENT_WIDTH", 1920))
SUNSHINE_CLIENT_HEIGHT = int(os.getenv("SUNSHINE_CLIENT_HEIGHT", 1080))
SUNSHINE_CLIENT_FPS = int(os.getenv("SUNSHINE_CLIENT_FPS", 60))
SUNSHINE_CLIENT_HDR = bool(os.getenv("SUNSHINE_CLIENT_HDR")) == True


DESKTOP_TO_CLASS: dict[str, type[ResolutionManager]] = {
    "KDE": KscreenDoctor,
    "COSMIC": CosmicRandr,
    "GNOME": GnomeRandr,
}


class SunshineResArgs(NamedTuple):
    command: str
    supersample: float
    target_output: str | None
    virtual: bool


def parse_args(sys_argv: list[str]) -> SunshineResArgs:
    parser = argparse.ArgumentParser(
        "sunshine-res", description="Sunshine Resolution Manager"
    )

    _ = parser.add_argument(
        "command",
        type=str,
        nargs="?",
        default="auto",
        help="Command to execute: do, undo, auto (default: auto)",
    )

    _ = parser.add_argument(
        "-s",
        "--supersample",
        type=float,
        default=1.0,
        help="Supersampling scale factor (default: 1.0, disabled)",
    )

    _ = parser.add_argument(
        "-o",
        "--target-output",
        type=str,
        default=None,
        help="Target output for resolution updates (default: first display)",
    )

    _ = parser.add_argument(
        "-v",
        "--virtual",
        action="store_true",
        help="Create and manage a virtual display instead of modifying a physical one",
    )

    parsed_args = parser.parse_args(sys_argv[1:])
    return SunshineResArgs(
        command=cast(str, parsed_args.command),
        supersample=cast(float, parsed_args.supersample),
        target_output=cast(str | None, parsed_args.target_output),
        virtual=cast(bool, parsed_args.virtual),
    )


def main() -> None:
    """Entry point for sunshine-res command line tool."""
    # Get the currently listed desktop
    current_desktop = os.getenv(
        "XDG_CURRENT_DESKTOP",
        os.getenv("XDG_SESSION_DESKTOP", os.getenv("SESSION_DESKTOP")),
    )
    if not current_desktop:
        print("ERROR: Could not determine current desktop")
        exit(1)

    args = parse_args(sys.argv)
    command = args.command

    # If the virtual flag is passed, bypass physical monitor manipulation completely
    if args.virtual:
        virtual_manager = VirtualDisplayManager(
            client_width=SUNSHINE_CLIENT_WIDTH,
            client_height=SUNSHINE_CLIENT_HEIGHT,
            client_fps=SUNSHINE_CLIENT_FPS,
            client_hdr=SUNSHINE_CLIENT_HDR,
        )
        if command == "auto":
            virtual_manager.toggle()
        elif command == "do":
            virtual_manager.do()
        elif command == "undo":
            virtual_manager.undo()
        else:
            print(f"Unknown command {command}")
            exit(1)
        return

    # Find a physical manager class that matches
    manager: ResolutionManager
    for desktop in current_desktop.split(":"):
        if mc := DESKTOP_TO_CLASS.get(desktop.upper()):
            manager = mc(
                client_width=SUNSHINE_CLIENT_WIDTH,
                client_height=SUNSHINE_CLIENT_HEIGHT,
                client_fps=SUNSHINE_CLIENT_FPS,
                client_hdr=SUNSHINE_CLIENT_HDR,
                supersample_scale=args.supersample,
                target_output=args.target_output,
            )
            break
    else:
        print(f"Could not find resolution manager for desktop {current_desktop}")
        exit(1)

    # Execute command in given physical manager
    if command == "auto":
        manager.toggle()
    elif command == "do":
        manager.do()
    elif command == "undo":
        manager.undo()
    else:
        print(f"Unknown command {command}")
        exit(1)


if __name__ == "__main__":
    main()
