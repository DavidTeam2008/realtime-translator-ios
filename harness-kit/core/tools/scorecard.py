#!/usr/bin/env python3
"""harness 评分卡工具（生成草稿 / 过期提醒；标准库；不联网）。

用法：
    python3 tools/scorecard.py [--generate] [--root PATH]
    python3 tools/scorecard.py --check-stale [--strict] [--root PATH]
    python3 tools/scorecard.py ... [--json]

根目录默认「本脚本上级目录」；`--root` 可覆盖。配置唯一来源是
`<root>/harness/config.json`（README/SPEC 见 kit；阈值在 `scorecard` 段）：

    "scorecard": { "maxAgeDays": 30, "maxCommits": 50 }

- `--generate`（默认）：依次跑 `check_docs` / `check_agents` /
  `check_plan check --lenient-uncommitted` / `check_hygiene` / `check_layers` /
  `verify_claim --all`，记录命令、退出码与关键输出，生成
  `<paths.reviews>/<YYYY-MM-DD>-scorecard.md` 草稿（含 checkedAt、commit、
  证据 ID、测试计数、文档计数、五子系统「自评 / 独立复评」两列 TBD）。
  门禁本身失败只记录，不阻断生成（草稿要如实反映现状）。
- `--check-stale`：读 reviews 下最新 `*-scorecard.md`；checkedAt 超过
  `maxAgeDays` 天，或 commit 之后新增提交数超过 `maxCommits` → `[WARN]`；
  没有 scorecard → `[WARN]`。默认 exit 0（只提醒），`--strict` 才 exit 1。
- `--json`：机器可读结果（供测试/CI 摘要）。

不写文件（`--generate` 只写评分卡草稿）、不联网、无第三方依赖。
退出码：0 正常；1 配置/写入错误，或 `--strict` 判定过期；2 用法错误。
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

CONFIG_REL = Path("harness") / "config.json"
SCORECARD_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-scorecard\.md$")
CHECKED_AT_RE = re.compile(r"^-\s*checkedAt:\s*(\S+)\s*$", re.MULTILINE)
COMMIT_RE = re.compile(r"^-\s*commit:\s*([0-9a-f]{7,40})", re.MULTILINE)
EVIDENCE_ID_RE = re.compile(r"^\d{8}T\d{6}Z-[a-z0-9][a-z0-9-]*$")
DEFAULT_MAX_AGE_DAYS = 30
DEFAULT_MAX_COMMITS = 50
GATE_TOOLS = (
    ("check_docs", ["tools/check_docs.py"]),
    ("check_agents", ["tools/check_agents.py"]),
    ("check_plan", ["tools/check_plan.py", "check", "--lenient-uncommitted"]),
    ("check_hygiene", ["tools/check_hygiene.py"]),
    ("check_layers", ["tools/check_layers.py"]),
    ("verify_claim", ["tools/verify_claim.py", "--all"]),
)
SUBSYSTEMS = (
    ("Instructions", "根 / 嵌套指令、预算、引用可解析", "make check / check_agents"),
    ("State", "计划状态机、handoff、唯一 active、证据绑定", "check_plan / verify_claim"),
    ("Verification", "静态 / 动态门禁、证据三值、skip 白名单", "门禁快照 / verify_claim"),
    ("Scope", "改动范围声明、越界拦截、DoD", "check_plan / scope.allow"),
    ("Session Lifecycle", "冷启动、健康检查、收尾与交接", "make status / handoff"),
)


class ScorecardError(Exception):
    """配置 / 写入错误（exit 1）。"""


def load_config(root: Path) -> dict:
    path = root / CONFIG_REL
    if not path.is_file():
        raise ScorecardError(f"缺少配置文件 {CONFIG_REL.as_posix()}（相对 {root}）")
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ScorecardError(f"{CONFIG_REL.as_posix()} 不是合法 JSON：{exc}") from exc
    if not isinstance(config, dict):
        raise ScorecardError(f"{CONFIG_REL.as_posix()} 顶层必须是 JSON 对象")
    return config


def config_path(root: Path, config: dict, key: str, default: str) -> Path:
    paths = config.get("paths") if isinstance(config.get("paths"), dict) else {}
    value = paths.get(key, default)
    return root / (str(value) if isinstance(value, str) and value else default)


def scorecard_settings(config: dict) -> tuple[int, int]:
    section = config.get("scorecard")
    if section is None:
        section = {}
    if not isinstance(section, dict):
        raise ScorecardError("config.scorecard 必须是对象")
    max_age = section.get("maxAgeDays", DEFAULT_MAX_AGE_DAYS)
    max_commits = section.get("maxCommits", DEFAULT_MAX_COMMITS)
    for value, label in ((max_age, "maxAgeDays"), (max_commits, "maxCommits")):
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ScorecardError(f"config.scorecard.{label} 必须是非负整数")
    return max_age, max_commits


def run_gate(root: Path, parts: list[str]) -> dict:
    script = root / parts[0]
    display = "python3 " + parts[0] + ("" if len(parts) == 1 else " " + " ".join(parts[1:]))
    if not script.is_file():
        return {
            "command": display,
            "exitCode": None,
            "status": "SKIP（缺少 " + parts[0] + "）",
            "keyOutput": [],
        }
    try:
        result = subprocess.run(
            [sys.executable, str(script), *parts[1:]],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=180,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:  # pragma: no cover - 防御
        return {
            "command": display,
            "exitCode": None,
            "status": f"ERROR（{exc}）",
            "keyOutput": [],
        }
    output = (result.stdout or "") + (result.stderr or "")
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    key = [line for line in lines if line.startswith(("[OK]", "[FAIL]", "[WARN]", "[SKIP]"))][:5]
    if not key:
        key = lines[-3:]
    return {
        "command": display,
        "exitCode": result.returncode,
        "status": "PASS" if result.returncode == 0 else "FAIL",
        "keyOutput": key,
    }


def git_run(root: Path, *args: str) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args], capture_output=True, text=True, timeout=30
        )
    except (OSError, subprocess.TimeoutExpired):
        return False, ""
    return result.returncode == 0, result.stdout.strip()


def git_value(root: Path, *args: str) -> str | None:
    ok, output = git_run(root, *args)
    return output if ok else None


def dotted_value(document: object, dotted: str) -> object | None:
    current = document
    for part in dotted.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def latest_evidence(root: Path, config: dict) -> list[dict]:
    evidence_dir = config_path(root, config, "evidence", "harness/evidence")
    claims = [
        claim.get("name")
        for claim in config.get("claims", [])
        if isinstance(claim, dict) and isinstance(claim.get("name"), str)
    ]
    rows: list[dict] = []
    for claim in claims:
        found: tuple[str, str | None] | None = None
        if evidence_dir.is_dir():
            for path in sorted(evidence_dir.glob("*.json"), reverse=True):
                if not EVIDENCE_ID_RE.fullmatch(path.stem):
                    continue
                try:
                    doc = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue
                if isinstance(doc, dict) and doc.get("claim") == claim:
                    found = (path.stem, str(doc.get("verdict") or "?"))
                    break
        rows.append(
            {"claim": claim, "id": found[0] if found else None, "verdict": found[1] if found else None}
        )
    return rows


def test_baseline(root: Path, config: dict) -> dict | None:
    for claim in config.get("claims", []):
        if not isinstance(claim, dict) or claim.get("type") != "test-count":
            continue
        baseline_rel = claim.get("baseline")
        floor_path = claim.get("floor")
        skipped_path = claim.get("expectedSkipped")
        if not isinstance(baseline_rel, str) or not isinstance(floor_path, str):
            return None
        baseline_file = root / baseline_rel
        if not baseline_file.is_file():
            return None
        try:
            document = json.loads(baseline_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return {
            "baseline": baseline_rel,
            "floor": dotted_value(document, floor_path),
            "expectedSkipped": dotted_value(document, skipped_path)
            if isinstance(skipped_path, str)
            else None,
        }
    return None


def count_documents(root: Path, config: dict) -> int:
    paths = config.get("paths") if isinstance(config.get("paths"), dict) else {}
    docs_dir = root / str(paths.get("docs", "docs"))
    references_dir = root / str(paths.get("references", "references"))
    count = 0
    for directory in (docs_dir, references_dir):
        if not directory.is_dir():
            continue
        for path in directory.rglob("*.md"):
            if not path.is_file():
                continue
            parts = path.relative_to(root).parts
            if "runs" in parts or "_archive" in parts:
                continue
            count += 1
    root_docs = paths.get("rootDocs")
    if isinstance(root_docs, list):
        count += sum(1 for rel in root_docs if isinstance(rel, str) and (root / rel).is_file())
    return count


def collect_snapshot(root: Path, config: dict) -> dict:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    commit = git_value(root, "rev-parse", "--short", "HEAD")
    dirty_output = git_value(root, "status", "--porcelain")
    dirty = len([line for line in (dirty_output or "").splitlines() if line.strip()])
    gates = [run_gate(root, parts) for _, parts in GATE_TOOLS]
    return {
        "checkedAt": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "date": now.strftime("%Y-%m-%d"),
        "commit": commit,
        "dirty": dirty,
        "kitVersion": str(config.get("kitVersion") or "unknown"),
        "gates": gates,
        "evidence": latest_evidence(root, config),
        "testBaseline": test_baseline(root, config),
        "docsCount": count_documents(root, config),
    }


def _escape_cell(text: str) -> str:
    return text.replace("|", "\\|")


def render_scorecard(snapshot: dict) -> str:
    evidence_line = "；".join(
        f"{row['claim']}={row['id'] or '（无证据）'}（{row['verdict'] or 'UNVERIFIED'}）"
        for row in snapshot["evidence"]
    ) or "（无 claims）"
    baseline = snapshot["testBaseline"]
    if baseline is None:
        baseline_line = "（未配置 test-count baseline）"
    else:
        baseline_line = (
            f"floor={baseline['floor']} expectedSkipped={baseline['expectedSkipped']}"
            f"（{baseline['baseline']}）"
        )
    lines = [
        f"# harness 评分卡 · {snapshot['date']}",
        "",
        "> 草稿：由 `make scorecard`（`tools/scorecard.py --generate`）生成；"
        "「自评」与「独立复评」两列需人工填写，生成器只提供门禁快照，不自动打分。",
        "> **自评不是认证**；「独立复评」列为 TBD 时，本评分卡不算完成证据。",
        "> 每次大改后重新生成；`make check` 会对过期评分卡给出 WARN（不阻断）。",
        "",
        f"- checkedAt: {snapshot['checkedAt']}",
        f"- commit: {snapshot['commit'] or '（非 git 仓库）'}"
        + (f"（dirty 文件 {snapshot['dirty']} 个）" if snapshot["dirty"] else ""),
        f"- kitVersion: {snapshot['kitVersion']}",
        f"- evidence: {evidence_line}",
        f"- 测试基线：{baseline_line}",
        f"- 文档计数：{snapshot['docsCount']} 篇（docs/ + references/ + rootDocs 中现有文件）",
        "",
        "## 1. 门禁快照（自动）",
        "",
        "| 命令 | exit | 关键输出 |",
        "| --- | --- | --- |",
    ]
    for gate in snapshot["gates"]:
        output = "；".join(_escape_cell(line) for line in gate["keyOutput"]) or "（无输出）"
        exit_code = "—" if gate["exitCode"] is None else str(gate["exitCode"])
        lines.append(f"| `{_escape_cell(gate['command'])}` | {exit_code} | {output} |")
    lines += [
        "",
        "## 2. 五子系统评分（自评 / 独立复评）",
        "",
        "| 子系统 | 关注点 | 自评（1–5） | 独立复评（1–5） | 证据 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for name, focus, evidence in SUBSYSTEMS:
        lines.append(f"| {name} | {focus} | TBD | TBD | {evidence} |")
    lines += [
        "",
        "## 3. 未验证 / 待人工",
        "",
        "- 五子系统分数为 TBD：需人工按 1–5 口径（1 缺失 / 3 有规则不可机检 / 5 有门禁+证据+定期复核）自评；",
        "- 自评不是认证；独立复评列为 TBD 时本卡不算完成证据（release 门禁可另行强制）。",
        "- 独立复评需由未参与实现的人/Agent 只读仓库后填写；自评与独立复评分列，不互相替代。",
        "- 门禁快照只证明「命令跑了、退出码如此」，不证明行为正确；动态/真机/性能仍需项目自己的证据。",
        "",
        "## 4. 复现",
        "",
        "```bash",
        "make scorecard          # 重新生成本文件",
        "make verify-static      # 静态门禁",
        "make selftest           # 负向注入自检（证明门禁会红）",
        "make verify-claim       # 证据三值判定",
        "```",
        "",
    ]
    return "\n".join(lines)


def write_scorecard(root: Path, config: dict, snapshot: dict) -> dict:
    reviews_dir = config_path(root, config, "reviews", "harness/reviews")
    try:
        reviews_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ScorecardError(f"无法创建 reviews 目录：{reviews_dir}：{exc}") from exc
    target = reviews_dir / f"{snapshot['date']}-scorecard.md"
    try:
        target.write_text(render_scorecard(snapshot), encoding="utf-8")
    except OSError as exc:
        raise ScorecardError(f"无法写入评分卡：{target}：{exc}") from exc
    snapshot["scorecard"] = target.relative_to(root).as_posix()
    return snapshot


def latest_scorecard(root: Path, config: dict) -> Path | None:
    reviews_dir = config_path(root, config, "reviews", "harness/reviews")
    if not reviews_dir.is_dir():
        return None
    candidates = sorted(
        (path for path in reviews_dir.glob("*-scorecard.md") if SCORECARD_RE.fullmatch(path.name)),
        reverse=True,
    )
    return candidates[0] if candidates else None


def parse_checked_at(text: str) -> datetime | None:
    match = CHECKED_AT_RE.search(text)
    if not match:
        return None
    try:
        return datetime.strptime(match.group(1), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def check_stale(root: Path, config: dict) -> dict:
    max_age, max_commits = scorecard_settings(config)
    path = latest_scorecard(root, config)
    result: dict = {
        "status": "missing",
        "scorecard": None,
        "ageDays": None,
        "commitsSince": None,
        "maxAgeDays": max_age,
        "maxCommits": max_commits,
        "warnings": [],
    }
    if path is None:
        result["warnings"].append("未找到 scorecard（先跑 make scorecard 生成草稿）")
        return result
    result["scorecard"] = path.relative_to(root).as_posix()
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        result["status"] = "invalid"
        result["warnings"].append(f"无法读取 scorecard：{exc}")
        return result
    checked_at = parse_checked_at(text)
    if checked_at is None:
        result["status"] = "invalid"
        result["warnings"].append("scorecard 缺少可解析的 checkedAt（YYYY-MM-DDTHH:MM:SSZ）")
        return result
    age_days = max(0, (datetime.now(timezone.utc) - checked_at).days)
    result["ageDays"] = age_days
    if age_days > max_age:
        result["warnings"].append(f"scorecard 已 {age_days} 天未更新（阈值 {max_age} 天）")
    commit_match = COMMIT_RE.search(text)
    if not commit_match:
        result["warnings"].append("scorecard 缺少可解析 commit（无法校验 commit 时效/祖先）")
    if commit_match:
        commit = commit_match.group(1)
        ancestor_ok, _ = git_run(root, "merge-base", "--is-ancestor", commit, "HEAD")
        if not ancestor_ok:
            result["warnings"].append(
                f"scorecard commit {commit} 不是 HEAD 祖先（可能来自其他分支/已重写历史）"
            )
        count_output = git_value(root, "rev-list", "--count", f"{commit}..HEAD")
        if count_output is not None and count_output.isdigit():
            result["commitsSince"] = int(count_output)
            if int(count_output) > max_commits:
                result["warnings"].append(
                    f"scorecard 之后新增 {count_output} 个提交（阈值 {max_commits} 个）"
                )
        elif ancestor_ok:
            result["warnings"].append(f"无法解析 scorecard commit：{commit}（可能不在当前历史）")
    result["status"] = "stale" if result["warnings"] else "fresh"
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="harness 评分卡：生成草稿 / 过期提醒（只提醒，不认证）。",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="项目根（默认脚本上级目录）",
    )
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--generate", action="store_true", help="生成评分卡草稿（默认）")
    action.add_argument("--check-stale", action="store_true", help="检查评分卡是否过期")
    parser.add_argument("--strict", action="store_true", help="配合 --check-stale：过期时 exit 1")
    parser.add_argument("--json", action="store_true", help="输出机器可读 JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.expanduser().resolve()
    if args.strict and not args.check_stale:
        print("[FAIL] --strict 只能配合 --check-stale 使用", file=sys.stderr)
        return 2
    if not root.is_dir():
        print(f"[FAIL] 根目录不存在：{root}", file=sys.stderr)
        return 1
    try:
        config = load_config(root)
        if args.check_stale:
            result = check_stale(root, config)
            if args.json:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                for warning in result["warnings"]:
                    print(f"[WARN] {warning}")
                if result["status"] == "fresh":
                    print(
                        f"[OK] scorecard 新鲜：{result['scorecard']}"
                        f"（{result['ageDays']} 天前，之后 {result['commitsSince']} 个提交）"
                    )
            if args.strict and result["status"] != "fresh":
                return 1
            return 0

        snapshot = collect_snapshot(root, config)
        snapshot = write_scorecard(root, config, snapshot)
        if args.json:
            print(json.dumps(snapshot, ensure_ascii=False, indent=2))
        else:
            failed = [gate for gate in snapshot["gates"] if gate["exitCode"] not in (0, None)]
            print(f"[OK] 评分卡草稿已生成：{snapshot['scorecard']}")
            print(
                f"      门禁快照：{len(snapshot['gates'])} 条，"
                f"{len(failed)} 条非 0（已如实记录；自评/独立复评为 TBD）"
            )
        return 0
    except ScorecardError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
