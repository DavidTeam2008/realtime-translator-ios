"""Machine-checkable Superpowers discipline receipts.

A receipt is process evidence.  It never contains task checkboxes and never
changes ``complete/total``.  The gate checks the consistency between the
declared discipline version, red/green command logs and referenced delivery
evidence.  It cannot prove that an agent read the upstream skill text; that
tamper-resistant layer remains Git review / CI.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Iterable

from .delivery import DeliveryError

DisciplineError = DeliveryError

SCHEMA_VERSION = 1
RECEIPT_KIND = "superpowers-discipline-receipt"
DISCIPLINE_NAME = "superpowers"
DISCIPLINE_VERSION = "v7.0.2"
DISCIPLINE_COMMIT = "22f0b463e7a5e579904dd6211a520321035526f7"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
EXIT_CODE_RE = re.compile(r"^EXIT_CODE=(\d+)$", re.MULTILINE)
DEFAULT_DIR = "harness/evidence/discipline"


def _read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DeliveryError(f"discipline receipt 读取失败：{path} ({exc})") from exc
    if not isinstance(value, dict):
        raise DeliveryError("discipline receipt 顶层必须是 object")
    return value


def _require_object(value: object, label: str) -> dict:
    if not isinstance(value, dict):
        raise DeliveryError(f"{label} 必须是 object")
    return value


def _require_str(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DeliveryError(f"{label} 必须是非空字符串")
    return value.strip()


def _require_int(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise DeliveryError(f"{label} 必须是整数")
    return value


def _require_commit(value: object, label: str) -> str:
    commit = _require_str(value, label).lower()
    if not COMMIT_RE.fullmatch(commit):
        raise DeliveryError(f"{label} 必须是 40 位小写 commit hash")
    return commit


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(root: Path, *args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", *args], cwd=root, capture_output=True, text=True, timeout=60
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise DeliveryError(f"git discipline 校验失败：{exc}") from exc
    if completed.returncode != 0:
        raise DeliveryError(
            f"git {' '.join(args)} 失败（exit {completed.returncode}）："
            f"{completed.stderr.strip()[:300]}"
        )
    return completed.stdout


def _safe_repo_path(root: Path, relative: str, label: str) -> Path:
    path = (root / relative).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise DeliveryError(f"{label} 路径越界：{relative}") from exc
    if not path.is_file():
        raise DeliveryError(f"{label} 不存在：{relative}")
    return path


def _require_tracked(root: Path, relative: str) -> None:
    try:
        _git(root, "ls-files", "--error-unmatch", "--", relative)
    except DeliveryError as exc:
        raise DeliveryError(f"discipline artifact 未被 git 跟踪：{relative}") from exc


def _require_ancestor(root: Path, commit: str, head: str, label: str) -> None:
    try:
        _git(root, "merge-base", "--is-ancestor", commit, head)
    except DeliveryError as exc:
        raise DeliveryError(f"{label} commit 不是 head 祖先：{commit}") from exc


def verify_receipt(
    root: Path,
    receipt_path: Path,
    *,
    expected_change: str,
    expected_task: int,
    expected_base: str,
    expected_head: str,
    evidence_ids: Iterable[str],
) -> None:
    root = root.resolve()
    receipt_path = receipt_path.resolve()
    try:
        receipt_path.relative_to(root)
    except ValueError as exc:
        raise DeliveryError(f"discipline receipt 路径越界：{receipt_path}") from exc
    receipt = _read_json(receipt_path)

    if receipt.get("schemaVersion") != SCHEMA_VERSION:
        raise DeliveryError(f"discipline schemaVersion 必须是 {SCHEMA_VERSION}")
    if receipt.get("kind") != RECEIPT_KIND:
        raise DeliveryError("discipline receipt kind 非法")
    if receipt.get("change") != expected_change:
        raise DeliveryError(f"discipline receipt change 不一致：{receipt.get('change')!r}")
    task = _require_int(receipt.get("task"), "discipline task")
    if task != expected_task:
        raise DeliveryError(f"discipline receipt task 不一致：{task} != {expected_task}")
    base = _require_str(receipt.get("base"), "discipline base")
    if base != expected_base:
        raise DeliveryError(f"discipline receipt base 不一致：{base} != {expected_base}")
    head = _require_str(receipt.get("head"), "discipline head")
    if head != expected_head:
        raise DeliveryError(f"discipline receipt head 不一致：{head} != {expected_head}")

    discipline = _require_object(receipt.get("discipline"), "discipline")
    if discipline.get("name") != DISCIPLINE_NAME:
        raise DeliveryError(f"discipline name 必须是 {DISCIPLINE_NAME}")
    if discipline.get("version") != DISCIPLINE_VERSION:
        raise DeliveryError(f"discipline version 必须是 {DISCIPLINE_VERSION}")
    discipline_commit = _require_commit(discipline.get("commit"), "discipline commit")
    if discipline_commit != DISCIPLINE_COMMIT:
        raise DeliveryError("discipline commit 与工具链固定常量不一致")

    tdd = _require_object(receipt.get("tdd"), "discipline tdd")
    stages: dict[str, tuple[int, bool]] = {"red": (1, False), "green": (0, True)}
    artifact_hashes: dict[str, str] = {}
    for name, (expected_exit, require_zero) in stages.items():
        stage = _require_object(tdd.get(name), f"discipline tdd.{name}")
        stage_commit = _require_commit(stage.get("commit"), f"tdd.{name}.commit")
        _require_ancestor(root, stage_commit, head, f"tdd.{name}")
        command = _require_str(stage.get("command"), f"tdd.{name}.command")
        exit_code = _require_int(stage.get("exitCode"), f"tdd.{name}.exitCode")
        if require_zero and exit_code != 0:
            raise DeliveryError(f"tdd.{name}.exitCode 必须为 0，实际 {exit_code}")
        if not require_zero and exit_code <= 0:
            raise DeliveryError(f"tdd.{name}.exitCode 必须非零，实际 {exit_code}")
        relative = _require_str(stage.get("artifact"), f"tdd.{name}.artifact")
        path = _safe_repo_path(root, relative, f"tdd.{name}.artifact")
        _require_tracked(root, relative)
        expected_sha = _require_str(stage.get("sha256"), f"tdd.{name}.sha256").lower()
        if not SHA256_RE.fullmatch(expected_sha):
            raise DeliveryError(f"tdd.{name}.sha256 必须是 64 位小写 hex")
        actual_sha = _sha256(path)
        if actual_sha != expected_sha:
            raise DeliveryError(f"tdd.{name}.artifact 哈希不一致：{relative}")
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise DeliveryError(f"tdd.{name}.artifact 无法读取：{relative} ({exc})") from exc
        bindings = [int(value) for value in EXIT_CODE_RE.findall(text)]
        if bindings != [exit_code]:
            raise DeliveryError(
                f"tdd.{name}.artifact 缺少一致的 EXIT_CODE 绑定：期望 [{exit_code}]，实际 {bindings}"
            )
        if command not in text:
            raise DeliveryError(f"tdd.{name}.artifact 未绑定 command：{relative}")
        artifact_hashes[name] = expected_sha

    debugging = _require_object(receipt.get("debugging"), "discipline debugging")
    _require_str(debugging.get("rootCause"), "debugging.rootCause")

    verification = _require_object(receipt.get("verification"), "discipline verification")
    ids = verification.get("evidenceIds")
    if not isinstance(ids, list) or not ids or not all(isinstance(item, str) and item for item in ids):
        raise DeliveryError("verification.evidenceIds 必须是非空字符串数组")
    allowed = set(evidence_ids)
    if len(ids) != len(set(ids)) or not set(ids).issubset(allowed):
        raise DeliveryError(
            f"verification.evidenceIds 必须属于当前 PASS evidence 集合：{ids!r}"
        )


def verify_discipline_receipts(
    root: Path,
    *,
    task_ids: Iterable[int],
    change: str,
    base: str,
    head: str,
    evidence_ids: Iterable[str],
    discipline: dict | None,
) -> list[Path]:
    if not isinstance(discipline, dict) or discipline.get("required") is not True:
        return []
    directory = discipline.get("dir", DEFAULT_DIR)
    if not isinstance(directory, str) or not directory.strip():
        raise DeliveryError("discipline.dir 必须是非空字符串")
    base_dir = (root / directory).resolve() / change
    try:
        base_dir.relative_to(root.resolve())
    except ValueError as exc:
        raise DeliveryError(f"discipline 目录越界：{directory}") from exc
    if not base_dir.is_dir():
        raise DeliveryError(f"discipline receipt 目录不存在：{base_dir.relative_to(root)}")

    ids = list(task_ids)
    if not ids:
        raise DeliveryError("discipline gate 不能用于 0 任务")
    receipts: list[Path] = []
    red_hashes: set[str] = set()
    green_hashes: set[str] = set()
    stage_commits: set[tuple[str, str]] = set()
    expected_files = {f"task-{task}.json" for task in ids}
    actual_files = {path.name for path in base_dir.glob("task-*.json") if path.is_file()}
    unexpected = sorted(actual_files - expected_files)
    if unexpected:
        raise DeliveryError(f"discipline receipt 与 task 不一致：{', '.join(unexpected)}")

    for task in ids:
        receipt_path = base_dir / f"task-{task}.json"
        if not receipt_path.is_file():
            raise DeliveryError(f"缺少 discipline receipt：task {task}")
        verify_receipt(
            root,
            receipt_path,
            expected_change=change,
            expected_task=task,
            expected_base=base,
            expected_head=head,
            evidence_ids=evidence_ids,
        )
        receipt = _read_json(receipt_path)
        tdd = _require_object(receipt.get("tdd"), "discipline tdd")
        red = _require_object(tdd.get("red"), "discipline tdd.red")
        green = _require_object(tdd.get("green"), "discipline tdd.green")
        red_sha = _require_str(red.get("sha256"), "tdd.red.sha256")
        green_sha = _require_str(green.get("sha256"), "tdd.green.sha256")
        red_commit = _require_commit(red.get("commit"), "tdd.red.commit")
        green_commit = _require_commit(green.get("commit"), "tdd.green.commit")
        if red_sha in red_hashes or green_sha in green_hashes:
            raise DeliveryError(f"discipline artifact 在多个 task 中复用：task {task}")
        pair = (red_commit, green_commit)
        if pair in stage_commits:
            raise DeliveryError(f"discipline red/green commit 组合复用：task {task}")
        red_hashes.add(red_sha)
        green_hashes.add(green_sha)
        stage_commits.add(pair)
        receipts.append(receipt_path)
    return receipts
