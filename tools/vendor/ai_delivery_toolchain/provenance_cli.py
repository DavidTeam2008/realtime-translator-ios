"""CLI for OpenSpec provenance receipt verification."""
from __future__ import annotations

import sys

from .provenance import main

if __name__ == "__main__":
    sys.exit(main())
