from __future__ import annotations

import re
from datetime import datetime


# Regular expression to capture a timestamp pattern from folder names.
FOLDER_TS_RE = re.compile(r"(\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2})")


def parse_child_folder_start_time(folder_name: str) -> datetime | None:
    """
    Extract a datetime from a folder name based on the pattern
    yyyy-mm-dd-hh-mm-ss. Returns None if not found.
    """
    match = FOLDER_TS_RE.search(folder_name)
    if not match:
        return None
    timestamp_str = match.group(1)
    return datetime.strptime(timestamp_str, "%Y-%m-%d-%H-%M-%S")

# Additional helper to extract a start timestamp from a media file name.
#
# Some media files are named with a pattern like ``YYYY-MM-DD-HH-MM-SS``
# embedded somewhere in the filename (e.g. ``2025-01-01-12-00-00_video.mp4``).
# When such a pattern is present, the timestamp is parsed as a datetime
# (naive, assumed local time). If no timestamp pattern is found, None
# is returned.
def parse_media_file_start_time(file_name: str) -> datetime | None:
    """
    Attempt to extract a timestamp from a media file name using the
    same pattern as folder names. Returns a datetime if found or
    ``None`` otherwise.

    Args:
        file_name: The name of the media file (not including path).

    Returns:
        A naive ``datetime`` object if a timestamp is found in the name,
        otherwise ``None``.
    """
    m = FOLDER_TS_RE.search(file_name)
    if not m:
        return None
    ts_str = m.group(1)
    try:
        return datetime.strptime(ts_str, "%Y-%m-%d-%H-%M-%S")
    except Exception:
        return None


def parse_media_file_start_time(file_name: str) -> datetime | None:
    """
    Extract a datetime from a media file name based on the pattern
    ``yyyy-mm-dd-hh-mm-ss``. Returns None if not found or parsing fails.

    Args:
        file_name: The name of the media file (not the full path).

    Returns:
        A ``datetime`` object if the file name contains a timestamp; otherwise ``None``.
    """
    match = FOLDER_TS_RE.search(file_name)
    if not match:
        return None
    timestamp_str = match.group(1)
    try:
        return datetime.strptime(timestamp_str, "%Y-%m-%d-%H-%M-%S")
    except Exception:
        return None