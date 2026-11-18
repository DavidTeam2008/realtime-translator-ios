"""Delivery gate primitives for OpenSpec tasks, scope, evidence and review.

This module intentionally avoids host imports.  The host supplies a small JSON
profile and invokes this module after running its pinned OpenSpec wrapper.
"""
from __future__ import annotations

import fnmatch
import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


class DeliveryError(ValueError):
    """The delivery contract, task state, scope, evidence or review is invalid."""


CONTRACT_KEYS = (
    "Change",
    "Level",
    "Owner",
    "Base",
    "Scope allow",
    "Scope deny",
    "Acceptance",
    "Verify",
    "Evidence",
    "Review",
    "Archive gate",
    "CI",
)
TASK_HEADING = re.compile(r"^### Task (\d+):\s*(.+?)\s*$")
CHECKBOX = re.compile(r"^\s*-\s*\[[ xX]\]\s*(.*)$")
CLAIM = re.compile(r"^([a-z0-9][a-z0-9-]*)\b")


@dataclass(frozen=True)
class EvidenceSpec:
    name: str
    required: bool
    detail: str


@dataclass(frozen=True)
class ReviewSpec:
    required: bool
    path: str
    p0_closed: bool
    p1_closed: bool


@dataclass(frozen=True)
class Contract:
    change: str
    level: str
    owner: str
    base: str
    scope_allow: tuple[str, ...]
    scope_deny: tuple[str, ...]
    acceptance: dict[str, tuple[str, str]]
    verify: tuple[str, ...]
    evidence: dict[str, EvidenceSpec]
    review: ReviewSpec
    archive_gate: str
    ci_required: bool


@dataclass(frozen=True)
class Tasks:
    total: int
    complete: int
    task_ids: tuple[int, ...]

    @property
    def all_done(self) -> bool:
        return self.total > 0 and self.complete == self.total


def _split_items(value: str, separator: str = r"[,;]") -> tuple[str, ...]:
    return tuple(item.strip() for item in re.split(separator, value) if item.strip())


def _parse_review(value: str) -> ReviewSpec:
    required = value.strip().lower().startswith("required")
    match = re.search(r"path=([^\s,;]+)", value)
    path = match.group(1).strip() if match else ""
    p0 = bool(re.search(r"P0\s*(?:/|、|和)?\s*closed|P0\s*已关闭", value, re.I))
    p1 = bool(re.search(r"P1\s*(?:/|、|和)?\s*closed|P1\s*已关闭", value, re.I))
    if not p0 and re.search(r"P0\s*(?:/|、|和)?\s*P1\s*closed", value, re.I):
        p0 = p1 = True
    if required and not path:
        raise DeliveryError("Review 字段缺少 path=")
    return ReviewSpec(required=required, path=path, p0_closed=p0, p1_closed=p1)


def parse_contract(text: str) -> Contract:
    lines = text.splitlines()
    try:
        start = next(i for i, line in enumerate(lines) if line.strip() == "# Delivery Contract")
        end = next(i for i, line in enumerate(lines[start + 1 :], start + 1) if line.strip() == "## Tasks")
    except StopIteration as exc:
        raise DeliveryError("tasks.md 必须包含 '# Delivery Contract' 与 '## Tasks'") from exc

    values: dict[str, str] = {}
    for line in lines[start + 1 : end]:
        stripped = line.strip()
        if not stripped.startswith("- "):
            continue
        key_value = stripped[2:].split(":", 1)
        if len(key_value) != 2:
            continue
        key, value = key_value[0].strip(), key_value[1].strip()
        if key in CONTRACT_KEYS:
            if key in values:
                raise DeliveryError(f"Delivery Contract 重复字段：{key}")
            values[key] = value
    missing = [key for key in CONTRACT_KEYS if key not in values]
    if missing:
        raise DeliveryError(f"Delivery Contract 缺字段：{', '.join(missing)}")

    scope_allow = _split_items(values["Scope allow"])
    scope_deny = _split_items(values["Scope deny"])
    if not scope_allow:
        raise DeliveryError("Scope allow 不能为空")

    acceptance: dict[str, tuple[str, str]] = {}
    for item in _split_items(values["Acceptance"], r";"):
        match = re.match(r"^(A\d+)\s*=\s*(.*?)\s*(?:\(([^()]*)\))?$", item)
        if not match:
            raise DeliveryError(f"Acceptance 条目格式非法：{item!r}")
        acceptance[match.group(1)] = (match.group(2).strip(), (match.group(3) or "").strip())
    if not acceptance:
        raise DeliveryError("Acceptance 不能为空")

    evidence: dict[str, EvidenceSpec] = {}
    for item in _split_items(values["Evidence"], r";"):
        match = CLAIM.match(item)
        if not match:
            raise DeliveryError(f"Evidence 条目缺少 claim：{item!r}")
        name = match.group(1)
        if name in evidence:
            raise DeliveryError(f"Evidence 重复 claim：{name}")
        evidence[name] = EvidenceSpec(
            name=name,
            required="required" in item.lower(),
            detail=item,
        )
    if not evidence:
        raise DeliveryError("Evidence 不能为空")

    ci = values["CI"].strip().lower()
    ci_required = not (ci.startswith("not applicable") or ci.startswith("不适用") or ci.startswith("n/a"))

    verify = tuple(item for item in _split_items(values["Verify"], r";"))
    if not verify:
        raise DeliveryError("Verify 不能为空")
    if not values["Base"].strip():
        raise DeliveryError("Base 不能为空")
    return Contract(
        change=values["Change"],
        level=values["Level"],
        owner=values["Owner"],
        base=values["Base"],
        scope_allow=scope_allow,
        scope_deny=scope_deny,
        acceptance=acceptance,
        verify=verify,
        evidence=evidence,
        review=_parse_review(values["Review"]),
        archive_gate=values["Archive gate"],
        ci_required=ci_required,
    )


def parse_tasks(text: str) -> Tasks:
    lines = text.splitlines()
    try:
        start = next(i for i, line in enumerate(lines) if line.strip() == "## Tasks")
    except StopIteration as exc:
        raise DeliveryError("tasks.md 缺少 '## Tasks'") from exc

    heading_indices = [i for i, line in enumerate(lines[start + 1 :], start + 1) if TASK_HEADING.match(line)]
    if not heading_indices:
        raise DeliveryError("tasks.md 没有 '### Task N:'，0 任务不能作为交付")
    task_ids: list[int] = []
    complete = 0
    for position, index in enumerate(heading_indices):
        match = TASK_HEADING.match(lines[index])
        assert match is not None
        task_id = int(match.group(1))
        task_ids.append(task_id)
        block_end = heading_indices[position + 1] if position + 1 < len(heading_indices) else len(lines)
        block = lines[index + 1 : block_end]
        boxes = [line for line in block if CHECKBOX.match(line)]
        if len(boxes) != 1:
            raise DeliveryError(f"Task {task_id} 必须恰好有一个任务级复选框，实际 {len(boxes)}")
        box = boxes[0]
        if not box.split("]", 1)[1].strip().startswith(f"Task {task_id}:"):
            raise DeliveryError(f"Task {task_id} 的复选框必须引用同一 Task")
        if box.lstrip().lower().startswith("- [x]"):
            complete += 1
        if not any("**Files:**" in line for line in block):
            raise DeliveryError(f"Task {task_id} 缺少 Files")
        if not any("Expected" in line for line in block):
            raise DeliveryError(f"Task {task_id} 缺少 Expected")
    if task_ids != list(range(1, len(task_ids) + 1)):
        raise DeliveryError(f"Task ID 必须从 1 连续：{task_ids}")
    for line in lines[:start]:
        if CHECKBOX.match(line):
            raise DeliveryError("Delivery Contract 中不允许复选框")
    return Tasks(total=len(task_ids), complete=complete, task_ids=tuple(task_ids))


def validate_apply(document: dict, tasks: Tasks) -> None:
    if not isinstance(document, dict):
        raise DeliveryError("instructions apply 必须是 JSON object")
    state = document.get("state")
    progress = document.get("progress")
    if not isinstance(progress, dict):
        raise DeliveryError("instructions apply 缺少 progress")
    total = progress.get("total")
    complete = progress.get("complete")
    remaining = progress.get("remaining")
    if not all(isinstance(value, int) and not isinstance(value, bool) for value in (total, complete, remaining)):
        raise DeliveryError("instructions apply progress 必须是整数")
    if state != "all_done":
        raise DeliveryError(f"instructions apply state 必须是 all_done，实际 {state!r}")
    if total <= 0 or total != tasks.total:
        raise DeliveryError(f"OpenSpec total={total} 与任务标题数 {tasks.total} 不一致")
    if complete != tasks.complete or remaining != 0 or complete != total:
        raise DeliveryError("OpenSpec 任务未全部完成，不能交付或归档")


def _git(root: Path, *args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", *args], cwd=root, capture_output=True, text=True, timeout=60
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise DeliveryError(f"git 执行失败：{exc}") from exc
    if completed.returncode != 0:
        raise DeliveryError(f"git {' '.join(args)} 失败：{completed.stderr.strip()[:200]}")
    return completed.stdout


def _matches(path: str, pattern: str) -> bool:
    pattern = pattern.strip()
    if not pattern:
        return False
    if pattern.endswith("/"):
        return path.startswith(pattern)
    return path == pattern or fnmatch.fnmatchcase(path, pattern)


def _changed_paths(root: Path, base: str) -> list[str]:
    committed = [item for item in _git(root, "diff", "--name-only", f"{base}..HEAD").splitlines() if item]
    status = _git(root, "status", "--porcelain")
    paths = set(committed)
    for line in status.splitlines():
        if not line.strip():
            continue
        path = line[3:]
        if " -> " in path:
            old, new = path.split(" -> ", 1)
            paths.add(old)
            paths.add(new)
        else:
            paths.add(path)
    return sorted(paths)


def check_scope(
    root: Path,
    base: str,
    allow: Iterable[str],
    deny: Iterable[str],
    *,
    changed: Iterable[str] | None = None,
) -> None:
    root = root.resolve()
    if not _git(root, "rev-parse", "--is-inside-work-tree").strip() == "true":
        raise DeliveryError("scope 检查需要 git 工作树")
    try:
        _git(root, "merge-base", "--is-ancestor", base, "HEAD")
    except DeliveryError as exc:
        raise DeliveryError(f"Base 不是 HEAD 祖先：{base}") from exc
    paths = list(changed) if changed is not None else _changed_paths(root, base)
    allow = tuple(allow)
    deny = tuple(deny)
    denied = [path for path in paths if any(_matches(path, pattern) for pattern in deny)]
    if denied:
        raise DeliveryError(f"scope deny 命中：{', '.join(denied)}")
    outside = [path for path in paths if not any(_matches(path, pattern) for pattern in allow)]
    if outside:
        raise DeliveryError(f"scope allow 未覆盖：{', '.join(outside)}")


def _read_front_matter(path: Path) -> dict[str, str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise DeliveryError(f"review 读取失败：{path} ({exc})") from exc
    if not lines or lines[0].strip() != "---":
        raise DeliveryError(f"review 缺少 front matter：{path}")
    values: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return values
        if ":" in line:
            key, value = line.split(":", 1)
            values[key.strip()] = value.strip()
    raise DeliveryError(f"review front matter 未闭合：{path}")


def check_review(root: Path, review_path: str, base: str, head: str, *, required: bool) -> None:
    if not required:
        return
    path = (root / review_path).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise DeliveryError("review 路径必须位于仓库内") from exc
    if not path.is_file():
        raise DeliveryError(f"review 不存在：{review_path}")
    values = _read_front_matter(path)
    for key in ("base", "head", "reviewer", "p0", "p1", "p2", "verdict"):
        if not values.get(key):
            raise DeliveryError(f"review 缺字段：{key}")
    if values["base"] != base:
        raise DeliveryError(f"review.base 不一致：{values['base']} != {base}")
    if values["head"] != head:
        raise DeliveryError(f"review.head 不一致：{values['head']} != {head}")
    if values["p0"].lower() != "closed" or values["p1"].lower() != "closed":
        raise DeliveryError("review P0/P1 未关闭")
    if values["verdict"].lower() != "pass":
        raise DeliveryError("review verdict 不是 pass")


def check_ci(
    ci: dict,
    head: str,
    *,
    required: bool,
    required_jobs: Iterable[str] = (),
) -> None:
    if not isinstance(ci, dict):
        raise DeliveryError("CI profile 必须是 object")
    if not required:
        if not ci.get("reason"):
            raise DeliveryError("CI 不适用必须提供结构化 reason")
        return
    if ci.get("required") is not True:
        raise DeliveryError("CI required 与 profile 不一致")
    if ci.get("headSha") != head:
        raise DeliveryError("CI headSha 与 HEAD 不一致")
    if ci.get("conclusion") != "success":
        raise DeliveryError("CI conclusion 不是 success")
    jobs = ci.get("jobs")
    if not isinstance(jobs, list) or not jobs:
        raise DeliveryError("CI jobs 缺失")
    by_name = {job.get("name"): job.get("conclusion") for job in jobs if isinstance(job, dict)}
    for name in required_jobs:
        if by_name.get(name) != "success":
            raise DeliveryError(f"CI 必需 job 未成功：{name}")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_json(path: Path, label: str) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DeliveryError(f"{label} 读取失败：{path} ({exc})") from exc
    if not isinstance(value, dict):
        raise DeliveryError(f"{label} 顶层必须是 object")
    return value


def _head(root: Path) -> str:
    return _git(root, "rev-parse", "HEAD").strip()


def _is_ancestor(root: Path, commit: str, head: str) -> bool:
    try:
        _git(root, "merge-base", "--is-ancestor", commit, head)
        return True
    except DeliveryError:
        return False


def _changed_since(root: Path, commit: str, head: str) -> list[str]:
    paths = {item for item in _git(root, "diff", "--name-only", f"{commit}..{head}").splitlines() if item}
    status = _git(root, "status", "--porcelain")
    for line in status.splitlines():
        if not line.strip():
            continue
        path = line[3:]
        if " -> " in path:
            old, new = path.split(" -> ", 1)
            paths.add(old)
            paths.add(new)
        else:
            paths.add(path)
    return sorted(paths)


def _require_tracked(root: Path, relative: str) -> None:
    if not _git(root, "ls-files", "--error-unmatch", "--", relative).strip():
        raise DeliveryError(f"artifact 未被 git 跟踪：{relative}")


def check_evidence(root: Path, contract: Contract, profile: dict, head: str | None = None) -> list[str]:
    """Validate required Harness claims from current evidence files.

    Profile shape:
      {"evidenceDir": "harness/evidence",
       "claims": {"unit-tests-pass": {"target": {...}, "passedFloor": 1,
                  "expectedSkipped": 0, "freshness": ["tools/**"]}}}
    """
    root = root.resolve()
    head = head or _head(root)
    claims_config = profile.get("claims")
    evidence_dir = profile.get("evidenceDir", "harness/evidence")
    if not isinstance(claims_config, dict):
        raise DeliveryError("profile.claims 必须是 object")
    evidence_root = (root / evidence_dir).resolve()
    try:
        evidence_root.relative_to(root)
    except ValueError as exc:
        raise DeliveryError("evidenceDir 必须位于仓库内") from exc
    if not evidence_root.is_dir():
        raise DeliveryError(f"evidenceDir 不存在：{evidence_dir}")

    from . import manifest as manifest_module
    from .junit_strict import count_file

    errors: list[str] = []
    passed: list[str] = []
    for claim, spec in contract.evidence.items():
        if not spec.required or claim == "review":
            continue
        cfg = claims_config.get(claim)
        if not isinstance(cfg, dict):
            errors.append(f"缺少 claim profile：{claim}")
            continue
        candidates: list[tuple[str, Path, dict]] = []
        for path in sorted(evidence_root.glob(f"*{claim}.json")):
            if path.parent.name == "_archive":
                continue
            try:
                doc = _read_json(path, "evidence")
            except DeliveryError as exc:
                errors.append(str(exc))
                continue
            if doc.get("claim") == claim and doc.get("verdict") == "PASS":
                candidates.append((path.stem, path, doc))
        if len(candidates) != 1:
            errors.append(f"claim {claim} 必须有且仅有一条当前 PASS 证据，实际 {len(candidates)}")
            continue
        evidence_id, evidence_path, doc = candidates[0]
        git = doc.get("git") if isinstance(doc.get("git"), dict) else {}
        commit = str(git.get("commit") or "").strip().lower()
        if not commit:
            errors.append(f"{evidence_id} 缺少 git.commit")
            continue
        if git.get("dirty") is not False:
            errors.append(f"{evidence_id} 不是 clean 证据")
            continue
        if not _is_ancestor(root, commit, head):
            errors.append(f"{evidence_id} 的 commit 不是 HEAD 祖先")
            continue
        freshness = cfg.get("freshness")
        if not isinstance(freshness, list) or not freshness:
            errors.append(f"{claim} 缺少 freshness 规则")
            continue
        stale = [path for path in _changed_since(root, commit, head) if any(_matches(path, pattern) for pattern in freshness)]
        if stale:
            errors.append(f"{evidence_id} 已 STALE：{', '.join(stale[:3])}")
            continue
        result = doc.get("result") if isinstance(doc.get("result"), dict) else {}
        artifacts = result.get("artifacts")
        junit_rel = result.get("junit")
        manifest_rel = result.get("manifest")
        if not isinstance(artifacts, list) or not isinstance(junit_rel, str) or not isinstance(manifest_rel, str):
            errors.append(f"{evidence_id} 缺少 JUnit/manifest artifacts")
            continue
        try:
            junit_path = (root / junit_rel).resolve()
            manifest_path = (root / manifest_rel).resolve()
            for path in (junit_path, manifest_path):
                path.relative_to(root)
        except (ValueError, OSError) as exc:
            errors.append(f"{evidence_id} artifact 路径越界：{exc}")
            continue
        if not junit_path.is_file() or not manifest_path.is_file():
            errors.append(f"{evidence_id} artifact 不存在")
            continue
        try:
            _require_tracked(root, junit_rel)
            _require_tracked(root, manifest_rel)
            counts = count_file(junit_path)
            if counts.passed < int(cfg.get("passedFloor", 0)):
                errors.append(f"{evidence_id} passed={counts.passed} 低于 floor")
                continue
            if counts.failed != 0:
                errors.append(f"{evidence_id} JUnit failed={counts.failed}")
                continue
            if counts.skipped != int(cfg.get("expectedSkipped", -1)):
                errors.append(f"{evidence_id} skipped={counts.skipped} 与 profile 不一致")
                continue
            if (result.get("passed"), result.get("failed"), result.get("skipped")) != (
                counts.passed,
                counts.failed,
                counts.skipped,
            ):
                errors.append(f"{evidence_id} 证据计数与 JUnit 不一致")
                continue
            target = cfg.get("target")
            if not isinstance(target, dict):
                errors.append(f"{claim} 缺少 target")
                continue
            manifest = manifest_module.load_manifest(manifest_path)
            manifest_module.verify_manifest(
                manifest,
                junit_path.read_bytes(),
                expected_claim=claim,
                expected_target=target,
                junit_name=junit_path.name,
            )
        except (DeliveryError, OSError, ValueError, manifest_module.ManifestError) as exc:
            errors.append(f"{evidence_id} 证据链失败：{exc}")
            continue
        passed.append(evidence_id)
    if errors:
        raise DeliveryError("；".join(errors))
    return passed


def check_delivery(
    root: Path,
    tasks_path: str,
    profile: dict,
    *,
    validate_doc: dict,
    apply_doc: dict,
    ci: dict | None = None,
    head: str | None = None,
) -> dict:
    root = root.resolve()
    head = head or _head(root)
    tasks_file = (root / tasks_path).resolve()
    try:
        tasks_file.relative_to(root)
    except ValueError as exc:
        raise DeliveryError("tasks 路径必须位于仓库内") from exc
    text = tasks_file.read_text(encoding="utf-8")
    contract = parse_contract(text)
    tasks = parse_tasks(text)
    validate_apply(apply_doc, tasks)
    if not isinstance(validate_doc, dict):
        raise DeliveryError("OpenSpec validate JSON 必须是 object")
    items = validate_doc.get("items")
    if not isinstance(items, list) or len(items) != 1 or items[0].get("valid") is not True:
        raise DeliveryError("OpenSpec validate 未返回 valid=true")
    if items[0].get("id") != contract.change:
        raise DeliveryError("OpenSpec validate change 不一致")
    check_scope(root, contract.base, contract.scope_allow, contract.scope_deny)
    evidence = check_evidence(root, contract, profile, head)
    if contract.review.required:
        check_review(root, contract.review.path, contract.base, head, required=True)
    if ci is None:
        ci = profile.get("ci")
    check_ci(ci, head, required=contract.ci_required, required_jobs=profile.get("requiredJobs", []))
    for acceptance, (_, evidence_name) in contract.acceptance.items():
        if evidence_name and evidence_name not in contract.evidence and evidence_name not in {"manual", "review"}:
            raise DeliveryError(f"Acceptance {acceptance} 映射了未知 evidence：{evidence_name}")
    return {
        "change": contract.change,
        "base": contract.base,
        "head": head,
        "tasks": {"total": tasks.total, "complete": tasks.complete},
        "evidence": evidence,
    }
