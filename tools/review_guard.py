#!/usr/bin/env python3
"""Fail-closed guard for independent dual-axis review bundles.

The guard checks structure and execution provenance:

1. fixed executor (Claude Code + /code-review skill) declared by config;
2. a tracked execution receipt binding change/base/head/executor, with
   Skill/Task permissions, at least two sub-agents, and a read-only tool set;
3. two tracked axis reports with declared isolated contexts;
4. a tracked gate receipt produced by a separate gate-runner wrapper, with the
   configured commands actually exiting 0;
5. P1 fix re-review fields when P1s were opened.

The guard cannot prove a determined agent could not forge local artifacts; it
turns "write any string" into "produce a consistent execution receipt".
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

DEFAULT_MODE = "dual-context"
DEFAULT_GATE_COMMANDS = ("make verify-static", "python3 tools/check-test-baseline.py")
DEFAULT_REQUIRED_TOOLS = ("Skill", "Task")
DEFAULT_DENIED_TOOLS = ("Write", "Edit")
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


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path, label: str) -> dict:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReviewGuardError(f"{label} 读取失败：{path.name} ({exc})") from exc
    if not isinstance(document, dict):
        raise ReviewGuardError(f"{label} 必须是 JSON object：{path.name}")
    return document


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


def load_review_config(root: Path) -> dict:
    """Public accessor for wrappers/tests."""
    return _config_review(root)


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
            "Change",
            "Level",
            "Base",
            "Review",
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


def load_contract(root: Path, change: str) -> tuple[str, str, str, str]:
    """Public accessor for wrappers/tests."""
    return _contract(root, change)


def _axis_check(
    root: Path,
    front: dict,
    report_key: str,
    expected_axis: str,
    errors: list[str],
) -> None:
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


def _execution_check(
    root: Path, front: dict, review: dict, change: str, errors: list[str]
) -> str | None:
    executor_cfg = review.get("executor")
    if not isinstance(executor_cfg, dict) or not executor_cfg.get("required"):
        errors.append("config.delivery.review.executor.required 缺失")
        return None
    required_executor = str(executor_cfg["required"])
    actual_executor = front.get("executor", "").strip()
    if actual_executor != required_executor:
        errors.append(
            f"review.executor 必须是 {required_executor}，实际 {actual_executor!r}"
        )

    relative = front.get("execution_receipt", "").strip()
    if not relative:
        errors.append("review 缺少 execution_receipt")
        return None
    try:
        path = _resolve(root, relative, "execution_receipt")
    except ReviewGuardError as exc:
        errors.append(str(exc))
        return None
    if not _tracked(root, relative):
        errors.append(f"execution_receipt 未被 git 跟踪：{relative}")
        return None
    try:
        receipt = _load_json(path, "execution_receipt")
    except ReviewGuardError as exc:
        errors.append(str(exc))
        return None

    if receipt.get("kind") != "dual-review-execution":
        errors.append("execution_receipt.kind 必须是 dual-review-execution")
    if receipt.get("ok") is not True:
        errors.append("execution_receipt.ok 必须是 true")
    if receipt.get("change") != change:
        errors.append("execution_receipt.change 与 --change 不一致")
    if receipt.get("executor") != required_executor:
        errors.append("execution_receipt.executor 与 config 不一致")
    for key in ("base", "head"):
        if str(receipt.get(key, "")).lower() != str(front.get(key, "")).lower():
            errors.append(f"execution_receipt.{key} 与 review 不一致")

    session_id = str(receipt.get("sessionId") or "")
    if not session_id:
        errors.append("execution_receipt 缺少 sessionId")
    prompt = str(receipt.get("prompt") or "")
    if "/code-review" not in prompt:
        errors.append("execution_receipt.prompt 缺少显式 /code-review")
    command_text = " ".join(str(item) for item in (receipt.get("command") or []))
    if "/code-review" not in command_text:
        errors.append("execution_receipt.command 缺少 /code-review")
    if not str(receipt.get("claudeVersion") or "").strip():
        errors.append("execution_receipt 缺少 claudeVersion")
    for key in ("startedAt", "finishedAt"):
        if not str(receipt.get(key) or "").strip():
            errors.append(f"execution_receipt 缺少 {key}")

    permissions = receipt.get("permissions") or {}
    allowed = set(permissions.get("allowed") or [])
    disallowed = set(permissions.get("disallowed") or [])
    for tool in executor_cfg.get("requiredTools") or list(DEFAULT_REQUIRED_TOOLS):
        if tool not in allowed:
            errors.append(f"execution_receipt.permissions.allowed 缺 {tool}")
    for tool in executor_cfg.get("deniedTools") or list(DEFAULT_DENIED_TOOLS):
        if tool not in disallowed:
            errors.append(f"execution_receipt.permissions.disallowed 缺 {tool}")
    gate_tokens = ("make", "verify-static", "delivery-check", "xcodebuild", "evals")
    for tool in allowed:
        lowered = str(tool).lower()
        if tool == "Bash" or any(token in lowered for token in gate_tokens):
            errors.append("execution_receipt.permissions.allowed 不应包含交付门禁执行能力")
            break

    try:
        min_subagents = int(executor_cfg.get("minSubagents", 2))
    except (TypeError, ValueError):
        errors.append("config.delivery.review.executor.minSubagents 必须是整数")
        return session_id
    stats = receipt.get("subagentStats") or {}
    try:
        spawned = int(stats.get("spawned", 0))
    except (TypeError, ValueError):
        spawned = 0
    if spawned < min_subagents:
        errors.append(f"execution_receipt.subagentStats.spawned={spawned} < {min_subagents}")

    events = receipt.get("events") or {}
    events_rel = str(events.get("path") or "").strip()
    if not events_rel:
        errors.append("execution_receipt 缺少 events.path")
        return session_id
    try:
        events_path = _resolve(root, events_rel, "execution events")
    except ReviewGuardError as exc:
        errors.append(str(exc))
        return session_id
    if not _tracked(root, events_rel):
        errors.append(f"execution events 未被 git 跟踪：{events_rel}")
    if events.get("sha256") != _sha256(events_path):
        errors.append("execution events sha256 不一致")
    try:
        events_doc = _load_json(events_path, "execution events")
    except ReviewGuardError as exc:
        errors.append(str(exc))
        return session_id
    entries = events_doc.get("entries")
    if not isinstance(entries, list):
        errors.append("execution events.entries 必须是数组")
        return session_id
    if not any(
        isinstance(item, dict)
        and item.get("type") == "prompt"
        and "/code-review" in str(item.get("text", ""))
        for item in entries
    ):
        errors.append("execution events 缺少 /code-review prompt")
    spawns = [
        item
        for item in entries
        if isinstance(item, dict)
        and item.get("type") == "subagent_spawn"
        and item.get("tool") in ("Agent", "Task")
    ]
    if len(spawns) < min_subagents:
        errors.append(f"execution events 中 Agent/Task 子代理调用 {len(spawns)} < {min_subagents}")
    spawn_descriptions = {
        str(item.get("description"))
        for item in spawns
        if item.get("description")
    }
    if len(spawn_descriptions) < min_subagents:
        errors.append("execution events 中子代理描述不唯一")
    subagent_entries = {
        str(item.get("agentId"))
        for item in entries
        if isinstance(item, dict) and item.get("type") == "subagent"
    }
    if len(subagent_entries) < min_subagents:
        errors.append(f"execution events 中 subagent 记录 {len(subagent_entries)} < {min_subagents}")
    result_entry = next(
        (
            item
            for item in reversed(entries)
            if isinstance(item, dict) and item.get("type") == "result"
        ),
        None,
    )
    if not result_entry or str(result_entry.get("sessionId") or "") != session_id:
        errors.append("execution events.result 与 execution_receipt.sessionId 不一致")
    return session_id


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
            line
            for line in text.splitlines()
            if command in line and "PASS" in line
        ]
        if not matched:
            errors.append(f"gate_report 缺少 PASS 行：{command}")


def _gate_receipt_check(
    root: Path,
    front: dict,
    review: dict,
    change: str,
    execution_session: str | None,
    errors: list[str],
) -> None:
    receipts_cfg = review.get("receipts")
    if isinstance(receipts_cfg, dict) and receipts_cfg.get("required") is False:
        return
    relative = front.get("gate_receipt", "").strip()
    if not relative:
        errors.append("review 缺少 gate_receipt")
        return
    try:
        path = _resolve(root, relative, "gate_receipt")
    except ReviewGuardError as exc:
        errors.append(str(exc))
        return
    if not _tracked(root, relative):
        errors.append(f"gate_receipt 未被 git 跟踪：{relative}")
        return
    try:
        receipt = _load_json(path, "gate_receipt")
    except ReviewGuardError as exc:
        errors.append(str(exc))
        return

    if receipt.get("kind") != "dual-review-gates":
        errors.append("gate_receipt.kind 必须是 dual-review-gates")
    if receipt.get("change") != change:
        errors.append("gate_receipt.change 与 --change 不一致")
    if str(receipt.get("overall")) != "PASS":
        errors.append("gate_receipt.overall 必须是 PASS")
    for key in ("base", "head"):
        if str(receipt.get(key, "")).lower() != str(front.get(key, "")).lower():
            errors.append(f"gate_receipt.{key} 与 review 不一致")
    runner = str(receipt.get("runner") or "")
    if not runner:
        errors.append("gate_receipt 缺少 runner")
    elif runner != front.get("gate_runner", "").strip():
        errors.append("gate_receipt.runner 与 review.gate_runner 不一致")
    if runner and runner == front.get("reviewer", "").strip():
        errors.append("gate_receipt.runner 不能与 reviewer 相同")
    session_id = str(receipt.get("sessionId") or "")
    if not session_id:
        errors.append("gate_receipt 缺少 sessionId")
    elif execution_session and session_id == execution_session:
        errors.append("gate_receipt.sessionId 不能与 review execution session 相同")
    for key in ("startedAt", "finishedAt"):
        if not str(receipt.get(key) or "").strip():
            errors.append(f"gate_receipt 缺少 {key}")

    required = review.get("requiredGateCommands", list(DEFAULT_GATE_COMMANDS))
    if not isinstance(required, list) or not required:
        errors.append("config.delivery.review.requiredGateCommands 必须是非空数组")
        return
    commands = {
        str(item.get("command")): item
        for item in (receipt.get("commands") or [])
        if isinstance(item, dict)
    }
    for command in required:
        item = commands.get(str(command))
        if item is None:
            errors.append(f"gate_receipt 缺少命令：{command}")
            continue
        if item.get("exitCode") != 0:
            errors.append(f"gate_receipt 命令未返回 0：{command}")
        if item.get("required") is not True:
            errors.append(f"gate_receipt 命令未标记 required：{command}")

    report_info = receipt.get("report") or {}
    if report_info.get("path") != front.get("gate_report", "").strip():
        errors.append("gate_receipt.report.path 与 review.gate_report 不一致")
    try:
        report_path = _resolve(root, front.get("gate_report", ""), "gate_report")
    except ReviewGuardError:
        report_path = None
    if report_path is not None and report_info.get("sha256") != _sha256(report_path):
        errors.append("gate_receipt.report.sha256 与 gate_report 不一致")


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
    axes = {item.strip() for item in front.get("axes", "").split(",") if item.strip()}
    if not {"standards", "spec"}.issubset(axes):
        errors.append("review.axes 必须包含 standards,spec")

    _axis_check(root, front, "standards_report", "standards", errors)
    _axis_check(root, front, "spec_report", "spec", errors)
    standards = front.get("standards_report", "").strip()
    spec = front.get("spec_report", "").strip()
    if standards and standards == spec:
        errors.append("standards_report 与 spec_report 不能相同")

    execution_session = _execution_check(root, front, review, change, errors)

    if review.get("requireGateRunner", True):
        gate_runner = front.get("gate_runner", "").strip()
        if not gate_runner:
            errors.append("review 缺少 gate_runner")
        elif gate_runner == front.get("reviewer", "").strip():
            errors.append("gate_runner 不能与 reviewer 相同")
        _gate_check(root, front, review, errors)
        _gate_receipt_check(root, front, review, change, execution_session, errors)

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
        check_for_change(
            Path(args.root).expanduser().resolve(), args.change, head=args.head
        )
        print(
            json.dumps(
                {"ok": True, "change": args.change, "mode": "dual-context"},
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 0
    except ReviewGuardError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
