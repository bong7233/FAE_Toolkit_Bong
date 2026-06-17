"""GUI entry point: ``fae-toolkit-gui``."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from fae_toolkit.ui.main_window import MainWindow


def main(argv: list[str] | None = None) -> int:
    app = QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName("FAE Toolkit")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
