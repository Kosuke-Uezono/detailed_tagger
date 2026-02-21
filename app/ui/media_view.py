from __future__ import annotations

import numpy as np
import cv2
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QGroupBox,
    QHBoxLayout,
    QPushButton,
)


class MediaView(QWidget):
    """
    Widget for displaying video frames or images along with frame stepping controls.

    This widget exposes signals for stepping frames, which can be connected to
    handlers in the main window. The frame stepping controls are displayed
    beneath the image area, keeping all playback-related controls in the
    left pane.
    """

    # Signal emitted when the user requests to step a given number of frames.
    step_frames_requested = pyqtSignal(int)

    def __init__(self) -> None:
        super().__init__()
        # Image label for displaying frames
        self.label = QLabel("No media loaded")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setMinimumSize(640, 360)

        # Create frame control buttons (-30F, -10F, -1F, +1F, +10F, +30F)
        self.frame_group = QGroupBox("フレーム送り")
        frame_layout = QHBoxLayout()
        # Create individual buttons
        self.btn_step_m30 = QPushButton("-30F")
        self.btn_step_m10 = QPushButton("-10F")
        self.btn_step_m1 = QPushButton("-1F")
        self.btn_step_p1 = QPushButton("+1F")
        self.btn_step_p10 = QPushButton("+10F")
        self.btn_step_p30 = QPushButton("+30F")
        # Add buttons to layout
        frame_layout.addWidget(self.btn_step_m30)
        frame_layout.addWidget(self.btn_step_m10)
        frame_layout.addWidget(self.btn_step_m1)
        frame_layout.addWidget(self.btn_step_p1)
        frame_layout.addWidget(self.btn_step_p10)
        frame_layout.addWidget(self.btn_step_p30)
        self.frame_group.setLayout(frame_layout)

        # Connect buttons to emit signals
        self.btn_step_m30.clicked.connect(lambda _=False: self.step_frames_requested.emit(-30))
        self.btn_step_m10.clicked.connect(lambda _=False: self.step_frames_requested.emit(-10))
        self.btn_step_m1.clicked.connect(lambda _=False: self.step_frames_requested.emit(-1))
        self.btn_step_p1.clicked.connect(lambda _=False: self.step_frames_requested.emit(1))
        self.btn_step_p10.clicked.connect(lambda _=False: self.step_frames_requested.emit(10))
        self.btn_step_p30.clicked.connect(lambda _=False: self.step_frames_requested.emit(30))

        # Compose layout: image label above, frame controls below
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.frame_group)
        layout.setSpacing(4)
        # Allocate most of the vertical space to the video label (approximately 90%)
        # and a smaller portion to the frame controls (approximately 10%).
        layout.setStretch(0, 9)
        layout.setStretch(1, 1)
        self.setLayout(layout)

    def show_bgr(self, bgr: np.ndarray) -> None:
        """Display an image in BGR format."""
        # Convert BGR to RGB
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        height, width, channels = rgb.shape
        bytes_per_line = channels * width
        # Create QImage and scale to fit the label while keeping aspect ratio
        qimg = QImage(rgb.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg)
        self.label.setPixmap(
            pixmap.scaled(
                self.label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def resizeEvent(self, event) -> None:
        """Handle widget resizing by re-scaling the pixmap."""
        if pixmap := self.label.pixmap():
            self.label.setPixmap(
                pixmap.scaled(
                    self.label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        super().resizeEvent(event)