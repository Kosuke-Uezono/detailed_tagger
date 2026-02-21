from __future__ import annotations

import sys
from PyQt6.QtWidgets import QApplication

from .ui.main_window import MainWindow


def main() -> int:
    """Application entry point. Initializes the Qt application and shows the main window."""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())