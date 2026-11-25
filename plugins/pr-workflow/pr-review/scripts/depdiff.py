#!/usr/bin/env python3
"""Entry point: `depdiff --help`. Run through the `depdiff` wrapper, which supplies Python 3.11+ and pyyaml."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from depreview.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
