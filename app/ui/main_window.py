from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QSplitter,
    QFileDialog,
    QMessageBox,
)

from .top_bar import TopBar
from .media_view import MediaView
from .right_panel import RightPanel
from ..core.project_loader import ProjectLoader, MediaFile
from ..core.simple_tag_indexer import SimpleTagIndexer
from ..core.media_backend import MediaBackend
from ..core.annotation_store import AnnotationStore
from ..core.exporter import Exporter
from ..core.time_utils import parse_child_folder_start_time
from ..core.timeline import SessionTimeline
from datetime import datetime


class MainWindow(QMainWindow):
    """Main window of the tagging application."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Detailed Tagging Tool (Step1)")
        self.resize(1280, 800)

        # Instantiate UI components
        self.top_bar = TopBar()
        self.media_view = MediaView()
        self.right_panel = RightPanel()

        # Core components
        self.project_loader = ProjectLoader()
        self.simple_indexer = SimpleTagIndexer()
        self.media_backend = MediaBackend()
        self.annotation_store = AnnotationStore()
        self.exporter = Exporter()

        # Cache of SessionTimeline objects keyed by child session path.
        self._session_timelines: dict[Path, "SessionTimeline"] = {}

        # Track loaded context
        self.parents: list = []
        self.current_parent: Optional[Path] = None
        self.current_child: Optional[Path] = None
        self.current_media: Optional[Path] = None

        # Build UI and wire signals
        self._build_ui()
        self._connect_signals()

        # Container to hold dynamically created QShortcuts from tag configuration.
        # These will be cleared and recreated when a new config is loaded.
        self._dynamic_shortcuts: list[QShortcut] = []

        # Initialize frame info display
        self._update_frame_info()

    # UI construction
    def _build_ui(self) -> None:
        """Construct the main layout with top bar and split panels."""
        root = QWidget()
        layout = QVBoxLayout()
        splitter_v = QSplitter(Qt.Orientation.Vertical)
        splitter_h = QSplitter(Qt.Orientation.Horizontal)

        # Compose horizontal splitter (bottom area)
        splitter_h.addWidget(self.media_view)
        splitter_h.addWidget(self.right_panel)
        splitter_h.setStretchFactor(0, 7)
        splitter_h.setStretchFactor(1, 3)

        # Top area with top bar
        top_widget = QWidget()
        top_layout = QVBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.addWidget(self.top_bar)
        top_widget.setLayout(top_layout)

        # Compose vertical splitter
        splitter_v.addWidget(top_widget)
        splitter_v.addWidget(splitter_h)
        splitter_v.setStretchFactor(0, 1)
        splitter_v.setStretchFactor(1, 9)

        layout.addWidget(splitter_v)
        root.setLayout(layout)
        self.setCentralWidget(root)

    def _connect_signals(self) -> None:
        """Connect UI events to handler methods."""
        # Top bar actions
        self.top_bar.load_project_clicked.connect(self._handle_load_project)
        self.top_bar.load_simple_csv_clicked.connect(self._handle_load_simple_csv)
        self.top_bar.load_tag_config_clicked.connect(self._handle_load_tag_config)
        self.top_bar.export_clicked.connect(self._handle_export)

        # Search and tag actions
        self.right_panel.search_btn.clicked.connect(self._handle_search_simple)
        self.right_panel.simple_tag_selected.connect(self._handle_simple_tag_selected)
        self.right_panel.tag_apply_requested.connect(self._handle_apply_tag)
        # Range tagging
        self.right_panel.tag_apply_range_requested.connect(self._handle_apply_range_tag)
        # Undo and remove
        self.right_panel.undo_requested.connect(self._handle_undo)
        self.right_panel.annotation_remove_requested.connect(self._handle_annotation_remove)

        # Basic frame stepping shortcuts (D/A for next/prev frame). Additional shortcuts can be loaded later.
        QShortcut(QKeySequence("D"), self, activated=lambda: self._step_frames(+1))
        QShortcut(QKeySequence("A"), self, activated=lambda: self._step_frames(-1))

        # Frame stepping and next file from the right panel
        # Frame stepping: from right panel (deprecated) and media view
        self.right_panel.step_frames_requested.connect(self._handle_step_frames)
        # Connect frame stepping from the media view controls
        try:
            # MediaView may emit step_frames_requested when user presses a step button
            self.media_view.step_frames_requested.connect(self._handle_step_frames)
        except Exception:
            pass
        self.right_panel.next_file_requested.connect(self._handle_next_file)
        # Previous file signal
        self.right_panel.prev_file_requested.connect(self._handle_prev_file)

        # Set start time action from the top bar
        self.top_bar.set_start_time_clicked.connect(self._handle_set_start_time)

    # Handler methods for top bar
    def _handle_load_project(self) -> None:
        """Load a parent folder and populate sessions and media."""
        directory = QFileDialog.getExistingDirectory(
            self,
            "親フォルダを選択（1つずつ。複数は繰り返し選択）",
        )
        if not directory:
            return
        loaded = self.project_loader.load([directory])
        if not loaded:
            QMessageBox.warning(self, "Load", "フォルダから読み込めませんでした。")
            return
        self.parents.extend(loaded)
        # Take the first session for preview
        parent = loaded[0]
        self.current_parent = parent.path
        if not parent.child_sessions:
            QMessageBox.information(self, "Load", "子フォルダ内にメディアが見つかりません。")
            return
        session = parent.child_sessions[0]
        self.current_child = session.path
        if not session.media_files:
            QMessageBox.information(self, "Load", "メディアがありません。")
            return
        # Open first media file
        self._open_media(session.media_files[0])
        self.top_bar.set_status(
            f"Loaded parent: {parent.path.name} / child: {session.path.name}"
        )

    def _open_media(self, media_file: MediaFile) -> None:
        """Open and display a media file (image or video)."""
        path: Path = media_file.converted_path or media_file.path
        self.current_media = path
        if media_file.kind == "image":
            # Display image directly
            import cv2

            img = cv2.imread(str(path))
            if img is None:
                QMessageBox.warning(self, "Load", f"画像が読み込めません: {path}")
                return
            self.media_view.show_bgr(img)
            # Reset backend for images
            self.media_backend.close()
            # Update frame info for image (frame 0/1)
            self._update_frame_info()
        else:
            try:
                self.media_backend.open_video(str(path))
            except Exception as exc:
                QMessageBox.warning(self, "Load", str(exc))
                return
            frame = self.media_backend.read_current()
            if frame:
                self.media_view.show_bgr(frame.image_bgr)
            # Update frame info after opening video
            self._update_frame_info()

    def _handle_load_simple_csv(self) -> None:
        """Load simple tag CSV file."""
        file_path, _ = QFileDialog.getOpenFileName(self, "簡易タグCSVを選択", filter="CSV (*.csv)")
        if not file_path:
            return
        self.simple_indexer.load_csv(file_path)
        self.top_bar.set_status(f"Loaded simple tag CSV: {Path(file_path).name}")

    def _handle_load_tag_config(self) -> None:
        """Load tag configuration JSON file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "タグ設定JSONを選択", filter="JSON (*.json)"
        )
        if not file_path:
            return
        self.right_panel.load_tag_config(file_path)
        # After loading tag config, register any shortcuts defined in the ontology
        try:
            self._register_shortcuts()
        except Exception:
            # Ignore errors during shortcut registration
            pass
        self.top_bar.set_status(f"Loaded tag config: {Path(file_path).name}")

    def _handle_export(self) -> None:
        """Export current annotations to CSV in the parent folder."""
        if not self.current_parent:
            QMessageBox.information(self, "Export", "親フォルダが未選択です。")
            return
        out_path = Path(self.current_parent) / "detailed_tags.csv"
        self.exporter.export_csv(self.annotation_store, str(out_path))
        self.top_bar.set_status(f"Exported: {out_path.name}")

    # Search / tagging handlers
    def _handle_search_simple(self) -> None:
        keyword = self.right_panel.search_edit.text().strip()
        hits = self.simple_indexer.search(keyword)
        self.right_panel.set_search_results(
            [
                {"idx": rec.idx, "text": f"[{rec.idx}] {rec.jst_time} / {rec.tag}"}
                for rec in hits
            ]
        )
        self.top_bar.set_status(f"Search hits: {len(hits)}")

    def _handle_simple_tag_selected(self, idx: int) -> None:
        """
        Handle selection of a simple tag row. Stores the selected index and
        jumps to the corresponding frame in the current session if possible.
        """
        self._selected_simple_idx = idx
        # Jump to frame corresponding to this simple tag
        try:
            self._jump_to_simple_tag(idx)
        except Exception as e:
            # If mapping fails, still keep selection but warn user
            self.top_bar.set_status(f"Failed to jump: {e}")

    def _handle_apply_tag(self, lv1: str, lv2: str, lv3: str) -> None:
        """Add a new annotation to the store for the current frame."""
        if not (self.current_parent and self.current_child and self.current_media):
            return
        # Determine current frame number; if no video loaded, default to 0
        frame_no = self.media_backend.frame_no if self.media_backend.cap else 0
        # Get simple tag row if one is selected
        simple_info = None
        idx_attr = getattr(self, "_selected_simple_idx", None)
        if idx_attr is not None and self.simple_indexer.df is not None:
            row = self.simple_indexer.df.loc[idx_attr].to_dict()
            simple_info = {
                "idx": int(idx_attr),
                "jst_time": str(row.get("timestamp", "")),
                "gps_time": row.get("gps_time", None),
                "tag": str(row.get("tag", "")),
                "lat": row.get("lat", None),
                "lon": row.get("lon", None),
                "alt": row.get("alt", None),
            }
        # Create record and add to store
        record = self.annotation_store.new_record(
            parent_folder=str(self.current_parent),
            child_folder=str(self.current_child),
            media_file=str(self.current_media.name),
            frame_no=frame_no,
            lv1=lv1,
            lv2=lv2,
            lv3=lv3,
            simple=simple_info,
        )
        self.annotation_store.add_many([record])
        self.top_bar.set_status(
            f"Tagged: {lv1}/{lv2}/{lv3} @ frame {frame_no} (total={len(self.annotation_store.items)})"
        )
        # Update annotation list display
        self.right_panel.update_annotations(self.annotation_store.list_all())

    # Utility for stepping frames; positive or negative delta
    def _step_frames(self, delta: int) -> None:
        """Step forward or backward by delta frames and display the new frame."""
        if self.media_backend.cap is None:
            return
        # Clamp the target frame within [0, total-1]
        total = self.media_backend.frame_count
        if total > 0:
            target = self.media_backend.frame_no + delta
            if target < 0:
                target = 0
            if target >= total:
                target = total - 1
        else:
            target = max(0, self.media_backend.frame_no + delta)
        # Decode the frame at the target index without advancing the internal pointer
        frame = self.media_backend.read_frame_at(target)
        if frame:
            self.media_view.show_bgr(frame.image_bgr)
        # Update frame info display
        self._update_frame_info()

    def _handle_step_frames(self, delta: int) -> None:
        """Handle frame stepping requests from the right panel."""
        self._step_frames(delta)

    def _handle_next_file(self) -> None:
        """Handle a request to open the next media file in the current session."""
        # Find current session and current media index
        session = self._get_current_session()
        if session is None:
            return
        # Determine current media file index
        current_path = self.current_media
        if current_path is None:
            return
        # Identify the index of the current media
        current_idx = None
        for i, mf in enumerate(session.media_files):
            mf_path = mf.converted_path or mf.path
            if Path(mf_path) == current_path:
                current_idx = i
                break
        if current_idx is None:
            return
        # Check if next media exists
        if current_idx + 1 >= len(session.media_files):
            QMessageBox.information(
                self,
                "Next File",
                "次のファイルはありません。最後のファイルです。",
            )
            return
        next_mf = session.media_files[current_idx + 1]
        # Open the next media file and reset selection state
        self._open_media(next_mf)
        # Clear selected simple tag index as new file is loaded
        if hasattr(self, "_selected_simple_idx"):
            delattr(self, "_selected_simple_idx")
        # Update annotation display does not change
        # Update status bar
        self.top_bar.set_status(f"Opened next file: {next_mf.path.name}")
        # Update frame info display
        self._update_frame_info()

    def _handle_set_start_time(self) -> None:
        """
        Prompt the user to input a custom start timestamp for the current media file. If provided,
        update the ``start_time`` attribute of the MediaFile and write a corresponding text file.
        """
        from PyQt6.QtWidgets import QInputDialog
        # Determine the current media file
        mf = self._get_current_media_file()
        if mf is None:
            QMessageBox.information(self, "Start Time", "現在のメディアファイルが選択されていません。")
            return
        # Prompt for start time string
        current_value = ""
        if getattr(mf, "start_time", None):
            try:
                current_value = mf.start_time.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                current_value = ""
        text, ok = QInputDialog.getText(
            self,
            "開始時刻の入力",
            "開始時刻を入力してください (YYYY-MM-DD HH:MM:SS)",
            text=current_value,
        )
        if not ok or not text.strip():
            return
        inp = text.strip()
        # Try to parse input in multiple formats
        from datetime import datetime
        parsed = None
        for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d-%H-%M-%S", "%Y/%m/%d %H:%M:%S"]:
            try:
                parsed = datetime.strptime(inp, fmt)
                break
            except Exception:
                continue
        if parsed is None:
            QMessageBox.warning(self, "開始時刻", "入力された日時の形式が正しくありません。")
            return
        # Assign and write
        mf.start_time = parsed
        self._write_start_time_file(mf)
        self.top_bar.set_status(f"開始時刻を設定しました: {parsed.strftime('%Y-%m-%d %H:%M:%S')}")
        # Update frame info display
        self._update_frame_info()

    def _write_start_time_file(self, media_file):
        """
        Write a text file containing the media file name and start timestamp in the same directory.

        The file will be named ``<start_time>_<original_filename>.txt``. If writing fails,
        the error is silently ignored.
        """
        try:
            st = getattr(media_file, "start_time", None)
            if not st:
                return
            from datetime import datetime
            if not isinstance(st, datetime):
                return
            start_str = st.strftime("%Y-%m-%d-%H-%M-%S")
            out_name = f"{start_str}_{media_file.path.name}.txt"
            out_path = media_file.path.with_name(out_name)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(f"{media_file.path.name},{start_str}\n")
        except Exception:
            # Ignore any exceptions during writing
            pass

    def _handle_prev_file(self) -> None:
        """Handle a request to open the previous media file in the current session."""
        session = self._get_current_session()
        if session is None:
            return
        current_path = self.current_media
        if current_path is None:
            return
        current_idx = None
        for i, mf in enumerate(session.media_files):
            mf_path = mf.converted_path or mf.path
            if Path(mf_path) == current_path:
                current_idx = i
                break
        if current_idx is None:
            return
        if current_idx == 0:
            QMessageBox.information(
                self,
                "Previous File",
                "前のファイルはありません。最初のファイルです。",
            )
            return
        prev_mf = session.media_files[current_idx - 1]
        self._open_media(prev_mf)
        if hasattr(self, "_selected_simple_idx"):
            delattr(self, "_selected_simple_idx")
        self.top_bar.set_status(f"Opened previous file: {prev_mf.path.name}")
        self._update_frame_info()

    # Range tagging handler
    def _handle_apply_range_tag(self, start: int, end: int, lv1: str, lv2: str, lv3: str) -> None:
        """Apply the selected tag to a range of frames in the current media file."""
        if not (self.current_parent and self.current_child and self.current_media):
            return
        if start > end:
            start, end = end, start
        # Prepare simple info if a simple tag is selected
        simple_info = None
        idx_attr = getattr(self, "_selected_simple_idx", None)
        if idx_attr is not None and self.simple_indexer.df is not None:
            row = self.simple_indexer.df.loc[idx_attr].to_dict()
            simple_info = {
                "idx": int(idx_attr),
                "jst_time": str(row.get("timestamp", "")),
                "gps_time": row.get("gps_time", None),
                "tag": str(row.get("tag", "")),
                "lat": row.get("lat", None),
                "lon": row.get("lon", None),
                "alt": row.get("alt", None),
            }
        # Create records for each frame in the range
        records = []
        for frame_no in range(start, end + 1):
            rec = self.annotation_store.new_record(
                parent_folder=str(self.current_parent),
                child_folder=str(self.current_child),
                media_file=str(self.current_media.name),
                frame_no=frame_no,
                lv1=lv1,
                lv2=lv2,
                lv3=lv3,
                simple=simple_info,
            )
            records.append(rec)
        if records:
            self.annotation_store.add_many(records)
            self.top_bar.set_status(
                f"Tagged range {start}-{end} with {lv1}/{lv2}/{lv3} (total={len(self.annotation_store.items)})"
            )
            self.right_panel.update_annotations(self.annotation_store.list_all())

    # Undo handler
    def _handle_undo(self) -> None:
        removed = self.annotation_store.undo()
        if removed:
            self.top_bar.set_status(f"Undo: removed {removed} annotations (total={len(self.annotation_store.items)})")
        else:
            self.top_bar.set_status("Nothing to undo")
        self.right_panel.update_annotations(self.annotation_store.list_all())

    # Annotation removal handler
    def _handle_annotation_remove(self, annotation_id: str) -> None:
        removed = self.annotation_store.remove_by_id(annotation_id)
        if removed:
            self.top_bar.set_status(f"Removed annotation {annotation_id}")
        else:
            self.top_bar.set_status(f"Annotation {annotation_id} not found")
        self.right_panel.update_annotations(self.annotation_store.list_all())

    # Helper to find current child session object
    def _get_current_session(self):
        if not (self.current_parent and self.current_child):
            return None
        for pf in self.parents:
            if pf.path == self.current_parent:
                for session in pf.child_sessions:
                    if session.path == self.current_child:
                        return session
        return None

    # Helper to find the MediaFile object corresponding to the current media path
    def _get_current_media_file(self):
        if not (self.current_parent and self.current_child and self.current_media):
            return None
        session = self._get_current_session()
        if session is None:
            return None
        for mf in session.media_files:
            # Use converted_path if available, else path
            mp = mf.converted_path or mf.path
            try:
                if Path(mp) == self.current_media:
                    return mf
            except Exception:
                continue
        return None

    # Jump to the frame corresponding to a simple tag index
    def _jump_to_simple_tag(self, idx: int) -> None:
        """
        Map the selected simple tag's timestamp to a frame within the current session and jump to it.

        This implementation uses session timelines and precise presentation timestamps (PTS) if
        available. The timestamp in the simple tag (column ``timestamp``) is parsed as a
        naive datetime in the format ``YYYY-MM-DD HH:MM:SS``. The child session's start
        time is derived from its folder name via ``parse_child_folder_start_time``. The
        difference between these times yields ``delta`` seconds relative to the session
        start. That offset is mapped via a ``SessionTimeline`` to a specific
        ``MediaFile`` and local time within the file. If the media backend has a PTS
        list for the file, a binary search locates the nearest frame; otherwise a
        fallback using average FPS is employed.

        Raises a ``ValueError`` if the CSV is not loaded, the index is invalid,
        or the timestamp lies outside the session.
        """
        # Ensure current session is valid
        session = self._get_current_session()
        if session is None:
            raise ValueError("No session loaded")

        df = self.simple_indexer.df
        if df is None:
            raise ValueError("Simple tag CSV not loaded")
        if idx not in df.index:
            raise ValueError("Invalid tag index")
        row = df.loc[idx]
        ts_str = str(row.get("timestamp"))

        # Parse tag timestamp
        try:
            ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
        except Exception:
            raise ValueError(f"Invalid timestamp format: {ts_str}")

        # Parse session start (derived from folder name). If not present, cannot map
        session_start = parse_child_folder_start_time(session.path.name)
        if session_start is None:
            raise ValueError("Session start time not found in folder name")
        # Compute seconds offset from session start
        delta_sec = (ts - session_start).total_seconds()
        if delta_sec < 0:
            raise ValueError("Tag timestamp is before session start")

        # Obtain or build the timeline for this session
        timeline = self._session_timelines.get(session.path)
        if timeline is None:
            timeline = SessionTimeline(session)
            self._session_timelines[session.path] = timeline

        # Map time to media and local time within that media
        mapped = timeline.map_time(delta_sec)
        if not mapped:
            raise ValueError("Timestamp beyond session duration")
        target_media, local_time = mapped

        # Open the target media if it differs from the current one
        current_media_path = Path(self.current_media) if self.current_media else None
        if current_media_path is None or current_media_path != target_media.path:
            self.current_media = target_media.path
            # Use converted path if available
            self.media_backend.open_video(str(target_media.converted_path or target_media.path))

        # Load PTS list for the media if not loaded yet
        self.media_backend.load_frame_pts()
        # Compute nearest frame index
        frame_index = self.media_backend.get_nearest_frame_index(local_time)
        # Seek and read the target frame without advancing the pointer
        frame = self.media_backend.read_frame_at(frame_index)
        if frame:
            self.media_view.show_bgr(frame.image_bgr)
        # Update status bar
        self.top_bar.set_status(
            f"Jumped to {ts_str} -> {target_media.path.name}, frame {frame_index}"
        )
        # Update frame info display
        self._update_frame_info()

    def _update_frame_info(self) -> None:
        """
        Update the top bar with the current frame number, total frame count,
        and approximate timestamp of the current frame. If no video is loaded,
        clears the frame info display.
        """
        # If no video loaded, clear
        if self.media_backend.cap is None or self.media_backend.frame_count == 0:
            self.top_bar.set_frame_info("")
            return
        frame_no = self.media_backend.frame_no
        total = self.media_backend.frame_count
        # Ensure frame_no is within bounds
        if frame_no < 0:
            frame_no = 0
        if frame_no >= total:
            frame_no = total - 1
        # Determine relative timestamp (seconds from start of file)
        time_sec: float | None = None
        pts = self.media_backend.frame_pts
        if pts and 0 <= frame_no < len(pts):
            time_sec = pts[frame_no]
        else:
            fps = self.media_backend.fps
            if fps > 0:
                time_sec = frame_no / fps

        # Build time string: if media has a start_time, compute absolute timestamp
        time_str: str
        if time_sec is not None:
            # Try to get file start time
            mf = self._get_current_media_file()
            if mf and getattr(mf, "start_time", None):
                from datetime import timedelta

                st = mf.start_time
                # If st is not datetime, skip absolute time
                try:
                    absolute = st + timedelta(seconds=time_sec)
                    time_str = absolute.strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    time_str = f"{time_sec:.3f}s"
            else:
                time_str = f"{time_sec:.3f}s"
        else:
            time_str = "?"
        # Set frame info label: frame index is 1-based for display? or 0-based; we keep 0-based as internal
        self.top_bar.set_frame_info(f"{frame_no}/{total} ({time_str})")

    def _register_shortcuts(self) -> None:
        """
        Register keyboard shortcuts based on the currently loaded tag configuration.

        This method clears any previously registered dynamic shortcuts and creates
        new ``QShortcut`` instances for:

        * Detailed tag shortcuts defined in ``ontology.detail_shortcuts``
        * Global action shortcuts defined in ``ontology.shortcuts``

        If multiple actions or tags specify the same key sequence, a warning
        message is displayed in the status bar to alert the user of the
        conflict. Reserved keys already bound by the application (e.g. A/D)
        may still be overridden by the configuration.
        """
        # Clear existing dynamic shortcuts
        for sc in getattr(self, "_dynamic_shortcuts", []):
            try:
                # Disconnect and remove from parent to free resources
                sc.setParent(None)
            except Exception:
                pass
        self._dynamic_shortcuts = []

        # If no ontology loaded, nothing to register
        ontology = getattr(self.right_panel, "ontology", None)
        if not ontology:
            return

        used_keys: dict[str, str] = {}
        warnings: list[str] = []
        # Register detailed tag shortcuts
        for key, (lv1, lv2, lv3) in getattr(ontology, "detail_shortcuts", {}).items():
            if not key:
                continue
            # Detect duplicates
            if key in used_keys:
                warnings.append(key)
            used_keys[key] = f"tag:{lv1}/{lv2}/{lv3}"
            sc = QShortcut(QKeySequence(key), self)
            # Use default arguments to bind current values
            sc.activated.connect(lambda lv1=lv1, lv2=lv2, lv3=lv3: self._handle_apply_tag(lv1, lv2, lv3))
            self._dynamic_shortcuts.append(sc)
        # Register action shortcuts
        for action, key in getattr(ontology, "shortcuts", {}).items():
            if not key:
                continue
            # Detect duplicates
            if key in used_keys:
                warnings.append(key)
            used_keys[key] = f"action:{action}"
            # Determine the callback based on action name
            cb = None
            if action == "undo":
                cb = self._handle_undo
            elif action == "export":
                cb = self._handle_export
            elif action == "next_file":
                cb = self._handle_next_file
            elif action == "prev_file":
                cb = self._handle_prev_file
            elif action.startswith("step_"):
                # Expect pattern like step_<number>_<direction> where direction is 'forward' or 'back'
                parts = action.split("_")
                try:
                    # e.g. step_10_forward
                    if len(parts) >= 3:
                        n = int(parts[1])
                        direction = parts[2]
                        delta = n if direction.lower().startswith("forward") else -n
                        cb = lambda delta=delta: self._step_frames(delta)
                except Exception:
                    pass
            # Skip unrecognized actions
            if cb is None:
                continue
            sc = QShortcut(QKeySequence(key), self)
            sc.activated.connect(cb)
            self._dynamic_shortcuts.append(sc)
        # Display warning if duplicates found
        if warnings:
            dup_keys = ", ".join(sorted(set(warnings)))
            self.top_bar.set_status(f"ショートカットが重複しています: {dup_keys}")