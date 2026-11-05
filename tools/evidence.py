#!/usr/bin/env python3
"""证据链工具（纯标准库）：列出 / 查看 / 校验 / 写入 `.apm/evidence/*.json`。

用法：
    python3 tools/evidence.py                       # 默认 = ls + validate（便利入口）
    python3 tools/evidence.py ls [--claim CLAIM] [--json]
    python3 tools/evidence.py show <id|路径>
    python3 tools/evidence.py validate              # 校验 schema + 语义；失败 exit 1
    python3 tools/evidence.py write --claim NAME --status STATUS --passed N [--failed N]
        [--skipped N] [--duration SEC] [--xcode VER] [--simulator RUNTIME] [--device NAME]
        [--build CONFIG] [--host HOST] [--xcresult PATH] [--metrics PATH]
        [--command CMD] [--verdict V] [--notes TEXT] [--session-id ID]
    python3 tools/evidence.py write --from-json PATH|-    # 读草稿 JSON（支持 stdin）

通用参数：--root PATH（默认脚本上级目录，供 fixture/测试使用）。
退出码：0 成功；1 校验/写入失败；2 用法错误。
写入前按 `.apm/evidence/schema.json` 校验并自动填 id/createdAt/git/verifier；
路径按"仓库相对 或 ~/ 相对"归一化，不在仓库/主目录内的产物路径置 null 并告警。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_REL = ".apm/evidence"
SCHEMA_NAME = "schema.json"
TEMPLATE_NAME = "TEMPLATE.json"
README_NAME = "README.md"
VERIFIER = "tools/evidence.py@1"
SCHEMA_VERSION = 1
ID_RE = re.compile(r"^[0-9]{8}T[0-9]{6}Z-[a-z0-9][a-z0-9-]*$")
CREATED_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")
CLAIMS = (
    "unit-tests-pass",
    "ui-tests-pass",
    "device-tests-pass",
    "docs-pass",
    "arch-pass",
    "perf-measurement",
    "perf-no-regression",
    "perf-improved",
)
STATUSES = ("SUCCEEDED", "FAILED", "SKIPPED", "UNVERIFIED")
VERDICTS = ("PASS", "FAIL", "UNVERIFIED")
SKIP_NAMES = frozenset({SCHEMA_NAME, TEMPLATE_NAME, README_NAME})


# ── 基础工具 ────────────────────────────────────────────────────────────────
def evidence_dir(root: Path) -> Path:
    return root / EVIDENCE_REL


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def id_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def git_short_commit(root: Path) -> str:
    """返回 HEAD 短 hash；不在 git 仓库或有误时抛 RuntimeError。"""
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--short=12", "HEAD"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError) as exc:  # pragma: no cover - 环境异常
        raise RuntimeError(f"无法执行 git：{exc}") from exc
    if proc.returncode != 0:
        raise RuntimeError(f"无法获取 git HEAD（exit {proc.returncode}）：{proc.stderr.strip()[:160]}")
    commit = proc.stdout.strip()
    if not re.fullmatch(r"[0-9a-f]{7,40}", commit):
        raise RuntimeError(f"git HEAD 短 hash 非法：{commit!r}")
    return commit


def git_dirty(root: Path) -> bool:
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:  # pragma: no cover - 环境异常
        raise RuntimeError(f"无法执行 git status：{exc}") from exc
    if proc.returncode != 0:
        raise RuntimeError(f"无法获取 git status（exit {proc.returncode}）")
    return bool(proc.stdout.strip())


def portable_path(root: Path, value: str | None) -> tuple[str | None, str | None]:
    """把路径归一化为仓库相对或 ~/ 相对。

    返回 (portable, warning)。不在仓库/主目录内的路径返回 (None, warning)，
    避免把本机绝对路径写进入库证据。
    """
    if value is None:
        return None, None
    raw = str(value).strip()
    if not raw:
        return None, None
    path = Path(os.path.expanduser(raw))
    if not path.is_absolute():
        path = root / path
    try:
        resolved = path.resolve()
    except OSError:  # pragma: no cover - 极端文件系统错误
        resolved = path
    root_resolved = root.resolve()
    try:
        return resolved.relative_to(root_resolved).as_posix(), None
    except ValueError:
        pass
    home = Path(os.path.expanduser("~"))
    try:
        home_resolved = home.resolve()
    except OSError:  # pragma: no cover
        home_resolved = home
    try:
        return "~/" + resolved.relative_to(home_resolved).as_posix(), None
    except ValueError:
        return None, f"产物路径不在仓库/主目录内，已置 null：{path.name}"


# ── 最小 draft-07 子集校验（无第三方依赖）────────────────────────────────────
_TYPE_CHECKS = {
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "null": lambda v: v is None,
}


def _type_ok(value: Any, spec_type: str | list[str]) -> bool:
    types = [spec_type] if isinstance(spec_type, str) else list(spec_type)
    return any(_TYPE_CHECKS.get(t, lambda _v: False)(value) for t in types)


def validate_document(value: Any, spec: dict[str, Any], path: str = "") -> list[str]:
    """校验 JSON 文档与 schema 子集；返回错误列表（空 = 通过）。"""
    errors: list[str] = []
    label = path or "<root>"
    spec_type = spec.get("type")
    if spec_type is not None and not _type_ok(value, spec_type):
        errors.append(f"{label}: 类型应为 {spec_type}，实际 {type(value).__name__}")
        return errors
    if "const" in spec and value != spec["const"]:
        errors.append(f"{label}: 期望常量 {spec['const']!r}，实际 {value!r}")
    enum = spec.get("enum")
    if enum is not None and value not in enum:
        errors.append(f"{label}: 取值 {value!r} 不在允许集合 {enum}")
    if isinstance(value, str):
        minimum_length = spec.get("minLength")
        if isinstance(minimum_length, int) and len(value) < minimum_length:
            errors.append(f"{label}: 长度 {len(value)} < {minimum_length}")
        pattern = spec.get("pattern")
        if pattern and not re.search(pattern, value):
            errors.append(f"{label}: 不匹配 pattern {pattern}（值 {value!r}）")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in spec and value < spec["minimum"]:
            errors.append(f"{label}: {value} < minimum {spec['minimum']}")
        if "maximum" in spec and value > spec["maximum"]:
            errors.append(f"{label}: {value} > maximum {spec['maximum']}")
    if isinstance(value, list):
        min_items = spec.get("minItems")
        if isinstance(min_items, int) and len(value) < min_items:
            errors.append(f"{label}: 元素数 {len(value)} < {min_items}")
        item_spec = spec.get("items")
        if isinstance(item_spec, dict):
            for index, item in enumerate(value):
                errors.extend(validate_document(item, item_spec, f"{label}[{index}]"))
    if isinstance(value, dict):
        for required in spec.get("required", []):
            if required not in value:
                errors.append(f"{label}: 缺少必填字段 {required!r}")
        properties = spec.get("properties", {})
        extra = spec.get("additionalProperties", True)
        for key, item in value.items():
            child = f"{label}.{key}" if label != "<root>" else key
            if key in properties:
                errors.extend(validate_document(item, properties[key], child))
            elif extra is False:
                errors.append(f"{label}: 不允许的字段 {key!r}")
            elif isinstance(extra, dict):
                errors.extend(validate_document(item, extra, child))
    return errors


def load_schema(root: Path) -> tuple[dict[str, Any] | None, list[str]]:
    path = evidence_dir(root) / SCHEMA_NAME
    if not path.is_file():
        return None, [f"缺少 {EVIDENCE_REL}/{SCHEMA_NAME}"]
    try:
        return json.loads(path.read_text(encoding="utf-8")), []
    except json.JSONDecodeError as exc:
        return None, [f"{EVIDENCE_REL}/{SCHEMA_NAME} 不是合法 JSON：{exc}"]


def load_schema_for(root: Path) -> tuple[dict[str, Any] | None, list[str]]:
    """优先用目标仓库 schema；fixture 仓库没有时退回工具自身仓库（schema 属工具链）。"""
    schema, errors = load_schema(root)
    if schema is not None:
        return schema, errors
    try:
        same_as_tool = root.resolve() == DEFAULT_ROOT.resolve()
    except OSError:  # pragma: no cover - 极端路径
        same_as_tool = False
    if same_as_tool:
        return None, errors
    fallback, fallback_errors = load_schema(DEFAULT_ROOT)
    if fallback is not None:
        return fallback, []
    return None, errors + fallback_errors


def evidence_files(root: Path) -> list[Path]:
    directory = evidence_dir(root)
    if not directory.is_dir():
        return []
    return sorted(
        path
        for path in directory.glob("*.json")
        if path.is_file() and path.name not in SKIP_NAMES
    )


def semantic_errors(doc: dict[str, Any], path: Path) -> list[str]:
    """schema 之外的语义检查（id=文件名、时间可解析、verdict 与 result 自洽）。"""
    errors: list[str] = []
    if doc.get("id") != path.stem:
        errors.append(f"id {doc.get('id')!r} 必须等于文件名 stem {path.stem!r}")
    created = doc.get("createdAt")
    if isinstance(created, str) and not CREATED_RE.match(created):
        errors.append(f"createdAt 必须是 UTC RFC3339（…Z）：{created!r}")
    if doc.get("verdict") == "PASS":
        result = doc.get("result") or {}
        if result.get("status") != "SUCCEEDED":
            errors.append("verdict=PASS 但 result.status != SUCCEEDED")
        if int(result.get("failed", 0) or 0) != 0:
            errors.append("verdict=PASS 但 result.failed != 0")
    return errors


def validate_file(root: Path, schema: dict[str, Any], path: Path) -> list[str]:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{path.name}: 不是合法 JSON：{exc}"]
    errors = [f"{path.name}: {e}" for e in validate_document(doc, schema)]
    if not errors:
        errors = [f"{path.name}: {e}" for e in semantic_errors(doc, path)]
    return errors


# ── 子命令 ──────────────────────────────────────────────────────────────────
def cmd_ls(root: Path, args: argparse.Namespace) -> int:
    files = evidence_files(root)
    if args.claim:
        files = [
            path
            for path in files
            if (json.loads(path.read_text(encoding="utf-8")).get("claim") == args.claim)
        ]
    if args.json:
        entries = []
        for path in files:
            try:
                doc = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                entries.append({"file": path.name, "error": "invalid json"})
                continue
            entries.append(doc)
        print(json.dumps(entries, ensure_ascii=False, indent=2))
        return 0
    if not files:
        print("（无 evidence 文件；先在 .apm/evidence/ 生成或写入）")
        return 0
    for path in files:
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"[BAD-JSON] {path.name}")
            continue
        git = doc.get("git") or {}
        result = doc.get("result") or {}
        print(
            f"{doc.get('id', path.stem)}  claim={doc.get('claim', '?')}  "
            f"verdict={doc.get('verdict', '?')}  git={git.get('commit', '?')}"
            f"(dirty={git.get('dirty', '?')})  "
            f"passed={result.get('passed', '?')} failed={result.get('failed', '?')} "
            f"skipped={result.get('skipped', '?')}"
        )
    print(f"共 {len(files)} 条 evidence")
    return 0


def cmd_show(root: Path, args: argparse.Namespace) -> int:
    target = Path(args.target)
    candidates: list[Path] = []
    if target.is_file():
        candidates.append(target)
    else:
        candidates.extend(path for path in evidence_files(root) if path.stem == args.target)
    if not candidates:
        print(f"[FAIL] 找不到 evidence：{args.target}", file=sys.stderr)
        return 1
    for path in candidates:
        print(path.read_text(encoding="utf-8"))
    return 0


def cmd_validate(root: Path, args: argparse.Namespace) -> int:
    if not evidence_dir(root).is_dir():
        print(f"[FAIL] 缺少 {EVIDENCE_REL}/（证据目录应入库）", file=sys.stderr)
        return 1
    schema, schema_errors = load_schema_for(root)
    if schema is None:
        for error in schema_errors:
            print(f"[FAIL] {error}", file=sys.stderr)
        return 1
    files = evidence_files(root)
    errors: list[str] = []
    for path in files:
        file_errors = validate_file(root, schema, path)
        if file_errors:
            errors.extend(file_errors)
        else:
            doc = json.loads(path.read_text(encoding="utf-8"))
            print(f"[OK] {doc.get('id')}  claim={doc.get('claim')}  verdict={doc.get('verdict')}")
    if errors:
        print(f"\n[FAIL] {len(errors)} 个 evidence 校验问题：", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"[PASS] {len(files)} 条 evidence 通过 schema + 语义校验")
    return 0


def _derive_verdict(result: dict[str, Any]) -> str:
    if result.get("status") == "SUCCEEDED" and int(result.get("failed", 0) or 0) == 0:
        return "PASS"
    return "FAIL"


def _build_from_args(args: argparse.Namespace) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "schemaVersion": SCHEMA_VERSION,
        "claim": args.claim,
        "command": args.evidence_command,
        "environment": {
            "xcode": args.xcode,
            "simulator": args.simulator,
            "device": args.device,
            "build": args.build,
            "host": args.host,
        },
        "result": {
            "status": args.status,
            "passed": args.passed,
            "failed": args.failed,
            "skipped": args.skipped,
            "durationSec": args.duration,
            "xcresultPath": args.xcresult,
            "metricsPath": args.metrics,
        },
        "verdict": args.verdict,
        "verifier": VERIFIER,
    }
    if args.notes:
        doc["notes"] = args.notes
    if args.session_id:
        doc["sessionId"] = args.session_id
    return doc


def _read_draft(from_json: str) -> dict[str, Any]:
    try:
        if from_json == "-":
            return json.load(sys.stdin)
        return json.loads(Path(from_json).read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"草稿 JSON 非法：{exc}") from exc
    except OSError as exc:
        raise ValueError(f"无法读取草稿 {from_json}：{exc}") from exc


def _next_id(directory: Path, claim: str) -> str:
    base = f"{id_stamp()}-{claim}"
    candidate = base
    index = 2
    while (directory / f"{candidate}.json").exists():
        candidate = f"{base}-{index}"
        index += 1
    return candidate


def cmd_write(root: Path, args: argparse.Namespace) -> int:
    if args.from_json:
        try:
            doc = _read_draft(args.from_json)
        except ValueError as exc:
            print(f"[FAIL] {exc}", file=sys.stderr)
            return 1
        if not isinstance(doc, dict):
            print("[FAIL] 草稿必须是 JSON object", file=sys.stderr)
            return 1
    else:
        doc = _build_from_args(args)

    claim = doc.get("claim")
    if claim not in CLAIMS:
        print(f"[FAIL] claim 非法：{claim!r}（允许：{', '.join(CLAIMS)}）", file=sys.stderr)
        return 1
    warnings: list[str] = []

    # 写方可靠性字段：无论来自参数还是草稿，都由 writer 重新生成（防止手填/复制旧值）。
    doc["schemaVersion"] = SCHEMA_VERSION
    try:
        doc["git"] = {"commit": git_short_commit(root), "dirty": git_dirty(root)}
    except RuntimeError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1
    if not doc.get("createdAt"):
        doc["createdAt"] = now_utc()
    if not doc.get("verifier"):
        doc["verifier"] = VERIFIER

    result = doc.setdefault("result", {})
    if not isinstance(result, dict):
        print("[FAIL] result 必须是 object", file=sys.stderr)
        return 1
    for key in ("xcresultPath", "metricsPath"):
        if key in result and result[key] is not None:
            portable, warning = portable_path(root, str(result[key]))
            result[key] = portable
            if warning:
                warnings.append(warning)
    if "verdict" not in doc or not doc["verdict"]:
        doc["verdict"] = _derive_verdict(result)

    directory = evidence_dir(root)
    directory.mkdir(parents=True, exist_ok=True)
    doc["id"] = _next_id(directory, claim)
    doc["createdAt"] = doc.get("createdAt") or now_utc()

    schema, schema_errors = load_schema_for(root)
    if schema is None:
        for error in schema_errors:
            print(f"[FAIL] {error}", file=sys.stderr)
        return 1
    errors = validate_document(doc, schema)
    if not errors:
        target = directory / f"{doc['id']}.json"
        errors = semantic_errors(doc, target)
    if errors:
        print(f"[FAIL] evidence 未通过 schema 校验（未写入）：", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    target = directory / f"{doc['id']}.json"
    target.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for warning in warnings:
        print(f"[WARN] {warning}", file=sys.stderr)
    try:
        print(target.relative_to(root).as_posix())
    except ValueError:  # pragma: no cover - root 外不常见
        print(target.as_posix())
    return 0


# ── CLI ────────────────────────────────────────────────────────────────────
def _add_root_option(parser: argparse.ArgumentParser) -> None:
    """子命令也接受 --root（兼容 `write ... --root X` 写法）；未显式给出时不覆盖全局值。"""
    parser.add_argument(
        "--root",
        type=Path,
        default=argparse.SUPPRESS,
        help="仓库根（也可写在子命令前；默认脚本上级目录）",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="证据链工具：ls / show / validate / write（默认 ls + validate）",
    )
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="仓库根（默认脚本上级目录）")
    sub = parser.add_subparsers(dest="command")

    ls = sub.add_parser("ls", help="列出 evidence")
    _add_root_option(ls)
    ls.add_argument("--claim", help="只列指定 claim")
    ls.add_argument("--json", action="store_true", help="输出 JSON 数组")

    show = sub.add_parser("show", help="查看单条 evidence（id 或路径）")
    _add_root_option(show)
    show.add_argument("target")

    validate = sub.add_parser("validate", help="校验 .apm/evidence/*.json（schema + 语义）")
    _add_root_option(validate)
    validate.set_defaults(command="validate")

    check = sub.add_parser("check", help="validate 的别名")
    _add_root_option(check)
    check.set_defaults(command="validate")

    write = sub.add_parser("write", help="写入一条 evidence")
    _add_root_option(write)
    write.add_argument("--from-json", help="草稿 JSON 路径；- 表示 stdin")
    write.add_argument("--claim", choices=CLAIMS)
    write.add_argument("--status", choices=STATUSES, default="SUCCEEDED")
    write.add_argument("--passed", type=int, default=0)
    write.add_argument("--failed", type=int, default=0)
    write.add_argument("--skipped", type=int, default=0)
    write.add_argument("--duration", type=float, default=0.0)
    write.add_argument("--xcode", default=None)
    write.add_argument("--simulator", default=None)
    write.add_argument("--device", default=None)
    write.add_argument("--build", default=None)
    write.add_argument("--host", default=None)
    write.add_argument("--xcresult", default=None)
    write.add_argument("--metrics", default=None)
    write.add_argument("--command", dest="evidence_command", default="")
    write.add_argument("--verdict", choices=VERDICTS, default=None)
    write.add_argument("--notes", default=None)
    write.add_argument("--session-id", default=None)
    return parser


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command in ("ls", "show", "write"):
        pass
    elif args.command is None:
        # 无子命令 = 便利入口：列证据 + 校验
        args.command = "list-and-validate"
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = Path(args.root).resolve()
    if args.command == "ls":
        return cmd_ls(root, args)
    if args.command == "show":
        return cmd_show(root, args)
    if args.command == "validate":
        return cmd_validate(root, args)
    if args.command == "write":
        return cmd_write(root, args)
    # 无子命令：ls + validate
    rc = cmd_ls(root, argparse.Namespace(claim=None, json=False))
    return cmd_validate(root, argparse.Namespace()) or rc


if __name__ == "__main__":
    sys.exit(main())
