#!/usr/bin/env python3
"""Run the configured delivery gates and write a machine-checkable receipt.

The review executor must not certify its own gates. This wrapper is the
gate-runner side: it executes the required commands in a separate process,
records exit codes and output digests, writes the gate report markdown and a
JSON receipt, then stages both for review_guard.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import time
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

from review_guard import (  # noqa: E402
    DEFAULT_GATE_COMMANDS,
    ReviewGuardError,
    load_contract,
    load_review_config,
)

DEFAULT_TIMEOUT = 1800


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_write(path: Path, document: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _run_git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, timeout=120
    )
    if completed.returncode != 0:
        raise ReviewGuardError(
            f"git {' '.join(args)} 失败：{completed.stderr.strip()[:200]}"
        )
    return completed.stdout.strip()


def _run_command(root: Path, command: str, timeout: int) -> dict:
    started = time.time()
    try:
        completed = subprocess.run(
            command,
            shell=True,
            cwd=root,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        stdout = completed.stdout
        stderr = completed.stderr
        exit_code = completed.returncode
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        stdout = stdout + "\n[timeout]\n"
        exit_code = None
    duration_ms = int((time.time() - started) * 1000)
    combined = (stdout + "\n" + stderr).encode("utf-8", "replace")
    return {
        "command": command,
        "exitCode": exit_code,
        "durationMs": duration_ms,
        "outputSha256": _sha256(combined),
        "stdoutTail": stdout[-2000:],
        "stderrTail": stderr[-2000:],
    }


def run_gates(
    root: Path,
    change: str,
    *,
    runner: str,
    head: str | None = None,
    extras: list[str] | None = None,
    report: str | None = None,
    timeout: int = DEFAULT_TIMEOUT,
    stage: bool = True,
) -> int:
    review = load_review_config(root)
    if not review:
        print("[FAIL] config.delivery.review 未启用", file=sys.stderr)
        return 2
    try:
        level, base, _review_path, _ = load_contract(root, change)
    except ReviewGuardError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 2
    if level != "L2":
        print(f"[FAIL] {change} 不是 L2（Level={level}）", file=sys.stderr)
        return 2

    current_head = _run_git(root, "rev-parse", "HEAD")
    head = (head or current_head).lower()
    if head != current_head:
        print(
            f"[FAIL] gate head {head} 与当前 HEAD {current_head} 不一致；"
            "gate-runner 只能在待验证 commit 上运行",
            file=sys.stderr,
        )
        return 2

    required = review.get("requiredGateCommands", list(DEFAULT_GATE_COMMANDS))
    if not isinstance(required, list) or not required:
        print("[FAIL] requiredGateCommands 必须是非空数组", file=sys.stderr)
        return 2
    extra_commands = [item for item in (extras or []) if item]
    commands = list(dict.fromkeys([str(item) for item in required] + extra_commands))

    report_rel = report or f"harness/reviews/{date.today().isoformat()}-{change}-gates.md"
    report_path = (root / report_rel).resolve()
    try:
        report_path.relative_to(root)
    except ValueError:
        print(f"[FAIL] gate report 路径越界：{report_rel}", file=sys.stderr)
        return 2

    started_at = _utc_now()
    results = []
    for command in commands:
        item = _run_command(root, command, timeout)
        item["required"] = command in required
        results.append(item)
    finished_at = _utc_now()
    overall = "PASS" if all(item["exitCode"] == 0 for item in results) else "FAIL"

    receipt_rel = (
        f"harness/receipts/reviews/{change}/{head[:7]}-gates.json"
    )
    receipt_path = root / receipt_rel
    session_id = str(uuid.uuid4())

    lines = [
        f"# Gate Run — {change}",
        "",
        f"- Base: {base}",
        f"- Head: {head}",
        f"- Gate runner: {runner}（tools/run_gate_runner.py 独立进程）",
        f"- Environment: {platform.system()} {platform.release()} / Python {platform.python_version()}",
        f"- Overall: {overall}",
        "",
        "| command | exit | result | duration(ms) |",
        "| --- | --- | --- | --- |",
    ]
    for item in results:
        result = "PASS" if item["exitCode"] == 0 else "FAIL"
        lines.append(
            f"| {item['command']} | {item['exitCode']} | {result} | {item['durationMs']} |"
        )
    lines += [
        "",
        f"- Receipt: {receipt_rel}",
        f"- Session: {session_id}",
        "",
        "- 说明：本报告由 gate-runner wrapper 实际执行命令后生成；不替代 review 结论。",
        "",
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")
    report_sha = _sha256(report_path.read_bytes())

    receipt = {
        "schemaVersion": 1,
        "kind": "dual-review-gates",
        "change": change,
        "base": base,
        "head": head,
        "runner": runner,
        "sessionId": session_id,
        "environment": {
            "platform": platform.platform(),
            "python": platform.python_version(),
        },
        "commands": results,
        "requiredGateCommands": [str(item) for item in required],
        "overall": overall,
        "report": {
            "path": report_path.relative_to(root).as_posix(),
            "sha256": report_sha,
        },
        "startedAt": started_at,
        "finishedAt": finished_at,
    }
    _json_write(receipt_path, receipt)

    if stage:
        _run_git(
            root,
            "add",
            "--",
            report_path.relative_to(root).as_posix(),
            receipt_path.relative_to(root).as_posix(),
        )

    print(
        json.dumps(
            {
                "ok": overall == "PASS",
                "change": change,
                "base": base,
                "head": head,
                "overall": overall,
                "report": report_path.relative_to(root).as_posix(),
                "receipt": receipt_rel,
                "commands": [
                    {"command": item["command"], "exitCode": item["exitCode"]}
                    for item in results
                ],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0 if overall == "PASS" else 2


def main() -> int:
    parser = argparse.ArgumentParser(prog="run_gate_runner")
    parser.add_argument("--change", required=True)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--runner", default="gate-runner-local")
    parser.add_argument("--head")
    parser.add_argument("--extra", action="append", default=[])
    parser.add_argument("--report")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument("--no-stage", action="store_true")
    args = parser.parse_args()
    try:
        return run_gates(
            Path(args.root).expanduser().resolve(),
            args.change,
            runner=args.runner,
            head=args.head,
            extras=args.extra,
            report=args.report,
            timeout=args.timeout,
            stage=not args.no_stage,
        )
    except (OSError, ValueError, ReviewGuardError) as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
