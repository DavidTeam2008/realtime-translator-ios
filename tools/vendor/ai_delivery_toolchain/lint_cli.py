"""CLI for contract lint."""
from __future__ import annotations

import sys

from .lint import main

if __name__ == "__main__":
    sys.exit(main())
