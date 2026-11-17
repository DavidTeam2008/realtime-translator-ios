"""Strict JUnit XML validation and recounting.

Only testcase detail is authoritative. Declared aggregate attributes, when
present, must match the details exactly. Attribute-only suites, empty reports,
unknown roots, duplicate case identities and ambiguous testcase outcomes are
rejected instead of being counted.
"""
from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

MAX_BYTES = 5 * 1024 * 1024
SUITE_ATTRS = {
    "name",
    "tests",
    "failures",
    "errors",
    "skipped",
    "time",
    "timestamp",
    "hostname",
    "id",
    "package",
}
CASE_ATTRS = {"name", "classname", "time", "file", "line"}
COUNT_ATTRS = ("tests", "failures", "errors", "skipped")
OUTCOMES = ("failure", "error", "skipped")


class StrictJUnitError(ValueError):
    """The document cannot be trusted as test evidence."""


@dataclass
class Counts:
    tests: int = 0
    failed: int = 0
    skipped: int = 0
    duration: float = 0.0

    @property
    def passed(self) -> int:
        return self.tests - self.failed - self.skipped


@dataclass
class _SuiteDetail:
    tests: int = 0
    failures: int = 0
    errors: int = 0
    skipped: int = 0
    duration: float = 0.0


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _check_attrs(element: ET.Element, allowed: set[str], label: str) -> None:
    unknown = sorted(set(element.attrib) - allowed)
    if unknown:
        raise StrictJUnitError(f"{label} 包含不允许的属性：{', '.join(unknown)}")


def _non_empty(element: ET.Element, attr: str, label: str) -> str:
    value = (element.get(attr) or "").strip()
    if not value:
        raise StrictJUnitError(f"{label} 缺少非空 {attr}")
    return value


def _summary_count(element: ET.Element, attr: str, label: str) -> int | None:
    raw = element.get(attr)
    if raw is None:
        return None
    try:
        value = int(raw.strip())
    except ValueError:
        raise StrictJUnitError(f"{label}.{attr} 必须是非负整数：{raw!r}") from None
    if value < 0:
        raise StrictJUnitError(f"{label}.{attr} 必须是非负整数：{raw!r}")
    return value


def _time(element: ET.Element, label: str) -> float | None:
    raw = element.get("time")
    if raw is None:
        return None
    try:
        value = float(raw.strip())
    except ValueError:
        raise StrictJUnitError(f"{label}.time 必须是秒数：{raw!r}") from None
    if not math.isfinite(value) or value < 0:
        raise StrictJUnitError(f"{label}.time 必须是有限非负数：{raw!r}")
    return value


def _validate_case(case: ET.Element, suite_name: str, index: int, seen: set[str]) -> tuple[str, float]:
    label = f"{suite_name}.testcase[{index}]"
    _check_attrs(case, CASE_ATTRS, label)
    name = _non_empty(case, "name", label)
    classname = _non_empty(case, "classname", label)
    identity = f"{classname}::{name}"
    if identity in seen:
        raise StrictJUnitError(f"重复的 testcase 身份：{identity}")
    seen.add(identity)
    duration = _time(case, label)
    outcomes: list[str] = []
    for child in case:
        child_name = local_name(child.tag)
        if child_name not in OUTCOMES:
            raise StrictJUnitError(f"{label} 包含未知子元素：{child_name}")
        outcomes.append(child_name)
    if len(outcomes) > 1:
        raise StrictJUnitError(f"{label} 包含多个结果子元素：{', '.join(outcomes)}")
    return (outcomes[0] if outcomes else "passed"), (duration or 0.0)


def _validate_suite(suite: ET.Element, seen: set[str]) -> _SuiteDetail:
    _check_attrs(suite, SUITE_ATTRS, "testsuite")
    suite_name = _non_empty(suite, "name", "testsuite")
    cases = [child for child in suite if local_name(child.tag) == "testcase"]
    unknown = [local_name(child.tag) for child in suite if local_name(child.tag) != "testcase"]
    if unknown:
        raise StrictJUnitError(f"testsuite {suite_name} 包含未知子元素：{', '.join(sorted(set(unknown)))}")
    if not cases:
        raise StrictJUnitError(f"testsuite {suite_name} 缺少 testcase 明细（属性汇总不可作为证据）")
    detail = _SuiteDetail()
    case_times = 0
    for index, case in enumerate(cases):
        outcome, duration = _validate_case(case, suite_name, index, seen)
        detail.tests += 1
        detail.duration += duration
        if outcome in ("failure", "error"):
            detail.failures += outcome == "failure"
            detail.errors += outcome == "error"
        elif outcome == "skipped":
            detail.skipped += 1
        if case.get("time") is not None:
            case_times += 1
    suite_time = _time(suite, f"testsuite {suite_name}")
    if case_times == 0 and suite_time is not None:
        detail.duration += suite_time
    declared = {attr: _summary_count(suite, attr, f"testsuite {suite_name}") for attr in COUNT_ATTRS}
    actual = {
        "tests": detail.tests,
        "failures": detail.failures,
        "errors": detail.errors,
        "skipped": detail.skipped,
    }
    for attr, value in declared.items():
        if value is not None and value != actual[attr]:
            raise StrictJUnitError(
                f"testsuite {suite_name} 汇总计数与明细不一致：{attr} 声明 {value} / 明细 {actual[attr]}"
            )
    return detail


def _add(counts: Counts, detail: _SuiteDetail) -> None:
    counts.tests += detail.tests
    counts.failed += detail.failures + detail.errors
    counts.skipped += detail.skipped
    counts.duration += detail.duration


def aggregate(root: ET.Element) -> Counts:
    """Validate one parsed JUnit document and recount it from testcase detail."""
    tag = local_name(root.tag)
    if tag not in ("testsuites", "testsuite"):
        raise StrictJUnitError(f"根元素必须是 testsuites 或 testsuite：{tag!r}")
    counts = Counts()
    seen: set[str] = set()
    if tag == "testsuite":
        _add(counts, _validate_suite(root, seen))
    else:
        _check_attrs(
            root,
            SUITE_ATTRS - {"timestamp", "hostname", "id", "package"} | {"name"},
            "testsuites",
        )
        suites = [child for child in root if local_name(child.tag) == "testsuite"]
        unknown = [local_name(child.tag) for child in root if local_name(child.tag) != "testsuite"]
        if unknown:
            raise StrictJUnitError(f"testsuites 包含未知子元素：{', '.join(sorted(set(unknown)))}")
        if not suites:
            raise StrictJUnitError("testsuites 没有 testcase 明细")
        details = [_validate_suite(suite, seen) for suite in suites]
        for detail in details:
            _add(counts, detail)
        declared = {attr: _summary_count(root, attr, "testsuites") for attr in COUNT_ATTRS}
        actual = {
            "tests": sum(detail.tests for detail in details),
            "failures": sum(detail.failures for detail in details),
            "errors": sum(detail.errors for detail in details),
            "skipped": sum(detail.skipped for detail in details),
        }
        for attr, value in declared.items():
            if value is not None and value != actual[attr]:
                raise StrictJUnitError(
                    f"testsuites 汇总计数与明细不一致：{attr} 声明 {value} / 明细 {actual[attr]}"
                )
        root_time = _time(root, "testsuites")
        if root_time is not None and not any(detail.duration for detail in details):
            counts.duration = root_time
    if counts.tests == 0:
        raise StrictJUnitError("文档没有 testcase 明细")
    if counts.passed < 0:
        raise StrictJUnitError("明细计数非法：passed < 0")
    return counts


def count_text(text: str) -> Counts:
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise StrictJUnitError(f"XML 解析失败：{exc}") from exc
    return aggregate(root)


def count_file(path: Path) -> Counts:
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise StrictJUnitError(f"JUnit XML 无法读取：{path}：{exc}") from exc
    if size > MAX_BYTES:
        raise StrictJUnitError(f"JUnit XML 超过 {MAX_BYTES} bytes：{path}（{size} bytes）")
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise StrictJUnitError(f"JUnit XML 无法读取：{path}：{exc}") from exc
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as exc:
        raise StrictJUnitError(f"XML 解析失败：{path}：{exc}") from exc
    return aggregate(root)
