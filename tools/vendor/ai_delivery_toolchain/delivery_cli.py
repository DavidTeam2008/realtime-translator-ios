"""CLI for the delivery gate; archive is never executed here."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from .delivery import DeliveryError, check_delivery, parse_contract


def _read_json(path: str | None, label: str) -> dict:
    if not path:
        raise DeliveryError(f"缺少 {label}")
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DeliveryError(f"{label} 读取失败：{exc}") from exc
    if not isinstance(value, dict):
        raise DeliveryError(f"{label} 顶层必须是 object")
    return value


def _run_json(argv: list[str], label: str) -> dict:
    try:
        completed = subprocess.run(argv, capture_output=True, text=True, timeout=300)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise DeliveryError(f"{label} 执行失败：{exc}") from exc
    if completed.returncode != 0:
        raise DeliveryError(f"{label} 非零退出（{completed.returncode}）：{completed.stderr.strip()[:300]}")
    try:
        value = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise DeliveryError(f"{label} 输出不是 JSON：{exc}") from exc
    if not isinstance(value, dict):
        raise DeliveryError(f"{label} 顶层必须是 object")
    return value


def _load_openspec(root: Path, path: str, change: str, validate_json: str | None, apply_json: str | None):
    if validate_json:
        validate = _read_json(validate_json, "validate JSON")
    else:
        validate = _run_json(
            [path, "validate", change, "--type", "change", "--strict", "--json"],
            "openspec validate",
        )
    if apply_json:
        apply = _read_json(apply_json, "apply JSON")
    else:
        apply = _run_json(
            [path, "instructions", "apply", "--change", change, "--json"],
            "openspec instructions apply",
        )
    return validate, apply


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ai-delivery-toolchain delivery-check")
    parser.add_argument("command", choices=("check", "archive-gate"))
    parser.add_argument("--root", required=True)
    parser.add_argument("--tasks", default="openspec/changes/<change>/tasks.md")
    parser.add_argument("--change")
    parser.add_argument("--profile", required=True)
    parser.add_argument("--openspec", required=True)
    parser.add_argument("--validate-json")
    parser.add_argument("--apply-json")
    parser.add_argument("--ci-json")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    root = Path(args.root).expanduser().resolve()
    try:
        profile = _read_json(args.profile, "profile")
        tasks_path = args.tasks
        if "<change>" in tasks_path:
            if not args.change:
                raise DeliveryError("tasks 路径含 <change> 时必须提供 --change")
            tasks_path = tasks_path.replace("<change>", args.change)
        text = (root / tasks_path).read_text(encoding="utf-8")
        contract = parse_contract(text)
        if args.change and args.change != contract.change:
            raise DeliveryError("--change 与 Delivery Contract 不一致")
        validate, apply = _load_openspec(
            root,
            args.openspec,
            contract.change,
            args.validate_json,
            args.apply_json,
        )
        ci = _read_json(args.ci_json, "CI JSON") if args.ci_json else None
        result = check_delivery(
            root,
            tasks_path,
            profile,
            validate_doc=validate,
            apply_doc=apply,
            ci=ci,
        )
        result["archiveGate"] = args.command == "archive-gate"
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (DeliveryError, OSError) as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
