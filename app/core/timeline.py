"""
Session timeline utilities.

This module defines helper classes and functions for mapping absolute
timestamps (relative to a session's start) to a specific media file and
local time within that file. It leverages the durations recorded on
``MediaFile`` objects (if available) to construct a cumulative timeline
for each child session.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

from .project_loader import ChildSession, MediaFile


@dataclass
class SegmentInfo:
    """Container for segment timing information."""

    media: MediaFile
    start: float  # start time relative to session start (seconds)
    end: float    # end time relative to session start (seconds)


class SessionTimeline:
    """Construct a timeline for a child session based on media file durations."""

    def __init__(self, session: ChildSession) -> None:
        self.segments: List[SegmentInfo] = []
        current_start = 0.0
        for m in session.media_files:
            duration = None
            # Use duration from MediaFile if available, otherwise 0
            if m.duration is not None:
                duration = m.duration
            # For images or unknown durations assume 0 seconds; they can still
            # receive frame mappings if local_time falls exactly at start.
            seg_end = current_start + (duration or 0.0)
            self.segments.append(SegmentInfo(media=m, start=current_start, end=seg_end))
            current_start = seg_end

    def map_time(self, time_sec: float) -> Optional[Tuple[MediaFile, float]]:
        """Map a time offset (seconds) to a media file and local time.

        Args:
            time_sec: The offset in seconds relative to the session start.

        Returns:
            A tuple of (MediaFile, local_time) if ``time_sec`` falls within
            any segment. ``local_time`` is the time offset within the returned
            ``MediaFile``. Returns ``None`` if the time lies outside all
            segments.
        """
        for seg in self.segments:
            if time_sec < seg.start:
                # times earlier than the first segment start are not valid
                break
            if time_sec < seg.end or seg.media.duration is None:
                # time falls within this segment (or duration unknown, treat as match)
                local_time = time_sec - seg.start
                # Clamp negative local time to zero
                if local_time < 0:
                    local_time = 0.0
                return (seg.media, local_time)
        return None