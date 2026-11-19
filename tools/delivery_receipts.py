#!/usr/bin/env python3
"""Generate OpenSpec / Superpowers receipts for the host gates."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OPENSPEC = ROOT / "tools" / "openspec"
DEFAULT_MANIFEST = ROOT / "tools" / "vendor" / "ai_delivery_toolchain" / "skills.manifest.json"
OVERLAY = Path("harness") / "superpowers-overlay.md"
RECEIPTS = Path("harness") / "receipts"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _json(path: Path, document: dict) -> None:
    _write(path, json.dumps(document, ensure_ascii=False, indent=2) + "\n")


def _rel(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _git(root: Path, *args: str) -> str:
    completed = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, timeout=60)
    if completed.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} 失败：{completed.stderr.strip()[:300]}")
    return completed.stdout.strip()


def _run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
    if completed.returncode != 0:
        print(completed.stdout)
        print(completed.stderr, file=sys.stderr)
        raise SystemExit(f"命令失败（exit {completed.returncode}）：{' '.join(command)}")
    return completed


def _change_paths(root: Path, change: str) -> tuple[Path, Path]:
    change_dir = root / "openspec" / "changes" / change
    receipt_dir = root / RECEIPTS / "openspec" / change
    return change_dir, receipt_dir


def cmd_scaffold(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    change = args.change
    change_dir, receipt_dir = _change_paths(root, change)
    if change_dir.exists():
        raise SystemExit(f"change 已存在：{change_dir}")
    completed = _run([args.openspec, "new", "change", change], cwd=root)
    yaml = change_dir / ".openspec.yaml"
    if not yaml.is_file():
        raise SystemExit("缺少 .openspec.yaml")
    log = receipt_dir / "logs" / "scaffold.log"
    _write(log, completed.stdout + completed.stderr)
    base = _git(root, "rev-parse", "HEAD")
    _json(receipt_dir / "scaffold.json", {
        "schemaVersion": 1,
        "kind": "openspec-scaffold",
        "change": change,
        "base": base,
        "command": f"openspec new change {change}",
        "exitCode": 0,
        "createdAt": _utc_now(),
        "outputArtifact": _rel(root, log),
        "outputSha256": _sha(log),
        "openspecYaml": _rel(root, yaml),
        "openspecYamlSha256": _sha(yaml),
    })
    print(f"scaffold receipt: {_rel(root, receipt_dir / 'scaffold.json')}")
    return 0


def cmd_instructions(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    change = args.change
    artifact = args.artifact
    _, receipt_dir = _change_paths(root, change)
    completed = _run([args.openspec, "instructions", artifact, "--change", change, "--json"], cwd=root)
    log = receipt_dir / "logs" / f"{artifact}.log"
    _write(log, completed.stdout + completed.stderr)
    _json(receipt_dir / f"instructions-{artifact}.json", {
        "schemaVersion": 1,
        "kind": "openspec-instructions",
        "change": change,
        "artifact": artifact,
        "command": f"openspec instructions {artifact} --change {change} --json",
        "exitCode": 0,
        "outputSha256": _sha(log),
        "outputArtifact": _rel(root, log),
    })
    print(f"instructions receipt: {_rel(root, receipt_dir / f'instructions-{artifact}.json')}")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    change = args.change
    change_dir, receipt_dir = _change_paths(root, change)
    completed = _run([args.openspec, "validate", change, "--type", "change", "--strict", "--json"], cwd=root)
    payload = receipt_dir / "validate.json"
    _write(payload, completed.stdout + completed.stderr)
    artifacts = {
        path.relative_to(change_dir).as_posix(): _sha(path)
        for path in sorted(change_dir.rglob("*.md"))
        if path.is_file()
    }
    _json(receipt_dir / "validate-receipt.json", {
        "schemaVersion": 1,
        "kind": "openspec-validate",
        "change": change,
        "command": f"openspec validate {change} --type change --strict --json",
        "exitCode": 0,
        "artifactsSha256": artifacts,
        "validateJson": _rel(root, payload),
        "validateJsonSha256": _sha(payload),
    })
    print(f"validate receipt: {_rel(root, receipt_dir / 'validate-receipt.json')}")
    return 0


def cmd_clarification(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    change = args.change
    directory = root / RECEIPTS / "clarification" / change
    notes = Path(args.notes).expanduser().resolve() if args.notes else None
    if notes is not None and not notes.is_file():
        raise SystemExit(f"notes 不存在：{notes}")
    document = {
        "schemaVersion": 1,
        "kind": "clarification",
        "change": change,
        "skill": args.skill,
        "createdAt": _utc_now(),
    }
    if notes is not None:
        target = directory / "notes.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(notes.read_bytes())
        document["notesArtifact"] = _rel(root, target)
        document["notesSha256"] = _sha(target)
    _json(directory / "clarification.json", document)
    print(f"clarification receipt: {_rel(root, directory / 'clarification.json')}")
    return 0


def cmd_skill_receipt(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    manifest = json.loads(Path(args.manifest).expanduser().read_text(encoding="utf-8"))
    sources = manifest.get("sources")
    if not isinstance(sources, dict):
        raise SystemExit("manifest.sources 缺失")
    source = None
    suffix = f"/{args.skill}/SKILL.md"
    for name, candidate in sources.items():
        if not isinstance(candidate, dict):
            continue
        files = candidate.get("files") or {}
        for relative, digest in files.items():
            if relative.endswith(suffix):
                source = (name, candidate, relative, digest)
                break
        if source:
            break
    if source is None:
        raise SystemExit(f"manifest 中找不到 skill：{args.skill}")
    name, candidate, relative, digest = source
    host_file = Path(args.host_file).expanduser().resolve()
    host_root = Path(args.host_root).expanduser().resolve()
    if not host_file.is_file():
        raise SystemExit(f"host skill 不存在：{host_file}")
    try:
        host_relative = host_file.relative_to(host_root).as_posix()
    except ValueError:
        raise SystemExit("host-file 必须位于 host-root 下")
    if _sha(host_file) != digest:
        raise SystemExit("host skill 哈希与 manifest 不一致")
    overlay = root / OVERLAY
    if not overlay.is_file():
        raise SystemExit(f"缺少 Superpowers overlay：{OVERLAY.as_posix()}")
    directory = root / RECEIPTS / "skills" / args.change
    path = directory / f"task-{args.task}-{args.skill}.json"
    _json(path, {
        "schemaVersion": 1,
        "kind": "skill-invoked",
        "change": args.change,
        "task": args.task,
        "phase": args.phase,
        "skill": args.skill,
        "source": {
            "project": name,
            "version": candidate.get("version"),
            "commit": candidate.get("commit"),
            "path": relative,
            "sha256": digest,
        },
        "hostSkill": {
            "root": args.root_id,
            "path": host_relative,
            "sha256": _sha(host_file),
        },
        "overlay": {
            "path": _rel(root, overlay),
            "sha256": _sha(overlay),
        },
        "host": {"name": args.host_name, "version": args.host_version},
        "invokedAt": _utc_now(),
        "head": _git(root, "rev-parse", "HEAD"),
    })
    print(f"skill receipt: {_rel(root, path)}")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="delivery_receipts")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("scaffold", "instructions", "validate"):
        command = sub.add_parser(name)
        command.add_argument("--root", default=".")
        command.add_argument("--change", required=True)
        command.add_argument("--openspec", default=str(DEFAULT_OPENSPEC))
        if name == "instructions":
            command.add_argument("--artifact", required=True)
        command.set_defaults(func={"scaffold": cmd_scaffold, "instructions": cmd_instructions, "validate": cmd_validate}[name])
    clarification = sub.add_parser("clarification")
    clarification.add_argument("--root", default=".")
    clarification.add_argument("--change", required=True)
    clarification.add_argument("--skill", required=True)
    clarification.add_argument("--notes")
    clarification.set_defaults(func=cmd_clarification)

    skill = sub.add_parser("skill-receipt")
    skill.add_argument("--root", default=".")
    skill.add_argument("--change", required=True)
    skill.add_argument("--task", required=True, type=int)
    skill.add_argument("--phase", required=True)
    skill.add_argument("--skill", required=True)
    skill.add_argument("--root-id", required=True)
    skill.add_argument("--host-root", required=True)
    skill.add_argument("--host-file", required=True)
    skill.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    skill.add_argument("--host-name", default="dsh")
    skill.add_argument("--host-version", default="unknown")
    skill.set_defaults(func=cmd_skill_receipt)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
