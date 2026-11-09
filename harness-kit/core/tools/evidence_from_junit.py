#!/usr/bin/env python3
"""JUnit XML → harness evidence payload adapter (standard library only).

Usage:
    python3 tools/evidence_from_junit.py --xml GLOB [--xml GLOB ...] \
        --command "CMD" [--claim NAME] [--environment K=V ...] \
        [--notes TEXT] [--output PATH] [--root PATH]

Aggregates one or more JUnit XML reports (`testsuites` / `testsuite` / `testcase`)
and prints (or writes) a JSON payload accepted by
`tools/evidence.py write --from-json`:

    {
      "schemaVersion": 1,
      "claim": "tests-pass",
      "command": ".",
      "environment": {"source": "junit-xml"},
      "result": {
        "status": "SUCCEEDED|FAILED",
        "passed": 12, "failed": 1, "skipped": 2, "durationSec": 3.14,
        "artifacts": ["build/reports/tests/TEST-x.xml"]
      },
      "verdict": "PASS|FAIL",
      "verifier": "tools/evidence_from_junit.py"
    }

Counting rules:
  - tests   = <testcase> elements (a <testsuite> with no testcase children falls
              back to its `tests` attribute);
  - failed  = <failure> + <error> child elements (a test with both counts twice);
  - skipped = <skipped> child elements;
  - passed  = max(0, tests - failed - skipped);
  - status  = SUCCEEDED when failed == 0 else FAILED (skips are expected);
  - verdict = PASS when failed == 0 else FAIL;
  - durationSec = sum of testcase `time` attributes; when a suite's testcases
              carry no `time` attribute (or the suite has no testcase children),
              the testsuite `time` attribute is used instead (rounded to 3 decimals).

`--xml` patterns may be files, directories (searched recursively for `*.xml`) or
globs, resolved relative to `--root` (default: script parent parent). Every
pattern must match at least one `*.xml` file. `--output` is also relative to
`--root` when relative. Hit content is not interpreted: this adapter only counts.

Exit codes: 0 = payload produced; 2 = usage error / missing or malformed XML.
No third-party dependencies, no network; only `--output` is written.
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

DEFAULT_CLAIM = "tests-pass"
VERIFIER = "tools/evidence_from_junit.py"


class JUnitError(Exception):
    """User-facing failure (exit 2)."""


@dataclass
class Counts:
    """Aggregated JUnit counters."""

    tests: int = 0
    failed: int = 0
    skipped: int = 0
    duration: float = 0.0


def local_name(tag: str) -> str:
    """Strip an XML namespace from a tag name."""
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def as_int(value: object, default: int = 0) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def as_float(value: object, default: float = 0.0) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return default


def display(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def count_case(element: ET.Element, counts: Counts) -> None:
    counts.tests += 1
    counts.duration += as_float(element.get("time"))
    for child in element:
        name = local_name(child.tag)
        if name in ("failure", "error"):
            counts.failed += 1
        elif name == "skipped":
            counts.skipped += 1


def count_suite(suite: ET.Element, counts: Counts) -> None:
    cases = [child for child in suite if local_name(child.tag) == "testcase"]
    if cases:
        has_case_time = any(case.get("time") is not None for case in cases)
        for case in cases:
            count_case(case, counts)
        if not has_case_time:
            # Reporters that keep the duration only at suite level.
            counts.duration += as_float(suite.get("time"))
        return
    # Report-only suite (no testcase children): trust the aggregation attributes.
    counts.tests += as_int(suite.get("tests"))
    counts.failed += as_int(suite.get("failures")) + as_int(suite.get("errors"))
    counts.skipped += as_int(suite.get("skipped"))
    counts.duration += as_float(suite.get("time"))


def aggregate(root: ET.Element) -> Counts:
    """Aggregate one parsed JUnit document; tolerates testsuites/testsuite/testcase roots."""
    counts = Counts()
    tag = local_name(root.tag)
    if tag == "testcase":
        count_case(root, counts)
        return counts
    if tag == "testsuite":
        count_suite(root, counts)
        return counts
    suites = [child for child in root if local_name(child.tag) == "testsuite"]
    if not suites:
        suites = [element for element in root.iter() if local_name(element.tag) == "testsuite"]
    if suites:
        for suite in suites:
            count_suite(suite, counts)
        return counts
    # Unknown wrapper without suites: treat it as an attribute-only suite container.
    count_suite(root, counts)
    return counts


def resolve_xml_patterns(root: Path, patterns: list[str]) -> tuple[list[Path], list[str]]:
    """Expand --xml file/dir/glob patterns into a de-duplicated, sorted file list."""
    files: list[Path] = []
    problems: list[str] = []
    seen: set[Path] = set()
    for pattern in patterns:
        candidate = Path(pattern).expanduser()
        search = str(candidate if candidate.is_absolute() else root / candidate)
        matches = sorted(glob.glob(search, recursive=True))
        found: list[Path] = []
        for match in matches:
            path = Path(match)
            if path.is_dir():
                found.extend(sorted(path.rglob("*.xml")))
            elif path.is_file() and path.suffix.lower() == ".xml":
                found.append(path)
        if not found:
            problems.append(f"--xml 模式未匹配到 XML 文件：{pattern}")
            continue
        for path in found:
            resolved = path.resolve()
            if resolved not in seen:
                seen.add(resolved)
                files.append(resolved)
    if not patterns:
        problems.append("至少需要一个 --xml GLOB")
    return files, problems


def parse_environment(pairs: list[str]) -> dict[str, str]:
    environment: dict[str, str] = {}
    for pair in pairs:
        if "=" not in pair:
            raise JUnitError(f"--environment 需要 KEY=VALUE 形式：{pair!r}")
        key, value = pair.split("=", 1)
        key = key.strip()
        if not key:
            raise JUnitError(f"--environment 的 KEY 不能为空：{pair!r}")
        environment[key] = value
    return environment or {"source": "junit-xml"}


def build_payload(
    root: Path,
    files: list[Path],
    claim: str,
    command: str,
    environment: dict[str, str],
    notes: str | None,
) -> dict:
    totals = Counts()
    for path in files:
        try:
            element = ET.parse(path).getroot()
        except ET.ParseError as exc:
            raise JUnitError(f"JUnit XML 解析失败：{display(root, path)}：{exc}") from exc
        except OSError as exc:
            raise JUnitError(f"JUnit XML 无法读取：{display(root, path)}：{exc}") from exc
        counts = aggregate(element)
        totals.tests += counts.tests
        totals.failed += counts.failed
        totals.skipped += counts.skipped
        totals.duration += counts.duration
    passed = max(0, totals.tests - totals.failed - totals.skipped)
    payload: dict = {
        "schemaVersion": 1,
        "claim": claim,
        "command": command,
        "environment": environment,
        "result": {
            "status": "SUCCEEDED" if totals.failed == 0 else "FAILED",
            "passed": passed,
            "failed": totals.failed,
            "skipped": totals.skipped,
            "durationSec": round(totals.duration, 3),
            "artifacts": [display(root, path) for path in files],
        },
        "verdict": "PASS" if totals.failed == 0 else "FAIL",
        "verifier": VERIFIER,
    }
    if notes is not None:
        payload["notes"] = notes
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Aggregate JUnit XML into a harness evidence payload (JSON).",
    )
    parser.add_argument(
        "--xml",
        action="append",
        required=True,
        metavar="GLOB",
        help="JUnit XML file/directory/glob, relative to --root (repeatable)",
    )
    parser.add_argument("--claim", default=DEFAULT_CLAIM, help=f"claim name (default: {DEFAULT_CLAIM})")
    parser.add_argument("--command", required=True, help="command that produced these reports")
    parser.add_argument(
        "--environment",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="environment entry for the evidence record (repeatable)",
    )
    parser.add_argument("--notes", help="free-form notes stored in the evidence record")
    parser.add_argument("--output", metavar="PATH", help="write JSON here (default: stdout)")
    parser.add_argument(
        "--root",
        default=str(Path(__file__).resolve().parent.parent),
        help="project root for relative paths (default: script parent parent)",
    )
    return parser


def fail(message: str) -> int:
    print(f"[FAIL] {message}", file=sys.stderr)
    return 2


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        return fail(f"--root 目录不存在：{root}")
    command = args.command.strip()
    if not command:
        return fail("--command 不能为空（写入证据 provenance 的测试命令）")
    if not args.claim.strip():
        return fail("--claim 不能为空")

    files, problems = resolve_xml_patterns(root, args.xml)
    if problems:
        for problem in problems:
            print(f"[FAIL] {problem}", file=sys.stderr)
        return 2
    try:
        environment = parse_environment(args.environment)
        payload = build_payload(root, files, args.claim.strip(), command, environment, args.notes)
    except JUnitError as exc:
        return fail(str(exc))

    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        output = Path(args.output).expanduser()
        if not output.is_absolute():
            output = root / output
        try:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(text, encoding="utf-8")
        except OSError as exc:
            return fail(f"--output 写入失败：{output}：{exc}")
        result = payload["result"]
        print(
            f"[OK] wrote {display(root, output.resolve())} "
            f"(tests={result['status']} passed={result['passed']} "
            f"failed={result['failed']} skipped={result['skipped']})"
        )
        return 0
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
