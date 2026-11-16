#!/usr/bin/env python3
"""harness: one-screen project state and plan/verify/handoff entry for a harness-kit host.

Usage (inside an initialized target project):
    python3 tools/harness.py status [--json]
    python3 tools/harness.py start --topic TOPIC [--goal TEXT] [--scope PATH ...]
                                    [--acceptance TEXT ...] [--level L1|L2]
    python3 tools/harness.py verify [--no-sync] [--claims-strict]
    python3 tools/harness.py handoff [--json]
    python3 tools/harness.py intake --file <需求卡.md> [--topic T] [--scope P ...]
    python3 tools/harness.py release [--check] [--strict]
    python3 tools/harness.py plan check
    python3 tools/harness.py upgrade [--apply]

Contract: standard library only; no network. `status` / `plan check` / `upgrade` are
read-only; `start` writes one plan file; `verify` / `handoff` may rewrite the active
plan's「未提交改动」section to match `git status` (来源：harness-kit v0.3.0-alpha).
Exit codes: 0 ok; 1 gate/plan failure; 2 usage or missing capability.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

CONFIG_REL = Path("harness") / "config.json"
MANIFEST_NAME = ".harness-manifest.json"
EVIDENCE_ID_RE = re.compile(r"^\d{8}T\d{6}Z-[a-z0-9-]+$")
COMMIT_RE = re.compile(r"^[0-9a-f]{7,40}$")
PATH_TOKEN_RE = re.compile(r"`([^`\n]+)`")
CLEAN_RE = re.compile(r"无未提交改动|没有未提交|工作区\s*(clean|干净)|全部已提交|已全部提交")
PLACEHOLDER_HINTS = ("待补", "待填", "TODO", "FIXME")


# ── 基础 ─────────────────────────────────────────────────────────────────
def fail(message: str, code: int = 1) -> int:
    print(f"[FAIL] {message}", file=sys.stderr)
    return code


def info(message: str) -> None:
    print(f"[OK] {message}")


def root_from_script() -> Path:
    return Path(__file__).resolve().parent.parent


def load_config(root: Path) -> dict:
    path = root / CONFIG_REL
    if not path.is_file():
        raise SystemExit(fail(f"缺少配置：{path}（先由 harness-init 生成；或已不在项目根运行）", 2))
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(fail(f"配置无法解析：{path}：{exc}", 2))
    if not isinstance(config, dict):
        raise SystemExit(fail(f"配置必须是 JSON object：{path}", 2))
    for key in ("kitVersion", "paths", "commands", "claims"):
        if key not in config:
            raise SystemExit(fail(f"配置缺字段：{key}（{path}）", 2))
    return config


def config_path(root: Path, config: dict, key: str) -> Path:
    return root / config["paths"][key]


def git(root: Path, args: list[str], timeout: int = 30) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(
            ["git", *args], cwd=str(root), capture_output=True, text=True, timeout=timeout
        )
        return proc.returncode, proc.stdout, proc.stderr
    except (OSError, subprocess.TimeoutExpired) as exc:  # pragma: no cover - 防御
        return 127, "", str(exc)


def git_status_paths(root: Path) -> set[str] | None:
    code, out, _ = git(root, ["status", "--porcelain", "-z", "--untracked-files=all"])
    if code != 0:
        return None
    paths: set[str] = set()
    records = out.split("\0")
    index = 0
    while index < len(records):
        record = records[index]
        index += 1
        if not record or len(record) < 4:
            continue
        status, path = record[:2], record[3:]
        if "R" in status or "C" in status:
            index += 1
        paths.add(path.strip())
    return paths


def git_user(root: Path) -> str:
    code, out, _ = git(root, ["config", "user.name"])
    if code == 0 and out.strip():
        return out.strip()
    return os.environ.get("USER") or os.environ.get("GIT_AUTHOR_NAME") or "agent"


def slugify(topic: str) -> str:
    return re.sub(r"[^\w.-]+", "-", topic.strip().lower()).strip("-")


def project_name(config: dict) -> str:
    project = config.get("project") if isinstance(config.get("project"), dict) else {}
    return str(project.get("name") or "project")


def read_manifest(root: Path) -> dict | None:
    path = root / MANIFEST_NAME
    if not path.is_file():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return doc if isinstance(doc, dict) else None


# ── 计划解析 ─────────────────────────────────────────────────────────────
class Plan:
    def __init__(self, path: Path, text: str) -> None:
        self.path = path
        self.text = text
        self.meta: dict[str, object] = {}
        self.body = text
        self._parse()

    @property
    def status(self) -> str:
        value = self.meta.get("status")
        return str(value).strip() if isinstance(value, str) else ""

    @property
    def rel(self) -> str:
        return self.path.as_posix()

    def _parse(self) -> None:
        lines = self.text.splitlines()
        if not lines or lines[0].strip() != "---":
            return
        end = None
        for index in range(1, len(lines)):
            if lines[index].strip() == "---":
                end = index
                break
        if end is None:
            return
        fm = lines[1:end]
        self.body = "\n".join(lines[end + 1:])
        last_key: str | None = None
        for raw in fm:
            stripped = raw.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped.startswith("- "):
                if last_key:
                    bucket = self.meta.setdefault(last_key, [])
                    if isinstance(bucket, list):
                        bucket.append(stripped[2:].strip())
                continue
            match = re.match(r"^([A-Za-z0-9_.-]+):\s*(.*)$", stripped)
            if not match:
                last_key = None
                continue
            key, value = match.group(1), match.group(2).strip()
            if value:
                self.meta[key] = value
                last_key = None
            else:
                last_key = key
                if key in ("scope", "acceptance", "verify"):
                    self.meta.setdefault(key, [])

    def allow(self) -> list[str]:
        raw = self.meta.get("allow")
        if not isinstance(raw, list):
            return []
        return [str(item).strip() for item in raw if str(item).strip()]

    def section(self, *aliases: str) -> str:
        """Return the body text of the first `## ...` heading matching any alias."""
        lines = self.body.splitlines()
        starts: list[tuple[int, str]] = []
        for index, line in enumerate(lines):
            match = re.match(r"^##\s+(.+?)\s*$", line)
            if match:
                starts.append((index, match.group(1)))
        for position, (index, title) in enumerate(starts):
            if any(alias in title for alias in aliases):
                end = starts[position + 1][0] if position + 1 < len(starts) else len(lines)
                return "\n".join(lines[index + 1:end]).strip()
        return ""

    def goal_text(self) -> str:
        return self.section("目标与非目标", "目标与验收", "目标")

    def acceptance_text(self) -> str:
        return self.section("验收")


def load_plans(root: Path, config: dict) -> list[Plan]:
    directory = config_path(root, config, "plans")
    if not directory.is_dir():
        return []
    plans: list[Plan] = []
    for path in sorted(directory.glob("*.md")):
        if path.name.startswith("_"):
            continue
        try:
            plans.append(Plan(path, path.read_text(encoding="utf-8")))
        except OSError:
            continue
    return plans


def active_plan(plans: list[Plan]) -> Plan | None:
    active = [plan for plan in plans if plan.status == "active"]
    return active[0] if active else None


def load_archived_plans(root: Path, config: dict) -> list[Plan]:
    """读取 plans/_archive/*.md（按文件名倒序，最新在前）；用于无 active 时回读。"""
    directory = config_path(root, config, "plans") / "_archive"
    if not directory.is_dir():
        return []
    plans: list[Plan] = []
    for path in sorted(directory.glob("*.md"), reverse=True):
        if path.name.startswith("_"):
            continue
        try:
            plans.append(Plan(path, path.read_text(encoding="utf-8")))
        except OSError:
            continue
    return plans


def plan_unverified(plan: Plan) -> str:
    """「未验证项」正文（排除「未验证豁免」节）。"""
    lines = plan.body.splitlines()
    starts: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        match = re.match(r"^##\s+(.+?)\s*$", line)
        if match:
            starts.append((index, match.group(1)))
    for position, (index, title) in enumerate(starts):
        lowered = title.lower()
        if "豁免" in title or "waiver" in lowered or "未验证" not in title:
            continue
        end = starts[position + 1][0] if position + 1 < len(starts) else len(lines)
        return "\n".join(lines[index + 1:end]).strip()
    return ""


def plan_summary(plan: Plan, root: Path) -> dict:
    """计划摘要（active 与归档共用；归档回读不把它当当前计划）。"""
    try:
        rel = plan.path.relative_to(root).as_posix()
    except ValueError:
        rel = plan.path.as_posix()
    goal = plan.goal_text()
    return {
        "id": plan.meta.get("id"),
        "path": rel,
        "archived": plan.path.parent.name == "_archive",
        "status": plan.status,
        "level": plan.meta.get("level"),
        "owner": plan.meta.get("owner"),
        "updated": plan.meta.get("updated"),
        "submitted": str(plan.meta.get("submitted") or ""),
        "goal": goal.splitlines()[0] if goal else "",
        "unverified": plan_unverified(plan),
        "next": plan.section("下一步"),
    }


# ── 需求卡（intake）────────────────────────────────────────────────────────
def markdown_sections(text: str) -> dict[str, str]:
    """Split a markdown file into {heading: body} for `## ` headings."""
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        match = re.match(r"^##\s+(.+?)\s*$", line)
        if match:
            current = match.group(1)
            sections.setdefault(current, [])
            continue
        if current is not None:
            sections[current].append(line)
    return {key: "\n".join(value).strip() for key, value in sections.items()}


def section_any(sections: dict[str, str], *aliases: str) -> str:
    for title, body in sections.items():
        if any(alias in title for alias in aliases):
            return body
    return ""


EXECUTABLE_HINTS = (
    "make ", "make\t", "python3 ", "python ", "npm ", "pnpm ", "yarn ", "pytest",
    "go test", "swift test", "gradlew", "xcodebuild", "harness.py", "bash ", "sh ",
    "curl ", "node ", "cargo ", "dotnet ",
)


def validate_acceptance(item: str) -> str | None:
    """Return None when acceptable, else a human-readable reason."""
    text = item.strip()
    if not text:
        return "空判据"
    if re.search(r"https?://", text) and ("复核" in text or "review" in text.lower()):
        return None
    lowered = text.lower()
    if any(hint in lowered for hint in EXECUTABLE_HINTS):
        return None
    return "必须是“命令 + 期望结果”，或“可复核链接 + 复核者”"


def parse_requirement_card(path: Path) -> tuple[str, list[str], list[str]]:
    """Return (goal, acceptance, problems) from a requirement markdown file."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SystemExit(fail(f"需求卡无法读取：{path}：{exc}", 2))
    sections = markdown_sections(text)
    goal_body = section_any(sections, "目标", "需求")
    goal = ""
    for line in goal_body.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            goal = stripped.lstrip("-* ").strip()
            break
    if not goal:
        raise SystemExit(fail("需求卡缺少非空「## 目标」", 2))
    acceptance_body = section_any(sections, "验收判据", "验收")
    acceptance = [
        line.strip()[2:].strip()
        for line in acceptance_body.splitlines()
        if line.strip().startswith(("- ", "* ")) and line.strip()[2:].strip()
    ]
    if not acceptance:
        raise SystemExit(fail("需求卡缺少「## 验收判据」列表（每条 = 命令 + 期望结果）", 2))
    problems = [f"{item}：{reason}" for item in acceptance if (reason := validate_acceptance(item))]
    return goal, acceptance, problems


# ── 未提交改动同步 ───────────────────────────────────────────────────────
def normalize_token(token: str) -> str | None:
    text = token.strip().strip("`").strip()
    text = text.strip("。，,；;：:'\"")
    while text.startswith("./"):
        text = text[2:]
    if not text or text.startswith("/") or ".." in Path(text).parts:
        return None
    if COMMIT_RE.fullmatch(text):
        return None
    if "/" in text or re.search(r"\.[A-Za-z0-9]{1,10}$", text):
        return text
    return None


def declared_paths(body: str) -> set[str]:
    found: set[str] = set()
    for line in body.splitlines():
        stripped = line.strip()
        for match in PATH_TOKEN_RE.finditer(stripped):
            token = normalize_token(match.group(1))
            if token:
                found.add(token)
    return found


def path_covered(paths: set[str], target: str) -> bool:
    for declared in paths:
        base = declared.rstrip("/")
        if declared == target or target == base or target.startswith(base + "/"):
            return True
    return False


def in_allow(path: str, allow: list[str]) -> bool:
    if not allow:
        return True
    for pattern in allow:
        pat = str(pattern).strip()
        if not pat:
            continue
        if any(char in pat for char in "*?["):
            if fnmatch.fnmatch(path, pat) or fnmatch.fnmatch(path, pat.rstrip("/") + "/*"):
                return True
            continue
        base = pat.rstrip("/")
        if path == base or path.startswith(base + "/"):
            return True
    return False


SCOPE_WARN = "> 由 `python3 tools/harness.py verify` 同步；scope.allow 之外的文件不应出现在这里。"


def render_uncommitted(paths: list[str]) -> str:
    if not paths:
        return "- 无未提交改动\n"
    lines = [f"- `{path}` / 运行中改动（harness verify 自动同步）" for path in paths]
    return "\n".join(lines) + "\n"


def replace_section(text: str, aliases: tuple[str, ...], body: str) -> tuple[str, bool]:
    lines = text.splitlines()
    starts: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        match = re.match(r"^##\s+(.+?)\s*$", line)
        if match:
            starts.append((index, match.group(1)))
    for position, (index, title) in enumerate(starts):
        if not any(alias in title for alias in aliases):
            continue
        end = starts[position + 1][0] if position + 1 < len(starts) else len(lines)
        before = lines[: index + 1]
        after = lines[end:]
        new_lines = before + [""] + body.rstrip().splitlines() + [""] + after
        return "\n".join(new_lines).rstrip() + "\n", True
    return text, False


def sync_uncommitted(plan: Plan, root: Path) -> list[str] | None:
    actual = git_status_paths(root)
    if actual is None:
        return None
    allow = plan.allow()
    scoped = sorted(path for path in actual if in_allow(path, allow))
    text, found = replace_section(plan.text, ("未提交改动",), render_uncommitted(scoped))
    if not found:
        text = text.rstrip() + "\n\n## 未提交改动\n\n" + render_uncommitted(scoped)
    if text != plan.text:
        plan.path.write_text(text, encoding="utf-8")
    return scoped


# ── 证据摘要 ─────────────────────────────────────────────────────────────
def evidence_summary(root: Path, config: dict) -> dict:
    directory = config_path(root, config, "evidence")
    counts = {"PASS": 0, "FAIL": 0, "UNVERIFIED": 0, "other": 0}
    claims: dict[str, dict] = {}
    entries: list[dict] = []
    if directory.is_dir():
        for path in sorted(directory.glob("*.json")):
            if not EVIDENCE_ID_RE.fullmatch(path.stem):
                continue
            try:
                doc = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                counts["other"] += 1
                continue
            if not isinstance(doc, dict):
                counts["other"] += 1
                continue
            verdict = str(doc.get("verdict") or "UNVERIFIED")
            counts[verdict if verdict in counts else "other"] += 1
            claim = str(doc.get("claim") or "?")
            claims[claim] = {"id": path.stem, "verdict": verdict}
            entries.append({
                "id": path.stem,
                "claim": claim,
                "verdict": verdict,
                "createdAt": str(doc.get("createdAt") or ""),
            })
    archived_total = 0
    if directory.is_dir():
        for path in directory.rglob("*.json"):
            if EVIDENCE_ID_RE.fullmatch(path.stem) and "_archive" in path.relative_to(directory).parts:
                archived_total += 1
    return {
        "counts": counts,
        "claims": claims,
        "entries": entries,
        "total": sum(counts.values()),
        "archivedTotal": archived_total,
    }


# ── 子命令：status ───────────────────────────────────────────────────────
def detect_default_branch(root: Path) -> str | None:
    """origin/HEAD → init.defaultBranch → current branch（K05 / K14 漂移检查用）。"""
    code, out, _ = git(root, ["symbolic-ref", "--short", "refs/remotes/origin/HEAD"])
    if code == 0 and out.strip():
        value = out.strip()
        return value.split("/", 1)[1] if value.startswith("origin/") else value
    code, out, _ = git(root, ["config", "--get", "init.defaultBranch"])
    if code == 0 and out.strip():
        return out.strip()
    code, out, _ = git(root, ["rev-parse", "--abbrev-ref", "HEAD"])
    if code == 0 and out.strip() and out.strip() != "HEAD":
        return out.strip()
    return None


def hooks_state(root: Path) -> dict:
    hook = root / ".githooks" / "pre-push"
    code, out, _ = git(root, ["config", "--get", "core.hooksPath"])
    return {
        "hookFile": hook.is_file(),
        "hooksPath": out.strip() if code == 0 and out.strip() else None,
        "installed": hook.is_file() and code == 0 and out.strip() == ".githooks",
    }


def build_status(root: Path, config: dict) -> dict:
    manifest = read_manifest(root)
    manifest_version = manifest.get("kitVersion") if manifest else None
    manifest_branch = ((manifest or {}).get("options") or {}).get("branch")
    default_branch = detect_default_branch(root)
    hooks = hooks_state(root)
    plans = load_plans(root, config)
    plan = active_plan(plans)
    archived = load_archived_plans(root, config)
    last_plan = archived[0] if archived else None
    evidence = evidence_summary(root, config)
    skills: list[str] = []
    for agent, rel in (("dsh", ".dsh/skills/harness/SKILL.md"), ("claude-code", ".claude/skills/harness/SKILL.md")):
        if (root / rel).is_file():
            skills.append(agent)
    actual = git_status_paths(root) or set()
    declared: set[str] = set()
    scoped_actual: list[str] = []
    if plan is not None:
        scoped_actual = sorted(path for path in actual if in_allow(path, plan.allow()))
        declared = declared_paths(plan.section("未提交改动"))
    actions: list[str] = []

    version_problem = None
    if manifest_version is not None and str(manifest_version) != str(config.get("kitVersion")):
        version_problem = f"manifest.kitVersion={manifest_version} != config.kitVersion={config.get('kitVersion')}"
        actions.append("版本不一致：检查 `.harness-manifest.json` 与 `harness/config.json`，或运行 kit 侧 upgrade --check")

    branch_problem = None
    if manifest_branch and default_branch and str(manifest_branch) != str(default_branch):
        branch_problem = (
            f"manifest.options.branch={manifest_branch} != 仓库默认分支 {default_branch}"
            "（CI / manifest 漂移；常见于在 feature 分支接入）"
        )
        actions.append(
            f"CI/manifest 分支漂移：重跑 init `--default-branch {default_branch}`，"
            "或手工同步 `.github/workflows/verify.yml` 与 `.harness-manifest.json`（旧版可在 feature 分支接入）"
        )
    if hooks["hookFile"] and not hooks["installed"]:
        actions.append("pre-push 已生成但未生效：运行 `git config core.hooksPath .githooks`（或 init 加 --install-hooks）")

    if manifest is None:
        actions.append("没有 `.harness-manifest.json`（v0.2.13 之前接入）：升级/漂移检查走 playbook 手工路径")
    if plan is None:
        if last_plan is not None:
            actions.append(
                f"无 active 计划；先读上一计划 {last_plan.meta.get('id')}（{last_plan.path.relative_to(root).as_posix() if last_plan.path.is_relative_to(root) else last_plan.path}）："
                "核对「未验证项」与「下一步」后再决定新建计划"
            )
        else:
            actions.append("创建首个计划：`python3 tools/harness.py start --topic <topic> --goal \"<目标>\"`")
    else:
        unresolved = [path for path in scoped_actual if not path_covered(declared, path)]
        stale = [path for path in declared if not path_covered(set(scoped_actual), path)]
        if unresolved or stale:
            actions.append("计划与 git 不一致：运行 `python3 tools/harness.py verify` 自动同步未提交段并跑门禁")
        if any(hint in plan.goal_text() for hint in PLACEHOLDER_HINTS):
            actions.append("补全计划「目标与非目标」与「验收」（当前仍是占位内容）")
        if evidence["total"] == 0:
            actions.append("还没有证据：完成前按 `references/verification.md` 写真实证据（无证据 = 未验证）")
        elif evidence["counts"]["UNVERIFIED"] or evidence["counts"]["FAIL"]:
            actions.append("存在未通过/未验证证据：补跑并重新写 evidence 后再 `harness verify`")
        else:
            actions.append("继续实现；收尾跑 `python3 tools/harness.py verify` → `handoff`")
    return {
        "project": project_name(config),
        "kitVersion": config.get("kitVersion"),
        "manifestKitVersion": manifest_version,
        "profile": (manifest or {}).get("profile"),
        "versionProblem": version_problem,
        "branchProblem": branch_problem,
        "manifestBranch": manifest_branch,
        "defaultBranch": default_branch,
        "hooks": hooks,
        "plan": None if plan is None else plan_summary(plan, root),
        "lastPlan": None if last_plan is None else plan_summary(last_plan, root),
        "plans": len(plans),
        "archivedPlans": len(archived),
        "activePlans": sum(1 for item in plans if item.status == "active"),
        "git": {
            "dirty": sorted(actual),
            "scoped": scoped_actual,
            "declared": sorted(declared),
            "inSync": None if plan is None else (
                not [p for p in scoped_actual if not path_covered(declared, p)]
                and not [p for p in declared if not path_covered(set(scoped_actual), p)]
            ),
        },
        "evidence": evidence,
        "skills": skills,
        "nextActions": actions,
    }


def cmd_status(root: Path, args: argparse.Namespace) -> int:
    try:
        config = load_config(root)
    except SystemExit as exc:  # load_config 已打印
        return int(exc.code or 1)
    result = build_status(root, config)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    plan = result["plan"]
    print(f"harness status · {result['project']}")
    print(f"kit: {result['kitVersion']} · manifest: {result['manifestKitVersion'] or '无'} · profile: {result['profile'] or config.get('profile') or '?'}")
    plan_line = "无 active 计划"
    if plan is not None:
        plan_line = f"{plan['id']} ({plan['status']}/{plan['level']}, owner={plan['owner']}, updated={plan['updated']})"
    print(f"计划: {plan_line}")
    last = result["lastPlan"]
    if plan is None and last is not None:
        print(f"上一计划（已归档）: {last['id']} ({last['status']}, updated={last['updated']}) · {last['path']}")
        print("        归档时点快照：未验证项可能已被后续证据解决；这是历史，不是当前计划。")
        newer = [
            item for item in result["evidence"].get("entries", [])
            if item["verdict"] == "PASS" and str(item["createdAt"])[:10] > str(last["updated"] or "")
        ]
        if newer:
            shown = "、".join(item["id"] for item in newer[:5])
            print(f"        归档后新增 PASS 证据：{shown}{'…' if len(newer) > 5 else ''}")
        unverified = (last["unverified"] or "").strip()
        if unverified:
            preview = re.sub(r"\s+", " ", unverified)[:300]
            print(f"上一计划未验证项: {preview}{'…' if len(preview) >= 300 else ''}")
        next_step = (last["next"] or "").strip()
        if next_step:
            preview = re.sub(r"\s+", " ", next_step)[:300]
            print(f"上一计划下一步: {preview}{'…' if len(preview) >= 300 else ''}")
    if plan is not None and plan["goal"]:
        print(f"目标: {plan['goal'][:100]}")
    git_info = result["git"]
    if plan is None:
        print(f"未提交: {len(git_info['dirty'])} 个（无 active 计划，不做范围校验）")
    else:
        print(f"未提交: {len(git_info['dirty'])} 个（scope 内 {len(git_info['scoped'])}；与计划声明{'一致' if git_info['inSync'] else '不一致'}）")
    counts = result["evidence"]["counts"]
    archived_note = f"；归档 {result['evidence'].get('archivedTotal', 0)} 条（不参与判定）" if result['evidence'].get('archivedTotal') else ""
    print(f"证据: {result['evidence']['total']} 条（PASS={counts['PASS']} / UNVERIFIED={counts['UNVERIFIED']} / FAIL={counts['FAIL']}{archived_note}）")
    print(f"skill: {', '.join(result['skills']) if result['skills'] else '未安装（可选；kit 侧 harness-skill install）'}")
    if result["versionProblem"]:
        print(f"[WARN] {result['versionProblem']}")
    if result.get("branchProblem"):
        print(f"[WARN] {result['branchProblem']}")
    hooks = result.get("hooks") or {}
    if hooks.get("hookFile"):
        state = "已生效" if hooks.get("installed") else "未生效"
        print(f"hooks: .githooks/pre-push（{state}；core.hooksPath={hooks.get('hooksPath') or '未设置'}）")
    if result["nextActions"]:
        print("建议下一步:")
        for index, action in enumerate(result["nextActions"], 1):
            print(f"  {index}. {action}")
    return 0


# ── 子命令：start ────────────────────────────────────────────────────────
def fill_plan_template(
    template: str,
    *,
    topic: str,
    goal: str,
    owner: str,
    level: str,
    plan_rel: str,
    allow: list[str],
    acceptance: list[str],
    verify_command: str,
) -> str:
    """Build a valid active plan from the kit template (front matter rebuilt, body filled)."""
    today = date.today().isoformat()
    lines = template.splitlines()
    closing = None
    if lines and lines[0].strip() == "---":
        for index in range(1, len(lines)):
            if lines[index].strip() == "---":
                closing = index
                break
    body = "\n".join(lines[closing + 1:]) if closing is not None else template
    body = body.replace("<date>", today).replace("{{DATE}}", today)
    body = body.replace("<topic>", topic).replace("{{TOPIC}}", topic).replace("<主题>", topic)
    body = re.sub(r"(?m)^- 目标：\s*$", f"- 目标：{goal}", body)
    body = re.sub(r"(?m)^- 非目标：\s*$", "- 非目标：不扩大本次范围（越界先停下更新计划）", body)
    body = re.sub(r"(?m)^- \[ \] <可执行判据.*$", f"- [ ] {acceptance[0]}", body)
    body = re.sub(r"(?m)^- 文件 / 意图 / 是否可丢弃：\s*$",
                  "- 无未提交改动（harness verify 会同步实际差异）", body)
    body = re.sub(r"(?m)^1\.\s*$",
                  "1. 补全目标/验收后开工；完成前跑 `python3 tools/harness.py verify` 与 `harness.py handoff`", body)
    front = [
        "---",
        f"id: {today}-{slugify(topic)}",
        "status: active",
        f"level: {level}",
        f"owner: {owner}",
        f"updated: {today}",
        "scope:",
        "  allow:",
        *[f"    - {item}" for item in allow],
        "  deny: []",
        "acceptance:",
        *[f"  - {item}" for item in acceptance],
        "verify:",
        f"  - {verify_command}",
        "# 完成（status: done）时填写证据 commit 短 hash，并移入 _archive/",
        "# submitted: <hash1,hash2>",
        "---",
    ]
    return "\n".join(front) + "\n" + body


def create_plan(
    root: Path,
    config: dict,
    *,
    topic: str,
    goal: str,
    level: str,
    scope: list[str],
    acceptance: list[str],
) -> tuple[Path, bool]:
    plans_dir = config_path(root, config, "plans")
    if not plans_dir.is_dir():
        raise SystemExit(fail("当前 profile 没有 plans 目录（minimal 不支持计划）；用 standard/strict 或手动创建", 2))
    template_path = plans_dir / "_template.md"
    if not template_path.is_file():
        raise SystemExit(fail(f"缺少计划模板：{template_path}", 2))
    slug = slugify(topic)
    if not slug:
        raise SystemExit(fail("--topic 需包含字母/数字/其它可见字符", 2))
    plan_path = plans_dir / f"{date.today().isoformat()}-{slug}.md"
    if plan_path.exists():
        return plan_path, False
    rel = plan_path.relative_to(root).as_posix()
    text = fill_plan_template(
        template_path.read_text(encoding="utf-8"),
        topic=topic,
        goal=goal,
        owner=git_user(root),
        level=level,
        plan_rel=rel,
        allow=[rel] + [str(item) for item in scope],
        acceptance=acceptance,
        verify_command=str(config.get("commands", {}).get("verify") or "make verify-static"),
    )
    plan_path.write_text(text, encoding="utf-8")
    check = subprocess.run(
        [sys.executable, "tools/check_plan.py", "check", "--lenient-uncommitted"],
        cwd=str(root), capture_output=True, text=True,
    )
    if check.returncode != 0:
        print(check.stdout or check.stderr, file=sys.stderr)
        raise SystemExit(fail("计划已创建但 check_plan 不通过；修正上面的 error 后重试", check.returncode))
    return plan_path, True


def cmd_start(root: Path, args: argparse.Namespace) -> int:
    try:
        config = load_config(root)
    except SystemExit as exc:
        return int(exc.code or 1)
    goal = args.goal or "待补：一句话目标（编辑本计划后开工）"
    acceptance = args.acceptance or ["待补验收判据：命令 + 期望结果（编辑本计划后生效）"]
    plan_path, created = create_plan(
        root, config, topic=args.topic, goal=goal, level=args.level,
        scope=list(args.scope or []), acceptance=acceptance,
    )
    rel = plan_path.relative_to(root).as_posix()
    if not created:
        print(f"[SKIP] 计划已存在：{rel}（幂等；继续用现有计划）")
        return 0
    print(f"[OK] 已创建 {rel}（status=active）")
    print("下一步：编辑「目标与非目标」「验收」补全判据，然后 `python3 tools/harness.py verify`。")
    return 0


def cmd_intake(root: Path, args: argparse.Namespace) -> int:
    try:
        config = load_config(root)
    except SystemExit as exc:
        return int(exc.code or 1)
    card = Path(args.file).expanduser()
    if not card.is_absolute():
        card = root / card
    goal, acceptance, problems = parse_requirement_card(card)
    if problems:
        print("需求卡验收判据不可执行：", file=sys.stderr)
        for item in problems:
            print(f"  - {item}", file=sys.stderr)
        return 2
    if args.dry_run:
        print(f"目标：{goal}")
        for item in acceptance:
            print(f"验收：{item}")
        print("dry-run：未创建计划")
        return 0
    topic = args.topic or card.stem
    plan_path, _ = create_plan(
        root, config, topic=topic, goal=goal, level=args.level,
        scope=list(args.scope or []), acceptance=acceptance,
    )
    print(f"[OK] 需求卡 → {plan_path.relative_to(root).as_posix()}（验收判据 {len(acceptance)} 条已机检）")
    print("下一步：核对 scope.allow 与验收，然后开工；完成前 `python3 tools/harness.py verify`。")
    return 0


# ── 子命令：verify ───────────────────────────────────────────────────────
def run_gate(root: Path, command: str) -> int:
    print(f"== gate: {command} ==")
    proc = subprocess.run(command, shell=True, cwd=str(root))
    print(f"== gate exit: {proc.returncode} ==")
    return proc.returncode


def cmd_verify(root: Path, args: argparse.Namespace) -> int:
    try:
        config = load_config(root)
    except SystemExit as exc:
        return int(exc.code or 1)
    plans = load_plans(root, config)
    plan = active_plan(plans)
    if plan is not None and not args.no_sync:
        synced = sync_uncommitted(plan, root)
        if synced is None:
            print("[WARN] git 不可用，跳过未提交段同步")
        else:
            print(f"[OK] 已同步「未提交改动」：{len(synced)} 个 scope 内文件")
    gate = str(config.get("commands", {}).get("verify") or "")
    if not gate:
        return fail("config.commands.verify 未配置", 2)
    gate_code = run_gate(root, gate)
    plan_code = 0
    if plans:
        print("== plan check (strict) ==")
        proc = subprocess.run(
            [sys.executable, "tools/check_plan.py", "check", "--strict"], cwd=str(root)
        )
        plan_code = proc.returncode
    claims_code = 0
    if (root / "tools" / "verify_claim.py").is_file():
        print("== claims (three-valued) ==")
        proc = subprocess.run(
            [sys.executable, "tools/verify_claim.py", "--all"], cwd=str(root),
            capture_output=True, text=True,
        )
        print(proc.stdout.rstrip())
        claims_code = proc.returncode
        if claims_code != 0 and not args.claims_strict:
            print("[INFO] claims 非全 PASS（exit %d）；默认不计入 verify 结果，加 --claims-strict 可阻断" % claims_code)
    overall = 0
    if gate_code != 0:
        overall = gate_code
    elif plan_code != 0:
        overall = 1
    elif args.claims_strict and claims_code != 0:
        overall = claims_code
    print(f"== verify: {'PASS' if overall == 0 else 'FAIL'} ==")
    return overall


# ── 子命令：handoff ──────────────────────────────────────────────────────
def cmd_handoff(root: Path, args: argparse.Namespace) -> int:
    try:
        config = load_config(root)
    except SystemExit as exc:
        return int(exc.code or 1)
    plans = load_plans(root, config)
    plan = active_plan(plans)
    archived = load_archived_plans(root, config)
    last_plan = archived[0] if archived else None
    if plan is not None:
        sync_uncommitted(plan, root)
    brief = subprocess.run(
        [sys.executable, "tools/check_plan.py", "brief"], cwd=str(root),
        capture_output=True, text=True,
    )
    evidence = evidence_summary(root, config)
    result = {
        "project": project_name(config),
        "kitVersion": config.get("kitVersion"),
        "plan": None if plan is None else {
            "id": plan.meta.get("id"), "status": plan.status, "level": plan.meta.get("level"),
            "owner": plan.meta.get("owner"), "updated": plan.meta.get("updated"),
            "path": plan.rel, "goal": plan.goal_text(), "next": plan.section("下一步"),
            "unverified": plan_unverified(plan),
        },
        "lastPlan": None if last_plan is None else plan_summary(last_plan, root),
        "archivedPlans": len(archived),
        "evidence": evidence,
        "plans": len(plans),
        "briefExit": brief.returncode,
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if plan is None:
        if last_plan is None:
            print("没有 active 计划：无交接状态可固化。先 `python3 tools/harness.py start --topic <topic>`。")
            return 0
        summary = plan_summary(last_plan, root)
        counts = evidence["counts"]
        print("# handoff（无 active 计划；回读最近归档计划·历史快照）")
        print(f"上一计划: {summary['id']} status={summary['status']} updated={summary['updated']} path={summary['path']}")
        newer = [
            item for item in evidence.get("entries", [])
            if item["verdict"] == "PASS" and str(item["createdAt"])[:10] > str(summary["updated"] or "")
        ]
        if newer:
            print(f"归档后新增 PASS 证据: {'、'.join(item['id'] for item in newer[:5])}")
        print(f"目标: {summary['goal'] or '（未填写）'}")
        print(f"未验证项: {summary['unverified'] or '（无）'}")
        print(f"下一步: {summary['next'] or '（未填写）'}")
        archived_note = f"；归档 {evidence.get('archivedTotal', 0)} 条（不参与判定）" if evidence.get("archivedTotal") else ""
        print(f"证据: {evidence['total']} 条（PASS={counts['PASS']} / UNVERIFIED={counts['UNVERIFIED']} / FAIL={counts['FAIL']}{archived_note}）")
        print("提示：归档计划不是当前计划；核对未验证项后新建计划再继续。")
        return 0
    print(f"# handoff · {plan.meta.get('id')}")
    print(f"status={plan.status} level={plan.meta.get('level')} owner={plan.meta.get('owner')} updated={plan.meta.get('updated')}")
    print(f"目标: {plan.goal_text().splitlines()[0] if plan.goal_text() else '（未填写）'}")
    unverified = plan_unverified(plan)
    print(f"未验证项: {unverified or '（无）'}")
    counts = evidence["counts"]
    print(f"证据: {evidence['total']} 条（PASS={counts['PASS']} / UNVERIFIED={counts['UNVERIFIED']} / FAIL={counts['FAIL']}）")
    print(f"下一步: {plan.section('下一步') or '（未填写）'}")
    if brief.returncode != 0:
        print("[WARN] check_plan brief 非 0（先修计划再交接）")
        return 1
    return 0


# ── 子命令：release ──────────────────────────────────────────────────────
def cmd_release(root: Path, args: argparse.Namespace) -> int:
    try:
        config = load_config(root)
    except SystemExit as exc:
        return int(exc.code or 1)
    claims = root / "tools" / "verify_claim.py"
    if not claims.is_file():
        return fail("当前 profile 没有 verify_claim（minimal）；release 需要 standard/strict", 2)
    plans = load_plans(root, config)
    plan = active_plan(plans)
    if plan is not None:
        sync_uncommitted(plan, root)
    gate = str(config.get("commands", {}).get("verify") or "")
    if not gate:
        return fail("config.commands.verify 未配置", 2)
    gate_code = run_gate(root, gate)
    cmd = [sys.executable, "tools/verify_claim.py", "--all", "--fresh"]
    if args.strict:
        cmd.append("--strict")
    print("== claims (fresh%s) ==" % (" + strict" if args.strict else ""))
    claim_proc = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True)
    print(claim_proc.stdout.rstrip())
    claim_code = claim_proc.returncode
    if gate_code != 0:
        overall = gate_code
    else:
        overall = claim_code
    print(f"== release: {'PASS' if overall == 0 else 'FAIL'} ==")
    if overall != 0:
        print("[HINT] 3 值语义：FAIL=1 / UNVERIFIED=2；UNVERIFIED 不是通过，需补可复核证据")
    return overall


# ── 子命令：plan / upgrade ───────────────────────────────────────────────
def cmd_plan(root: Path, args: argparse.Namespace) -> int:
    if args.action != "check":
        return fail("用法：harness.py plan check [--strict]", 2)
    cmd = [sys.executable, "tools/check_plan.py", "check"]
    if not args.strict:
        cmd.append("--lenient-uncommitted")
    return subprocess.run(cmd, cwd=str(root)).returncode


def cmd_upgrade(root: Path, args: argparse.Namespace) -> int:
    if args.apply:
        return fail("--apply 在 v0.3.0-alpha 未实现（kit 侧 harness-upgrade 只读）；按 --plan 输出人工应用", 2)
    manifest = read_manifest(root)
    print("升级由 kit 侧只读脚本执行（需要 kit 路径）：")
    print("  <kit>/scripts/harness-upgrade --target . --check")
    print("  <kit>/scripts/harness-upgrade --target . --plan")
    print(f"当前 manifest: {manifest.get('kitVersion') if manifest else '无（v0.2.13 之前接入，走 playbook 手工路径）'}")
    return 0


# ── CLI ──────────────────────────────────────────────────────────────────
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="harness: one-screen state + plan/verify/handoff entry.")
    parser.add_argument("--root", default=None, help="project root (default: script parent parent)")
    sub = parser.add_subparsers(dest="command", required=True)

    status = sub.add_parser("status", help="一屏状态（只读）")
    status.add_argument("--json", action="store_true")

    start = sub.add_parser("start", help="幂等创建 active 计划")
    start.add_argument("--topic", required=True)
    start.add_argument("--goal")
    start.add_argument("--scope", action="append", default=[])
    start.add_argument("--acceptance", action="append", default=[])
    start.add_argument("--level", default="L1", choices=("L1", "L2"))

    verify = sub.add_parser("verify", help="同步未提交段 + 静态门禁 + 计划严格校验")
    verify.add_argument("--no-sync", action="store_true")
    verify.add_argument("--claims-strict", action="store_true")

    intake = sub.add_parser("intake", help="需求卡 → 计划（校验验收判据）")
    intake.add_argument("--file", required=True)
    intake.add_argument("--topic")
    intake.add_argument("--scope", action="append", default=[])
    intake.add_argument("--level", default="L1", choices=("L1", "L2"))
    intake.add_argument("--dry-run", action="store_true")

    release = sub.add_parser("release", help="发布前检查（fresh 证据 + 严格计划）")
    release.add_argument("--check", action="store_true")
    release.add_argument("--strict", action="store_true")

    handoff = sub.add_parser("handoff", help="交接摘要（会同步未提交段）")
    handoff.add_argument("--json", action="store_true")

    plan = sub.add_parser("plan", help="计划机检")
    plan.add_argument("action", choices=("check",))
    plan.add_argument("--strict", action="store_true", help="未提交段也必须与 git 一致")

    upgrade = sub.add_parser("upgrade", help="说明 kit 侧升级命令")
    upgrade.add_argument("--apply", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root).expanduser().resolve() if args.root else root_from_script()
    handlers = {
        "status": cmd_status,
        "start": cmd_start,
        "intake": cmd_intake,
        "release": cmd_release,
        "verify": cmd_verify,
        "handoff": cmd_handoff,
        "plan": cmd_plan,
        "upgrade": cmd_upgrade,
    }
    return handlers[args.command](root, args)


if __name__ == "__main__":
    sys.exit(main())
