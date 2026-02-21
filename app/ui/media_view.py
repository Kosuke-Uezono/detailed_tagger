from __future__ import annotations

import numpy as np
import cv2
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout


class MediaView(QWidget):
    """Widget for displaying video frames or images."""

    def __init__(self) -> None:
        super().__init__()
        self.label = QLabel("No media loaded")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setMinimumSize(640, 360)
        layout = QVBoxLayout()
        layout.addWidget(self.label)
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