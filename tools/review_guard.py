#!/usr/bin/env python3
"""Fail-closed guard for independent dual-axis review bundles.

The guard exists because a Markdown convention is not enforcement.  It checks
that an L2 review really has two isolated axis reports, a separate gate-runner
report, and a reproducible base/head binding before delivery-check is allowed
to trust the aggregate report.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

DEFAULT_MODE = "dual-context"
DEFAULT_GATE_COMMANDS = ("make verify-static", "python3 tools/check-test-baseline.py")
FRONT_MATTER_END = "---"


class ReviewGuardError(RuntimeError):
    pass


def _read_front_matter(path: Path) -> dict[str, str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ReviewGuardError(f"review 读取失败：{path} ({exc})") from exc
    if not lines or lines[0].strip() != FRONT_MATTER_END:
        raise ReviewGuardError(f"review 缺少 front matter：{path}")
    values: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == FRONT_MATTER_END:
            return values
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key, value = key.strip(), value.strip()
        if key and value:
            values[key] = value
    raise ReviewGuardError(f"review front matter 未闭合：{path}")


def _git(root: Path, *args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", *args], cwd=root, capture_output=True, text=True, timeout=60
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ReviewGuardError(f"git 执行失败：{exc}") from exc
    if completed.returncode != 0:
        raise ReviewGuardError(
            f"git {' '.join(args)} 失败：{completed.stderr.strip()[:200]}"
        )
    return completed.stdout


def _tracked(root: Path, relative: str) -> bool:
    return bool(_git(root, "ls-files", "--error-unmatch", "--", relative).strip())


def _is_ancestor(root: Path, commit: str, head: str) -> bool:
    try:
        _git(root, "merge-base", "--is-ancestor", commit, head)
        return True
    except ReviewGuardError:
        return False


def _resolve(root: Path, relative: str, label: str) -> Path:
    path = (root / relative).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ReviewGuardError(f"{label} 路径越界：{relative}") from exc
    if not path.is_file():
        raise ReviewGuardError(f"{label} 不存在：{relative}")
    return path


def _config_review(root: Path) -> dict:
    path = root / "harness" / "config.json"
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReviewGuardError(f"config 读取失败：{exc}") from exc
    delivery = config.get("delivery")
    review = delivery.get("review") if isinstance(delivery, dict) else None
    if not isinstance(review, dict) or review.get("required") is not True:
        return {}
    return review


def _contract(root: Path, change: str) -> tuple[str, str, str, str]:
    tasks = root / "openspec" / "changes" / change / "tasks.md"
    try:
        text = tasks.read_text(encoding="utf-8")
    except OSError as exc:
        raise ReviewGuardError(f"tasks.md 读取失败：{exc}") from exc
    fields: dict[str, str] = {}
    for line in text.splitlines():
        if not line.startswith("- "):
            continue
        key_value = line[2:].split(":", 1)
        if len(key_value) == 2 and key_value[0].strip() in {
            "Change", "Level", "Base", "Review"
        }:
            fields[key_value[0].strip()] = key_value[1].strip()
    missing = [key for key in ("Change", "Level", "Base", "Review") if not fields.get(key)]
    if missing:
        raise ReviewGuardError(f"Delivery Contract 缺失：{', '.join(missing)}")
    if fields["Change"] != change:
        raise ReviewGuardError("Delivery Contract Change 与 --change 不一致")
    review_value = fields["Review"]
    match = re.search(r"path=([^\s,;]+)", review_value)
    if not match:
        raise ReviewGuardError("Delivery Contract Review 缺少 path=")
    return fields["Level"], fields["Base"], match.group(1), review_value


def _axis_check(root: Path, front: dict, report_key: str, expected_axis: str, errors: list[str]) -> None:
    relative = front.get(report_key, "").strip()
    if not relative:
        errors.append(f"review 缺少 {report_key}")
        return
    try:
        path = _resolve(root, relative, report_key)
    except ReviewGuardError as exc:
        errors.append(str(exc))
        return
    if not _tracked(root, relative):
        errors.append(f"{report_key} 未被 git 跟踪：{relative}")
        return
    try:
        report = _read_front_matter(path)
    except ReviewGuardError as exc:
        errors.append(str(exc))
        return
    if report.get("axis") != expected_axis:
        errors.append(f"{report_key}.axis 必须是 {expected_axis}")
    if report.get("context") not in ("isolated", "fresh"):
        errors.append(f"{report_key}.context 必须是 isolated/fresh")
    if report.get("base") and front.get("base") and report["base"] != front["base"]:
        errors.append(f"{report_key}.base 与聚合 review 不一致")
    axis_head = report.get("head", "").strip()
    review_head = front.get("head", "").strip()
    if axis_head and review_head and axis_head != review_head:
        if not _is_ancestor(root, axis_head, review_head):
            errors.append(f"{report_key}.head 既不是 review.head 也非其祖先")



def _gate_check(root: Path, front: dict, review: dict, errors: list[str]) -> None:
    relative = front.get("gate_report", "").strip()
    if not relative:
        errors.append("review 缺少 gate_report")
        return
    try:
        path = _resolve(root, relative, "gate_report")
    except ReviewGuardError as exc:
        errors.append(str(exc))
        return
    if not _tracked(root, relative):
        errors.append(f"gate_report 未被 git 跟踪：{relative}")
    text = path.read_text(encoding="utf-8", errors="replace")
    commands = review.get("requiredGateCommands", list(DEFAULT_GATE_COMMANDS))
    if not isinstance(commands, list) or not commands:
        errors.append("config.delivery.review.requiredGateCommands 必须是非空数组")
        return
    for command in commands:
        matched = [
            line for line in text.splitlines()
            if command in line and "PASS" in line
        ]
        if not matched:
            errors.append(f"gate_report 缺少 PASS 行：{command}")


def _p1_check(root: Path, front: dict, errors: list[str]) -> None:
    try:
        opened = int(front.get("p1_opened", "0"))
    except ValueError:
        errors.append("review.p1_opened 必须是整数")
        return
    if opened <= 0:
        return
    if front.get("p1", "").lower() != "closed":
        errors.append("review.p1_opened > 0 但 p1 不是 closed")
        return
    relative = front.get("p1_fix_review", "").strip()
    if not relative:
        errors.append("存在 P1 修复但缺少 p1_fix_review")
        return
    try:
        _resolve(root, relative, "p1_fix_review")
    except ReviewGuardError as exc:
        errors.append(str(exc))
        return
    if not _tracked(root, relative):
        errors.append(f"p1_fix_review 未被 git 跟踪：{relative}")
    if front.get("p1_fix_reviewed_head") and front.get("head"):
        if front["p1_fix_reviewed_head"] != front["head"]:
            errors.append("p1_fix_reviewed_head 与 review.head 不一致")


def check_review(root: Path, change: str, *, head: str | None = None) -> list[str]:
    root = root.resolve()
    review = _config_review(root)
    if not review:
        return []
    level, base, review_path, _ = _contract(root, change)
    if level != "L2":
        return []
    returned_head = (head or _git(root, "rev-parse", "HEAD").strip()).lower()
    path = _resolve(root, review_path, "review")
    if not _tracked(root, review_path):
        raise ReviewGuardError(f"review 未被 git 跟踪：{review_path}")
    front = _read_front_matter(path)
    errors: list[str] = []

    if front.get("base") != base:
        errors.append(f"review.base 不一致：{front.get('base')} != {base}")
    if (front.get("head") or "").lower() != returned_head:
        errors.append(f"review.head 不一致：{front.get('head')} != {returned_head}")

    mode = review.get("mode", DEFAULT_MODE)
    if front.get("review_mode") != mode:
        errors.append(f"review.review_mode 必须是 {mode}，实际 {front.get('review_mode')!r}")
    if not front.get("executor"):
        errors.append("review 缺少 executor")
    axes = {item.strip() for item in front.get("axes", "").split(",") if item.strip()}
    if not {"standards", "spec"}.issubset(axes):
        errors.append("review.axes 必须包含 standards,spec")

    _axis_check(root, front, "standards_report", "standards", errors)
    _axis_check(root, front, "spec_report", "spec", errors)
    standards = front.get("standards_report", "").strip()
    spec = front.get("spec_report", "").strip()
    if standards and standards == spec:
        errors.append("standards_report 与 spec_report 不能相同")

    if review.get("requireGateRunner", True):
        gate_runner = front.get("gate_runner", "").strip()
        if not gate_runner:
            errors.append("review 缺少 gate_runner")
        elif gate_runner == front.get("reviewer", "").strip():
            errors.append("gate_runner 不能与 reviewer 相同")
        _gate_check(root, front, review, errors)

    _p1_check(root, front, errors)
    return errors


def check_for_change(root: Path, change: str, *, head: str | None = None) -> None:
    errors = check_review(root, change, head=head)
    if errors:
        raise ReviewGuardError("；".join(errors))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="review_guard")
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check")
    check.add_argument("--root", default=".")
    check.add_argument("--change", required=True)
    check.add_argument("--head")
    args = parser.parse_args(argv)
    try:
        check_for_change(Path(args.root).expanduser().resolve(), args.change, head=args.head)
        print(json.dumps({"ok": True, "change": args.change, "mode": "dual-context"}, ensure_ascii=False, sort_keys=True))
        return 0
    except ReviewGuardError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())