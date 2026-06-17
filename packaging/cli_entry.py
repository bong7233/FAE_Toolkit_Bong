"""PyInstaller entry point for the headless CLI.

Kept as a tiny standalone script so PyInstaller has a concrete file to bundle.
"""

import sys

from fae_toolkit.cli import main

if __name__ == "__main__":
    sys.exit(main())
