#!/usr/bin/env python3
"""harness-kit 通用证据工具（标准库；无第三方依赖；不联网）。

用法（脚本被 init 复制到目标项目 tools/ 下）：
  python3 tools/evidence.py ls [--claim NAME] [--root PATH]
  python3 tools/evidence.py validate [--root PATH]
  python3 tools/evidence.py write --claim NAME --from-json <FILE|-> [--root PATH]
  python3 tools/evidence.py write --from-json <FILE|-> [--root PATH]   # claim 取自 JSON

根目录 = 脚本上级目录（tools/ 的父目录）；--root 可覆盖。配置唯一来源
<root>/harness/config.json；证据格式由 <root>/harness/evidence/schema.json 定义
（脚本内置标准库手写子集校验，不引入 jsonschema）。

语义约定：
  - 证据文件名为 `<id>.json`，id 形如 `20260101T000000Z-<claim>`；`id` 必须等于
    文件名 stem；`claim` 必须已声明在 config.claims。
  - `write` 自动填 id / createdAt / git.commit / git.dirty / verifier（覆盖输入里的
    同名字段）；工作树必须 clean，否则拒绝写入（dirty 证据不可判 PASS）。
  - `write` 必须用 `--from-json` 提供 command / result / environment / verdict 等
    业务字段；不支持空文档静默补全。
  - `validate` 只扫描文件名符合证据 id 的文件；`TEMPLATE.json` / `schema.json` /
    README 等非证据文件会被跳过并计数。额外语义：verdict=PASS 时 git.dirty 必须为
    false。

退出码：0 = 成功/全部有效；1 = 校验失败 / 拒绝写入 / 配置不可用；2 = 用法错误。
"""
from __future__ import annotations

import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

CONFIG_REL = Path("harness") / "config.json"
EVIDENCE_ID_RE = re.compile(r"^\d{8}T\d{6}Z-[a-z0-9-]+$")
CREATED_AT_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
COMMIT_RE = re.compile(r"^[0-9a-f]{7,40}$")
VERDICTS = ("PASS", "FAIL", "UNVERIFIED")


# ── 输出与 CLI ────────────────────────────────────────────────────────────
def fail(message: str, code: int = 1) -> None:
    print(f"[FAIL] {message}")
    raise SystemExit(code)


def info(message: str) -> None:
    print(f"[INFO] {message}")


def display(path: Path) -> str:
    return str(path)


def parse_cli(argv: list[str]) -> tuple[Path, list[str]]:
    args = list(argv)
    root: Path | None = None
    if "--root" in args:
        index = args.index("--root")
        if index + 1 >= len(args):
            fail("--root 需要一个目录参数", 2)
        root = Path(args[index + 1]).expanduser().resolve()
        del args[index:index + 2]
    if root is None:
        root = Path(__file__).resolve().parent.parent
    return root, args


def pop_option(args: list[str], name: str) -> str | None:
    """取出单值选项（支持 `--name value` 与 `--name=value`）。"""
    for index, item in enumerate(list(args)):
        if item == name:
            if index + 1 >= len(args):
                fail(f"{name} 需要一个参数", 2)
            value = args[index + 1]
            del args[index:index + 2]
            return value
        if item.startswith(name + "="):
            value = item.split("=", 1)[1]
            del args[index]
            return value
    return None


# ── 配置 ─────────────────────────────────────────────────────────────────
def load_config(root: Path) -> dict:
    path = root / CONFIG_REL
    if not path.is_file():
        fail(f"缺少配置：{display(path)}（先运行 harness-init 生成 harness/config.json）")
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"配置无法解析：{display(path)}：{exc}")
    if not isinstance(config, dict):
        fail(f"配置必须是 JSON object：{display(path)}")
    problems: list[str] = []
    for key in ("kitVersion", "project", "paths", "commands", "claims"):
        if key not in config:
            problems.append(f"缺少字段 {key}")
    paths = config.get("paths") if isinstance(config.get("paths"), dict) else {}
    for key in ("docs", "references", "harness", "plans", "evidence", "tools"):
        if key not in paths:
            problems.append(f"缺少字段 paths.{key}")
    commands = config.get("commands") if isinstance(config.get("commands"), dict) else {}
    if not isinstance(commands.get("test"), str) or not commands.get("test", "").strip():
        problems.append("缺少字段 commands.test")
    claims = config.get("claims")
    if not isinstance(claims, list) or not claims:
        problems.append("缺少非空字段 claims")
    else:
        for index, claim in enumerate(claims):
            if not isinstance(claim, dict):
                problems.append(f"claims[{index}] 必须是 object")
                continue
            if not isinstance(claim.get("name"), str) or not claim.get("name"):
                problems.append(f"claims[{index}].name 缺失")
            if claim.get("type") not in ("test-count", "static"):
                problems.append(f"claims[{index}].type 必须是 test-count|static")
    for key, value in paths.items():
        if isinstance(value, list):  # 如 paths.rootDocs
            if not all(isinstance(item, str) and item for item in value):
                problems.append(f"paths.{key} 列表项必须是非空字符串")
            continue
        if not isinstance(value, str) or not value:
            problems.append(f"paths.{key} 必须是非空字符串或字符串列表")
            continue
        candidate = Path(value)
        if candidate.is_absolute() or ".." in candidate.parts:
            problems.append(f"paths.{key} 必须是仓库相对路径且不含 ..：{value!r}")
    if problems:
        fail("配置不可用：\n  - " + "\n  - ".join(problems))
    return config


def config_path(root: Path, config: dict, key: str) -> Path:
    return root / config["paths"][key]


def claim_names(config: dict) -> list[str]:
    return [
        claim["name"]
        for claim in config.get("claims", [])
        if isinstance(claim, dict) and claim.get("name")
    ]


# ── git ──────────────────────────────────────────────────────────────────
def git(root: Path, args: list[str]) -> tuple[int, str, str]:
    try:
        result = subprocess.run(
            ["git", *args], cwd=str(root), capture_output=True, text=True, timeout=30
        )
        return result.returncode, result.stdout, result.stderr
    except (OSError, subprocess.TimeoutExpired) as exc:  # pragma: no cover - 防御
        return 127, "", str(exc)


def git_is_repo(root: Path) -> bool:
    code, out, _ = git(root, ["rev-parse", "--is-inside-work-tree"])
    return code == 0 and out.strip() == "true"


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


def git_sha(root: Path, rev: str) -> str | None:
    code, out, _ = git(root, ["rev-parse", "--verify", f"{rev}^{{commit}}"])
    return out.strip() if code == 0 and out.strip() else None


# ── JSON Schema 子集校验（手写，无第三方） ───────────────────────────────
def type_matches(value: object, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    return True


def validate_schema(instance: object, schema: object, path: str = "$") -> list[str]:
    """JSON Schema draft-07 的常用子集：type/required/properties/items/enum/const/
    pattern/minLength/minItems/minimum/additionalProperties=false。未知关键字忽略。"""
    issues: list[str] = []
    if not isinstance(schema, dict):
        return issues
    if "const" in schema and instance != schema["const"]:
        issues.append(f"{path}: 值应为 {schema['const']!r}")
    expected = schema.get("type")
    if expected is not None:
        types = expected if isinstance(expected, list) else [expected]
        if not any(type_matches(instance, item) for item in types if isinstance(item, str)):
            return [f"{path}: 类型应为 {'/'.join(str(item) for item in types)}"]
    if "enum" in schema and instance not in schema["enum"]:
        issues.append(f"{path}: 值不在枚举 {schema['enum']!r} 内")
    if isinstance(instance, str):
        if "pattern" in schema and isinstance(schema["pattern"], str):
            if re.search(schema["pattern"], instance) is None:
                issues.append(f"{path}: 不符合 pattern {schema['pattern']!r}")
        if "minLength" in schema and len(instance) < int(schema["minLength"]):
            issues.append(f"{path}: 长度小于 {schema['minLength']}")
    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            issues.append(f"{path}: 小于最小值 {schema['minimum']}")
    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < int(schema["minItems"]):
            issues.append(f"{path}: 元素数小于 {schema['minItems']}")
        items = schema.get("items")
        if isinstance(items, dict):
            for index, item in enumerate(instance):
                issues.extend(validate_schema(item, items, f"{path}[{index}]"))
    if isinstance(instance, dict):
        for key in schema.get("required", []) or []:
            if key not in instance:
                issues.append(f"{path}: 缺少必需字段 {key}")
        properties = schema.get("properties") or {}
        if isinstance(properties, dict):
            for key, sub_schema in properties.items():
                if key in instance:
                    issues.extend(validate_schema(instance[key], sub_schema, f"{path}.{key}"))
        if schema.get("additionalProperties") is False and isinstance(properties, dict):
            for key in instance:
                if key not in properties:
                    issues.append(f"{path}: 不允许的字段 {key}")
    return issues


# ── 证据文件 ─────────────────────────────────────────────────────────────
def evidence_dir(root: Path, config: dict) -> Path:
    return config_path(root, config, "evidence")


def evidence_rel(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return display(path)


def load_schema(root: Path, config: dict) -> dict:
    path = evidence_dir(root, config) / "schema.json"
    if not path.is_file():
        fail(f"缺少证据 schema：{display(path)}（先运行 harness-init 生成）")
    try:
        schema = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"证据 schema 无法解析：{display(path)}：{exc}")
    if not isinstance(schema, dict):
        fail(f"证据 schema 必须是 JSON object：{display(path)}")
    return schema


def evidence_paths(root: Path, config: dict) -> list[Path]:
    directory = evidence_dir(root, config)
    if not directory.is_dir():
        fail(f"证据目录不存在：{display(directory)}（先运行 harness-init 生成）")
    return sorted(
        path for path in directory.glob("*.json") if EVIDENCE_ID_RE.fullmatch(path.stem)
    )


def load_json_file(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(str(exc)) from exc


def semantic_issues(config: dict, evidence_id: str, doc: dict) -> list[str]:
    """schema 之外的跨字段语义校验。"""
    issues: list[str] = []
    if doc.get("id") != evidence_id:
        issues.append(f"id 与文件名不一致：{doc.get('id')!r} != {evidence_id!r}")
    claim = doc.get("claim")
    if claim not in claim_names(config):
        issues.append(f"claim 未在 config.claims 中声明：{claim!r}")
    created = doc.get("createdAt")
    if not isinstance(created, str) or CREATED_AT_RE.fullmatch(created) is None:
        issues.append(f"createdAt 需为 UTC RFC3339（YYYY-MM-DDTHH:MM:SSZ）：{created!r}")
    git_meta = doc.get("git")
    if not isinstance(git_meta, dict):
        issues.append("git 必须是 object（含 commit/dirty）")
    else:
        commit = git_meta.get("commit")
        if not isinstance(commit, str) or COMMIT_RE.fullmatch(commit) is None:
            issues.append(f"git.commit 需为 7–40 位短 hash：{commit!r}")
        if not isinstance(git_meta.get("dirty"), bool):
            issues.append("git.dirty 必须是 boolean")
        if doc.get("verdict") == "PASS" and git_meta.get("dirty") is not False:
            issues.append("verdict=PASS 但 git.dirty 非 false（dirty 证据不可判 PASS）")
    if doc.get("verdict") not in VERDICTS:
        issues.append(f"verdict 必须是 {'/'.join(VERDICTS)}：{doc.get('verdict')!r}")
    return issues


def validate_doc(root: Path, config: dict, schema: dict, evidence_id: str, doc: dict) -> list[str]:
    return validate_schema(doc, schema) + semantic_issues(config, evidence_id, doc)


# ── 命令：ls / validate / write ──────────────────────────────────────────
def cmd_ls(root: Path, config: dict, claim_filter: str | None) -> int:
    names = claim_names(config)
    if claim_filter and claim_filter not in names:
        fail(f"--claim 不在 config.claims：{claim_filter!r}（可用：{', '.join(names)}）")
    rows: list[tuple[str, str, str, str]] = []
    for path in evidence_paths(root, config):
        try:
            doc = load_json_file(path)
        except ValueError:
            rows.append((path.stem, "?", "?", "（无法解析）"))
            continue
        if not isinstance(doc, dict):
            rows.append((path.stem, "?", "?", "（非 object）"))
            continue
        claim = str(doc.get("claim") or "?")
        if claim_filter and claim != claim_filter:
            continue
        rows.append((path.stem, str(doc.get("verdict") or "?"), claim, str(doc.get("createdAt") or "?")))
    print(f"证据目录：{evidence_rel(root, evidence_dir(root, config))}（{len(rows)} 条）")
    for evidence_id, verdict, claim, created in rows:
        print(f"{evidence_id}\t{verdict}\t{claim}\t{created}")
    return 0


def cmd_validate(root: Path, config: dict) -> int:
    schema = load_schema(root, config)
    directory = evidence_dir(root, config)
    all_files = sorted(directory.glob("*.json")) if directory.is_dir() else []
    if not directory.is_dir():
        fail(f"证据目录不存在：{display(directory)}")
    evidence_files = [path for path in all_files if EVIDENCE_ID_RE.fullmatch(path.stem)]
    skipped = [path.name for path in all_files if path not in evidence_files]
    print(f"校验 {evidence_rel(root, directory)}/*.json（跳过 {len(skipped)} 个非证据文件）")
    if skipped:
        info("跳过：" + ", ".join(skipped[:5]) + ("…" if len(skipped) > 5 else ""))
    errors = 0
    for path in evidence_files:
        try:
            doc = load_json_file(path)
        except ValueError as exc:
            print(f"[FAIL] {path.name}: JSON 无法解析：{exc}")
            errors += 1
            continue
        if not isinstance(doc, dict):
            print(f"[FAIL] {path.name}: 顶层必须是 object")
            errors += 1
            continue
        issues = validate_doc(root, config, schema, path.stem, doc)
        if issues:
            print(f"[FAIL] {path.name}")
            for issue in issues:
                print(f"       - {issue}")
            errors += 1
        else:
            print(f"[OK]   {path.name}  verdict={doc.get('verdict')}  claim={doc.get('claim')}")
    verdict = "PASS" if errors == 0 else "FAIL"
    print(f"结论：{verdict}（{len(evidence_files)} 个证据，{errors} error / 0 warn）")
    return 0 if errors == 0 else 1


def read_payload(source: str) -> dict:
    if source == "-":
        raw = sys.stdin.read()
        origin = "stdin"
    else:
        path = Path(source)
        if not path.is_file():
            fail(f"--from-json 文件不存在：{source}")
        raw = path.read_text(encoding="utf-8")
        origin = source
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        fail(f"--from-json 无法解析（{origin}）：{exc}")
    if not isinstance(payload, dict):
        fail("--from-json 顶层必须是 JSON object")
    return payload


def cmd_write(root: Path, config: dict, claim_arg: str | None, source: str | None) -> int:
    if not source:
        fail("write 需要 --from-json <FILE|->（提供 command/result/environment/verdict 等字段）")
    payload = read_payload(source)
    claim = claim_arg or payload.get("claim")
    if not claim:
        fail("缺少 claim：用 --claim NAME 或在 JSON 内提供 claim")
    names = claim_names(config)
    if claim not in names:
        fail(f"claim 不在 config.claims：{claim!r}（可用：{', '.join(names)}）")
    if payload.get("claim") and payload["claim"] != claim:
        fail(f"--claim 与 JSON 内 claim 不一致：{claim!r} != {payload['claim']!r}")
    if not git_is_repo(root):
        fail("不是 git 仓库：无法自动填 git.commit/git.dirty")
    changed = git_status_paths(root)
    if changed is None:
        fail("读取 git status 失败")
    if changed:
        preview = "、".join(sorted(changed)[:5]) + ("…" if len(changed) > 5 else "")
        fail(f"工作树不 clean（{len(changed)} 个改动：{preview}）；先提交/清理后再写证据")
    commit = git_sha(root, "HEAD")
    if commit is None:
        fail("无法解析 HEAD 提交（仓库还没有 commit？）")
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    evidence_id = f"{now.strftime('%Y%m%dT%H%M%SZ')}-{claim}"
    target = evidence_dir(root, config) / f"{evidence_id}.json"
    if target.exists():
        fail(f"证据已存在：{evidence_rel(root, target)}（同一秒重复写入；稍后重试）")
    doc = dict(payload)
    doc["id"] = evidence_id
    doc["claim"] = claim
    doc["createdAt"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    doc["git"] = {"commit": commit[:12], "dirty": False}
    doc["verifier"] = f"tools/evidence.py@{config.get('kitVersion', 'unknown')}"
    schema = load_schema(root, config)
    issues = validate_doc(root, config, schema, evidence_id, doc)
    if issues:
        fail("证据不符合 schema/语义：\n  - " + "\n  - ".join(issues))
    evidence_dir(root, config).mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[OK] 已写入 {evidence_rel(root, target)}（id={evidence_id}，verdict={doc.get('verdict')}）")
    return 0


# ── main ─────────────────────────────────────────────────────────────────
def main(argv: list[str]) -> int:
    root, args = parse_cli(argv)
    claim_arg = pop_option(args, "--claim")
    source = pop_option(args, "--from-json")
    if not args or args[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0 if args else 2
    command = args[0]
    rest = args[1:]
    config = load_config(root)
    if command == "ls":
        if rest:
            fail(f"用法：evidence.py ls [--claim NAME]（未知参数：{' '.join(rest)}）", 2)
        return cmd_ls(root, config, claim_arg)
    if command == "validate":
        if rest:
            fail(f"用法：evidence.py validate（未知参数：{' '.join(rest)}）", 2)
        return cmd_validate(root, config)
    if command == "write":
        if rest:
            fail(f"用法：evidence.py write --claim NAME --from-json <FILE|->（未知参数：{' '.join(rest)}）", 2)
        return cmd_write(root, config, claim_arg, source)
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
