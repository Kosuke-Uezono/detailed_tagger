from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QGroupBox,
    QLabel,
    QGridLayout,
    QTabWidget,
    QSpinBox,
)

from ..core.tag_ontology import TagOntology


class RightPanel(QWidget):
    """
    Panel on the right side containing the search UI for simple tags and
    the hierarchical buttons/list for detailed tags.
    """

    # Signal emitted when a simple tag search result is clicked. Sends the row index.
    simple_tag_selected = pyqtSignal(int)
    # Signal emitted when the user requests to apply a detailed tag to the current frame(s).
    tag_apply_requested = pyqtSignal(str, str, str)
    # Signal emitted when the user requests to apply a tag to a range of frames.
    tag_apply_range_requested = pyqtSignal(int, int, str, str, str)
    # Signal emitted when the user requests undo of the last annotation operation.
    undo_requested = pyqtSignal()
    # Signal emitted when the user requests to remove a specific annotation. Sends annotation id.
    annotation_remove_requested = pyqtSignal(str)
    # Signal emitted when the user wants to step a given number of frames. Positive or negative value.
    step_frames_requested = pyqtSignal(int)
    # Signal emitted when the user requests to advance to the next media file.
    next_file_requested = pyqtSignal()
    # Signal emitted when the user requests to go to the previous media file.
    prev_file_requested = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        # Ontology holds the loaded tag configuration
        self.ontology = TagOntology()
        # Current selections in the 3-level hierarchy
        self.current_lv1 = ""
        self.current_lv2 = ""
        self.current_lv3 = ""

        # Create search widgets
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("簡易タグ検索キーワード")
        self.search_btn = QPushButton("検索")
        self.search_list = QListWidget()

        # Create tag UI widgets
        self.tabs = QTabWidget()
        self.lv2_box = QGroupBox("第2階層（ボタン）")
        self.lv3_box = QGroupBox("第3階層（詳細リスト）")
        self.lv2_area = QWidget()
        self.lv3_list = QListWidget()
        self.apply_btn = QPushButton("この詳細タグを付与")

        # Widgets for range selection
        self.range_group = QGroupBox("範囲選択: Start-End")
        self.range_start_spin = QSpinBox()
        self.range_start_spin.setMinimum(0)
        self.range_start_spin.setMaximum(10_000_000)
        self.range_end_spin = QSpinBox()
        self.range_end_spin.setMinimum(0)
        self.range_end_spin.setMaximum(10_000_000)
        self.range_apply_btn = QPushButton("範囲にタグ付与")

        # Widgets for annotation list and undo
        self.annot_group = QGroupBox("付与済みタグ一覧")
        self.annot_list = QListWidget()
        self.undo_btn = QPushButton("Undo (最後の操作)")

        # Widgets for frame stepping (forward/backward and next file)
        # Widgets for file navigation (next/prev file). Frame stepping controls are displayed in MediaView.
        self.file_group = QGroupBox("ファイル移動")
        # Buttons for jumping to the next or previous file in the current session
        self.btn_next_file = QPushButton("次ファイル")
        self.btn_prev_file = QPushButton("前ファイル")

        # Set up layouts
        self._build_ui()

    def _build_ui(self) -> None:
        """Construct the layout for the right panel."""
        layout = QVBoxLayout()

        # Search area
        search_layout = QHBoxLayout()
        search_layout.addWidget(self.search_edit)
        search_layout.addWidget(self.search_btn)
        layout.addLayout(search_layout)
        layout.addWidget(self.search_list)

        # Tag UI area
        layout.addWidget(self.tabs)
        layout.addWidget(self.lv2_box)
        self.lv2_box.setLayout(QVBoxLayout())
        self.lv2_box.layout().addWidget(self.lv2_area)
        layout.addWidget(self.lv3_box)
        self.lv3_box.setLayout(QVBoxLayout())
        self.lv3_box.layout().addWidget(self.lv3_list)
        layout.addWidget(self.apply_btn)

        # Range selection layout
        range_layout = QHBoxLayout()
        range_layout.addWidget(QLabel("Start"))
        range_layout.addWidget(self.range_start_spin)
        range_layout.addWidget(QLabel("End"))
        range_layout.addWidget(self.range_end_spin)
        range_layout.addWidget(self.range_apply_btn)
        self.range_group.setLayout(range_layout)
        layout.addWidget(self.range_group)

        # File navigation layout
        file_layout = QHBoxLayout()
        file_layout.addWidget(self.btn_prev_file)
        file_layout.addWidget(self.btn_next_file)
        self.file_group.setLayout(file_layout)
        layout.addWidget(self.file_group)

        # Annotation list layout
        annot_layout = QVBoxLayout()
        annot_layout.addWidget(self.annot_list)
        annot_layout.addWidget(self.undo_btn)
        self.annot_group.setLayout(annot_layout)
        layout.addWidget(self.annot_group)

        self.setLayout(layout)

        # Wire internal signals
        self.search_list.itemClicked.connect(self._handle_simple_item_clicked)
        self.lv3_list.itemClicked.connect(self._handle_lv3_clicked)
        self.apply_btn.clicked.connect(self._handle_apply_clicked)
        self.range_apply_btn.clicked.connect(self._handle_range_apply_clicked)
        self.undo_btn.clicked.connect(self._handle_undo_clicked)
        self.annot_list.itemClicked.connect(self._handle_annot_item_clicked)

        # File navigation signals
        self.btn_next_file.clicked.connect(lambda _=False: self.next_file_requested.emit())
        self.btn_prev_file.clicked.connect(lambda _=False: self.prev_file_requested.emit())

    # Public API
    def set_search_results(self, items: list[dict[str, int | str]]) -> None:
        """
        Populate the search result list with a list of dictionaries.
        Each dictionary must have keys: 'idx' (row index) and 'text' (display text).
        """
        self.search_list.clear()
        for item in items:
            idx = item.get("idx")
            text = item.get("text", "")
            lw_item = QListWidgetItem(text)
            lw_item.setData(Qt.ItemDataRole.UserRole, idx)
            self.search_list.addItem(lw_item)

    def load_tag_config(self, json_path: str) -> None:
        """Load tag configuration from JSON file and rebuild the UI."""
        self.ontology.load(json_path)
        self._rebuild_tag_ui()

    # Internal UI handlers
    def _rebuild_tag_ui(self) -> None:
        """Rebuild tabs and level 2/3 selectors based on the loaded ontology."""
        self.tabs.clear()
        # Build top-level tabs for each lv1
        for tab in self.ontology.tabs:
            content = QWidget()
            layout = QVBoxLayout()
            info = QLabel(f"第1階層: {tab.name}\n第2階層は下で選択してください")
            info.setWordWrap(True)
            layout.addWidget(info)
            content.setLayout(layout)
            self.tabs.addTab(content, tab.name)
        # Connect signal for tab change to update lv2
        self.tabs.currentChanged.connect(self._handle_tab_changed)
        # Initialize lv2 for the first tab
        if self.ontology.tabs:
            self._handle_tab_changed(0)

    def _handle_tab_changed(self, index: int) -> None:
        """Handle changes of the top-level tab (lv1)."""
        if index < 0 or index >= len(self.ontology.tabs):
            return
        tab = self.ontology.tabs[index]
        self.current_lv1 = tab.name
        # Build lv2 buttons for this tab
        lv2_widget = QWidget()
        grid = QGridLayout()
        lv2_widget.setLayout(grid)
        for i, btn_cfg in enumerate(tab.buttons):
            btn = QPushButton(btn_cfg.name)
            btn.clicked.connect(
                lambda _=False, name=btn_cfg.name: self._handle_lv2_clicked(name)
            )
            grid.addWidget(btn, i // 2, i % 2)
        # Replace current lv2 widget
        if self.lv2_area is not None:
            self.lv2_area.setParent(None)
        self.lv2_area = lv2_widget
        self.lv2_box.layout().addWidget(self.lv2_area)
        # Auto-select first lv2 item
        if tab.buttons:
            self._handle_lv2_clicked(tab.buttons[0].name)

    def _handle_lv2_clicked(self, lv2: str) -> None:
        """Handle selection of a level 2 item and populate level 3 list."""
        self.current_lv2 = lv2
        # Populate level 3 list based on selected lv1/lv2
        self.lv3_list.clear()
        # Find the current tab and button
        tab = next((t for t in self.ontology.tabs if t.name == self.current_lv1), None)
        if not tab:
            return
        button = next((b for b in tab.buttons if b.name == lv2), None)
        if not button:
            return
        for detail in button.details:
            text = detail.name
            if detail.shortcut:
                text += f"  [key:{detail.shortcut}]"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, detail.name)
            self.lv3_list.addItem(item)
        # Auto-select first lv3
        if button.details:
            self.current_lv3 = button.details[0].name

    def _handle_lv3_clicked(self, item: QListWidgetItem) -> None:
        """Capture level 3 selection from the list."""
        self.current_lv3 = str(item.data(Qt.ItemDataRole.UserRole))

    def _handle_apply_clicked(self) -> None:
        """Emit a tag apply signal when the user confirms tagging."""
        if self.current_lv1 and self.current_lv2 and self.current_lv3:
            self.tag_apply_requested.emit(
                self.current_lv1, self.current_lv2, self.current_lv3
            )

    def _handle_range_apply_clicked(self) -> None:
        """Handle clicking on the range apply button."""
        start = self.range_start_spin.value()
        end = self.range_end_spin.value()
        if start > end:
            # Swap if the user reversed them
            start, end = end, start
        if self.current_lv1 and self.current_lv2 and self.current_lv3:
            self.tag_apply_range_requested.emit(start, end, self.current_lv1, self.current_lv2, self.current_lv3)

    def _handle_undo_clicked(self) -> None:
        """Emit undo request."""
        self.undo_requested.emit()

    def _handle_annot_item_clicked(self, item: QListWidgetItem) -> None:
        """Emit annotation removal request when an annotation list item is clicked."""
        annot_id = str(item.data(Qt.ItemDataRole.UserRole))
        self.annotation_remove_requested.emit(annot_id)

    # Public method to update annotation list
    def update_annotations(self, annotations: list) -> None:
        """
        Refresh the annotation list display. Expects a list of AnnotationRecord objects.
        """
        self.annot_list.clear()
        for rec in annotations:
            text = f"Frame {rec.frame_no}: {rec.lv1}/{rec.lv2}/{rec.lv3}"
            item = QListWidgetItem(text)
            # Store annotation_id for removal
            item.setData(Qt.ItemDataRole.UserRole, rec.annotation_id)
            self.annot_list.addItem(item)

    def _handle_simple_item_clicked(self, item: QListWidgetItem) -> None:
        """Emit the index of the selected simple tag when clicked."""
        idx = int(item.data(Qt.ItemDataRole.UserRole))
        self.simple_tag_selected.emit(idx)