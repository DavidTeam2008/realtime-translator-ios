"""OpenSpec provenance receipts: scaffold, instructions and validate."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable

SCHEMA_VERSION = 1
RECEIPT_KINDS = ("openspec-scaffold", "openspec-instructions", "openspec-validate")
DEFAULT_ARTIFACTS = ("proposal", "design", "specs", "tasks")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class ProvenanceError(RuntimeError):
    pass


def _read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProvenanceError(f"receipt 读取失败：{path} ({exc})") from exc
    if not isinstance(value, dict):
        raise ProvenanceError(f"receipt 顶层必须是 object：{path}")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(root: Path, *args: str) -> str:
    completed = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, timeout=60)
    if completed.returncode != 0:
        raise ProvenanceError(f"git {' '.join(args)} 失败：{completed.stderr.strip()[:300]}")
    return completed.stdout.strip()


def _tracked(root: Path, relative: str, label: str) -> None:
    try:
        _git(root, "ls-files", "--error-unmatch", "--", relative)
    except ProvenanceError as exc:
        raise ProvenanceError(f"{label} 未被 git 跟踪：{relative}") from exc


def _safe(root: Path, relative: str, label: str) -> Path:
    path = (root / relative).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise ProvenanceError(f"{label} 路径越界：{relative}") from exc
    if not path.is_file():
        raise ProvenanceError(f"{label} 不存在：{relative}")
    return path


def _require_str(receipt: dict, key: str, label: str) -> str:
    value = receipt.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ProvenanceError(f"{label}.{key} 必须是非空字符串")
    return value.strip()


def _require_ok_exit(receipt: dict, label: str) -> None:
    exit_code = receipt.get("exitCode")
    if not isinstance(exit_code, int) or isinstance(exit_code, bool) or exit_code != 0:
        raise ProvenanceError(f"{label}.exitCode 必须为 0")


def _parse_openspec_yaml(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ProvenanceError(f".openspec.yaml 无法读取：{exc}") from exc
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        values[key.strip()] = value.strip()
    return values


def _parse_date(value: str, label: str) -> dt.date:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return dt.datetime.fromisoformat(text).date()
    except ValueError:
        try:
            return dt.date.fromisoformat(text)
        except ValueError as exc:
            raise ProvenanceError(f"{label} 不是合法日期：{value}") from exc


def _load_receipts(directory: Path) -> list[dict]:
    if not directory.is_dir():
        raise ProvenanceError(f"receipt 目录不存在：{directory}")
    receipts: list[dict] = []
    for path in sorted(directory.glob("*.json")):
        receipt = _read_json(path)
        kind = receipt.get("kind")
        if kind is None:
            # validate payload / instruction output / other non-receipt JSON
            continue
        if kind not in RECEIPT_KINDS:
            raise ProvenanceError(f"{path.name}.kind 非法：{kind!r}")
        if receipt.get("schemaVersion") != SCHEMA_VERSION:
            raise ProvenanceError(f"{path.name}.schemaVersion 必须是 {SCHEMA_VERSION}")
        receipt["_path"] = path
        receipts.append(receipt)
    return receipts


def verify_provenance(
    root: Path,
    change: str,
    *,
    receipts_dir: str = "harness/receipts/openspec",
    change_dir: str | None = None,
    schemas: Iterable[str] = ("spec-driven",),
    artifacts: Iterable[str] = DEFAULT_ARTIFACTS,
) -> list[str]:
    root = root.resolve()
    if not change or "/" in change or ".." in Path(change).parts:
        raise ProvenanceError(f"change 非法：{change!r}")
    change_path = (root / (change_dir or f"openspec/changes/{change}")).resolve()
    try:
        change_path.relative_to(root)
    except ValueError as exc:
        raise ProvenanceError("change 目录必须位于仓库内") from exc
    if not change_path.is_dir():
        raise ProvenanceError(f"change 目录不存在：{change_path}")
    receipt_root = (root / receipts_dir / change).resolve()
    try:
        receipt_root.relative_to(root)
    except ValueError as exc:
        raise ProvenanceError("receipts_dir 必须位于仓库内") from exc
    receipts = _load_receipts(receipt_root)
    scaffolds = [item for item in receipts if item["kind"] == "openspec-scaffold"]
    validates = [item for item in receipts if item["kind"] == "openspec-validate"]
    instructions = [item for item in receipts if item["kind"] == "openspec-instructions"]
    if len(scaffolds) != 1:
        raise ProvenanceError(f"必须恰好 1 份 scaffold receipt，实际 {len(scaffolds)}")
    if len(validates) != 1:
        raise ProvenanceError(f"必须恰好 1 份 validate receipt，实际 {len(validates)}")

    scaffold = scaffolds[0]
    if scaffold.get("change") != change:
        raise ProvenanceError("scaffold.change 不一致")
    _require_ok_exit(scaffold, "scaffold")
    created_at = _parse_date(_require_str(scaffold, "createdAt", "scaffold"), "scaffold.createdAt")
    output_rel = _require_str(scaffold, "outputArtifact", "scaffold")
    output_sha = _require_str(scaffold, "outputSha256", "scaffold")
    yaml_rel = _require_str(scaffold, "openspecYaml", "scaffold")
    yaml_sha = _require_str(scaffold, "openspecYamlSha256", "scaffold")
    output_path = _safe(root, output_rel, "scaffold.outputArtifact")
    yaml_path = _safe(root, yaml_rel, "scaffold.openspecYaml")
    _tracked(root, output_rel, "scaffold.outputArtifact")
    _tracked(root, yaml_rel, "scaffold.openspecYaml")
    if _sha256(output_path) != output_sha:
        raise ProvenanceError("scaffold.outputArtifact 哈希不一致")
    if _sha256(yaml_path) != yaml_sha:
        raise ProvenanceError("scaffold.openspecYaml 哈希不一致")
    metadata = _parse_openspec_yaml(yaml_path)
    schema = metadata.get("schema", "")
    if schema not in tuple(schemas):
        raise ProvenanceError(f".openspec.yaml schema 非法：{schema!r}")
    created = metadata.get("created", "")
    if not created:
        raise ProvenanceError(".openspec.yaml 缺 created")
    yaml_date = _parse_date(created, ".openspec.yaml created")
    if abs((yaml_date - created_at).days) > 1:
        raise ProvenanceError("scaffold.createdAt 与 .openspec.yaml created 相差超过 1 天")

    required = tuple(artifacts)
    by_artifact: dict[str, dict] = {}
    for receipt in instructions:
        if receipt.get("change") != change:
            raise ProvenanceError("instructions.change 不一致")
        artifact = _require_str(receipt, "artifact", "instructions")
        _require_ok_exit(receipt, f"instructions[{artifact}]")
        output = _require_str(receipt, "outputArtifact", f"instructions[{artifact}]")
        digest = _require_str(receipt, "outputSha256", f"instructions[{artifact}]")
        path = _safe(root, output, f"instructions[{artifact}].outputArtifact")
        _tracked(root, output, f"instructions[{artifact}].outputArtifact")
        if _sha256(path) != digest:
            raise ProvenanceError(f"instructions[{artifact}].outputArtifact 哈希不一致")
        by_artifact[artifact] = receipt
    missing = [artifact for artifact in required if artifact not in by_artifact]
    if missing:
        raise ProvenanceError(f"缺少 instructions receipt：{', '.join(missing)}")

    validate = validates[0]
    if validate.get("change") != change:
        raise ProvenanceError("validate.change 不一致")
    _require_ok_exit(validate, "validate")
    json_rel = _require_str(validate, "validateJson", "validate")
    json_sha = _require_str(validate, "validateJsonSha256", "validate")
    json_path = _safe(root, json_rel, "validate.validateJson")
    _tracked(root, json_rel, "validate.validateJson")
    if _sha256(json_path) != json_sha:
        raise ProvenanceError("validate.validateJson 哈希不一致")
    tree = validate.get("artifactsSha256")
    if not isinstance(tree, dict) or not tree:
        raise ProvenanceError("validate.artifactsSha256 必须是非空 object")
    actual_files = {
        path.relative_to(change_path).as_posix()
        for path in sorted(change_path.rglob("*.md"))
        if path.is_file()
    }
    expected_files = set(tree)
    if actual_files != expected_files:
        raise ProvenanceError(
            f"validate 工件树与当前不一致：多 {sorted(actual_files - expected_files)} / 缺 {sorted(expected_files - actual_files)}"
        )
    for relative, expected_sha in sorted(tree.items()):
        if not isinstance(expected_sha, str) or not SHA256_RE.fullmatch(expected_sha):
            raise ProvenanceError(f"validate.artifactsSha256[{relative}] 必须是 64 位 hex")
        path = (change_path / relative).resolve()
        try:
            path.relative_to(change_path)
        except ValueError as exc:
            raise ProvenanceError(f"validate artifact 路径越界：{relative}") from exc
        _tracked(root, path.relative_to(root).as_posix(), f"validate artifact {relative}")
        if _sha256(path) != expected_sha:
            raise ProvenanceError(f"validate artifact 哈希不一致：{relative}")

    return [item["_path"].relative_to(root).as_posix() for item in receipts]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="provenance_cli")
    sub = parser.add_subparsers(dest="command", required=True)
    verify = sub.add_parser("verify", help="校验 OpenSpec provenance receipts")
    verify.add_argument("--root", default=".")
    verify.add_argument("--change", required=True)
    verify.add_argument("--receipts-dir", default="harness/receipts/openspec")
    verify.add_argument("--change-dir")
    verify.add_argument("--schemas", default="spec-driven")
    verify.add_argument("--artifacts", default="proposal,design,specs,tasks")
    args = parser.parse_args(argv)
    try:
        if args.command == "verify":
            paths = verify_provenance(
                Path(args.root).expanduser().resolve(),
                args.change,
                receipts_dir=args.receipts_dir,
                change_dir=args.change_dir,
                schemas=tuple(item.strip() for item in args.schemas.split(",") if item.strip()),
                artifacts=tuple(item.strip() for item in args.artifacts.split(",") if item.strip()),
            )
            print(json.dumps({"verified": True, "change": args.change, "receipts": paths}, ensure_ascii=False, sort_keys=True))
            return 0
    except (ProvenanceError, OSError, ValueError) as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
