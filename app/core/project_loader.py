from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable, List

from .time_utils import parse_child_folder_start_time, parse_media_file_start_time


# Supported extensions for media files
VIDEO_EXT = {".mp4", ".avi", ".mf4"}
IMAGE_EXT = {".jpg", ".jpeg", ".png"}


@dataclass
class MediaFile:
    """
    Representation of a single media file with potential conversion information.

    Attributes:
        path: The original path to the media file.
        kind: "video" or "image".
        converted_path: If the file is an mf4 that has been converted to mp4, this stores the path
            to the converted file.
        frame_count: For video files, the total number of frames if known.
        fps: Frames per second for video files if known.
        duration: Duration of the media in seconds if known.
        start_time: A datetime representing the start timestamp of the media, derived
            from the file name. If no timestamp is found, this remains ``None``.
    """

    path: Path
    kind: str  # "video" or "image"
    converted_path: Path | None = None
    # Optional start time extracted from the file name. None if no timestamp is embedded.
    start_time: datetime | None = None
    # Frame metadata for video files. For image files these remain None.
    frame_count: int | None = None
    fps: float | None = None
    duration: float | None = None


@dataclass
class ChildSession:
    """A child session corresponds to a subfolder representing a session of continuous media files."""

    path: Path
    session_start: object | None
    media_files: List[MediaFile] = field(default_factory=list)


@dataclass
class ParentFolder:
    """Representation of a parent folder containing multiple child sessions."""

    path: Path
    child_sessions: List[ChildSession] = field(default_factory=list)


class ProjectLoader:
    """
    Load projects by scanning parent directories for child session folders and media files.
    Maintains the order as defined by folder names.
    """

    def load(self, parent_dirs: Iterable[str]) -> List[ParentFolder]:
        parents: List[ParentFolder] = []
        for directory in parent_dirs:
            p = Path(directory)
            if not p.exists():
                continue
            parent = ParentFolder(path=p)
            # Sort child directories by name (natural sort could be added later)
            child_dirs = [x for x in p.iterdir() if x.is_dir()]
            child_dirs.sort(key=lambda c: c.name)
            for child_dir in child_dirs:
                start_time = parse_child_folder_start_time(child_dir.name)
                session = ChildSession(path=child_dir, session_start=start_time)
                files: List[MediaFile] = []
                for f in child_dir.rglob("*"):
                    if not f.is_file():
                        continue
                    ext = f.suffix.lower()
                    if ext in VIDEO_EXT:
                        # Determine converted mp4 path for mf4 files
                        converted: Path | None = None
                        if ext == ".mf4":
                            mp4 = f.with_suffix(".mp4")
                            if mp4.exists():
                                converted = mp4
                        # Attempt to derive a start timestamp from the file name
                        st = parse_media_file_start_time(f.name)
                        media = MediaFile(path=f, kind="video", converted_path=converted, start_time=st)
                        # Attempt to read video metadata to obtain frame count, fps, and duration
                        try:
                            import cv2  # type: ignore
                            video_path = str(media.converted_path or media.path)
                            cap = cv2.VideoCapture(video_path)
                            if cap.isOpened():
                                frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
                                fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
                                cap.release()
                                # Assign metadata if valid
                                if frames > 0 and fps > 0:
                                    media.frame_count = int(frames)
                                    media.fps = float(fps)
                                    media.duration = media.frame_count / media.fps
                        except Exception:
                            # Silently ignore if cv2 is not available
                            pass
                        files.append(media)
                        # Create start time text file if start time is available
                        self._create_start_time_file(media)
                    elif ext in IMAGE_EXT:
                        # Create media for image and attempt to derive start time
                        st = parse_media_file_start_time(f.name)
                        img_media = MediaFile(path=f, kind="image", start_time=st)
                        files.append(img_media)
                        # Create start time text file for image if start time is available
                        self._create_start_time_file(img_media)
                # Sort files by path; maintain folder order first, then file names
                files.sort(key=lambda m: str(m.path))
                if files:
                    session.media_files = files
                    parent.child_sessions.append(session)
            parents.append(parent)
        return parents

    def _create_start_time_file(self, media: MediaFile) -> None:
        """
        Create a text file alongside the media file encoding the start timestamp and file name.

        The output file will be named ``<start_time>_<original_filename>.txt`` and will contain a
        single line in the format ``<original_filename>,<start_time>``. If the file already exists,
        it will be overwritten.

        Args:
            media: The MediaFile for which to create the start time file. Only operates
                if ``media.start_time`` is not None.
        """
        if not media.start_time:
            return
        # Format start time as yyyy-mm-dd-hh-mm-ss
        from datetime import datetime

        # Convert to datetime if necessary
        st = media.start_time
        if not isinstance(st, datetime):
            return
        start_str = st.strftime("%Y-%m-%d-%H-%M-%S")
        out_name = f"{start_str}_{media.path.name}.txt"
        out_path = media.path.with_name(out_name)
        try:
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(f"{media.path.name},{start_str}\n")
        except Exception:
            # Fail silently if write is not possible
            pass