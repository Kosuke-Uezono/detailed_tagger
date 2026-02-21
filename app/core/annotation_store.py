from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import uuid
from typing import List, Optional


@dataclass
class AnnotationRecord:
    """A record of a single annotation on a frame."""

    annotation_id: str
    parent_folder: str
    child_folder: str
    media_file: str
    frame_no: int
    lv1: str
    lv2: str
    lv3: str
    created_at: str
    jst_time: Optional[str] = None
    gps_time: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    alt: Optional[float] = None
    simple_tag: Optional[str] = None
    linked_simple_idx: Optional[int] = None


class AnnotationStore:
    """
    In-memory storage for annotation records. Supports addition, undo, and removal.
    """

    def __init__(self) -> None:
        self.items: List[AnnotationRecord] = []
        # Each operation's added annotation ids for undo
        self._undo_stack: List[List[str]] = []

    def new_record(
        self,
        parent_folder: str,
        child_folder: str,
        media_file: str,
        frame_no: int,
        lv1: str,
        lv2: str,
        lv3: str,
        simple: Optional[dict] = None,
    ) -> AnnotationRecord:
        """Construct a new annotation record and return it (not stored yet)."""
        record_id = str(uuid.uuid4())
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        rec = AnnotationRecord(
            annotation_id=record_id,
            parent_folder=parent_folder,
            child_folder=child_folder,
            media_file=media_file,
            frame_no=frame_no,
            lv1=lv1,
            lv2=lv2,
            lv3=lv3,
            created_at=now,
        )
        if simple:
            rec.jst_time = simple.get("jst_time")
            rec.gps_time = simple.get("gps_time")
            rec.lat = simple.get("lat")
            rec.lon = simple.get("lon")
            rec.alt = simple.get("alt")
            rec.simple_tag = simple.get("tag")
            rec.linked_simple_idx = simple.get("idx")
        return rec

    def add_many(self, records: List[AnnotationRecord]) -> None:
        """Add multiple records to the store and record them in the undo stack."""
        self.items.extend(records)
        self._undo_stack.append([r.annotation_id for r in records])

    def list_all(self) -> List[AnnotationRecord]:
        """Return a copy of all stored annotations."""
        return list(self.items)

    def undo(self) -> int:
        """Undo the last annotation operation. Returns the number of removed annotations."""
        if not self._undo_stack:
            return 0
        ids_to_remove = set(self._undo_stack.pop())
        before_count = len(self.items)
        self.items = [rec for rec in self.items if rec.annotation_id not in ids_to_remove]
        return before_count - len(self.items)

    def remove_by_id(self, annotation_id: str) -> bool:
        """Remove a single annotation by id. Returns True if removed."""
        before_count = len(self.items)
        self.items = [rec for rec in self.items if rec.annotation_id != annotation_id]
        return len(self.items) != before_count