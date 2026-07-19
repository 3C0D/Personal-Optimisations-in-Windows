"""
yt-dlp update manager.
Throttles updates to once per day maximum using a timestamp file.
Uses `uv pip install -U yt-dlp` because `yt-dlp -U` refuses to self-update
when the package was installed via pip (as it is here, since yt_dlp is
imported as a library). Running `yt-dlp -U` here would silently fail
with "You installed yt-dlp with pip..." and never actually update.
"""

import os
import time
import subprocess
import sys

from core.config import LAST_UPDATE_FILE, UPDATE_INTERVAL_SECONDS


def _read_last_update_time():
    """Read the timestamp of the last successful update."""
    try:
        if os.path.exists(LAST_UPDATE_FILE):
            with open(LAST_UPDATE_FILE, "r") as f:
                return float(f.read().strip())
    except (ValueError, OSError):
        pass
    return 0.0


def _write_last_update_time():
    """Write the current timestamp as last update time."""
    try:
        with open(LAST_UPDATE_FILE, "w") as f:
            f.write(str(time.time()))
    except OSError:
        pass


def update_yt_dlp_if_needed():
    """
    Update yt-dlp only if the last update was more than UPDATE_INTERVAL_SECONDS ago.
    Uses `uv pip install -U yt-dlp` because `yt-dlp -U` refuses to self-update
    when the package was installed via pip (as it is here, since yt_dlp is
    imported as a library). Running `yt-dlp -U` would silently fail with
    "You installed yt-dlp with pip..." and never actually update.
    """
    last_update = _read_last_update_time()
    elapsed = time.time() - last_update

    if elapsed < UPDATE_INTERVAL_SECONDS:
        hours_ago = elapsed / 3600
        print(f"\nyt-dlp: last updated {hours_ago:.0f}h ago, skipping check.")
        return

    try:
        print("\nChecking for yt-dlp updates...")
        print("Regular updates are necessary to bypass site API changes.")

        result = subprocess.run(
            ["uv", "pip", "install", "--python", sys.executable, "-U", "yt-dlp"],
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )

        output = (result.stdout + result.stderr).lower()
        if result.returncode == 0:
            if "audited" in output and "installed" not in output and "upgraded" not in output:
                print("yt-dlp is already up to date.")
            else:
                print("yt-dlp has been successfully updated.")
        else:
            print(f"Error updating yt-dlp: {output}")

        _write_last_update_time()

    except subprocess.TimeoutExpired:
        print("yt-dlp update check timed out, continuing...")
        _write_last_update_time()
    except Exception as e:
        print(f"Error checking yt-dlp updates: {e}")
