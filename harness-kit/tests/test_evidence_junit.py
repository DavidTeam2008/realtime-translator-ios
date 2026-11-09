#!/usr/bin/env python3
"""Regression tests for `tools/evidence_from_junit.py` (unittest, standard library only).

Covers: single/multiple suites & files, failure/error/skipped counting, duration
aggregation (testcase time + suite attribute fallback), directory/glob expansion,
malformed/missing XML (exit 2), missing --command (exit 2), --output content,
required payload keys, and `tools/evidence.py write --from-json` acceptance.

Run: cd harness-kit && PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -q
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
TOOL = KIT / "core" / "tools" / "evidence_from_junit.py"
EVIDENCE_TOOL = KIT / "core" / "tools" / "evidence.py"
EVIDENCE_SCHEMA = KIT / "core" / "templates" / "harness" / "evidence" / "schema.json"


def run_tool(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(TOOL), *args], cwd=str(cwd), capture_output=True, text=True, timeout=60
    )


def suite_xml(name: str, cases: str, *, attrs: str = "", wrap: bool = False) -> str:
    body = f'<testsuite name="{name}" {attrs}>{cases}</testsuite>'
    return f'<?xml version="1.0" encoding="UTF-8"?>\n{wrapper(body) if wrap else body}'


def wrapper(*suites: str) -> str:
    bodies = []
    for suite in suites:
        lines = suite.splitlines()
        if lines and lines[0].lstrip().startswith("<?xml"):
            lines = lines[1:]
        bodies.append("\n".join(lines))
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n<testsuites>\n'
        + "\n".join(bodies)
        + "\n</testsuites>"
    )


class JUnitAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="junit-evidence-")
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    # --- helpers ---------------------------------------------------------
    def write(self, rel: str, content: str) -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def invoke(self, *args: str, command: str = "make test") -> subprocess.CompletedProcess[str]:
        return run_tool(["--root", str(self.root), "--command", command, *args], self.root)

    def payload(self, *args: str, command: str = "make test") -> dict:
        result = self.invoke(*args, command=command)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        data = json.loads(result.stdout)
        self.assertIsInstance(data, dict)
        return data

    # --- counting --------------------------------------------------------
    def test_single_suite_passing(self) -> None:
        self.write(
            "reports/TEST-a.xml",
            suite_xml(
                "a",
                '<testcase name="t1" classname="A" time="0.1"/>'
                '<testcase name="t2" classname="A" time="0.2"/>',
            ),
        )
        data = self.payload("--xml", "reports/TEST-a.xml")
        self.assertEqual(data["schemaVersion"], 1)
        self.assertEqual(data["claim"], "tests-pass")
        self.assertEqual(data["command"], "make test")
        self.assertEqual(data["result"]["status"], "SUCCEEDED")
        self.assertEqual(data["verdict"], "PASS")
        self.assertEqual(data["result"]["passed"], 2)
        self.assertEqual(data["result"]["failed"], 0)
        self.assertEqual(data["result"]["skipped"], 0)
        self.assertAlmostEqual(data["result"]["durationSec"], 0.3)
        self.assertEqual(len(data["result"]["artifacts"]), 1)

    def test_failure_and_skipped_counts(self) -> None:
        self.write(
            "reports/TEST-a.xml",
            suite_xml(
                "a",
                '<testcase name="ok" classname="A" time="0.1"/>'
                '<testcase name="bad" classname="A" time="0.2">'
                '<failure message="boom">trace</failure></testcase>'
                '<testcase name="skip" classname="A" time="0.3">'
                '<skipped message="no device"/></testcase>',
            ),
        )
        data = self.payload("--xml", "reports/TEST-a.xml")
        result = data["result"]
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(data["verdict"], "FAIL")
        self.assertEqual((result["passed"], result["failed"], result["skipped"]), (1, 1, 1))
        self.assertAlmostEqual(result["durationSec"], 0.6)
        # 3 个 testcase: passed = tests - failed - skipped
        self.assertEqual(result["passed"], 3 - result["failed"] - result["skipped"])

    def test_error_child_counts_as_failed(self) -> None:
        self.write(
            "reports/TEST-e.xml",
            suite_xml(
                "e",
                '<testcase name="err" classname="E" time="0.4">'
                '<error message="kaboom"/></testcase>',
            ),
        )
        data = self.payload("--xml", "reports/TEST-e.xml")
        self.assertEqual(data["result"]["failed"], 1)
        self.assertEqual(data["result"]["status"], "FAILED")
        self.assertEqual(data["verdict"], "FAIL")

    def test_multiple_xml_files_aggregate(self) -> None:
        self.write("reports/a/TEST-a.xml", suite_xml("a", '<testcase name="t1" time="0.1"/>'))
        self.write(
            "reports/b/TEST-b.xml",
            suite_xml(
                "b",
                '<testcase name="t2" time="0.2"/><testcase name="t3" time="0.2">'
                "<failure/></testcase>",
            ),
        )
        data = self.payload(
            "--xml", "reports/a/TEST-a.xml", "--xml", "reports/b/TEST-b.xml"
        )
        result = data["result"]
        self.assertEqual(result["passed"], 2)
        self.assertEqual(result["failed"], 1)
        self.assertAlmostEqual(result["durationSec"], 0.5)
        self.assertEqual(len(result["artifacts"]), 2)

    def test_testsuites_root_with_multiple_suites(self) -> None:
        content = wrapper(
            suite_xml("s1", '<testcase name="t1" time="0.1"/><testcase name="t2" time="0.1"/>'),
            suite_xml("s2", '<testcase name="t3" time="0.1"><skipped/></testcase>'),
        )
        self.write("reports/all/TEST-all.xml", content)
        data = self.payload("--xml", "reports/all")
        result = data["result"]
        self.assertEqual((result["passed"], result["failed"], result["skipped"]), (2, 0, 1))
        self.assertEqual(result["status"], "SUCCEEDED")
        self.assertAlmostEqual(result["durationSec"], 0.3)

    def test_suite_attribute_fallback_without_testcases(self) -> None:
        self.write(
            "reports/TEST-attr.xml",
            '<?xml version="1.0"?><testsuite name="attr" tests="5" failures="1" '
            'errors="1" skipped="2" time="1.25"/>',
        )
        data = self.payload("--xml", "reports/TEST-attr.xml")
        result = data["result"]
        # tests=5, failed=failures+errors=2, skipped=2 → passed=1
        self.assertEqual((result["passed"], result["failed"], result["skipped"]), (1, 2, 2))
        self.assertEqual(result["status"], "FAILED")
        self.assertAlmostEqual(result["durationSec"], 1.25)

    def test_suite_time_fallback_when_no_case_times(self) -> None:
        self.write(
            "reports/TEST-time.xml",
            suite_xml("t", '<testcase name="t1"/><testcase name="t2"/>', attrs='time="2.5"'),
        )
        data = self.payload("--xml", "reports/TEST-time.xml")
        self.assertAlmostEqual(data["result"]["durationSec"], 2.5)

    def test_duration_is_rounded_to_milliseconds(self) -> None:
        self.write(
            "reports/TEST-d.xml",
            suite_xml(
                "d",
                '<testcase name="t1" time="0.1234"/><testcase name="t2" time="0.0006"/>',
            ),
        )
        data = self.payload("--xml", "reports/TEST-d.xml")
        self.assertEqual(data["result"]["durationSec"], 0.124)

    def test_directory_pattern_is_searched_recursively(self) -> None:
        self.write("build/one/TEST-1.xml", suite_xml("one", '<testcase name="t1" time="0.1"/>'))
        self.write("build/two/nested/TEST-2.xml", suite_xml("two", '<testcase name="t2" time="0.1"/>'))
        data = self.payload("--xml", "build")
        self.assertEqual(data["result"]["passed"], 2)
        self.assertEqual(len(data["result"]["artifacts"]), 2)

    # --- CLI options -----------------------------------------------------
    def test_claim_environment_notes_are_passed_through(self) -> None:
        self.write("reports/TEST-a.xml", suite_xml("a", '<testcase name="t1" time="0.1"/>'))
        data = self.payload(
            "--xml",
            "reports",
            "--claim",
            "tests-pass",
            "--environment",
            "os=linux",
            "--environment",
            "toolchain=java",
            "--notes",
            "nightly smoke",
        )
        self.assertEqual(data["claim"], "tests-pass")
        self.assertEqual(data["environment"], {"os": "linux", "toolchain": "java"})
        self.assertEqual(data["notes"], "nightly smoke")

    def test_output_file_contains_required_keys(self) -> None:
        self.write("reports/TEST-a.xml", suite_xml("a", '<testcase name="t1" time="0.1"/>'))
        result = self.invoke(
            "--xml", "reports", "--command", "make test", "--output", "payload.json"
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("[OK] wrote", result.stdout)
        target = self.root / "payload.json"
        self.assertTrue(target.is_file())
        data = json.loads(target.read_text(encoding="utf-8"))
        for key in ("schemaVersion", "claim", "command", "environment", "result", "verdict", "verifier"):
            self.assertIn(key, data)
        for key in ("status", "passed", "failed", "skipped", "durationSec"):
            self.assertIn(key, data["result"])
        self.assertEqual(data["result"]["passed"], 1)
        self.assertEqual(data["result"]["status"], "SUCCEEDED")

    # --- error handling --------------------------------------------------
    def test_missing_xml_glob_exits_2(self) -> None:
        result = self.invoke("--xml", "reports/missing/*.xml")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("[FAIL]", result.stderr)
        self.assertIn("未匹配到 XML", result.stderr)

    def test_malformed_xml_exits_2(self) -> None:
        self.write("reports/TEST-bad.xml", "<testsuite><testcase></testsuite>")
        result = self.invoke("--xml", "reports")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("[FAIL]", result.stderr)
        self.assertIn("解析失败", result.stderr)

    def test_missing_command_exits_2(self) -> None:
        self.write("reports/TEST-a.xml", suite_xml("a", '<testcase name="t1"/>'))
        result = run_tool(["--root", str(self.root), "--xml", "reports"], self.root)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)

    def test_invalid_environment_exits_2(self) -> None:
        self.write("reports/TEST-a.xml", suite_xml("a", '<testcase name="t1"/>'))
        result = self.invoke("--xml", "reports", "--environment", "no-equals-sign")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("KEY=VALUE", result.stderr)

    # --- integration with evidence.py ------------------------------------
    def test_payload_is_accepted_by_evidence_write(self) -> None:
        project = self.root / "project"
        reports = project / "build" / "reports" / "tests"
        reports.mkdir(parents=True)
        (reports / "TEST-a.xml").write_text(
            suite_xml("a", '<testcase name="t1" time="0.1"/><testcase name="t2" time="0.2"/>'),
            encoding="utf-8",
        )
        (project / "tools").mkdir()
        shutil.copy2(EVIDENCE_TOOL, project / "tools" / "evidence.py")
        (project / "harness" / "evidence").mkdir(parents=True)
        shutil.copy2(EVIDENCE_SCHEMA, project / "harness" / "evidence" / "schema.json")
        config = {
            "kitVersion": "0.2.1",
            "project": {"name": "Demo", "language": "android"},
            "paths": {
                "docs": "docs",
                "references": "references",
                "harness": "harness",
                "plans": "harness/plans",
                "evidence": "harness/evidence",
                "tools": "tools",
            },
            "commands": {"test": "./gradlew testDebugUnitTest"},
            "claims": [
                {
                    "name": "tests-pass",
                    "type": "test-count",
                    "baseline": "harness/test-baseline.json",
                    "floor": "unit.floor",
                    "expectedSkipped": "unit.expectedSkipped",
                    "command": "./gradlew testDebugUnitTest",
                }
            ],
        }
        (project / "harness" / "config.json").write_text(
            json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        git = ["git", "-C", str(project)]
        subprocess.run([*git, "init", "-q"], check=True)
        subprocess.run([*git, "config", "user.name", "kit-test"], check=True)
        subprocess.run([*git, "config", "user.email", "kit-test@example.invalid"], check=True)
        subprocess.run([*git, "add", "-A"], check=True)
        subprocess.run([*git, "commit", "-q", "-m", "harness"], check=True)

        produced = run_tool(
            [
                "--root",
                str(project),
                "--xml",
                "build/reports/tests",
                "--command",
                "./gradlew testDebugUnitTest",
                "--output",
                str(project / "payload.json"),
            ],
            self.root,
        )
        self.assertEqual(produced.returncode, 0, produced.stdout + produced.stderr)
        subprocess.run([*git, "add", "-A"], check=True)
        subprocess.run([*git, "commit", "-q", "-m", "payload"], check=True)
        written = subprocess.run(
            [sys.executable, "tools/evidence.py", "write", "--from-json", "payload.json"],
            cwd=str(project),
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(written.returncode, 0, written.stdout + written.stderr)
        self.assertIn("[OK] 已写入", written.stdout)
        evidence_files = sorted((project / "harness" / "evidence").glob("*.json"))
        self.assertTrue(
            [path for path in evidence_files if path.name != "schema.json"],
            "evidence record was not written",
        )


if __name__ == "__main__":
    unittest.main()
