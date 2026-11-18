"""Read-only toolchain information; never touches the network."""
from __future__ import annotations

import json
import sys

from . import __version__

SCHEMAS = (
    "discipline-receipt-v1",
    "discipline-receipt-v2",
    "skill-invoked-v1",
    "openspec-provenance-v1",
)
MODULES = (
    "discipline",
    "provenance",
    "delivery",
    "release_cli",
    "skill",
    "lint",
)


def build_info() -> dict:
    return {
        "version": __version__,
        "network": False,
        "schemas": list(SCHEMAS),
        "modules": list(MODULES),
    }


def main(argv: list[str] | None = None) -> int:
    print(json.dumps(build_info(), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
