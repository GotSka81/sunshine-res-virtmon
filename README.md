# Sunshine-Res-VirtMon (Virtual Monitor Fork)

> **Note:** The code in this fork was modified and enhanced with the assistance of Google's Gemini AI to add native Wayland virtual display support.

A resolution and display management tool for Sunshine and Moonlight. This fork expands upon the original `sunshine-res` project by adding the ability to dynamically spawn a virtual/headless monitor that matches the Moonlight client's requested resolution, refresh rate, and HDR specifications. 

To prevent physical displays from interfering with the stream, this fork automatically disables all physical displays when the virtual monitor is created, and securely restores them when the stream ends.

## Features
* **Virtual Display Generation:** Automatically creates a headless display on Wayland matching the Moonlight client's specs.
* **Smart Physical Display Management:** Takes a snapshot of your active physical displays, disables them during the stream, and restores them upon disconnect.
* **HDR Support:** Automatically toggles HDR on the virtual display if the Moonlight client requests it.
* **Supported Compositors:**
  * **KDE Plasma Wayland:** Utilizes `krfb-virtualmonitor` and `kscreen-doctor`.
  * **Hyprland:** Utilizes `hyprctl`.
  * **Sway:** Utilizes `swaymsg`.

## Prerequisites

Before installing, ensure your host machine has the required dependencies for your specific Desktop Environment:

**For KDE Plasma Wayland:**
You must have the KDE Remote Frame Buffer and KScreen tools installed. 
* Example (CachyOS): `sudo pacman -S krfb kscreen`
* Example (Nobara): `sudo dnf install krfb kscreen`
* **Important:** Sunshine's default capture method (`kms`) cannot capture KWin virtual displays. You must open your Sunshine Web UI, go to **Configuration -> Advanced**, and change **Force Capture Method** to `KWin Screencast`.

**For Hyprland / Sway:**
No extra packages are needed; the tool relies on the built-in `hyprctl` and `swaymsg` commands.

## Installation

It is recommended to install this tool using `pipx`.

1. Install the package directly from this repository:
   ```bash
   pipx install --force git+[https://github.com/GotSka81/sunshine-res-virtmon.git](https://github.com/GotSka81/sunshine-res-virtmon.git)
   ```

2. Ensure the installation directory is in your system PATH (if prompted by `pipx`):
   ```bash
   pipx ensurepath
   ```

## Configuration in Sunshine

To automate the display switching, you need to add the commands to your Sunshine application profiles.

1. Open the **Sunshine Web UI** (typically `https://localhost:47990`).
2. Navigate to the **Applications** tab.
3. Click **Edit** on the application profile you wish to use (e.g., "Desktop").
4. Scroll to the **Command Preparations** section.
5. In the **Do Command** field, add:
   ```bash
   sunshine-res do --virtual
   ```
6. In the **Undo Command** field, add:
   ```bash
   sunshine-res undo --virtual
   ```
7. Save the configuration. 

When you connect via Moonlight, Sunshine will now automatically generate the virtual display, route the stream to it, and disable your physical monitors until you disconnect.
