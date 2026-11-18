"""Contract lint for OpenSpec artifacts and the Delivery Contract."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable

from .delivery import DeliveryError, parse_contract, parse_tasks

PLACEHOLDER_RE = re.compile(r"TBD|TODO|待定|待补充|<[^>\n]+>|…")
VAGUE_RE = re.compile(r"尽量|大概|合理|友好|fast|friendly|enough|etc\.", re.IGNORECASE)
REQUIREMENT_RE = re.compile(r"^### Requirement:\s*(.+)$", re.MULTILINE)
SCENARIO_RE = re.compile(r"^#### Scenario:\s*(.+)$", re.MULTILINE)
TASK_HEADING_RE = re.compile(r"^### Task (\d+):", re.MULTILINE)
CHECKBOX_RE = re.compile(r"^\s*- \[[ xX]\]", re.MULTILINE)
COVERS_RE = re.compile(r"Covers:\s*([^\n]+)", re.IGNORECASE)


class LintError(RuntimeError):
    pass


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise LintError(f"无法读取 {path}：{exc}") from exc


def _git(root: Path, *args: str) -> str:
    completed = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, timeout=60)
    if completed.returncode != 0:
        raise LintError(f"git {' '.join(args)} 失败：{completed.stderr.strip()[:300]}")
    return completed.stdout.strip()


def _issue(issues: list[dict], rule: str, level: str, path: str, message: str) -> None:
    issues.append({"rule": rule, "level": level, "path": path, "message": message})


def _sections(text: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current = ""
    for line in text.splitlines():
        match = re.match(r"^##\s+(.+?)\s*$", line)
        if match:
            current = match.group(1).strip().lower()
            sections.setdefault(current, [])
        elif current:
            sections[current].append(line)
    return {key: "\n".join(value).strip() for key, value in sections.items()}


def _check_placeholders(issues: list[dict], path: Path, relative: str) -> None:
    text = _read(path)
    match = PLACEHOLDER_RE.search(text)
    if match:
        _issue(issues, "L1", "ERROR", relative, f"存在占位内容：{match.group(0)!r}")


def _check_proposal(issues: list[dict], change_dir: Path, relative: str) -> None:
    path = change_dir / "proposal.md"
    if not path.is_file():
        _issue(issues, "L1", "ERROR", relative, "缺少 proposal.md")
        return
    sections = _sections(_read(path))
    for name in ("why", "what changes", "out of scope"):
        if not sections.get(name, "").strip():
            _issue(issues, "L1", "ERROR", relative, f"proposal 缺少章节：{name}")
    _check_placeholders(issues, path, relative)


def _check_design(issues: list[dict], change_dir: Path, relative: str) -> None:
    path = change_dir / "design.md"
    if not path.is_file():
        _issue(issues, "L8", "ERROR", relative, "缺少 design.md")
        return
    text = _read(path)
    sections = _sections(text)
    for name in ("decisions", "risks"):
        if not sections.get(name, "").strip():
            _issue(issues, "L8", "ERROR", relative, f"design 缺少章节：{name}")
    if not any(token in text.lower() for token in ("verification", "验证边界", "验证")):
        _issue(issues, "L8", "ERROR", relative, "design 缺少验证边界")
    _check_placeholders(issues, path, relative)


def _check_specs(issues: list[dict], change_dir: Path) -> None:
    specs = sorted((change_dir / "specs").rglob("*.md")) if (change_dir / "specs").is_dir() else []
    if not specs:
        _issue(issues, "L2", "ERROR", "specs/", "缺少 specs/**/spec.md")
        return
    for spec in specs:
        relative = spec.relative_to(change_dir).as_posix()
        text = _read(spec)
        requirements = list(REQUIREMENT_RE.finditer(text))
        scenarios = list(SCENARIO_RE.finditer(text))
        if not requirements:
            _issue(issues, "L2", "ERROR", relative, "没有 ### Requirement:")
        if not scenarios:
            _issue(issues, "L2", "ERROR", relative, "没有 #### Scenario:")
        for requirement in requirements:
            if "SHALL" not in text[requirement.end(): requirement.end() + 400]:
                _issue(issues, "L2", "ERROR", relative, f"Requirement 缺少 SHALL：{requirement.group(1)[:60]}")
        for scenario in scenarios:
            block = text[scenario.end(): scenario.end() + 600]
            if "WHEN" not in block or "THEN" not in block:
                _issue(issues, "L2", "ERROR", relative, f"Scenario 缺少 WHEN/THEN：{scenario.group(1)[:60]}")
        _check_placeholders(issues, spec, relative)
        match = VAGUE_RE.search(text)
        if match:
            _issue(issues, "L3", "WARN", relative, f"可能含糊的措辞：{match.group(0)!r}")


def _check_tasks(issues: list[dict], root: Path, change_dir: Path) -> tuple[object | None, object | None]:
    path = change_dir / "tasks.md"
    if not path.is_file():
        _issue(issues, "L4", "ERROR", "tasks.md", "缺少 tasks.md")
        return None, None
    text = _read(path)
    headings = list(TASK_HEADING_RE.finditer(text))
    boxes = list(CHECKBOX_RE.finditer(text))
    if len(headings) != len(boxes):
        _issue(issues, "L4", "ERROR", "tasks.md", f"任务标题 {len(headings)} 个，复选框 {len(boxes)} 个")
    if not 3 <= len(headings) <= 7:
        _issue(issues, "L5", "WARN", "tasks.md", f"任务数 {len(headings)}，建议 3–7")
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        block = text[heading.end():end]
        if "**Files:**" not in block:
            _issue(issues, "L5", "ERROR", "tasks.md", f"Task {heading.group(1)} 缺少 Files")
        if "Expected" not in block:
            _issue(issues, "L5", "ERROR", "tasks.md", f"Task {heading.group(1)} 缺少 Expected")
        if not COVERS_RE.search(block):
            _issue(issues, "L6", "WARN", "tasks.md", f"Task {heading.group(1)} 缺少 Covers 映射")
    _check_placeholders(issues, path, "tasks.md")
    try:
        contract = parse_contract(text)
        tasks = parse_tasks(text)
    except DeliveryError as exc:
        _issue(issues, "L4", "ERROR", "tasks.md", str(exc))
        return None, None
    covers_text = " ".join(match.group(1) for match in COVERS_RE.finditer(text))
    for acceptance, (_, evidence_name) in contract.acceptance.items():
        if evidence_name and evidence_name not in contract.evidence and evidence_name not in {"manual", "review"}:
            _issue(issues, "L6", "ERROR", "tasks.md", f"{acceptance} 映射了未知 evidence：{evidence_name}")
        if acceptance not in covers_text:
            _issue(issues, "L6", "WARN", "tasks.md", f"acceptance {acceptance} 未被任务 Covers 覆盖")
    try:
        ancestor = subprocess.run(
            ["git", "merge-base", "--is-ancestor", contract.base, "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=60,
        ).returncode == 0
    except OSError:
        ancestor = False
    if not ancestor:
        _issue(issues, "L7", "ERROR", "tasks.md", f"Base {contract.base} 不是 HEAD 祖先")
    return contract, tasks


def _check_second_plan(issues: list[dict], root: Path) -> None:
    for relative in ("docs/superpowers/plans", ".superpowers/sdd"):
        if (root / relative).exists():
            _issue(issues, "L10", "ERROR", relative, "存在第二份计划/ledger 目录")


def _check_clarification(issues: list[dict], change_dir: Path) -> None:
    text = "\n".join(_read(path) for path in sorted(change_dir.rglob("*.md")))
    if "无需澄清" in text or "no clarification" in text.lower():
        return
    _issue(issues, "L11", "WARN", "change", "未记录 clarification receipt 或“无需澄清”理由")


def lint_change(
    root: Path,
    change: str,
    *,
    stage: str = "plan",
    profile: dict | None = None,
) -> dict:
    if stage not in ("plan", "delivery"):
        raise LintError("stage 只能是 plan 或 delivery")
    root = root.resolve()
    if not change or "/" in change or ".." in Path(change).parts:
        raise LintError(f"change 非法：{change!r}")
    change_dir = (root / "openspec" / "changes" / change).resolve()
    try:
        change_dir.relative_to(root)
    except ValueError as exc:
        raise LintError("change 目录必须位于仓库内") from exc
    if not change_dir.is_dir():
        raise LintError(f"change 目录不存在：{change_dir}")
    issues: list[dict] = []
    _check_proposal(issues, change_dir, "proposal.md")
    _check_design(issues, change_dir, "design.md")
    _check_specs(issues, change_dir)
    _check_tasks(issues, root, change_dir)
    _check_second_plan(issues, root)
    if stage == "plan":
        _check_clarification(issues, change_dir)
    if stage == "delivery" and profile is not None:
        if profile.get("required") is True and not isinstance(profile.get("profile", "strict"), str):
            _issue(issues, "CONFIG", "ERROR", "profile", "contractLint.profile 非法")
    issues.sort(key=lambda item: (item["rule"], item["path"], item["message"]))
    ok = not any(item["level"] == "ERROR" for item in issues)
    return {"ok": ok, "stage": stage, "change": change, "issues": issues}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="lint_cli")
    sub = parser.add_subparsers(dest="command", required=True)
    change = sub.add_parser("change")
    change.add_argument("--root", default=".")
    change.add_argument("--change", required=True)
    change.add_argument("--stage", choices=("plan", "delivery"), default="plan")
    change.add_argument("--profile")
    args = parser.parse_args(argv)
    try:
        profile = json.loads(Path(args.profile).read_text(encoding="utf-8")) if args.profile else None
        result = lint_change(Path(args.root).expanduser().resolve(), args.change, stage=args.stage, profile=profile)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0 if result["ok"] else 1
    except (LintError, OSError, ValueError) as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
