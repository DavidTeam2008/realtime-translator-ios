"""CLI for independent Superpowers discipline receipt verification."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .delivery import DeliveryError
from .discipline import verify_receipt


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ai-delivery-toolchain discipline")
    parser.add_argument("command", choices=("verify",))
    parser.add_argument("--root", required=True)
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--change", required=True)
    parser.add_argument("--task", required=True, type=int)
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--evidence", action="append", default=[])
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        verify_receipt(
            Path(args.root).expanduser().resolve(),
            Path(args.receipt).expanduser().resolve(),
            expected_change=args.change,
            expected_task=args.task,
            expected_base=args.base,
            expected_head=args.head,
            evidence_ids=args.evidence,
        )
        print(json.dumps({
            "verified": True,
            "receipt": args.receipt,
            "change": args.change,
            "task": args.task,
            "evidence": args.evidence,
        }, ensure_ascii=False, sort_keys=True))
        return 0
    except (DeliveryError, OSError) as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
