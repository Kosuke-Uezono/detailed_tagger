from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel


class TopBar(QWidget):
    """Top bar widget containing action buttons and a status label."""
    # Signals emitted when the user triggers actions on the top bar
    load_project_clicked = pyqtSignal()
    load_simple_csv_clicked = pyqtSignal()
    load_tag_config_clicked = pyqtSignal()
    export_clicked = pyqtSignal()
    # Signal emitted when the user wants to set a custom start time for the current file
    set_start_time_clicked = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        # Create widgets
        self.status_label = QLabel("Ready")
        # Label to show frame/total/time information
        self.frame_info_label = QLabel("")
        # Buttons
        self.btn_load_project = QPushButton("親フォルダ読込（複数）")
        self.btn_load_simple = QPushButton("簡易タグCSV読込")
        self.btn_load_config = QPushButton("タグ設定JSON読込")
        self.btn_export = QPushButton("CSV出力")
        # Button to set custom start time for the current media file
        self.btn_set_start_time = QPushButton("開始時刻設定")

        # Layout: buttons + status + frame info
        layout = QHBoxLayout()
        layout.addWidget(self.btn_load_project)
        layout.addWidget(self.btn_load_simple)
        layout.addWidget(self.btn_load_config)
        layout.addWidget(self.btn_export)
        layout.addWidget(self.btn_set_start_time)
        layout.addWidget(self.status_label, stretch=1)
        layout.addWidget(self.frame_info_label)
        self.setLayout(layout)

        # Connect signals to emitters
        self.btn_load_project.clicked.connect(self.load_project_clicked.emit)
        self.btn_load_simple.clicked.connect(self.load_simple_csv_clicked.emit)
        self.btn_load_config.clicked.connect(self.load_tag_config_clicked.emit)
        self.btn_export.clicked.connect(self.export_clicked.emit)
        self.btn_set_start_time.clicked.connect(self.set_start_time_clicked.emit)

    def set_status(self, text: str) -> None:
        """Update the status label text."""
        self.status_label.setText(text)

    def set_frame_info(self, text: str) -> None:
        """Update the frame info label text."""
        self.frame_info_label.setText(text)