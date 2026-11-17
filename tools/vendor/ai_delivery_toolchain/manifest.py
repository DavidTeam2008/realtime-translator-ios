"""Single-run manifest binding xcresult reports, JUnit and structured command."""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

from .junit_strict import StrictJUnitError, count_text, local_name
from .xcresult import ConversionResult

SCHEMA_VERSION = 1
KIND = "xcresult-test-run"
CLAIM_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
CREATED_AT_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
TARGET_KEYS = ("project", "scheme", "destination", "derivedDataPath", "resultBundlePath", "onlyTesting")
ENV_KEYS = ("id", "host", "xcode", "xcresulttool")
DEVICE_KEYS = ("deviceId", "deviceName", "modelName", "osVersion", "architecture")


class ManifestError(ValueError):
    """The run manifest is incomplete, stale, mismatched or tampered."""


def _require_str(document: dict, key: str, label: str) -> str:
    value = document.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ManifestError(f"{label} 缺少非空 {key}")
    return value.strip()


def _require_int(document: dict, key: str, label: str) -> int:
    value = document.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ManifestError(f"{label}.{key} 必须是非负整数：{value!r}")
    return value


def _require_sha(document: dict, key: str, label: str) -> str:
    value = _require_str(document, key, label)
    if not SHA256_RE.fullmatch(value):
        raise ManifestError(f"{label}.{key} 必须是 64 位小写 hex：{value!r}")
    return value


def _validate_created_at(value: str) -> str:
    if not CREATED_AT_RE.fullmatch(value):
        raise ManifestError(f"manifest.createdAt 需为 UTC RFC3339：{value!r}")
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        raise ManifestError(f"manifest.createdAt 非法：{value!r}") from None
    return value


def _validate_target(target: object) -> dict:
    if not isinstance(target, dict):
        raise ManifestError("manifest.target 必须是 object")
    unknown = sorted(set(target) - set(TARGET_KEYS))
    if unknown:
        raise ManifestError(f"manifest.target 包含未知字段：{', '.join(unknown)}")
    normalized = {key: _require_str(target, key, "manifest.target") for key in TARGET_KEYS}
    if "platform=" not in normalized["destination"]:
        raise ManifestError("manifest.target.destination 必须包含 platform=")
    if not normalized["resultBundlePath"].endswith(".xcresult"):
        raise ManifestError("manifest.target.resultBundlePath 必须以 .xcresult 结尾")
    return normalized


def canonical_command(target: dict) -> list[str]:
    normalized = _validate_target(target)
    return [
        "xcodebuild",
        "test",
        "-project",
        normalized["project"],
        "-scheme",
        normalized["scheme"],
        "-destination",
        normalized["destination"],
        "-derivedDataPath",
        normalized["derivedDataPath"],
        "-resultBundlePath",
        normalized["resultBundlePath"],
        "-only-testing:" + normalized["onlyTesting"],
    ]


def command_sha256(argv: list[str]) -> str:
    return hashlib.sha256("\0".join(argv).encode("utf-8")).hexdigest()


def _validate_device(device: object, label: str) -> dict:
    if not isinstance(device, dict):
        raise ManifestError(f"{label} 必须是 object")
    return {key: _require_str(device, key, label) for key in DEVICE_KEYS}


def _validate_environment(environment: object, conversion: ConversionResult) -> dict:
    if not isinstance(environment, dict):
        raise ManifestError("environment 必须是 object")
    unknown = sorted(set(environment) - set(ENV_KEYS) - {"device"})
    if unknown:
        raise ManifestError(f"environment 包含未知字段：{', '.join(unknown)}")
    normalized = {key: _require_str(environment, key, "environment") for key in ENV_KEYS}
    if not conversion.devices:
        raise ManifestError("conversion 缺少设备信息")
    normalized["device"] = _validate_device(conversion.devices[0], "environment.device")
    return normalized


def _junit_case_ids(junit_bytes: bytes) -> tuple[str, ...]:
    try:
        text = junit_bytes.decode("utf-8")
        root = ET.fromstring(junit_bytes)
    except (UnicodeDecodeError, ET.ParseError) as exc:
        raise ManifestError(f"JUnit 无法解析：{exc}") from exc
    try:
        count_text(text)
    except StrictJUnitError as exc:
        raise ManifestError(f"JUnit 严格校验失败：{exc}") from exc
    suites = [root] if local_name(root.tag) == "testsuite" else [
        child for child in root if local_name(child.tag) == "testsuite"
    ]
    identities = []
    for suite in suites:
        for case in suite:
            if local_name(case.tag) != "testcase":
                continue
            classname = (case.get("classname") or "").strip()
            name = (case.get("name") or "").strip()
            identities.append(f"{classname}::{name}")
    return tuple(sorted(identities))


def _case_ids_sha256(identities: tuple[str, ...]) -> str:
    payload = ("\n".join(identities) + "\n").encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _file_name(value: str, label: str, suffix: str) -> str:
    name = Path(value).name
    if name != value or not name.endswith(suffix):
        raise ManifestError(f"{label} 必须是不含路径的 {suffix} 文件名：{value!r}")
    return name


def build_manifest(
    *,
    claim: str,
    target: dict,
    environment: dict,
    conversion: ConversionResult,
    xcresult_name: str,
    junit_name: str,
    run_id: str | None = None,
    created_at: str | None = None,
) -> dict:
    if not isinstance(claim, str) or not CLAIM_RE.fullmatch(claim):
        raise ManifestError(f"claim 非法：{claim!r}")
    normalized_target = _validate_target(target)
    argv = canonical_command(normalized_target)
    normalized_environment = _validate_environment(environment, conversion)
    xcresult_file = _file_name(xcresult_name, "xcresult_name", ".xcresult")
    junit_file = _file_name(junit_name, "junit_name", ".xml")
    run = run_id or str(uuid.uuid4())
    try:
        uuid.UUID(run)
    except (ValueError, AttributeError):
        raise ManifestError(f"runId 必须是 UUID：{run!r}") from None
    created = _validate_created_at(created_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))

    identities = _junit_case_ids(conversion.junit_bytes)
    recounted = count_text(conversion.junit_bytes.decode("utf-8"))
    if (recounted.tests, recounted.failed, recounted.skipped) != (
        conversion.tests,
        conversion.failed,
        conversion.skipped,
    ):
        raise ManifestError("转换结果与 JUnit 重算不一致")
    if recounted.passed != conversion.passed:
        raise ManifestError("转换结果 passed 与 JUnit 重算不一致")

    summary = conversion.summary
    started = summary.get("startTime")
    finished = summary.get("finishTime")
    if (
        not isinstance(started, (int, float))
        or isinstance(started, bool)
        or not isinstance(finished, (int, float))
        or isinstance(finished, bool)
        or finished < started
    ):
        raise ManifestError("xcresult summary 缺少合法的 startTime/finishTime")

    return {
        "schemaVersion": SCHEMA_VERSION,
        "kind": KIND,
        "status": "complete",
        "claim": claim,
        "runId": run,
        "createdAt": created,
        "target": normalized_target,
        "command": {"argv": argv, "sha256": command_sha256(argv)},
        "environment": normalized_environment,
        "xcresult": {
            "name": xcresult_file,
            "summarySha256": _require_sha(
                {"summarySha256": conversion.summary_sha256}, "summarySha256", "xcresult"
            ),
            "testsSha256": _require_sha(
                {"testsSha256": conversion.report_sha256}, "testsSha256", "xcresult"
            ),
            "startedAt": started,
            "finishedAt": finished,
        },
        "junit": {
            "file": junit_file,
            "sha256": hashlib.sha256(conversion.junit_bytes).hexdigest(),
            "bytes": len(conversion.junit_bytes),
            "tests": conversion.tests,
            "passed": conversion.passed,
            "failed": conversion.failed,
            "skipped": conversion.skipped,
            "caseIdsSha256": _case_ids_sha256(identities),
        },
    }


def verify_manifest(
    manifest: dict,
    junit_bytes: bytes,
    *,
    expected_claim: str,
    expected_target: dict,
    junit_name: str,
) -> str:
    if not isinstance(manifest, dict):
        raise ManifestError("manifest 必须是 object")
    if manifest.get("schemaVersion") != SCHEMA_VERSION:
        raise ManifestError(f"manifest.schemaVersion 必须是 {SCHEMA_VERSION}")
    if manifest.get("kind") != KIND:
        raise ManifestError(f"manifest.kind 必须是 {KIND}")
    if manifest.get("status") != "complete":
        raise ManifestError(f"manifest.status 必须是 complete：{manifest.get('status')!r}")
    claim = _require_str(manifest, "claim", "manifest")
    if claim != expected_claim:
        raise ManifestError(f"manifest.claim 不一致：{claim!r} != {expected_claim!r}")
    run_id = _require_str(manifest, "runId", "manifest")
    try:
        uuid.UUID(run_id)
    except ValueError:
        raise ManifestError(f"manifest.runId 必须是 UUID：{run_id!r}") from None
    _validate_created_at(_require_str(manifest, "createdAt", "manifest"))

    target = _validate_target(manifest.get("target"))
    expected = _validate_target(expected_target)
    if canonical_command(target) != canonical_command(expected):
        raise ManifestError("manifest.target 与期望 target 不一致")

    command = manifest.get("command")
    if not isinstance(command, dict):
        raise ManifestError("manifest.command 必须是 object")
    argv = command.get("argv")
    if not isinstance(argv, list) or not argv or not all(isinstance(item, str) and item for item in argv):
        raise ManifestError("manifest.command.argv 必须是非空字符串数组")
    if argv != canonical_command(target):
        raise ManifestError("manifest.command.argv 与 target 推导的命令不一致")
    digest = _require_sha(command, "sha256", "manifest.command")
    if digest != command_sha256(argv):
        raise ManifestError("manifest.command.sha256 不一致")

    environment = manifest.get("environment")
    if not isinstance(environment, dict):
        raise ManifestError("manifest.environment 必须是 object")
    for key in ENV_KEYS:
        _require_str(environment, key, "manifest.environment")
    _validate_device(environment.get("device"), "manifest.environment.device")

    xcresult = manifest.get("xcresult")
    if not isinstance(xcresult, dict):
        raise ManifestError("manifest.xcresult 必须是 object")
    _file_name(_require_str(xcresult, "name", "manifest.xcresult"), "manifest.xcresult.name", ".xcresult")
    _require_sha(xcresult, "summarySha256", "manifest.xcresult")
    _require_sha(xcresult, "testsSha256", "manifest.xcresult")
    started = xcresult.get("startedAt")
    finished = xcresult.get("finishedAt")
    if (
        not isinstance(started, (int, float))
        or isinstance(started, bool)
        or not isinstance(finished, (int, float))
        or isinstance(finished, bool)
        or finished < started
    ):
        raise ManifestError("manifest.xcresult 的 startedAt/finishedAt 非法")

    junit = manifest.get("junit")
    if not isinstance(junit, dict):
        raise ManifestError("manifest.junit 必须是 object")
    file_name = _require_str(junit, "file", "manifest.junit")
    if file_name != Path(file_name).name or file_name != junit_name:
        raise ManifestError(f"manifest.junit.file 文件名不一致：{file_name!r} != {junit_name!r}")
    expected_sha = _require_sha(junit, "sha256", "manifest.junit")
    actual_sha = hashlib.sha256(junit_bytes).hexdigest()
    if expected_sha != actual_sha:
        raise ManifestError(f"manifest.junit.sha256 不一致：{expected_sha} != {actual_sha}")
    expected_bytes = _require_int(junit, "bytes", "manifest.junit")
    if expected_bytes != len(junit_bytes):
        raise ManifestError(f"manifest.junit.bytes 不一致：{expected_bytes} != {len(junit_bytes)}")
    expected_counts = {
        key: _require_int(junit, key, "manifest.junit") for key in ("tests", "passed", "failed", "skipped")
    }
    expected_case_ids = _require_sha(junit, "caseIdsSha256", "manifest.junit")

    try:
        recounted = count_text(junit_bytes.decode("utf-8"))
    except (UnicodeDecodeError, StrictJUnitError) as exc:
        raise ManifestError(f"JUnit 严格校验失败：{exc}") from exc
    actual_counts = {
        "tests": recounted.tests,
        "passed": recounted.passed,
        "failed": recounted.failed,
        "skipped": recounted.skipped,
    }
    if expected_counts != actual_counts:
        raise ManifestError(
            f"manifest.junit 计数与 JUnit 重算不一致：{expected_counts} != {actual_counts}"
        )
    if expected_counts["passed"] != expected_counts["tests"] - expected_counts["failed"] - expected_counts["skipped"]:
        raise ManifestError("manifest.junit 计数自相矛盾：passed != tests - failed - skipped")
    actual_ids = _case_ids_sha256(_junit_case_ids(junit_bytes))
    if expected_case_ids != actual_ids:
        raise ManifestError("manifest.junit 用例集合摘要不一致")

    return (
        f"claim={claim} runId={run_id} tests={actual_counts['tests']} "
        f"passed={actual_counts['passed']} failed={actual_counts['failed']} "
        f"skipped={actual_counts['skipped']}"
    )


def write_manifest(path: Path, manifest: dict) -> None:
    if path.exists():
        raise ManifestError(f"manifest 已存在（单次运行禁止复用路径）：{path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    handle, temp_name = tempfile.mkstemp(prefix=".manifest-", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(payload)
        os.replace(temp_name, path)
        temp_name = ""
    except OSError as exc:
        raise ManifestError(f"manifest 写入失败：{path}：{exc}") from exc
    finally:
        if temp_name and os.path.exists(temp_name):
            try:
                os.unlink(temp_name)
            except OSError:
                pass


def load_manifest(path: Path) -> dict:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ManifestError(f"manifest 无法读取：{path}：{exc}") from exc
    except json.JSONDecodeError as exc:
        raise ManifestError(f"manifest 不是合法 JSON：{path}：{exc}") from exc
    if not isinstance(document, dict):
        raise ManifestError("manifest 顶层必须是 object")
    return document
