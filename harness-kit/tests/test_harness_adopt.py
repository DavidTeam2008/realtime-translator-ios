#!/usr/bin/env python3
"""Acceptance tests for harness-kit/scripts/harness-adopt (read-only adoption inventory).

Contract: harness-kit/SPEC.md §8 (script conventions) / §9 (tests).
Runs the real CLI against temporary git fixtures; no network, no Xcode, no third-party deps.

Run: python3 -m unittest discover -s harness-kit/tests -q
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
ADOPT = KIT / "scripts" / "harness-adopt"
PLACEHOLDER_RE = re.compile(r"\{\{[A-Z0-9_]+\}\}")
LOCAL_PATH_RE = re.compile(r"/(?:Users|Volumes|home)/")


# ── helpers ───────────────────────────────────────────────────────────────
def run(cmd: list[str], cwd: Path | str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd, cwd=str(cwd), capture_output=True, text=True, timeout=120
    )


def git(target: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return run(["git", "-C", str(target), *args], cwd=target)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def make_fixture(root: Path) -> Path:
    """Minimal legacy project with the exact findings the report must surface."""
    target = root / "demo-project"
    (target / "docs").mkdir(parents=True)
    (target / "build").mkdir()
    (target / "src").mkdir()
    write(target / "README.md", "# Demo project\n\nA legacy project for inventory tests.\n")
    write(target / "NOTES.md", "# Scratch notes\n\nKeep this file out of the doc tree.\n")
    write(target / "docs" / "README.md", "# Docs index\n\n- [Guide](guide.md)\n")
    write(target / "docs" / "guide.md", "# Guide\n")
    write(target / "docs" / "extra.md", "# Extra doc\n\nNot linked from the docs index.\n")
    write(target / "docs" / "broken.md", "# Broken\n\n- [Missing](does-not-exist.md)\n")
    write(
        target / "docs" / "fence.md",
        "# Fence\n\n```text\nopened and never closed\n",
    )
    # Build the fixture path from parts so no absolute local path literal lands in the repo.
    write(target / "docs" / "local.md", "# Local\n\nPath: " + "/Us" + "ers/alice/demo-project\n")
    write(
        target / "docs" / "stale.md",
        "# Stale\n\n此方案已废弃，等待清理。\n\n写于实现之前，已被推翻；尚未编译，待真机验证。\n",
    )
    write(target / "src" / "app.py", "def main():\n    return 0\n")
    write(target / "build.gradle", "plugins {}\n")
    write(target / "build" / "output.bin", "binary-ish artifact\n")
    # Gradle wrapper files are legitimate tracked tooling even though they look build-like.
    write(target / "gradlew", "#!/bin/sh\n")
    write(target / "gradle" / "wrapper" / "gradle-wrapper.jar", "wrapper jar\n")
    write(target / "gradle" / "wrapper" / "gradle-wrapper.jar.sha256", "0" * 64 + "\n")
    write(target / ".gitignore", "build/\n")
    os.symlink("/tmp", target / "abs-link")
    run(["git", "init", "-q"], cwd=target)
    git(target, "config", "user.name", "kit-test")
    git(target, "config", "user.email", "kit-test@example.invalid")
    git(target, "add", "-A")
    git(target, "add", "-f", "build/output.bin")  # simulate a tracked build artifact
    git(target, "commit", "-q", "-m", "init")
    return target


def make_kit(root: Path, *, template: str | None = None) -> Path:
    kit = root / "fake-kit"
    (kit / "core" / "templates" / "harness" / "plans").mkdir(parents=True)
    (kit / "VERSION").write_text("9.9.9\n", encoding="utf-8")
    if template is not None:
        (kit / "core" / "templates" / "harness" / "plans" / "_adoption.md.template").write_text(
            template, encoding="utf-8"
        )
    return kit


ADOPTION_TEMPLATE = """---
id: <date>-<topic>
status: <status>
level: L2
owner: <owner>
updated: <date>
scope:
  allow:
    - .
acceptance:
  - <fill me>
verify:
  - make check
---

# {{PROJECT_NAME}} · harness-kit 接入计划

- 建议 profile：{{PROFILE}}
- test 命令：`{{TEST_COMMAND}}`
- 盘点摘要：{{SUMMARY}}

## 发现

{{FINDINGS}}

## 风险

{{RISKS}}

## 下一步

{{NEXT_STEPS}}
"""


def snapshot(root: Path) -> dict[str, tuple]:
    """Content snapshot of everything except .git (used to prove the default run is read-only)."""
    result: dict[str, tuple] = {}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if rel == ".git" or rel.startswith(".git/"):
            continue
        if path.is_symlink():
            result[rel] = ("link", os.readlink(path))
        elif path.is_file():
            result[rel] = ("file", path.stat().st_size, path.read_bytes())
        else:
            result[rel] = ("dir",)
    return result


class HarnessAdoptTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.target = make_fixture(self.tmp)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def invoke(self, *args: str, target: Path | None = None) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, str(ADOPT), "--target", str(target or self.target), *args]
        return run(command, cwd=KIT)

    # ── packaging / CLI guard ────────────────────────────────────────
    def test_script_is_executable_with_shebang(self) -> None:
        self.assertTrue(ADOPT.is_file(), "harness-adopt is missing")
        self.assertTrue(os.access(ADOPT, os.X_OK), "harness-adopt must be executable")
        first_line = ADOPT.read_text(encoding="utf-8").splitlines()[0]
        self.assertTrue(first_line.startswith("#!"), first_line)
        self.assertIn("python3", first_line)

    def test_invalid_target_exits_one(self) -> None:
        proc = self.invoke(target=self.tmp / "does-not-exist")
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("target directory does not exist", proc.stderr)
        self.assertTrue(ADOPT.is_file())

    # ── default read-only Markdown run ───────────────────────────────
    def test_default_run_is_read_only_and_reports_findings(self) -> None:
        before = snapshot(self.target)
        started = time.monotonic()
        proc = self.invoke()
        elapsed = time.monotonic() - started
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertLess(elapsed, 5.0, "inventory should be fast")
        self.assertEqual(before, snapshot(self.target), "default run must not modify the target")
        report = proc.stdout
        for heading in ("## 概览", "## 文档盘点", "## 卫生盘点", "## 建议", "## 下一步"):
            self.assertIn(heading, report)
        for expected in (
            "NOTES.md",             # root markdown outside the documented entry set
            "docs/extra.md",        # doc missing from docs/README.md index
            "does-not-exist.md",    # broken relative link sample
            "build/output.bin",     # tracked build artifact
            "abs-link",             # absolute symlink
            "断链",                 # broken-link section
            "围栏",                 # odd code-fence section
            "过期",                 # stale marker section
            "本机路径",             # machine-local path section
            "既有门禁文件",         # existing gates
            "- [ ]",                # next-step checklist
        ):
            self.assertIn(expected, report)
        self.assertIn("本机路径样本", report)
        self.assertIn("/<local>/", report)  # local paths are masked in the report
        self.assertNotIn("alice", report, "report must not leak the raw local path")

    # ── JSON contract ────────────────────────────────────────────────
    def test_json_output_contract(self) -> None:
        proc = self.invoke("--json")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        data = json.loads(proc.stdout)
        for key in (
            "target", "kitVersion", "generatedAt", "readOnly",
            "overview", "docs", "hygiene", "recommendation", "nextSteps", "writePlan",
        ):
            self.assertIn(key, data)
        self.assertTrue(data["readOnly"])
        self.assertIn("android", data["overview"]["languages"])  # build.gradle → android
        self.assertEqual("./gradlew testDebugUnitTest", data["recommendation"]["testCommand"])
        self.assertTrue(data["overview"]["git"]["isRepo"])
        self.assertGreaterEqual(data["overview"]["git"]["tracked"], 10)
        self.assertIn("docs/extra.md", data["docs"]["unregistered"])
        self.assertTrue(data["docs"]["hasIndex"])  # docs/README.md exists
        self.assertIn("build/output.bin", data["hygiene"]["trackedBuildArtifacts"])
        tracked = data["hygiene"]["trackedBuildArtifacts"]
        for allowed in (
            "gradlew",
            "gradle/wrapper/gradle-wrapper.jar",
            "gradle/wrapper/gradle-wrapper.jar.sha256",
        ):
            self.assertNotIn(allowed, tracked, f"{allowed} is legitimate wrapper tooling")
        stale = "\n".join(data["docs"]["staleMarkers"])
        self.assertIn("已被推翻", stale)
        self.assertIn("待真机验证", stale)
        absolute = [item["path"] for item in data["hygiene"]["absoluteSymlinks"]]
        self.assertIn("abs-link", absolute)
        self.assertTrue(data["hygiene"]["localPathHits"])
        self.assertIn(data["recommendation"]["profile"], ("minimal", "standard", "strict"))
        self.assertIn("testCommand", data["recommendation"])
        self.assertTrue(data["recommendation"]["risks"])
        self.assertFalse(data["writePlan"]["written"])

    # ── --report ────────────────────────────────────────────────────
    def test_report_written_to_requested_path(self) -> None:
        before = snapshot(self.target)
        report_path = self.tmp / "reports" / "adopt.md"
        report_path.parent.mkdir()
        proc = self.invoke("--report", str(report_path))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertTrue(report_path.is_file())
        self.assertIn("## 概览", report_path.read_text(encoding="utf-8"))
        self.assertIn("[OK] report written", proc.stdout)
        self.assertEqual(before, snapshot(self.target), "--report must not modify the target")

    # ── --write-plan ────────────────────────────────────────────────
    def test_write_plan_requires_plans_dir(self) -> None:
        before = snapshot(self.target)
        proc = self.invoke("--write-plan")
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("harness/plans", proc.stderr)
        self.assertEqual(before, snapshot(self.target))

    def test_write_plan_renders_kit_template(self) -> None:
        kit = make_kit(self.tmp, template=ADOPTION_TEMPLATE)
        (self.target / "harness" / "plans").mkdir(parents=True)
        before = snapshot(self.target)
        proc = self.invoke("--write-plan", "--root", str(kit))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        plans = sorted((self.target / "harness" / "plans").glob("*-adopt-harness.md"))
        self.assertEqual(len(plans), 1, proc.stdout)
        plan = plans[0].read_text(encoding="utf-8")
        self.assertNotRegex(plan, PLACEHOLDER_RE)
        self.assertIn("demo-project", plan)
        self.assertIn("profile", plan)
        self.assertRegex(plans[0].name, r"^\d{4}-\d{2}-\d{2}-adopt-harness\.md$")
        after = snapshot(self.target)
        new_files = set(after) - set(before)
        self.assertEqual(new_files, {f"harness/plans/{plans[0].name}"})
        self.assertIn("[OK] adoption plan written", proc.stdout)

    def test_write_plan_missing_template_reports_error(self) -> None:
        kit = make_kit(self.tmp, template=None)
        (self.target / "harness" / "plans").mkdir(parents=True)
        proc = self.invoke("--write-plan", "--root", str(kit))
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("adoption plan template not found", proc.stderr)
        self.assertFalse(list((self.target / "harness" / "plans").glob("*.md")))

    def test_write_plan_refuses_to_overwrite(self) -> None:
        kit = make_kit(self.tmp, template=ADOPTION_TEMPLATE)
        (self.target / "harness" / "plans").mkdir(parents=True)
        first = self.invoke("--write-plan", "--root", str(kit))
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        plans = list((self.target / "harness" / "plans").glob("*-adopt-harness.md"))
        self.assertEqual(len(plans), 1)
        original = plans[0].read_text(encoding="utf-8")
        second = self.invoke("--write-plan", "--root", str(kit))
        self.assertEqual(second.returncode, 1, second.stdout + second.stderr)
        self.assertIn("refusing to overwrite", second.stderr)
        self.assertEqual(original, plans[0].read_text(encoding="utf-8"))

    def test_android_command_falls_back_without_gradlew(self) -> None:
        plain = self.tmp / "android-no-wrapper"
        write(plain / "build.gradle", "plugins {}\n")
        proc = self.invoke("--json", target=plain)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        data = json.loads(proc.stdout)
        self.assertEqual("gradle testDebugUnitTest", data["recommendation"]["testCommand"])

    def test_json_with_write_plan_keeps_stdout_pure_json(self) -> None:
        kit = make_kit(self.tmp, template=ADOPTION_TEMPLATE)
        (self.target / "harness" / "plans").mkdir(parents=True)
        proc = self.invoke("--write-plan", "--json", "--root", str(kit))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        data = json.loads(proc.stdout)  # raises if any non-JSON line leaked into stdout
        self.assertTrue(data["writePlan"]["written"])
        self.assertEqual(1, len(list((self.target / "harness" / "plans").glob("*-adopt-harness.md"))))

    # ── non-git target ──────────────────────────────────────────────
    def test_non_git_target_is_scanned_without_git(self) -> None:
        plain = self.tmp / "plain"
        write(plain / "README.md", "# Plain\n")
        write(plain / "docs" / "README.md", "# Docs\n")
        os.symlink("/tmp", plain / "absolute-link")
        proc = self.invoke("--json", target=plain)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        data = json.loads(proc.stdout)
        self.assertFalse(data["overview"]["git"]["isRepo"])
        self.assertTrue(any(item["path"] == "absolute-link" for item in data["hygiene"]["symlinks"]))
        self.assertTrue(data["hygiene"]["absoluteSymlinks"])


if __name__ == "__main__":
    unittest.main()
