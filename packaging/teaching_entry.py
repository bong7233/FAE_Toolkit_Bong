"""PyInstaller entry point for TeachingManager (with offscreen --self-test)."""

import os
import sys


def _self_test() -> int:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    from fae_toolkit.teaching_manager.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.show()
    for _ in range(20):
        app.processEvents()
    window.close()
    print("TeachingManager self-test OK")
    return 0


def main() -> int:
    if "--self-test" in sys.argv:
        return _self_test()
    from fae_toolkit.teaching_manager.app import main as tm_main

    return tm_main()


if __name__ == "__main__":
    sys.exit(main())
