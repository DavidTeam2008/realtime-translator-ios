#!/usr/bin/env python3
"""Host-owned evidence chain adapter for the pinned ai-delivery-toolchain.

Verifies the vendored pin, runs a single xcresult test invocation, converts it
to strict JUnit plus a run manifest, and checks new evidence against both.
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import importlib
import importlib.util
import json
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

VENDOR_REL = Path("tools/vendor/ai_delivery_toolchain")
PIN_REL = VENDOR_REL / "PIN.json"
EVIDENCE_ID_RE = re.compile(r"^\d{8}T\d{6}Z-[a-z0-9-]+$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
MAX_JUNIT_BYTES = 5 * 1024 * 1024
STATIC_TARGET_KEYS = ("project", "scheme", "destination", "derivedDataPath", "onlyTesting")


class EvidenceChainError(RuntimeError):
    pass


def display(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise EvidenceChainError(f"无法读取 {path}：{exc}") from exc
    except json.JSONDecodeError as exc:
        raise EvidenceChainError(f"{path} 不是合法 JSON：{exc}") from exc
    if not isinstance(document, dict):
        raise EvidenceChainError(f"{path} 顶层必须是 object")
    return document


def load_pin(root: Path) -> dict:
    vendor = root / VENDOR_REL
    pin_path = root / PIN_REL
    pin = load_json(pin_path)
    if pin.get("schemaVersion") != 1:
        raise EvidenceChainError("PIN.schemaVersion 必须是 1")
    if pin.get("name") != "ai-delivery-toolchain":
        raise EvidenceChainError("PIN.name 必须是 ai-delivery-toolchain")
    if not isinstance(pin.get("version"), str) or not pin["version"]:
        raise EvidenceChainError("PIN.version 缺失")
    if not isinstance(pin.get("tag"), str) or not pin["tag"]:
        raise EvidenceChainError("PIN.tag 缺失")
    for key in ("tagCommit", "sourceCommit"):
        value = pin.get(key)
        if not isinstance(value, str) or not re.fullmatch(r"^[0-9a-f]{40}$", value):
            raise EvidenceChainError(f"PIN.{key} 必须是 40 位 commit SHA")
    files = pin.get("files")
    if not isinstance(files, dict) or not files:
        raise EvidenceChainError("PIN.files 必须是非空 object")
    actual = {path.name for path in vendor.glob("*.py")}
    expected = set(files)
    if actual != expected:
        raise EvidenceChainError(
            f"vendored 文件集合与 PIN 不一致：多 {sorted(actual - expected)} / 缺 {sorted(expected - actual)}"
        )
    for name, expected_sha in sorted(files.items()):
        if not isinstance(expected_sha, str) or not SHA256_RE.fullmatch(expected_sha):
            raise EvidenceChainError(f"PIN.files[{name}] 必须是 64 位小写 hex")
        candidate = vendor / name
        if candidate.is_symlink():
            raise EvidenceChainError(f"vendored 文件不能是符号链接：{candidate}")
        if not candidate.is_file():
            raise EvidenceChainError(f"vendored 文件不存在：{candidate}")
        actual_sha = sha256_file(candidate)
        if actual_sha != expected_sha:
            raise EvidenceChainError(
                f"vendored 文件哈希不一致：{name}（PIN {expected_sha} / 实际 {actual_sha}）"
            )
    return pin


def load_toolchain(root: Path) -> SimpleNamespace:
    load_pin(root)
    vendor = (root / "tools" / "vendor").resolve()
    package_dir = vendor / "ai_delivery_toolchain"
    sys.path.insert(0, str(vendor))
    for name in [item for item in sys.modules if item == "ai_delivery_toolchain" or item.startswith("ai_delivery_toolchain.")]:
        del sys.modules[name]
    package = importlib.import_module("ai_delivery_toolchain")
    package_file = Path(package.__file__).resolve()
    try:
        package_file.relative_to(package_dir)
    except ValueError:
        raise EvidenceChainError(f"导入的 ai_delivery_toolchain 不在 vendored 目录：{package_file}") from None
    return SimpleNamespace(
        package=package,
        junit=importlib.import_module("ai_delivery_toolchain.junit_strict"),
        manifest=importlib.import_module("ai_delivery_toolchain.manifest"),
        xcresult=importlib.import_module("ai_delivery_toolchain.xcresult"),
    )


def load_config(root: Path) -> dict:
    path = root / "harness" / "config.json"
    config = load_json(path)
    paths = config.get("paths")
    if not isinstance(paths, dict) or not isinstance(paths.get("evidence"), str):
        raise EvidenceChainError("harness/config.json 缺少 paths.evidence")
    claims = config.get("claims")
    if not isinstance(claims, list):
        raise EvidenceChainError("harness/config.json 缺少 claims")
    return config


def claim_config(config: dict, name: str) -> dict | None:
    return next(
        (
            claim
            for claim in config.get("claims", [])
            if isinstance(claim, dict) and claim.get("name") == name
        ),
        None,
    )


def repo_path(root: Path, rel: str, label: str) -> Path:
    candidate = Path(rel)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise EvidenceChainError(f"{label} 必须是仓库相对路径且不含 ..：{rel!r}")
    resolved = (root / candidate).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError:
        raise EvidenceChainError(f"{label} 解析后不在仓库内：{rel!r}") from None
    return resolved


def current_evidence(root: Path, config: dict) -> list[Path]:
    directory = root / config["paths"]["evidence"]
    if not directory.is_dir():
        return []
    current: list[Path] = []
    for path in sorted(directory.rglob("*.json")):
        if not EVIDENCE_ID_RE.fullmatch(path.stem):
            continue
        if "_archive" in path.relative_to(directory).parts:
            continue
        current.append(path)
    return current


def expected_static_target(claim: dict) -> dict:
    target = claim.get("expectedTarget")
    if not isinstance(target, dict):
        raise EvidenceChainError(f"claim {claim.get('name')!r} 缺少 expectedTarget")
    unknown = sorted(set(target) - set(STATIC_TARGET_KEYS))
    if unknown:
        raise EvidenceChainError(f"claim {claim.get('name')!r}.expectedTarget 含未知字段：{', '.join(unknown)}")
    normalized: dict[str, str] = {}
    for key in STATIC_TARGET_KEYS:
        value = target.get(key)
        if not isinstance(value, str) or not value.strip():
            raise EvidenceChainError(f"claim {claim.get('name')!r}.expectedTarget.{key} 缺失")
        normalized[key] = value.strip()
    return normalized


def result_bundle_root(claim: dict) -> Path:
    value = claim.get("resultBundleRoot")
    if not isinstance(value, str) or not value.strip():
        raise EvidenceChainError(f"claim {claim.get('name')!r} 缺少 resultBundleRoot")
    root = Path(value).expanduser()
    if not root.is_absolute():
        raise EvidenceChainError(f"claim {claim.get('name')!r}.resultBundleRoot 必须是绝对路径")
    return root


def check_manifest_evidence(
    root: Path,
    config: dict,
    claim: dict,
    evidence_id: str,
    doc: dict,
    modules: SimpleNamespace,
    seen_run_ids: dict[str, str],
) -> list[str]:
    label = f"CLAIM {evidence_id}"
    result = doc.get("result") if isinstance(doc.get("result"), dict) else {}
    manifest_rel = result.get("manifest")
    junit_rel = result.get("junit")
    errors: list[str] = []
    if not isinstance(manifest_rel, str) or not manifest_rel.strip():
        return [f"{label}: 缺 result.manifest（新链 PASS 必须绑定单次运行 manifest）"]
    if not isinstance(junit_rel, str) or not junit_rel.strip():
        return [f"{label}: 缺 result.junit"]
    artifacts = result.get("artifacts")
    if not isinstance(artifacts, list) or not all(isinstance(item, str) for item in artifacts):
        return [f"{label}: result.artifacts 必须是字符串数组"]
    if manifest_rel not in artifacts or junit_rel not in artifacts:
        errors.append(f"{label}: result.artifacts 必须同时包含 JUnit 与 manifest")
    try:
        manifest_path = repo_path(root, manifest_rel, "result.manifest")
        junit_path = repo_path(root, junit_rel, "result.junit")
    except EvidenceChainError as exc:
        return [f"{label}: {exc}"]
    if not manifest_path.is_file():
        return [f"{label}: manifest 不存在：{manifest_rel}"]
    if not junit_path.is_file():
        return [f"{label}: JUnit 不存在：{junit_rel}"]
    if manifest_path.parent != junit_path.parent:
        errors.append(f"{label}: JUnit 与 manifest 必须在同一目录")
    artifact_root = (root / config["paths"]["evidence"] / "artifacts").resolve()
    for rel, path in ((manifest_rel, manifest_path), (junit_rel, junit_path)):
        try:
            path.resolve().relative_to(artifact_root)
        except ValueError:
            errors.append(f"{label}: {rel} 必须在 {display(root, artifact_root)} 下")
    size = junit_path.stat().st_size
    if size > MAX_JUNIT_BYTES:
        return errors + [f"{label}: JUnit 超过 5 MiB（{size} bytes）"]
    try:
        manifest = modules.manifest.load_manifest(manifest_path)
    except modules.manifest.ManifestError as exc:
        return errors + [f"{label}: {exc}"]

    run_id = manifest.get("runId")
    if not isinstance(run_id, str) or not run_id.strip():
        return errors + [f"{label}: manifest.runId 缺失"]
    if run_id in seen_run_ids and seen_run_ids[run_id] != evidence_id:
        errors.append(f"{label}: runId 重复（已被 {seen_run_ids[run_id]} 使用）")
    else:
        seen_run_ids[run_id] = evidence_id

    try:
        target = modules.manifest._validate_target(manifest.get("target"))
        expected = expected_static_target(claim)
    except (modules.manifest.ManifestError, EvidenceChainError) as exc:
        return errors + [f"{label}: {exc}"]
    for key, value in expected.items():
        if target.get(key) != value:
            errors.append(f"{label}: manifest.target.{key} 不一致：{target.get(key)!r} != {value!r}")
    try:
        bundle_root = result_bundle_root(claim)
    except EvidenceChainError as exc:
        return errors + [f"{label}: {exc}"]
    bundle_path = Path(target["resultBundlePath"])
    if not bundle_path.is_absolute():
        errors.append(f"{label}: target.resultBundlePath 必须是绝对路径")
    if bundle_path.parent != (bundle_root / run_id):
        errors.append(
            f"{label}: target.resultBundlePath 必须位于 {bundle_root / run_id}（单次运行唯一路径）"
        )
    xcresult = manifest.get("xcresult") if isinstance(manifest.get("xcresult"), dict) else {}
    if xcresult.get("name") != bundle_path.name:
        errors.append(f"{label}: manifest.xcresult.name 与 resultBundlePath 文件名不一致")

    junit_bytes = junit_path.read_bytes()
    try:
        modules.manifest.verify_manifest(
            manifest,
            junit_bytes,
            expected_claim=claim["name"],
            expected_target=target,
            junit_name=junit_path.name,
        )
    except modules.manifest.ManifestError as exc:
        return errors + [f"{label}: {exc}"]

    counts = result.get("passed"), result.get("failed"), result.get("skipped")
    if not all(isinstance(value, int) and not isinstance(value, bool) for value in counts):
        return errors + [f"{label}: result.passed/failed/skipped 必须是整数"]
    junit_counts = manifest.get("junit") if isinstance(manifest.get("junit"), dict) else {}
    expected_counts = (junit_counts.get("passed"), junit_counts.get("failed"), junit_counts.get("skipped"))
    if counts != expected_counts:
        errors.append(f"{label}: 证据 counts {counts} 与 manifest {expected_counts} 不一致")

    evidence_env = doc.get("environment") if isinstance(doc.get("environment"), dict) else {}
    manifest_env = manifest.get("environment") if isinstance(manifest.get("environment"), dict) else {}
    if not isinstance(evidence_env.get("id"), str) or not evidence_env["id"].strip():
        errors.append(f"{label}: 证据 environment.id 缺失")
    elif evidence_env["id"] != manifest_env.get("id"):
        errors.append(
            f"{label}: environment.id 不一致：{evidence_env['id']!r} != {manifest_env.get('id')!r}"
        )
    command = doc.get("command")
    if not isinstance(command, str) or "xcodebuild test" not in command:
        errors.append(f"{label}: command 必须记录 xcodebuild test")
    settings = manifest.get("command", {}).get("buildSettings") if isinstance(manifest.get("command"), dict) else None
    try:
        _validate_build_settings(settings)
    except EvidenceChainError as exc:
        errors.append(f"{label}: {exc}")
    else:
        command_entries = _command_build_entries(command) if isinstance(command, str) else []
        if command_entries:
            if settings is None:
                errors.append(f"{label}: manifest 缺少 command.buildSettings（不得只把构建参数留在 evidence.command）")
            elif settings.get("entries") != command_entries:
                errors.append(f"{label}: manifest.command.buildSettings 与 evidence.command 不一致")
    return errors


def check_evidence(
    root: Path,
    config: dict | None = None,
    modules: SimpleNamespace | None = None,
    *,
    check_pin: bool = True,
    verbose: bool = False,
) -> list[str]:
    config = config or load_config(root)
    if modules is None:
        modules = load_toolchain(root) if check_pin else None
    if modules is None:
        raise EvidenceChainError("未提供 toolchain modules")
    claims = [
        claim
        for claim in config.get("claims", [])
        if isinstance(claim, dict) and claim.get("requireManifest") is True
    ]
    if not claims:
        return []
    errors: list[str] = []
    for claim in claims:
        try:
            expected_static_target(claim)
            result_bundle_root(claim)
        except EvidenceChainError as exc:
            errors.append(f"CLAIM {claim.get('name')}: {exc}")
    seen_run_ids: dict[str, str] = {}
    for path in current_evidence(root, config):
        doc = load_json(path)
        if doc.get("verdict") != "PASS":
            continue
        claim_name = doc.get("claim")
        claim = claim_config(config, claim_name) if isinstance(claim_name, str) else None
        if claim is None or claim.get("requireManifest") is not True:
            continue
        errors.extend(
            check_manifest_evidence(root, config, claim, path.stem, doc, modules, seen_run_ids)
        )
    if verbose and not errors:
        return [f"evidence chain PASS（{len(claims)} 个 claim 要求 manifest）"]
    return errors


def cmd_check_pin(root: Path) -> int:
    pin = load_pin(root)
    load_toolchain(root)
    print(f"PASS ai-delivery-toolchain {pin['version']} ({pin['tag']} → {pin['tagCommit']})")
    return 0


def cmd_check_evidence(root: Path) -> int:
    errors = check_evidence(root)
    for item in errors:
        print(item)
    if errors:
        return 1
    print("PASS evidence chain（manifest 绑定与严格重算）")
    return 0


def _detect_environment() -> dict[str, str]:
    def run(command: list[str], label: str) -> str:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=60)
        if completed.returncode != 0:
            raise EvidenceChainError(f"无法读取 {label}（exit {completed.returncode}）")
        lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
        if not lines:
            raise EvidenceChainError(f"读取 {label} 没有输出")
        return " / ".join(lines[:2])

    host = platform.mac_ver()[0]
    if not host:
        raise EvidenceChainError("无法识别 macOS 版本")
    return {
        "host": f"macOS {host}",
        "xcode": run(["xcodebuild", "-version"], "Xcode 版本"),
        "xcresulttool": run(["xcrun", "xcresulttool", "version"], "xcresulttool 版本"),
    }


def _parse_environment(pairs: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for pair in pairs:
        if "=" not in pair:
            raise EvidenceChainError(f"--environment 需要 KEY=VALUE：{pair!r}")
        key, value = pair.split("=", 1)
        key = key.strip()
        if key != "id":
            raise EvidenceChainError(f"--environment 当前仅支持 id：{key!r}")
        if not value.strip():
            raise EvidenceChainError("--environment id 不能为空")
        values[key] = value.strip()
    return values


def _signing_arguments(claim: dict) -> list[str]:
    if claim.get("requiresSigning") is not True:
        return []
    team = (os.environ.get("APM_TEAM") or os.environ.get("DEVELOPMENT_TEAM") or "").strip()
    if not team:
        raise EvidenceChainError(
            f"claim {claim.get('name')!r} 需要真机签名；请设置 APM_TEAM=<Team ID>"
        )
    return ["-allowProvisioningUpdates", f"DEVELOPMENT_TEAM={team}"]


def _warmup_argv(target: dict, only_testing: str) -> list[str]:
    return [
        "xcodebuild",
        "test",
        "-project",
        target["project"],
        "-scheme",
        target["scheme"],
        "-destination",
        target["destination"],
        "-derivedDataPath",
        target["derivedDataPath"],
        "-only-testing:" + only_testing,
    ]


def _run_xcodebuild(
    root: Path,
    argv: list[str],
    timeout: int,
    extra_argv: list[str] | None = None,
    build_argv: list[str] | None = None,
) -> None:
    extra_argv = extra_argv or []
    build_argv = build_argv or []
    printed = [*argv, *build_argv]
    print("[INFO] " + shlex.join(printed) + ("（含本机签名参数，未写入证据）" if extra_argv else ""))
    try:
        completed = subprocess.run(
            [*argv, *extra_argv, *build_argv],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise EvidenceChainError(f"xcodebuild 超时（{timeout}s）") from None
    except OSError as exc:
        raise EvidenceChainError(f"xcodebuild 无法执行：{exc}") from exc
    if completed.returncode == 0:
        return
    tail = (completed.stdout + "\n" + completed.stderr).strip().splitlines()[-40:]
    for line in tail:
        print(line)
    raise EvidenceChainError(f"xcodebuild 退出 {completed.returncode}；未生成证据")


BUILD_SETTING_ALLOWLIST = ("OTHER_SWIFT_FLAGS", "CODE_SIGNING_ALLOWED")


def _build_settings(build_args: list[str]) -> dict:
    entries: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in build_args:
        if "=" not in item:
            raise EvidenceChainError(f"构建参数必须是 KEY=VALUE：{item!r}")
        key, value = item.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key not in BUILD_SETTING_ALLOWLIST:
            raise EvidenceChainError(f"构建参数不在脱敏 allowlist：{key!r}")
        if key in seen:
            raise EvidenceChainError(f"构建参数重复：{key}")
        if not value or "\n" in value or "\r" in value:
            raise EvidenceChainError(f"构建参数值非法：{key}")
        seen.add(key)
        entries.append({"key": key, "value": value})
    document = {"schemaVersion": 1, "source": "XCODEBUILD_BUILD_ARGS", "entries": entries}
    document["sha256"] = hashlib.sha256(
        "\0".join(f"{item['key']}={item['value']}" for item in entries).encode("utf-8")
    ).hexdigest()
    return document


def _validate_build_settings(document: object) -> None:
    if document is None:
        return
    if not isinstance(document, dict):
        raise EvidenceChainError("manifest.command.buildSettings 必须是 object")
    if document.get("schemaVersion") != 1 or document.get("source") != "XCODEBUILD_BUILD_ARGS":
        raise EvidenceChainError("manifest.command.buildSettings 元数据非法")
    entries = document.get("entries")
    if not isinstance(entries, list):
        raise EvidenceChainError("manifest.command.buildSettings.entries 必须是数组")
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise EvidenceChainError("buildSettings entry 必须是 object")
        key, value = entry.get("key"), entry.get("value")
        if key not in BUILD_SETTING_ALLOWLIST or not isinstance(value, str) or not value:
            raise EvidenceChainError("buildSettings 含未允许或空值项")
        if key in seen:
            raise EvidenceChainError("buildSettings 重复 key")
        seen.add(key)
    expected = hashlib.sha256(
        "\0".join(f"{entry['key']}={entry['value']}" for entry in entries).encode("utf-8")
    ).hexdigest()
    if document.get("sha256") != expected:
        raise EvidenceChainError("manifest.command.buildSettings.sha256 不一致")


def _command_build_entries(command: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for token in shlex.split(command):
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        if key in BUILD_SETTING_ALLOWLIST:
            entries.append({"key": key, "value": value})
    return entries


def _write_evidence(root: Path, payload: dict) -> None:
    tool = root / "tools" / "evidence.py"
    if not tool.is_file():
        raise EvidenceChainError("缺 tools/evidence.py")
    completed = subprocess.run(
        [sys.executable, str(tool), "write", "--claim", payload["claim"], "--from-json", "-", "--root", str(root)],
        cwd=str(root),
        input=json.dumps(payload, ensure_ascii=False),
        capture_output=True,
        text=True,
    )
    if completed.stdout.strip():
        print(completed.stdout.strip())
    if completed.stderr.strip():
        print(completed.stderr.strip(), file=sys.stderr)
    if completed.returncode != 0:
        raise EvidenceChainError(f"evidence.py write 失败（exit {completed.returncode}）")


def cmd_run(root: Path, args: argparse.Namespace) -> int:
    config = load_config(root)
    claim = claim_config(config, args.claim)
    if claim is None:
        raise EvidenceChainError(f"claim 未在 config.claims 声明：{args.claim!r}")
    if claim.get("type") != "test-count":
        raise EvidenceChainError(f"claim {args.claim!r} 不是 test-count")
    target_static = expected_static_target(claim)
    bundle_root = result_bundle_root(claim)
    run_id = args.run_id or str(uuid.uuid4())
    try:
        uuid.UUID(run_id)
    except (ValueError, AttributeError):
        raise EvidenceChainError(f"--run-id 必须是 UUID：{run_id!r}") from None
    bundle_path = bundle_root / run_id / f"{args.claim}.xcresult"
    if bundle_path.exists():
        raise EvidenceChainError(f"xcresult 路径已存在（单次运行禁止复用）：{bundle_path}")
    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    artifact_dir = (
        root
        / config["paths"]["evidence"]
        / "artifacts"
        / f"{utc}-{args.claim}-{run_id[:8]}"
    )
    if artifact_dir.exists():
        raise EvidenceChainError(f"artifact 目录已存在（单次运行禁止复用）：{artifact_dir}")
    artifact_dir.mkdir(parents=True)
    junit_path = artifact_dir / f"{args.claim}.xml"
    manifest_path = artifact_dir / f"{args.claim}.manifest.json"
    target = dict(target_static)
    target["resultBundlePath"] = str(bundle_path)
    modules = load_toolchain(root)
    signing = _signing_arguments(claim)
    build_args = [item.strip() for item in args.xcodebuild_arg if item.strip()]
    warmup = claim.get("warmupOnlyTesting")
    if warmup is not None:
        if not isinstance(warmup, str) or not warmup.strip():
            raise EvidenceChainError("warmupOnlyTesting 必须是非空字符串")
        _run_xcodebuild(
            root,
            _warmup_argv(target_static, warmup.strip()),
            args.timeout,
            signing,
            build_args,
        )
    argv = modules.manifest.canonical_command(target)
    _run_xcodebuild(root, argv, args.timeout, signing, build_args)
    if not bundle_path.is_dir():
        raise EvidenceChainError(f"xcodebuild 成功但 xcresult 不存在：{bundle_path}")
    conversion = modules.xcresult.convert_bundle(
        bundle_path,
        junit_path,
        testsuites_name=target_static["onlyTesting"],
        redact_paths=(str(root.resolve()), str(Path.home()), str(bundle_root)),
    )
    device = dict(conversion.devices[0])
    device["deviceId"] = "$DEVICE_ID"
    if claim.get("sanitizeDeviceName") is True:
        device["deviceName"] = "$DEVICE_NAME"
    conversion = dataclasses.replace(conversion, devices=(device,))
    environment = _detect_environment()
    environment.update(_parse_environment(args.environment))
    environment.setdefault("id", (claim.get("environment") or {}).get("id") or "local-simulator")
    if not environment.get("id"):
        environment["id"] = "local-simulator"
    manifest = modules.manifest.build_manifest(
        claim=args.claim,
        target=target,
        environment=environment,
        conversion=conversion,
        xcresult_name=bundle_path.name,
        junit_name=junit_path.name,
        run_id=run_id,
        created_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
    if build_args:
        manifest["command"]["buildSettings"] = _build_settings(build_args)
    modules.manifest.write_manifest(manifest_path, manifest)
    modules.manifest.verify_manifest(
        manifest,
        junit_path.read_bytes(),
        expected_claim=args.claim,
        expected_target=target,
        junit_name=junit_path.name,
    )
    junit_rel = display(root, junit_path)
    manifest_rel = display(root, manifest_path)
    payload = {
        "schemaVersion": 1,
        "claim": args.claim,
        "command": shlex.join([*argv, *build_args]),
        "environment": environment,
        "result": {
            "status": "SUCCEEDED" if conversion.failed == 0 else "FAILED",
            "passed": conversion.passed,
            "failed": conversion.failed,
            "skipped": conversion.skipped,
            "durationSec": conversion.duration,
            "artifacts": [junit_rel, manifest_rel],
            "artifactMode": "sanitized-copy",
            "junit": junit_rel,
            "manifest": manifest_rel,
            "runId": run_id,
        },
        "verdict": "PASS" if conversion.failed == 0 else "FAIL",
        "verifier": "tools/evidence_chain.py",
        "notes": f"xcresult -> strict JUnit -> manifest; runId={run_id}",
    }
    summary = {
        "claim": args.claim,
        "runId": run_id,
        "junit": junit_rel,
        "manifest": manifest_rel,
        "tests": conversion.tests,
        "passed": conversion.passed,
        "failed": conversion.failed,
        "skipped": conversion.skipped,
        "artifactDir": display(root, artifact_dir),
    }
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    if args.write_evidence:
        _write_evidence(root, payload)
        print(f"[INFO] 证据已写入；提交前先 git add {junit_rel} {manifest_rel}")
    else:
        print("[INFO] 未写 evidence；加 --write-evidence 生成（工作树必须 clean）")
    return 0 if conversion.failed == 0 else 1


def _manifest_stub(modules: SimpleNamespace, junit_bytes: bytes, counts: tuple[int, int, int]) -> SimpleNamespace:
    tests, passed, skipped = counts
    failed = tests - passed - skipped
    return SimpleNamespace(
        junit_bytes=junit_bytes,
        tests=tests,
        passed=passed,
        failed=failed,
        skipped=skipped,
        summary={"startTime": 1700000000.0, "finishTime": 1700000001.0},
        summary_sha256=hashlib.sha256(b"summary").hexdigest(),
        report_sha256=hashlib.sha256(b"report").hexdigest(),
        devices=(
            {
                "deviceId": "SIM-UDID",
                "deviceName": "iPhone 17 Pro Max",
                "architecture": "arm64",
                "modelName": "iPhone 17 Pro Max",
                "osVersion": "26.4",
            },
        ),
    )


def _fixture(modules: SimpleNamespace, root: Path) -> tuple[dict, str, str]:
    claim = "demo-pass"
    run_id = str(uuid.uuid4())
    target = {
        "project": "Demo.xcodeproj",
        "scheme": "Demo",
        "destination": "platform=iOS Simulator,name=iPhone 17 Pro Max,OS=26.4.1",
        "derivedDataPath": "/tmp/demo-build",
        "resultBundlePath": f"/tmp/demo-evidence/{run_id}/{claim}.xcresult",
        "onlyTesting": "DemoTests",
    }
    junit_bytes = (
        b'<testsuites name="DemoTests" tests="2" failures="0" errors="0" skipped="1">'
        b'<testsuite name="DemoTests" tests="2" failures="0" errors="0" skipped="1">'
        b'<testcase classname="DemoTests.Foo" name="testA"/>'
        b'<testcase classname="DemoTests.Foo" name="testB"><skipped message="no speech"/></testcase>'
        b"</testsuite></testsuites>"
    )
    artifact_dir = root / "harness" / "evidence" / "artifacts" / f"run-{run_id[:8]}"
    artifact_dir.mkdir(parents=True)
    junit_path = artifact_dir / "demo.xml"
    junit_path.write_bytes(junit_bytes)
    manifest = modules.manifest.build_manifest(
        claim=claim,
        target=target,
        environment={
            "id": "local-simulator",
            "host": "macOS 27.0",
            "xcode": "Xcode 27.1",
            "xcresulttool": "xcresulttool 1.0",
        },
        conversion=_manifest_stub(modules, junit_bytes, (2, 1, 1)),
        xcresult_name=f"{claim}.xcresult",
        junit_name=junit_path.name,
        run_id=run_id,
        created_at="2026-01-01T00:00:00Z",
    )
    manifest_path = artifact_dir / "demo.manifest.json"
    modules.manifest.write_manifest(manifest_path, manifest)
    junit_rel = junit_path.relative_to(root).as_posix()
    manifest_rel = manifest_path.relative_to(root).as_posix()
    evidence = {
        "schemaVersion": 1,
        "id": "20260101T000000Z-demo-pass",
        "claim": claim,
        "createdAt": "2026-01-01T00:00:01Z",
        "git": {"commit": "0" * 40, "dirty": False},
        "command": "xcodebuild test -project Demo.xcodeproj",
        "environment": {"id": "local-simulator"},
        "result": {
            "status": "SUCCEEDED",
            "passed": 1,
            "failed": 0,
            "skipped": 1,
            "artifacts": [junit_rel, manifest_rel],
            "junit": junit_rel,
            "manifest": manifest_rel,
        },
        "verdict": "PASS",
        "verifier": "selftest",
    }
    (root / "harness" / "evidence" / "20260101T000000Z-demo-pass.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    config = {
        "paths": {"evidence": "harness/evidence"},
        "claims": [
            {
                "name": claim,
                "type": "test-count",
                "requireManifest": True,
                "expectedTarget": {
                    "project": "Demo.xcodeproj",
                    "scheme": "Demo",
                    "destination": "platform=iOS Simulator,name=iPhone 17 Pro Max,OS=26.4.1",
                    "derivedDataPath": "/tmp/demo-build",
                    "onlyTesting": "DemoTests",
                },
                "resultBundleRoot": "/tmp/demo-evidence",
            }
        ],
    }
    return config, junit_rel, manifest_rel


def _load_verify_claim(root: Path) -> SimpleNamespace:
    path = root / "tools" / "verify_claim.py"
    if not path.is_file():
        raise EvidenceChainError("缺 tools/verify_claim.py")
    spec = importlib.util.spec_from_file_location("host_verify_claim", path)
    if spec is None or spec.loader is None:
        raise EvidenceChainError("无法加载 tools/verify_claim.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _git_fixture(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise EvidenceChainError(f"fixture git {' '.join(args)} 失败：{completed.stderr.strip()}")
    return completed.stdout


def cmd_freshness_selftest(root: Path) -> int:
    config = load_config(root)
    claim_name = "unit-tests-pass"
    if claim_config(config, claim_name) is None:
        raise EvidenceChainError(f"config.claims 缺少 {claim_name}")
    patterns = (config.get("freshness") or {}).get(claim_name)
    if not isinstance(patterns, list) or not patterns:
        raise EvidenceChainError(f"config.freshness.{claim_name} 必须是非空数组")
    verify = _load_verify_claim(root)
    cases: list[str] = []
    with tempfile.TemporaryDirectory(prefix="evidence-freshness-selftest-") as temp:
        repo = Path(temp) / "repo"
        files = {
            "Makefile": "check:\n\ttrue\n",
            "tools/probe.py": "VALUE = 1\n",
            "Duiyi.xcodeproj/project.pbxproj": "// fixture\n",
            "harness/evidence/keep.json": "{}\n",
        }
        for rel, content in files.items():
            path = repo / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        _git_fixture(repo, "init", "-q")
        _git_fixture(repo, "add", ".")
        _git_fixture(
            repo,
            "-c",
            "user.name=selftest",
            "-c",
            "user.email=selftest@example.invalid",
            "commit",
            "-q",
            "-m",
            "fixture",
        )
        commit = _git_fixture(repo, "rev-parse", "HEAD").strip()
        fixture_config = {
            "paths": config.get("paths"),
            "freshness": {claim_name: patterns},
        }
        stale = verify.stale_files(repo, fixture_config, claim_name, commit)
        if stale:
            raise EvidenceChainError(f"clean fixture 不应 stale：{stale}")
        cases.append("clean fixture")

        for rel in ("Makefile", "tools/probe.py", "Duiyi.xcodeproj/project.pbxproj"):
            path = repo / rel
            path.write_text(path.read_text(encoding="utf-8") + "\n# changed\n", encoding="utf-8")
            stale = verify.stale_files(repo, fixture_config, claim_name, commit)
            if rel not in stale:
                raise EvidenceChainError(f"freshness 未检测到变更：{rel}（实际 {stale}）")
            _git_fixture(repo, "checkout", "--", rel)
            cases.append(f"stale {rel}")

        keep = repo / "harness/evidence/keep.json"
        keep.write_text('{"changed": true}\n', encoding="utf-8")
        stale = verify.stale_files(repo, fixture_config, claim_name, commit)
        if stale:
            raise EvidenceChainError(f"过程目录变更不应 stale：{stale}")
        cases.append("process path ignored")

    print(f"PASS freshness selftest: {len(cases)} cases（{len(cases) - 1} 个负向）")
    for case in cases:
        print(f"[OK] {case}")
    return 0


def cmd_selftest(root: Path) -> int:
    modules = load_toolchain(root)
    cases: list[str] = []
    with tempfile.TemporaryDirectory(prefix="evidence-chain-selftest-") as temp:
        base = Path(temp) / "base"
        config, junit_rel, manifest_rel = _fixture(modules, base)
        initial = check_evidence(base, config, modules, check_pin=False)
        if initial:
            raise EvidenceChainError("基线下不应报错：" + "；".join(initial))
        cases.append("valid fixture")

        def negative(name: str, mutate) -> None:
            case_root = Path(temp) / name.replace(" ", "-")
            shutil.copytree(base, case_root)
            mutate(case_root)
            errors = check_evidence(case_root, config, modules, check_pin=False)
            if not errors:
                raise EvidenceChainError(f"负向用例未被拒绝：{name}")
            cases.append(name)

        def mutate_junit(case_root: Path) -> None:
            (case_root / junit_rel).write_bytes((case_root / junit_rel).read_bytes() + b"\n")

        def mutate_attribute_only(case_root: Path) -> None:
            fake = (
                b'<testsuites name="DemoTests" tests="2" failures="0" errors="0" skipped="0"></testsuites>'
            )
            junit_path = case_root / junit_rel
            junit_path.write_bytes(fake)
            manifest_path = case_root / manifest_rel
            manifest = load_json(manifest_path)
            manifest["junit"].update(
                {
                    "sha256": hashlib.sha256(fake).hexdigest(),
                    "bytes": len(fake),
                    "tests": 2,
                    "passed": 2,
                    "failed": 0,
                    "skipped": 0,
                    "caseIdsSha256": hashlib.sha256(b"fake").hexdigest(),
                }
            )
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")

        def mutate_counts(case_root: Path) -> None:
            evidence_path = case_root / "harness" / "evidence" / "20260101T000000Z-demo-pass.json"
            evidence = load_json(evidence_path)
            evidence["result"]["passed"] = 2
            evidence_path.write_text(json.dumps(evidence, ensure_ascii=False), encoding="utf-8")

        def mutate_missing_manifest(case_root: Path) -> None:
            evidence_path = case_root / "harness" / "evidence" / "20260101T000000Z-demo-pass.json"
            evidence = load_json(evidence_path)
            evidence["result"]["manifest"] = "harness/evidence/artifacts/missing.json"
            evidence_path.write_text(json.dumps(evidence, ensure_ascii=False), encoding="utf-8")

        def mutate_target(case_root: Path) -> None:
            manifest_path = case_root / manifest_rel
            manifest = load_json(manifest_path)
            manifest["target"]["project"] = "Other.xcodeproj"
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")

        def mutate_claim(case_root: Path) -> None:
            manifest_path = case_root / manifest_rel
            manifest = load_json(manifest_path)
            manifest["claim"] = "other"
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")

        def mutate_duplicate_run(case_root: Path) -> None:
            evidence_path = case_root / "harness" / "evidence" / "20260101T000000Z-demo-pass.json"
            evidence = load_json(evidence_path)
            evidence["id"] = "20260101T000001Z-demo-pass"
            (case_root / "harness" / "evidence" / "20260101T000001Z-demo-pass.json").write_text(
                json.dumps(evidence, ensure_ascii=False), encoding="utf-8"
            )

        negative("tampered JUnit", mutate_junit)
        negative("attribute-only JUnit", mutate_attribute_only)
        negative("evidence count mismatch", mutate_counts)
        negative("missing manifest", mutate_missing_manifest)
        negative("target mismatch", mutate_target)
        negative("claim mismatch", mutate_claim)
        negative("duplicate runId", mutate_duplicate_run)

    print(f"PASS evidence chain selftest: {len(cases)} cases（{len(cases) - 1} 个负向）")
    for case in cases:
        print(f"[OK] {case}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="evidence_chain.py", description=__doc__)
    parser.add_argument("--version", action="version", version="evidence_chain 0.1.0")
    subparsers = parser.add_subparsers(dest="command", required=True)

    check_pin = subparsers.add_parser("check-pin", help="verify vendored toolchain hashes")
    check_pin.add_argument("--root", default=str(Path(__file__).resolve().parent.parent))
    check_pin.set_defaults(func=lambda args: cmd_check_pin(Path(args.root).expanduser().resolve()))

    check = subparsers.add_parser("check-evidence", help="verify manifest-bound current evidence")
    check.add_argument("--root", default=str(Path(__file__).resolve().parent.parent))
    check.set_defaults(func=lambda args: cmd_check_evidence(Path(args.root).expanduser().resolve()))

    run = subparsers.add_parser("run", help="run xcodebuild and convert the xcresult to evidence artifacts")
    run.add_argument("--claim", required=True)
    run.add_argument("--environment", action="append", default=[], metavar="KEY=VALUE")
    run.add_argument(
        "--xcodebuild-arg",
        action="append",
        default=[],
        metavar="ARG",
        help="append one local xcodebuild build setting (recorded in evidence command)",
    )
    run.add_argument("--run-id")
    run.add_argument("--timeout", type=int, default=3600)
    run.add_argument("--write-evidence", action="store_true")
    run.add_argument("--root", default=str(Path(__file__).resolve().parent.parent))
    run.set_defaults(func=lambda args: cmd_run(Path(args.root).expanduser().resolve(), args))

    selftest = subparsers.add_parser("selftest", help="negative fixtures for the manifest checks")
    selftest.add_argument("--root", default=str(Path(__file__).resolve().parent.parent))
    selftest.set_defaults(func=lambda args: cmd_selftest(Path(args.root).expanduser().resolve()))

    freshness = subparsers.add_parser(
        "freshness-selftest", help="negative fixtures for stale-evidence detection"
    )
    freshness.add_argument("--root", default=str(Path(__file__).resolve().parent.parent))
    freshness.set_defaults(func=lambda args: cmd_freshness_selftest(Path(args.root).expanduser().resolve()))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except EvidenceChainError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
