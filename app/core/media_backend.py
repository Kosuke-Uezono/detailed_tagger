from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import cv2
import numpy as np


@dataclass
class FrameData:
    """A container for a frame number and its BGR image."""

    frame_no: int
    image_bgr: np.ndarray


class MediaBackend:
    """
    Provides basic operations to open and navigate through video files using OpenCV.
    Step1 uses simple frame stepping and seeking by frame number or milliseconds.
    """

    def __init__(self) -> None:
        self.cap: cv2.VideoCapture | None = None
        self.path: Path | None = None
        self.frame_no: int = 0
        self.frame_count: int = 0
        self.fps: float = 0.0

        # A list of presentation timestamps for each frame, loaded via ffprobe.
        # If None, precise VFR mapping is not available. It will be lazily
        # populated when needed by calling ``load_frame_pts``.
        self.frame_pts: list[float] | None = None

        # Flag indicating whether we attempted to load frame_pts. Helps avoid
        # repeated probing on subsequent calls.
        self._pts_attempted: bool = False

    def open_video(self, path: str) -> None:
        """Open a video file for reading frames."""
        self.close()
        self.path = Path(path)
        self.cap = cv2.VideoCapture(str(self.path))
        if not self.cap.isOpened():
            raise RuntimeError(f"Failed to open video: {path}")
        self.frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        self.fps = float(self.cap.get(cv2.CAP_PROP_FPS) or 0.0)
        self.frame_no = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES) or 0)

        # Reset PTS information when opening a new file
        self.frame_pts = None
        self._pts_attempted = False

    def close(self) -> None:
        """Release any open video resource."""
        if self.cap is not None:
            self.cap.release()
        self.cap = None
        self.path = None
        self.frame_no = 0
        self.frame_count = 0
        self.fps = 0.0

        # Clear PTS data
        self.frame_pts = None
        self._pts_attempted = False

    def read_current(self) -> FrameData | None:
        """Read the current frame and return FrameData. Returns None on failure."""
        if self.cap is None:
            return None
        ok, frame = self.cap.read()
        if not ok:
            return None
        # Update internal frame number after reading
        self.frame_no = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES) or (self.frame_no + 1))
        return FrameData(frame_no=self.frame_no, image_bgr=frame)

    def read_frame_at(self, frame_no: int) -> FrameData | None:
        """
        Read a specific frame without advancing the internal position beyond that frame.

        This method seeks to ``frame_no``, decodes the frame, and then resets the
        capture's position back to the requested frame. It also updates
        ``self.frame_no`` to reflect the requested frame. This is useful for
        operations such as stepping backwards, where using ``seek_frame`` plus
        ``read_current`` would otherwise advance the internal pointer one frame ahead.

        Args:
            frame_no: The zero-based index of the frame to read.

        Returns:
            A ``FrameData`` containing the requested frame, or ``None`` if the frame
            could not be decoded.
        """
        if self.cap is None:
            return None
        # Clamp frame index to valid range
        total = self.frame_count
        if total:
            if frame_no < 0:
                frame_no = 0
            if frame_no >= total:
                frame_no = total - 1
        # Seek to target frame
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
        ok, frame = self.cap.read()
        if not ok:
            return None
        # Reset the capture back to the target frame to keep internal state consistent
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
        self.frame_no = frame_no
        return FrameData(frame_no=frame_no, image_bgr=frame)

    def seek_frame(self, frame_no: int) -> None:
        """Seek to a specific frame number (0-based index)."""
        if self.cap is None:
            return
        frame_no = max(0, frame_no)
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
        self.frame_no = frame_no

    def seek_msec(self, msec: float) -> None:
        """Seek to a position in milliseconds."""
        if self.cap is None:
            return
        self.cap.set(cv2.CAP_PROP_POS_MSEC, float(msec))
        self.frame_no = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES) or 0)

    def read_frame_at(self, frame_index: int) -> FrameData | None:
        """
        Decode and return the frame at the specified index without advancing the internal frame pointer.

        This method seeks to ``frame_index``, reads that frame, and then resets the underlying
        VideoCapture position back to ``frame_index`` so that subsequent reads begin from
        the same frame. The ``frame_no`` attribute is updated to ``frame_index``.

        Args:
            frame_index: Zero-based frame index to retrieve.

        Returns:
            A ``FrameData`` object if the frame was successfully decoded; otherwise ``None``.
        """
        if self.cap is None:
            return None
        # Clamp index within available frames
        if self.frame_count and frame_index >= self.frame_count:
            frame_index = self.frame_count - 1
        if frame_index < 0:
            frame_index = 0
        # Seek to the frame
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ok, frame = self.cap.read()
        if not ok:
            return None
        # Reset position back to the requested index
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        self.frame_no = frame_index
        return FrameData(frame_no=frame_index, image_bgr=frame)

    # VFR support -----------------------------------------------------------

    def load_frame_pts(self) -> None:
        """
        Load the presentation timestamps (PTS) for each frame in the current video.

        This method uses ``ffprobe`` via the helper in ``ffprobe_utils`` to
        extract a list of floating-point PTS values. If ffprobe is not
        available or fails, ``frame_pts`` remains ``None`` and callers should
        fall back to simple frame index estimation.
        """
        if self.cap is None or self.path is None:
            return
        if self._pts_attempted:
            return
        self._pts_attempted = True
        try:
            # Import lazily to avoid circular import issues
            from .ffprobe_utils import get_frame_pts

            pts_list = get_frame_pts(str(self.path))
            if pts_list:
                self.frame_pts = pts_list
        except Exception:
            # On any exception, leave frame_pts as None
            self.frame_pts = None

    def get_nearest_frame_index(self, time_sec: float) -> int:
        """
        Convert a presentation timestamp (in seconds) to the nearest frame index.

        If ``frame_pts`` is available (loaded via ``load_frame_pts``), this
        method performs a binary search to find the index of the PTS closest
        to ``time_sec``. Otherwise it falls back to using the average fps
        value to estimate the frame number.

        Args:
            time_sec: The time offset (seconds) within the current video file.

        Returns:
            The frame index (0-based) corresponding to the nearest PTS.
        """
        # Use precise mapping if PTS list has been loaded
        if self.frame_pts:
            pts = self.frame_pts
            # Binary search for nearest index
            import bisect
            pos = bisect.bisect_left(pts, time_sec)
            if pos <= 0:
                return 0
            if pos >= len(pts):
                return len(pts) - 1
            # Determine which of the neighbours is closer
            before = pts[pos - 1]
            after = pts[pos]
            if abs(after - time_sec) < abs(time_sec - before):
                return pos
            else:
                return pos - 1
        # Fallback: use average fps if available
        if self.fps > 0.0:
            idx = int(round(time_sec * self.fps))
            return max(0, min(idx, max(self.frame_count - 1, 0)))
        return 0