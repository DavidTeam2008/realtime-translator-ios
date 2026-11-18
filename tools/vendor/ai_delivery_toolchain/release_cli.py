"""Deterministic release manifest for the delivery toolchain."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Iterable

from . import __version__

SCHEMA_VERSION = 1
PACKAGE_NAME = "ai-delivery-toolchain"
MANIFEST_KIND = "release-manifest"


class ReleaseError(RuntimeError):
    pass


def _git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, timeout=60
    )
    if completed.returncode != 0:
        raise ReleaseError(f"git {' '.join(args)} 失败：{completed.stderr.strip()[:300]}")
    return completed.stdout.strip()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _manifest_files(root: Path) -> dict[str, str]:
    files: dict[str, str] = {}
    candidates: list[Path] = []
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        candidates.append(pyproject)
    for path in sorted(root.glob("*.json")):
        if path.is_file():
            candidates.append(path)
    package = root / "src" / "ai_delivery_toolchain"
    if package.is_dir():
        for path in sorted(package.rglob("*")):
            if not path.is_file():
                continue
            if "__pycache__" in path.parts or path.suffix in (".pyc", ".pyo"):
                continue
            candidates.append(path)
    for path in candidates:
        relative = path.relative_to(root).as_posix()
        files[relative] = _sha256(path)
    if not files:
        raise ReleaseError(f"root 下没有可入 manifest 的文件：{root}")
    return dict(sorted(files.items()))


def build_release_manifest(
    root: Path,
    *,
    tag: str,
    version: str | None = None,
    commit: str | None = None,
) -> dict:
    root = root.resolve()
    if not (root / ".git").exists():
        raise ReleaseError(f"不是 git 仓库：{root}")
    head = _git(root, "rev-parse", "HEAD")
    source_commit = _git(root, "rev-parse", commit or head)
    source_tree = _git(root, "rev-parse", f"{source_commit}^{{tree}}")
    tag_ref = f"refs/tags/{tag}"
    tag_check = subprocess.run(
        ["git", "rev-parse", "-q", "--verify", tag_ref],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if tag_check.returncode == 0:
        tag_commit = _git(root, "rev-parse", f"{tag}^{{commit}}")
        if tag_commit != source_commit:
            raise ReleaseError(f"tag {tag} 指向 {tag_commit}，与 commit {source_commit} 不一致")
    manifest_version = version or __version__
    manifest = {
        "schemaVersion": SCHEMA_VERSION,
        "name": PACKAGE_NAME,
        "kind": MANIFEST_KIND,
        "version": manifest_version,
        "tag": tag,
        "sourceCommit": source_commit,
        "sourceTree": source_tree,
        "files": _manifest_files(root),
    }
    return manifest


def canonical_json(manifest: dict) -> str:
    return json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def verify_manifest(root: Path, manifest_path: Path) -> None:
    root = root.resolve()
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReleaseError(f"manifest 读取失败：{exc}") from exc
    if not isinstance(manifest, dict):
        raise ReleaseError("manifest 顶层必须是 object")
    for key in ("schemaVersion", "name", "kind", "version", "tag", "sourceCommit", "sourceTree", "files"):
        if key not in manifest:
            raise ReleaseError(f"manifest 缺字段：{key}")
    if manifest["schemaVersion"] != SCHEMA_VERSION:
        raise ReleaseError(f"manifest schemaVersion 必须是 {SCHEMA_VERSION}")
    if manifest["name"] != PACKAGE_NAME or manifest["kind"] != MANIFEST_KIND:
        raise ReleaseError("manifest name/kind 非法")
    files = manifest["files"]
    if not isinstance(files, dict) or not files:
        raise ReleaseError("manifest files 必须是非空 object")
    expected = _manifest_files(root)
    if expected != files:
        raise ReleaseError("manifest files 与当前文件哈希不一致")
    source_commit = str(manifest["sourceCommit"])
    head_tree = _git(root, "rev-parse", f"{source_commit}^{{tree}}")
    if head_tree != manifest["sourceTree"]:
        raise ReleaseError("manifest sourceTree 与 commit 不一致")
    tag_check = subprocess.run(
        ["git", "rev-parse", "-q", "--verify", f"refs/tags/{manifest['tag']}"],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if tag_check.returncode == 0:
        tag_commit = _git(root, "rev-parse", f"{manifest['tag']}^{{commit}}")
        if tag_commit != source_commit:
            raise ReleaseError("manifest tag 与 sourceCommit 不一致")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="release_cli")
    sub = parser.add_subparsers(dest="command", required=True)

    manifest = sub.add_parser("manifest", help="生成确定性 release manifest")
    manifest.add_argument("--root", default=".")
    manifest.add_argument("--tag", required=True)
    manifest.add_argument("--version", default=__version__)
    manifest.add_argument("--commit")
    manifest.add_argument("--out")

    verify = sub.add_parser("verify", help="校验 manifest 与当前文件/tag")
    verify.add_argument("--root", default=".")
    verify.add_argument("--manifest", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "manifest":
            manifest = build_release_manifest(
                Path(args.root), tag=args.tag, version=args.version, commit=args.commit
            )
            text = canonical_json(manifest)
            if args.out:
                out = Path(args.out)
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(text, encoding="utf-8")
            else:
                print(text, end="")
            return 0
        verify_manifest(Path(args.root), Path(args.manifest))
        print("PASS release manifest")
        return 0
    except (ReleaseError, OSError, ValueError) as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
