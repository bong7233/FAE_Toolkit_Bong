"""PyInstaller entry point for the desktop GUI.

Running with ``--self-test`` constructs the main window offscreen and exits,
which lets CI verify the packaged bundle loads every module (Qt, pyqtgraph,
python-can, ...) without opening a window.
"""

import os
import sys


def _self_test() -> int:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    from fae_toolkit.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.show()
    for _ in range(20):
        app.processEvents()
    window.close()
    print("GUI self-test OK")
    return 0


def main() -> int:
    if "--self-test" in sys.argv:
        return _self_test()
    from fae_toolkit.ui.app import main as gui_main

    return gui_main()


if __name__ == "__main__":
    sys.exit(main())
