"""GUI entry point: ``teaching-manager`` launches TeachingManager."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from fae_toolkit.teaching_manager.main_window import MainWindow


def main(argv: list[str] | None = None) -> int:
    app = QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName("TeachingManager")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
