"""Convert `xcresulttool get test-results` output into strict JUnit XML.

Both the summary and the per-test tree are required; their counts must agree.
Multiple devices/configurations, unknown results, expected failures and
repetitions are rejected instead of being silently approximated.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

from .junit_strict import StrictJUnitError, count_file, count_text

MAX_MESSAGE = 2000
MAX_DETAILS = 8000
COMMAND_TIMEOUT = 300
VALID_RESULTS = ("Passed", "Failed", "Skipped")
SAFE_CHILD_TYPES = {
    "Failure Message",
    "Skip Message",
    "Attachment",
    "Source Code Reference",
    "Expression",
    "Test Value",
    "Runtime Warning",
}
INVALID_XML_RE = re.compile(
    "[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]"
)


class ConversionError(ValueError):
    """The xcresult bundle cannot be trusted or parsed."""


@dataclass
class ConversionResult:
    junit_bytes: bytes
    tests: int
    passed: int
    failed: int
    skipped: int
    duration: float
    case_ids: tuple[str, ...]
    devices: tuple[dict, ...]
    configurations: tuple[dict, ...]
    summary: dict = field(repr=False)
    summary_sha256: str = ""
    report_sha256: str = ""


def canonical_sha256(value: object) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _require_int(document: dict, key: str) -> int:
    value = document.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ConversionError(f"summary.{key} 必须是非负整数：{value!r}")
    return value


def _require_text(document: dict, key: str, label: str) -> str:
    value = document.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConversionError(f"{label}.{key} 必须是非空字符串")
    return value.strip()


def _check_result(value: object, label: str) -> str:
    if value == "Expected Failure":
        raise ConversionError(f"{label} 为 Expected Failure，暂不支持（拒绝静默归类）")
    if value == "unknown":
        raise ConversionError(f"{label} 的 result 为 unknown，拒绝计数")
    if value not in VALID_RESULTS:
        raise ConversionError(f"{label} 的 result 非法：{value!r}")
    return value


def _validate_device(value: object, label: str) -> dict:
    if not isinstance(value, dict):
        raise ConversionError(f"{label} 必须是 object")
    for key in ("deviceId", "deviceName", "modelName", "osVersion", "architecture"):
        _require_text(value, key, label)
    return value


def _as_list(value: object, label: str) -> list:
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return [value]
    raise ConversionError(f"summary.{label} 必须是数组或 object")


def _validate_environment(summary: dict, report: dict) -> tuple[dict, dict]:
    report_devices = report.get("devices")
    report_configs = report.get("testPlanConfigurations")
    if not isinstance(report_devices, list) or len(report_devices) != 1:
        raise ConversionError(f"tests.devices 必须恰好一个设备：{report_devices!r}")
    if not isinstance(report_configs, list) or len(report_configs) != 1:
        raise ConversionError(f"tests.testPlanConfigurations 必须恰好一个配置：{report_configs!r}")
    report_device = _validate_device(report_devices[0], "tests.devices[0]")
    report_config = report_configs[0]
    if not isinstance(report_config, dict):
        raise ConversionError("tests.testPlanConfigurations[0] 必须是 object")
    _require_text(report_config, "configurationId", "tests.testPlanConfigurations[0]")
    _require_text(report_config, "configurationName", "tests.testPlanConfigurations[0]")

    entries = _as_list(summary.get("devicesAndConfigurations"), "devicesAndConfigurations")
    if len(entries) != 1:
        raise ConversionError(f"summary.devicesAndConfigurations 必须恰好一个设备/配置：{len(entries)}")
    entry = entries[0]
    if not isinstance(entry, dict):
        raise ConversionError("summary.devicesAndConfigurations[0] 必须是 object")
    summary_device = _validate_device(entry.get("device"), "summary.devicesAndConfigurations[0].device")
    summary_config = entry.get("testPlanConfiguration")
    if not isinstance(summary_config, dict):
        raise ConversionError("summary.devicesAndConfigurations[0].testPlanConfiguration 必须是 object")
    _require_text(summary_config, "configurationId", "summary testPlanConfiguration")
    if summary_device["deviceId"] != report_device["deviceId"] or summary_device["osVersion"] != report_device["osVersion"]:
        raise ConversionError(
            "summary 设备与 tests 明细不一致："
            f"{summary_device['deviceId']}/{summary_device['osVersion']} vs "
            f"{report_device['deviceId']}/{report_device['osVersion']}"
        )
    if summary_config["configurationId"] != report_config["configurationId"]:
        raise ConversionError(
            "summary 测试计划配置与 tests 明细不一致："
            f"{summary_config['configurationId']} vs {report_config['configurationId']}"
        )
    for key in ("passedTests", "failedTests", "skippedTests", "expectedFailures"):
        value = entry.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ConversionError(f"summary.devicesAndConfigurations[0].{key} 必须是非负整数：{value!r}")
    return report_device, report_config


def _clean_text(value: object, limit: int, redact_paths: tuple[str, ...]) -> str:
    text = str(value or "")
    for root in sorted(redact_paths, key=len, reverse=True):
        if root:
            text = text.replace(root.rstrip("/"), "<REPO>")
    home = str(Path.home())
    if home:
        text = text.replace(home.rstrip("/"), "$HOME")
    text = INVALID_XML_RE.sub("\ufffd", text)
    return text[:limit]


def _message_parts(node: dict, label: str) -> tuple[str, str]:
    details = node.get("details")
    name = node.get("name")
    message = name.strip() if isinstance(name, str) and name.strip() else ""
    body = details.strip() if isinstance(details, str) and details.strip() else ""
    if not message and not body:
        raise ConversionError(f"{label} 缺少 message/details")
    return message or body, body or message


def _case_children(node: dict, label: str) -> tuple[str, str, str]:
    """Return (failure_message, failure_details, skip_message); empty means absent."""
    failure_message = ""
    failure_details = ""
    skip = ""
    for child in node.get("children") or []:
        if not isinstance(child, dict):
            raise ConversionError(f"{label}.children 元素必须是 object")
        node_type = child.get("nodeType")
        if node_type == "Test Case Run":
            raise ConversionError(f"{label} 包含 Test Case Run（多次运行）暂不支持")
        if node_type == "Repetition":
            raise ConversionError(f"{label} 包含 Repetition（重复运行）暂不支持")
        if node_type == "Failure Message":
            failure_message, failure_details = _message_parts(child, f"{label} Failure Message")
        elif node_type == "Skip Message":
            skip, _details = _message_parts(child, f"{label} Skip Message")
        elif node_type not in SAFE_CHILD_TYPES:
            raise ConversionError(f"{label} 包含未知子节点类型：{node_type!r}")
    return failure_message, failure_details, skip


def _walk_cases(
    nodes: object,
    bundle: str | None,
    suite: str | None,
    cases: list[dict],
    seen: set[str],
) -> None:
    if nodes is None:
        return
    if not isinstance(nodes, list):
        raise ConversionError("testNodes.children 必须是数组")
    for node in nodes:
        if not isinstance(node, dict):
            raise ConversionError("testNodes 元素必须是 object")
        node_type = node.get("nodeType")
        name = _require_text(node, "name", "testNode")
        result = node.get("result")
        if result is not None:
            _check_result(result, f"testNode {name}")
        children = node.get("children")
        if node_type in ("Unit test bundle", "UI test bundle"):
            _walk_cases(children, name, None, cases, seen)
        elif node_type == "Test Suite":
            _walk_cases(children, bundle, name, cases, seen)
        elif node_type == "Test Case":
            identifier = _require_text(node, "nodeIdentifier", f"Test Case {name}")
            if identifier in seen:
                raise ConversionError(f"重复的 nodeIdentifier：{identifier}")
            seen.add(identifier)
            classname = ".".join(part for part in (bundle, suite) if part)
            if not classname:
                raise ConversionError(f"Test Case {name} 缺少 bundle/suite 上下文")
            failure, failure_details, skip = _case_children(node, f"Test Case {identifier}")
            duration = node.get("durationInSeconds")
            if duration is not None and (
                not isinstance(duration, (int, float)) or isinstance(duration, bool) or duration < 0
            ):
                raise ConversionError(f"Test Case {identifier} durationInSeconds 非法：{duration!r}")
            cases.append(
                {
                    "identifier": identifier,
                    "name": name,
                    "classname": classname,
                    "result": result,
                    "duration": duration,
                    "failure": failure,
                    "failure_details": failure_details,
                    "skip": skip,
                }
            )
        elif node_type == "Test Case Run":
            raise ConversionError("顶层 Test Case Run 暂不支持")
        else:
            _walk_cases(children, bundle, suite, cases, seen)


def _build_xml(cases: list[dict], testsuites_name: str, redact_paths: tuple[str, ...]) -> tuple[bytes, float]:
    grouped: dict[str, list[dict]] = {}
    for case in cases:
        grouped.setdefault(case["classname"], []).append(case)
    total_failed = sum(1 for case in cases if case["result"] == "Failed")
    total_skipped = sum(1 for case in cases if case["result"] == "Skipped")
    total_duration = 0.0
    suites: list[ET.Element] = []
    for classname, group in grouped.items():
        suite_failed = sum(1 for case in group if case["result"] == "Failed")
        suite_skipped = sum(1 for case in group if case["result"] == "Skipped")
        suite_duration = sum(float(case["duration"] or 0) for case in group)
        total_duration += suite_duration
        suite = ET.Element(
            "testsuite",
            {
                "name": classname,
                "tests": str(len(group)),
                "failures": str(suite_failed),
                "errors": "0",
                "skipped": str(suite_skipped),
                "time": f"{suite_duration:.3f}",
            },
        )
        for case in group:
            attrs = {"classname": classname, "name": case["name"]}
            if case["duration"] is not None:
                attrs["time"] = f"{float(case['duration']):.3f}"
            element = ET.SubElement(suite, "testcase", attrs)
            if case["result"] == "Failed":
                failure = ET.SubElement(
                    element,
                    "failure",
                    {"message": _clean_text(case["failure"], MAX_MESSAGE, redact_paths)},
                )
                failure.text = _clean_text(case["failure_details"], MAX_DETAILS, redact_paths)
            elif case["result"] == "Skipped":
                ET.SubElement(
                    element,
                    "skipped",
                    {"message": _clean_text(case["skip"], MAX_MESSAGE, redact_paths)},
                )
        suites.append(suite)
    root = ET.Element(
        "testsuites",
        {
            "name": testsuites_name,
            "tests": str(len(cases)),
            "failures": str(total_failed),
            "errors": "0",
            "skipped": str(total_skipped),
            "time": f"{total_duration:.3f}",
        },
    )
    for suite in suites:
        root.append(suite)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True), total_duration


def build_junit(
    summary: dict,
    report: dict,
    *,
    testsuites_name: str,
    redact_paths: tuple[str, ...] = (),
) -> ConversionResult:
    if not isinstance(summary, dict) or not isinstance(report, dict):
        raise ConversionError("summary/tests 顶层必须是 object")
    if not testsuites_name.strip():
        raise ConversionError("testsuites_name 不能为空")
    device, configuration = _validate_environment(summary, report)
    counts = {key: _require_int(summary, key) for key in (
        "totalTestCount",
        "passedTests",
        "failedTests",
        "skippedTests",
        "expectedFailures",
    )}
    if counts["expectedFailures"] != 0:
        raise ConversionError("summary.expectedFailures 非零：Expected Failure 暂不支持")
    if counts["totalTestCount"] != (
        counts["passedTests"] + counts["failedTests"] + counts["skippedTests"] + counts["expectedFailures"]
    ):
        raise ConversionError(
            "summary.totalTestCount 与 passed/failed/skipped/expected 之和不一致："
            f"{counts['totalTestCount']}"
        )
    summary_result = _check_result(summary.get("result"), "summary")
    if summary_result not in ("Passed", "Failed"):
        raise ConversionError(f"summary.result 必须是 Passed/Failed：{summary_result!r}")

    cases: list[dict] = []
    _walk_cases(report.get("testNodes"), None, None, cases, set())
    if not cases:
        raise ConversionError("xcresult 没有 testcase 明细")

    passed = sum(1 for case in cases if case["result"] == "Passed")
    failed = sum(1 for case in cases if case["result"] == "Failed")
    skipped = sum(1 for case in cases if case["result"] == "Skipped")
    if len(cases) != counts["totalTestCount"]:
        raise ConversionError(
            "summary 与明细不一致："
            f"totalTestCount 声明 {counts['totalTestCount']} / 明细 {len(cases)}"
        )
    for key, actual in (("passedTests", passed), ("failedTests", failed), ("skippedTests", skipped)):
        if counts[key] != actual:
            raise ConversionError(f"summary 与明细不一致：{key} 声明 {counts[key]} / 明细 {actual}")
    if summary_result == "Passed" and failed != 0:
        raise ConversionError(f"summary 与明细不一致：result=Passed 但明细 failed={failed}")
    if summary_result == "Failed" and failed == 0:
        raise ConversionError("summary 与明细不一致：result=Failed 但明细没有失败用例")
    for case in cases:
        if case["result"] == "Passed" and (case["failure"] or case["skip"]):
            raise ConversionError(f"Test Case {case['identifier']} 为 Passed 但包含失败/跳过消息")
        if case["result"] == "Failed" and case["skip"]:
            raise ConversionError(f"Test Case {case['identifier']} 为 Failed 但包含跳过消息")
        if case["result"] == "Skipped" and case["failure"]:
            raise ConversionError(f"Test Case {case['identifier']} 为 Skipped 但包含失败消息")

    junit_bytes, duration = _build_xml(cases, testsuites_name.strip(), redact_paths)
    try:
        recounted = count_text(junit_bytes.decode("utf-8"))
    except StrictJUnitError as exc:
        raise ConversionError(f"生成的 JUnit 未通过严格校验：{exc}") from exc
    if (recounted.tests, recounted.failed, recounted.skipped) != (len(cases), failed, skipped):
        raise ConversionError(
            "生成的 JUnit 重算不一致："
            f"{(recounted.tests, recounted.failed, recounted.skipped)} vs {(len(cases), failed, skipped)}"
        )
    return ConversionResult(
        junit_bytes=junit_bytes,
        tests=len(cases),
        passed=passed,
        failed=failed,
        skipped=skipped,
        duration=round(duration, 3),
        case_ids=tuple(case["identifier"] for case in cases),
        devices=(device,),
        configurations=(configuration,),
        summary=summary,
        summary_sha256=canonical_sha256(summary),
        report_sha256=canonical_sha256(report),
    )


def _run_tool(arguments: list[str]) -> str:
    command = ["xcrun", "xcresulttool", "get", "test-results", *arguments]
    try:
        completed = subprocess.run(
            command, capture_output=True, text=True, timeout=COMMAND_TIMEOUT
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ConversionError(f"xcresulttool 无法执行：{exc}") from exc
    if completed.returncode != 0:
        tail = (completed.stderr or completed.stdout).strip().splitlines()[-3:]
        raise ConversionError(
            f"xcresulttool 退出 {completed.returncode}：{'; '.join(tail) or '<no output>'}"
        )
    return completed.stdout


def read_bundle_reports(xcresult_path: Path) -> tuple[dict, dict]:
    path = xcresult_path.expanduser()
    if path.is_symlink():
        raise ConversionError(f"xcresult 不能是符号链接：{path}")
    if not path.is_dir():
        raise ConversionError(f"xcresult 不存在或不是目录：{path}")
    if path.suffix != ".xcresult":
        raise ConversionError(f"xcresult 路径必须以 .xcresult 结尾：{path}")
    if not (path / "Info.plist").is_file():
        raise ConversionError(f"xcresult 缺少 Info.plist（损坏或不完整）：{path}")
    try:
        summary = json.loads(_run_tool(["summary", "--path", str(path), "--compact"]))
        report = json.loads(_run_tool(["tests", "--path", str(path), "--compact"]))
    except json.JSONDecodeError as exc:
        raise ConversionError(f"xcresulttool 输出不是合法 JSON：{exc}") from exc
    return summary, report


def convert_bundle(
    xcresult_path: Path,
    junit_path: Path,
    *,
    testsuites_name: str,
    redact_paths: tuple[str, ...] = (),
) -> ConversionResult:
    if junit_path.exists():
        raise ConversionError(f"JUnit 输出已存在（单次运行禁止复用路径）：{junit_path}")
    summary, report = read_bundle_reports(xcresult_path)
    result = build_junit(
        summary, report, testsuites_name=testsuites_name, redact_paths=redact_paths
    )
    junit_path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(prefix=".junit-", suffix=".tmp", dir=str(junit_path.parent))
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(result.junit_bytes)
        os.replace(temp_name, junit_path)
        temp_name = ""
    except OSError as exc:
        raise ConversionError(f"JUnit 写入失败：{junit_path}：{exc}") from exc
    finally:
        if temp_name and os.path.exists(temp_name):
            try:
                os.unlink(temp_name)
            except OSError:
                pass
    recounted = count_file(junit_path)
    if (recounted.tests, recounted.failed, recounted.skipped) != (
        result.tests,
        result.failed,
        result.skipped,
    ):
        raise ConversionError("写入后的 JUnit 重算不一致")
    return result
