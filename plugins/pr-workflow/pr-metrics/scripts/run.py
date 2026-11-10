#!/usr/bin/env python3
"""Entry point: `python3 run.py --help`. Needs Python 3.9+ and an authenticated `gh` CLI."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pr_metrics.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
