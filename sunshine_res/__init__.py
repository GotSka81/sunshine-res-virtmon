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

Usage:
sunshine-res [do/undo/auto]
"""

import os
import sys

from sunshine_res.cosmic import CosmicRandr
from sunshine_res.kde import KscreenDoctor
from sunshine_res.types import ResolutionManager

SUNSHINE_CLIENT_WIDTH = int(os.getenv("SUNSHINE_CLIENT_WIDTH", 1920))
SUNSHINE_CLIENT_HEIGHT = int(os.getenv("SUNSHINE_CLIENT_HEIGHT", 1080))
SUNSHINE_CLIENT_FPS = int(os.getenv("SUNSHINE_CLIENT_FPS", 60))
SUNSHINE_CLIENT_HDR = bool(os.getenv("SUNSHINE_CLIENT_HDR")) == True


DESKTOP_TO_CLASS: dict[str, type[ResolutionManager]] = {
    "KDE": KscreenDoctor,
    "COSMIC": CosmicRandr,
}


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

    # Find a manager class that matches
    manager: ResolutionManager
    for desktop in current_desktop.split(":"):
        if mc := DESKTOP_TO_CLASS.get(desktop):
            manager = mc(
                client_width=SUNSHINE_CLIENT_WIDTH,
                client_height=SUNSHINE_CLIENT_HEIGHT,
                client_fps=SUNSHINE_CLIENT_FPS,
                client_hdr=SUNSHINE_CLIENT_HDR,
            )
            break
    else:
        print(f"Could not find resolution manager for desktop {current_desktop}")
        exit(1)

    # Read the command from args
    command = ""
    if len(sys.argv) < 2:
        command = "auto"
    else:
        command = sys.argv[1]

    # Execute command in given manager
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
