"""
Utility functions for extracting timing information from media files
using ffprobe. These helpers wrap ffprobe via the subprocess module
to return lists of presentation timestamps (PTS) for each frame as
well as the overall duration of a video stream.

The functions defined here are designed to degrade gracefully if
``ffprobe`` is not available on the host system. In such cases the
functions will return ``None`` so that callers can fall back to
approximate frame timing (e.g. frame_count / fps) when necessary.

To install ffprobe on most systems you can install the full
``ffmpeg`` suite. On Debian-based systems this is provided by
``apt-get install ffmpeg``.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import List, Optional


def _run_ffprobe(cmd: list[str]) -> Optional[str]:
    """Run an ffprobe command and return its standard output as a string.

    Args:
        cmd: List of command line parts including the executable name and
            arguments. This helper inserts the ``ffprobe`` executable
            at the beginning if not already present.

    Returns:
        The stdout of the command if it succeeds, otherwise ``None``.
    """
    try:
        # Prepend ffprobe binary if not included
        if cmd[0] != "ffprobe":
            cmd = ["ffprobe"] + cmd
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return None
        return result.stdout.strip()
    except FileNotFoundError:
        # ffprobe not installed
        return None
    except Exception:
        return None


def get_frame_pts(file_path: str) -> Optional[List[float]]:
    """Extract a list of presentation timestamps (in seconds) for each frame.

    This uses ffprobe with ``-show_entries frame=pkt_pts_time`` to output
    the PTS for every decoded frame in the video stream. When ffprobe is
    unavailable or fails, this function returns ``None``.

    Args:
        file_path: The path to the video file.

    Returns:
        A list of floats representing the PTS time of each frame in
        ascending order, or ``None`` if the extraction fails.
    """
    p = Path(file_path)
    if not p.exists():
        return None
    output = _run_ffprobe(
        [
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "frame=pkt_pts_time",
            "-of",
            "csv=p=0",
            str(file_path),
        ]
    )
    if output is None:
        return None
    pts_list: list[float] = []
    for line in output.splitlines():
        if not line:
            continue
        try:
            pts_list.append(float(line.strip()))
        except ValueError:
            continue
    return pts_list if pts_list else None


def get_duration(file_path: str) -> Optional[float]:
    """Get the duration of a media file in seconds using ffprobe.

    Args:
        file_path: The path to the video file.

    Returns:
        A float value containing the duration in seconds, or ``None`` if
        the duration cannot be determined.
    """
    p = Path(file_path)
    if not p.exists():
        return None
    output = _run_ffprobe(
        [
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(file_path),
        ]
    )
    if output is None:
        return None
    try:
        return float(output.strip())
    except ValueError:
        return None