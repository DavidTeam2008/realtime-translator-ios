#!/usr/bin/env python3
"""Execute the pinned dual-axis review and write a machine-checkable receipt.

review_guard only accepts the claude-code-code-review-skill executor. This
wrapper is the standard way to produce the execution receipt: it invokes
Claude Code in print mode with Skill/Task permissions, runs the installed
/code-review skill (two parallel sub-agents), and records the session,
permissions, sub-agent statistics and a trimmed event log.

The review is read-only: write tools are denied, and only read-only git
commands are allowed. The wrapper never edits source files.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

from review_guard import (  # noqa: E402
    ReviewGuardError,
    load_contract,
    load_review_config,
)

EXECUTOR = "claude-code-code-review-skill"
DEFAULT_MAX_TURNS = 80
SUBAGENT_TOOLS = ("Agent", "Task")
READ_ONLY_TOOLS = (
    "Read",
    "Grep",
    "Glob",
    "Skill",
    "Task",
    "Agent",
    "Bash(git diff:*)",
    "Bash(git log:*)",
    "Bash(git show:*)",
    "Bash(git rev-parse:*)",
    "Bash(git merge-base:*)",
    "Bash(git status:*)",
    "Bash(ls:*)",
    "Bash(cat:*)",
    "Bash(wc:*)",
    "Bash(pwd)",
)
DENIED_TOOLS = (
    "Write",
    "Edit",
    "NotebookEdit",
    "Bash(git commit:*)",
    "Bash(git push:*)",
    "Bash(git add:*)",
    "Bash(git reset:*)",
    "Bash(git checkout:*)",
    "Bash(rm:*)",
    "Bash(mv:*)",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json_write(path: Path, document: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def parse_stream(text: str) -> dict:
    """Parse Claude Code stream-json output into receipt-friendly facts."""
    result = None
    tool_counts: dict[str, int] = {}
    subagent_spawns: list[dict] = []
    subagents: dict[str, dict] = {}

    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        event_type = event.get("type")
        if event_type == "assistant" and event.get("parent_tool_use_id") is None:
            message = event.get("message") or {}
            for block in message.get("content") or []:
                if not isinstance(block, dict) or block.get("type") != "tool_use":
                    continue
                name = str(block.get("name", ""))
                tool_counts[name] = tool_counts.get(name, 0) + 1
                if name in SUBAGENT_TOOLS:
                    data = block.get("input") or {}
                    subagent_spawns.append(
                        {
                            "tool": name,
                            "description": str(data.get("description", "")),
                            "subagentType": str(data.get("subagent_type", "")),
                        }
                    )
        agent_id = event.get("agent_id")
        if agent_id:
            subagents.setdefault(
                str(agent_id),
                {
                    "agentId": str(agent_id),
                    "subagentType": event.get("subagent_type"),
                    "taskDescription": event.get("task_description"),
                },
            )
        if event_type == "result":
            result = event

    return {
        "result": result,
        "toolCounts": tool_counts,
        "subagentSpawns": subagent_spawns,
        "subagents": list(subagents.values()),
    }


def build_events(parsed: dict, prompt: str, session_id: str) -> dict:
    entries: list[dict] = [{"type": "prompt", "text": prompt}]
    for spawn in parsed["subagentSpawns"]:
        entries.append(
            {
                "type": "subagent_spawn",
                "tool": spawn["tool"],
                "description": spawn["description"],
                "subagentType": spawn["subagentType"],
            }
        )
    for subagent in parsed["subagents"]:
        entries.append({"type": "subagent", **subagent})
    for name, count in sorted(parsed["toolCounts"].items()):
        entries.append({"type": "tool_count", "name": name, "count": count})
    result = parsed["result"] or {}
    entries.append(
        {
            "type": "result",
            "sessionId": session_id,
            "isError": bool(result.get("is_error")),
            "numTurns": result.get("num_turns"),
            "subagentStats": result.get("subagent_stats") or {},
        }
    )
    return {"schemaVersion": 1, "kind": "dual-review-events", "entries": entries}


def _run_git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, timeout=120
    )
    if completed.returncode != 0:
        raise ReviewGuardError(
            f"git {' '.join(args)} 失败：{completed.stderr.strip()[:200]}"
        )
    return completed.stdout.strip()


def _claude_version(binary: str) -> str:
    try:
        completed = subprocess.run(
            [binary, "--version"], capture_output=True, text=True, timeout=30
        )
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"
    output = (completed.stdout or completed.stderr).strip()
    return output.splitlines()[0] if output else "unknown"


def _command(
    binary: str, prompt: str, allowed: list[str], denied: list[str], max_turns: int
) -> list[str]:
    return [
        binary,
        "-p",
        prompt,
        "--output-format",
        "stream-json",
        "--verbose",
        "--allowedTools",
        ",".join(allowed),
        "--disallowedTools",
        ",".join(denied),
        "--permission-mode",
        "bypassPermissions",
        "--permission-prompts",
        "none",
        "--max-turns",
        str(max_turns),
    ]


def run_review(
    root: Path,
    change: str,
    *,
    dry_run: bool = False,
    stage: bool = True,
    timeout: int = 1800,
    max_turns: int = DEFAULT_MAX_TURNS,
    output_dir: Path | None = None,
) -> int:
    review = load_review_config(root)
    if not review:
        print("[FAIL] config.delivery.review 未启用", file=sys.stderr)
        return 2
    executor_cfg = review.get("executor")
    if not isinstance(executor_cfg, dict) or executor_cfg.get("required") != EXECUTOR:
        print(
            f"[FAIL] config.delivery.review.executor.required 必须是 {EXECUTOR}",
            file=sys.stderr,
        )
        return 2
    min_subagents = int(executor_cfg.get("minSubagents", 2))

    try:
        level, base, _review_path, _ = load_contract(root, change)
    except ReviewGuardError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 2
    if level != "L2":
        print(f"[FAIL] {change} 不是 L2（Level={level}）", file=sys.stderr)
        return 2

    head = _run_git(root, "rev-parse", "HEAD")
    try:
        _run_git(root, "merge-base", "--is-ancestor", base, head)
    except ReviewGuardError:
        print(f"[FAIL] base {base} 不是 head {head} 的祖先", file=sys.stderr)
        return 2
    if _run_git(root, "diff", "--name-only", f"{base}...{head}") == "":
        print(f"[FAIL] {base}...{head} 无 diff", file=sys.stderr)
        return 2

    claude = os.environ.get("CLAUDE_BIN") or shutil.which("claude")
    if not claude:
        print("[FAIL] 未找到 claude CLI", file=sys.stderr)
        return 2

    prompt = (
        f"/code-review {base}\n\n"
        f"Spec source(s): openspec/changes/{change}/proposal.md, "
        f"openspec/changes/{change}/design.md, "
        f"openspec/changes/{change}/specs, "
        f"openspec/changes/{change}/tasks.md\n"
        "This is a gated L2 change. Run both review axes (Standards and Spec) "
        "as parallel sub-agents with fresh contexts, then aggregate them. "
        "Read-only: do not modify files."
    )
    allowed = list(
        dict.fromkeys(READ_ONLY_TOOLS + tuple(executor_cfg.get("requiredTools") or []))
    )
    denied = list(
        dict.fromkeys(DENIED_TOOLS + tuple(executor_cfg.get("deniedTools") or []))
    )
    command = _command(claude, prompt, allowed, denied, max_turns)
    receipt_dir = (
        output_dir
        or (root / review.get("receipts", {}).get("dir", "harness/receipts/reviews"))
        / change
    )
    prefix = head[:7]
    receipt_path = receipt_dir / f"{prefix}-execution.json"
    events_path = receipt_dir / f"{prefix}-execution.events.json"

    if dry_run:
        print(
            json.dumps(
                {"command": command, "receipt": str(receipt_path)},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    started = time.time()
    started_at = _utc_now()
    try:
        completed = subprocess.run(
            command,
            cwd=root,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        stdout, stderr, exit_code = (
            completed.stdout,
            completed.stderr,
            completed.returncode,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        stdout = stdout + "\n[timeout]\n"
        exit_code = None

    parsed = parse_stream(stdout)
    result = parsed["result"] or {}
    session_id = str(result.get("session_id") or "")
    subagent_stats = result.get("subagent_stats") or {}
    spawned = (
        int(subagent_stats.get("spawned", 0))
        if isinstance(subagent_stats, dict)
        else 0
    )

    reasons: list[str] = []
    if exit_code != 0:
        reasons.append(f"claude 退出码：{exit_code}")
    if not result:
        reasons.append("stream 中没有 result 事件")
    elif result.get("is_error"):
        reasons.append("result.is_error=true")
    if not session_id:
        reasons.append("缺少 session_id")
    if spawned < min_subagents:
        reasons.append(f"子代理数 {spawned} < {min_subagents}")
    if len(parsed["subagentSpawns"]) < min_subagents:
        reasons.append(
            f"Agent/Task 调用数 {len(parsed['subagentSpawns'])} < {min_subagents}"
        )
    descriptions = {
        item["description"]
        for item in parsed["subagentSpawns"]
        if item["description"]
    }
    if len(descriptions) < min_subagents:
        reasons.append(f"子代理描述不唯一：{sorted(descriptions)}")
    if len(parsed["subagents"]) < min_subagents:
        reasons.append(
            f"subagent 事件数 {len(parsed['subagents'])} < {min_subagents}"
        )

    finished_at = _utc_now()
    duration_ms = int((time.time() - started) * 1000)
    events_doc = build_events(parsed, prompt, session_id)
    _json_write(events_path, events_doc)
    events_sha = _sha256(events_path)
    result_text = str(result.get("result") or "")
    output_path = receipt_dir / f"{prefix}-execution.output.md"
    output_path.write_text(
        result_text + ("\n" if result_text else ""), encoding="utf-8"
    )
    output_sha = _sha256(output_path)

    model_usage = result.get("modelUsage") or {}
    model = ""
    if isinstance(model_usage, dict) and model_usage:
        model = str(next(iter(model_usage)))
    receipt = {
        "schemaVersion": 1,
        "kind": "dual-review-execution",
        "ok": not reasons,
        "change": change,
        "base": base,
        "head": head,
        "executor": EXECUTOR,
        "claudeVersion": _claude_version(claude),
        "sessionId": session_id,
        "model": model,
        "prompt": prompt,
        "command": command,
        "permissions": {"allowed": allowed, "disallowed": denied},
        "subagentStats": subagent_stats,
        "subagentSpawns": parsed["subagentSpawns"],
        "subagents": parsed["subagents"],
        "toolCounts": parsed["toolCounts"],
        "events": {
            "path": events_path.relative_to(root).as_posix(),
            "sha256": events_sha,
        },
        "output": {
            "path": output_path.relative_to(root).as_posix(),
            "sha256": output_sha,
        },
        "startedAt": started_at,
        "finishedAt": finished_at,
        "durationMs": duration_ms,
        "exitCode": exit_code,
        "result": {
            "isError": bool(result.get("is_error")),
            "subtype": result.get("subtype"),
            "numTurns": result.get("num_turns"),
            "totalCostUsd": result.get("total_cost_usd"),
        },
        "stderrTail": stderr[-2000:],
    }
    if reasons:
        receipt["error"] = "；".join(reasons)
    _json_write(receipt_path, receipt)

    if reasons:
        print(
            "[FAIL] 真实 /code-review 执行未通过：" + "；".join(reasons),
            file=sys.stderr,
        )
        print(f"receipt: {receipt_path}", file=sys.stderr)
        return 2

    if stage:
        _run_git(
            root,
            "add",
            "--",
            receipt_path.relative_to(root).as_posix(),
            events_path.relative_to(root).as_posix(),
            output_path.relative_to(root).as_posix(),
        )

    print(
        json.dumps(
            {
                "ok": True,
                "change": change,
                "base": base,
                "head": head,
                "sessionId": session_id,
                "spawned": spawned,
                "descriptions": sorted(descriptions),
                "receipt": receipt_path.relative_to(root).as_posix(),
                "events": events_path.relative_to(root).as_posix(),
                "output": output_path.relative_to(root).as_posix(),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="run_dual_review")
    parser.add_argument("--change", required=True)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-stage", action="store_true")
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--max-turns", type=int, default=DEFAULT_MAX_TURNS)
    args = parser.parse_args()
    try:
        return run_review(
            Path(args.root).expanduser().resolve(),
            args.change,
            dry_run=args.dry_run,
            stage=not args.no_stage,
            timeout=args.timeout,
            max_turns=args.max_turns,
        )
    except (OSError, ValueError, ReviewGuardError) as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
