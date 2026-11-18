"""Superpowers skill manifest and invocation receipts."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

SCHEMA_VERSION = 1
MANIFEST_SCHEMA_VERSION = 1
RECEIPT_KIND = "skill-invoked"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class SkillError(RuntimeError):
    pass


def _read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SkillError(f"JSON 读取失败：{path} ({exc})") from exc
    if not isinstance(value, dict):
        raise SkillError(f"JSON 顶层必须是 object：{path}")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(root: Path, *args: str) -> str:
    completed = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, timeout=60)
    if completed.returncode != 0:
        raise SkillError(f"git {' '.join(args)} 失败：{completed.stderr.strip()[:300]}")
    return completed.stdout.strip()


def _tracked(root: Path, relative: str, label: str) -> None:
    try:
        _git(root, "ls-files", "--error-unmatch", "--", relative)
    except SkillError as exc:
        raise SkillError(f"{label} 未被 git 跟踪：{relative}") from exc


def _require_str(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SkillError(f"{label} 必须是非空字符串")
    return value.strip()


def load_manifest(path: Path) -> dict:
    manifest = _read_json(path)
    if manifest.get("schemaVersion") != MANIFEST_SCHEMA_VERSION:
        raise SkillError(f"manifest schemaVersion 必须是 {MANIFEST_SCHEMA_VERSION}")
    sources = manifest.get("sources")
    if not isinstance(sources, dict) or not sources:
        raise SkillError("manifest.sources 必须是非空 object")
    for name, source in sources.items():
        if not isinstance(source, dict):
            raise SkillError(f"manifest.sources[{name}] 必须是 object")
        for key in ("version", "commit", "files"):
            if key not in source:
                raise SkillError(f"manifest.sources[{name}] 缺 {key}")
        files = source.get("files")
        if not isinstance(files, dict) or not files:
            raise SkillError(f"manifest.sources[{name}].files 必须是非空 object")
        for relative, digest in files.items():
            if not isinstance(relative, str) or not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
                raise SkillError(f"manifest.sources[{name}].files 条目非法：{relative!r}")
    return manifest


def verify_skill_receipt(
    root: Path,
    receipt_path: Path,
    manifest: dict,
    *,
    expected_change: str,
    expected_task: int,
    roots: dict[str, Path],
) -> None:
    root = root.resolve()
    receipt_path = receipt_path.resolve()
    try:
        receipt_path.relative_to(root)
    except ValueError as exc:
        raise SkillError(f"skill receipt 路径越界：{receipt_path}") from exc
    _tracked(root, receipt_path.relative_to(root).as_posix(), "skill receipt")
    receipt = _read_json(receipt_path)
    if receipt.get("schemaVersion") != SCHEMA_VERSION:
        raise SkillError(f"skill receipt schemaVersion 必须是 {SCHEMA_VERSION}")
    if receipt.get("kind") != RECEIPT_KIND:
        raise SkillError("skill receipt kind 非法")
    if receipt.get("change") != expected_change:
        raise SkillError("skill receipt change 不一致")
    task = receipt.get("task")
    if not isinstance(task, int) or isinstance(task, bool) or task != expected_task:
        raise SkillError(f"skill receipt task 不一致：{task!r}")
    _require_str(receipt.get("phase"), "skill receipt phase")
    _require_str(receipt.get("skill"), "skill receipt skill")
    source = receipt.get("source")
    if not isinstance(source, dict):
        raise SkillError("skill receipt source 必须是 object")
    project = _require_str(source.get("project"), "source.project")
    version = _require_str(source.get("version"), "source.version")
    commit = _require_str(source.get("commit"), "source.commit")
    relative = _require_str(source.get("path"), "source.path")
    digest = _require_str(source.get("sha256"), "source.sha256")
    if not SHA256_RE.fullmatch(digest):
        raise SkillError("source.sha256 必须是 64 位小写 hex")
    manifest_sources = manifest.get("sources")
    if project not in manifest_sources:
        raise SkillError(f"source.project 不在 manifest：{project}")
    expected_source = manifest_sources[project]
    if version != expected_source.get("version") or commit != expected_source.get("commit"):
        raise SkillError("source.version/commit 与 manifest 不一致")
    files = expected_source.get("files")
    if relative not in files or files[relative] != digest:
        raise SkillError(f"source.path/sha256 不在 manifest 或哈希不一致：{relative}")

    host_skill = receipt.get("hostSkill")
    if not isinstance(host_skill, dict):
        raise SkillError("skill receipt hostSkill 必须是 object")
    root_id = _require_str(host_skill.get("root"), "hostSkill.root")
    host_relative = _require_str(host_skill.get("path"), "hostSkill.path")
    host_digest = _require_str(host_skill.get("sha256"), "hostSkill.sha256")
    if not SHA256_RE.fullmatch(host_digest):
        raise SkillError("hostSkill.sha256 必须是 64 位小写 hex")
    if root_id not in roots:
        raise SkillError(f"hostSkill.root 不在允许根：{root_id}")
    host_root = roots[root_id].expanduser().resolve()
    candidate = (host_root / host_relative).resolve()
    try:
        candidate.relative_to(host_root)
    except ValueError as exc:
        raise SkillError(f"hostSkill.path 越界：{host_relative}") from exc
    if not candidate.is_file():
        raise SkillError(f"hostSkill 不存在：{candidate}")
    if _sha256(candidate) != host_digest:
        raise SkillError("hostSkill.sha256 与宿主实际文件不一致")


def _parse_roots(value: str) -> dict[str, Path]:
    try:
        document = json.loads(value)
    except json.JSONDecodeError as exc:
        raise SkillError(f"--roots-json 非法 JSON：{exc}") from exc
    if not isinstance(document, dict) or not document:
        raise SkillError("--roots-json 必须是 {root_id: path} object")
    roots: dict[str, Path] = {}
    for key, path in document.items():
        if not isinstance(key, str) or not key or not isinstance(path, str) or not path:
            raise SkillError("--roots-json 条目必须是字符串")
        roots[key] = Path(path)
    return roots


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="skills_cli")
    sub = parser.add_subparsers(dest="command", required=True)
    verify = sub.add_parser("verify", help="校验 skill invocation receipt")
    verify.add_argument("--root", default=".")
    verify.add_argument("--manifest", required=True)
    verify.add_argument("--receipt", required=True)
    verify.add_argument("--change", required=True)
    verify.add_argument("--task", required=True, type=int)
    verify.add_argument("--roots-json", required=True)
    args = parser.parse_args(argv)
    try:
        manifest = load_manifest(Path(args.manifest).expanduser().resolve())
        roots = _parse_roots(args.roots_json)
        verify_skill_receipt(
            Path(args.root).expanduser().resolve(),
            Path(args.receipt).expanduser(),
            manifest,
            expected_change=args.change,
            expected_task=args.task,
            roots=roots,
        )
        print(json.dumps({"verified": True, "receipt": args.receipt}, ensure_ascii=False, sort_keys=True))
        return 0
    except (SkillError, OSError, ValueError) as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
