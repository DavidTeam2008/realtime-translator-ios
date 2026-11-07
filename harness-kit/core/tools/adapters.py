#!/usr/bin/env python3
"""Agent adapter sync/check: keep a single skill source and generate tool-specific copies.

Usage:
    python3 tools/adapters.py sync  [--root PATH]
    python3 tools/adapters.py check [--root PATH]

Config (harness/config.json):
    "adapters": { "claudeCode": { "skillsSource": ".dsh/skills",
                                  "skillsTarget": ".claude/skills" } }

Semantics:
  - sync: copy every file from skillsSource to skillsTarget (same relative paths),
    prune generated files that no longer exist in the source, and write a manifest
    with content hashes. Does not touch unrelated files under skillsTarget.
  - check: if the target directory does not exist -> OK (adapter not installed yet).
    If it exists, compare the manifest + hashes; any drift -> FAIL (exit 1).
Standard library only; no network; no secrets.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

MANIFEST_NAME = ".harness-adapters.json"
DEFAULT_SOURCE = ".dsh/skills"
DEFAULT_TARGET = ".claude/skills"


def find_root(override: str | None) -> Path:
    if override:
        return Path(override).expanduser().resolve()
    return Path(__file__).resolve().parent.parent


def load_config(root: Path) -> dict:
    path = root / "harness" / "config.json"
    if not path.is_file():
        raise SystemExit(f"[FAIL] missing config: {path.relative_to(root) if path.is_relative_to(root) else path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"[FAIL] invalid JSON in {path}: {exc}")
    if not isinstance(data, dict):
        raise SystemExit(f"[FAIL] {path} must contain a JSON object")
    return data


def adapter_paths(config: dict) -> tuple[Path, Path]:
    adapters = config.get("adapters")
    if not isinstance(adapters, dict) or not isinstance(adapters.get("claudeCode"), dict):
        raise SystemExit(
            "[FAIL] harness/config.json is missing adapters.claudeCode "
            '({"skillsSource": ".dsh/skills", "skillsTarget": ".claude/skills"})'
        )
    claude = adapters["claudeCode"]
    source = Path(str(claude.get("skillsSource") or DEFAULT_SOURCE))
    target = Path(str(claude.get("skillsTarget") or DEFAULT_TARGET))
    if source.is_absolute() or target.is_absolute() or ".." in source.parts or ".." in target.parts:
        raise SystemExit("[FAIL] adapter paths must be project-relative and must not contain '..'")
    return source, target


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def source_files(source_root: Path) -> dict[str, str]:
    files: dict[str, str] = {}
    if not source_root.is_dir():
        return files
    for path in sorted(source_root.rglob("*")):
        if not path.is_file():
            continue
        files[path.relative_to(source_root).as_posix()] = digest(path.read_bytes())
    return files


def read_manifest(target_root: Path) -> dict | None:
    path = target_root / MANIFEST_NAME
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def cmd_sync(root: Path) -> int:
    config = load_config(root)
    source_rel, target_rel = adapter_paths(config)
    source_root = root / source_rel
    target_root = root / target_rel
    files = source_files(source_root)
    if not files:
        print(f"[WARN] skills source is empty or missing: {source_rel}")
        return 0
    target_root.mkdir(parents=True, exist_ok=True)
    for rel, _hash in files.items():
        src = source_root / rel
        dst = target_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    previous = read_manifest(target_root)
    stale = set((previous or {}).get("files", {})) - set(files)
    for rel in sorted(stale):
        stale_path = target_root / rel
        if stale_path.is_file():
            stale_path.unlink()
    manifest = {
        "generatedBy": "tools/adapters.py",
        "source": source_rel.as_posix(),
        "files": files,
    }
    (target_root / MANIFEST_NAME).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"[OK] adapters sync: {len(files)} file(s) -> {target_rel}")
    return 0


def cmd_check(root: Path) -> int:
    config = load_config(root)
    source_rel, target_rel = adapter_paths(config)
    source_root = root / source_rel
    target_root = root / target_rel
    files = source_files(source_root)
    if not files:
        print(f"[OK] adapters check: no skills source ({source_rel}); adapter disabled")
        return 0
    if not target_root.is_dir():
        print(f"[OK] adapters check: target {target_rel} not installed (run: python3 tools/adapters.py sync)")
        return 0
    manifest = read_manifest(target_root)
    if manifest is None:
        print(f"[FAIL] adapters check: missing or invalid {target_rel}/{MANIFEST_NAME}; run sync")
        return 1
    problems: list[str] = []
    generated = manifest.get("files")
    if not isinstance(generated, dict):
        problems.append("manifest.files is not an object")
        generated = {}
    for rel, expected in files.items():
        if rel not in generated:
            problems.append(f"not synced: {rel}")
            continue
        if generated[rel] != expected:
            problems.append(f"stale source hash: {rel}")
        actual_path = target_root / rel
        if not actual_path.is_file():
            problems.append(f"missing generated file: {rel}")
            continue
        if digest(actual_path.read_bytes()) != expected:
            problems.append(f"generated file modified: {rel}")
    for rel in sorted(set(generated) - set(files)):
        problems.append(f"orphan generated file (source removed): {rel}")
    if problems:
        for item in problems:
            print(f"[FAIL] adapters check: {item}")
        return 1
    print(f"[OK] adapters check: {len(files)} file(s) in sync with {source_rel}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sync/check agent adapters (single skill source).")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("sync", "check"):
        child = sub.add_parser(name)
        child.add_argument("--root", help="project root (default: parent of tools/)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = find_root(args.root)
    try:
        return cmd_sync(root) if args.command == "sync" else cmd_check(root)
    except SystemExit as exc:  # config errors are user-facing failures
        if isinstance(exc.code, str):
            print(exc.code, file=sys.stderr)
            return 1
        raise


if __name__ == "__main__":
    sys.exit(main())
