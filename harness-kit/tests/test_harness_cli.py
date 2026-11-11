#!/usr/bin/env python3
"""Acceptance tests for `tools/harness.py` (v0.3.0-alpha unified entry).

Uses real `harness-init` hosts in temporary git repos (standard + minimal) and the
real Makefile targets; no network, no Xcode; standard library only.
Run: python3 -m unittest discover -s harness-kit/tests -q
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
INIT = KIT / "scripts" / "harness-init"


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=300)


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return run(["git", *args], cwd=repo)


def init_git(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    assert git(repo, "init", "-q").returncode == 0
    for key, value in (("user.name", "kit-test"), ("user.email", "kit-test@example.invalid")):
        assert git(repo, "config", key, value).returncode == 0
    (repo / "README.md").write_text("# Host project\n", encoding="utf-8")
    (repo / "app.py").write_text("def main():\n    return 0\n", encoding="utf-8")
    assert git(repo, "add", "-A").returncode == 0
    assert git(repo, "commit", "-q", "-m", "init").returncode == 0


def init_host(root: Path, name: str, *, profile: str = "standard", adapters: str = "ci,githooks") -> Path:
    host = root / name
    init_git(host)
    proc = run(
        [
            sys.executable, str(INIT), "--profile", profile, "--target", str(host),
            "--name", "CLI Demo", "--language", "python", "--test-command", "make test",
            "--adapters", adapters, "--force", "--no-check",
        ],
        cwd=KIT,
    )
    if proc.returncode != 0:
        raise AssertionError(f"harness-init failed:\n{proc.stdout}\n{proc.stderr}")
    assert git(host, "add", "-A").returncode == 0
    assert git(host, "commit", "-q", "-m", "scaffold").returncode == 0
    return host


def harness(host: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return run([sys.executable, "tools/harness.py", *args], cwd=host)


class StatusTests(unittest.TestCase):
    def test_status_without_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            host = init_host(Path(tmp), "status-host")
            proc = harness(host, "status")
            self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)
            self.assertIn("无 active 计划", proc.stdout)
            self.assertIn("start --topic", proc.stdout)
            data = json.loads(harness(host, "status", "--json").stdout)
            for key in ("project", "kitVersion", "manifestKitVersion", "profile", "plan",
                        "git", "evidence", "nextActions"):
                self.assertIn(key, data)
            self.assertIsNone(data["plan"])
            self.assertTrue(data["nextActions"])

    def test_status_is_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            host = init_host(Path(tmp), "readonly-host")
            before = git(host, "status", "--porcelain", "--untracked-files=all").stdout
            harness(host, "status")
            after = git(host, "status", "--porcelain", "--untracked-files=all").stdout
            self.assertEqual(before, after)


class PlanFlowTests(unittest.TestCase):
    def test_start_is_idempotent_and_make_check_green(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            host = init_host(Path(tmp), "start-host")
            proc = harness(host, "start", "--topic", "demo-task", "--goal", "验证 CLI", "--scope", "src/")
            self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)
            plans = sorted((host / "harness" / "plans").glob("*-demo-task.md"))
            self.assertEqual(1, len(plans))
            text = plans[0].read_text(encoding="utf-8")
            self.assertIn("status: active", text)
            self.assertIn("owner: kit-test", text)
            self.assertIn("harness/plans/", text)
            check = run(["make", "check"], cwd=host)
            self.assertEqual(0, check.returncode, check.stdout + check.stderr)
            # 幂等：再次 start 不新建第二个计划
            again = harness(host, "start", "--topic", "demo-task")
            self.assertEqual(0, again.returncode, again.stdout + again.stderr)
            self.assertIn("SKIP", again.stdout)
            self.assertEqual(1, len(list((host / "harness" / "plans").glob("*-demo-task.md"))))

    def test_verify_syncs_uncommitted_and_handoff_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            host = init_host(Path(tmp), "verify-host")
            self.assertEqual(0, harness(host, "start", "--topic", "demo", "--goal", "验证同步", "--scope", "src/").returncode)
            (host / "src").mkdir(exist_ok=True)
            (host / "src" / "a.py").write_text("VALUE = 2\n", encoding="utf-8")
            proc = harness(host, "verify")
            self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)
            self.assertIn("已同步", proc.stdout)
            self.assertIn("== verify: PASS ==", proc.stdout)
            plan = next((host / "harness" / "plans").glob("*-demo.md")).read_text(encoding="utf-8")
            self.assertIn("src/a.py", plan)
            status = json.loads(harness(host, "status", "--json").stdout)
            self.assertTrue(status["git"]["inSync"], status["git"])
            handoff = harness(host, "handoff", "--json")
            self.assertEqual(0, handoff.returncode, handoff.stdout + handoff.stderr)
            data = json.loads(handoff.stdout)
            self.assertIn("plan", data)
            self.assertIn("evidence", data)
            human = harness(host, "handoff")
            self.assertEqual(0, human.returncode, human.stdout + human.stderr)
            self.assertIn("# handoff", human.stdout)

    def test_plan_check_and_upgrade_stub(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            host = init_host(Path(tmp), "misc-host")
            self.assertEqual(0, harness(host, "start", "--topic", "misc").returncode)
            self.assertEqual(0, harness(host, "plan", "check").returncode)
            upgrade = harness(host, "upgrade")
            self.assertEqual(0, upgrade.returncode, upgrade.stdout + upgrade.stderr)
            self.assertIn("harness-upgrade", upgrade.stdout)
            apply = harness(host, "upgrade", "--apply")
            self.assertEqual(2, apply.returncode, apply.stdout + apply.stderr)
            self.assertIn("未实现", apply.stderr)


class IntakeReleaseTests(unittest.TestCase):
    def test_intake_creates_plan_and_make_check_green(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            host = init_host(Path(tmp), "intake-host")
            card = host / "harness" / "requirements" / "export.md"
            card.parent.mkdir(parents=True, exist_ok=True)
            card.write_text(
                "# 需求卡\n\n## 目标\n\n- 支持导出字幕\n\n"
                "## 验收判据\n\n- `make test` exit 0\n",
                encoding="utf-8",
            )
            proc = harness(host, "intake", "--file", "harness/requirements/export.md", "--scope", "src/")
            self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)
            plans = sorted((host / "harness" / "plans").glob("*-export.md"))
            self.assertEqual(1, len(plans))
            text = plans[0].read_text(encoding="utf-8")
            self.assertIn("支持导出字幕", text)
            self.assertIn("`make test` exit 0", text)
            self.assertEqual(0, run(["make", "check"], cwd=host).returncode)

    def test_intake_rejects_vague_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            host = init_host(Path(tmp), "intake-bad")
            card = host / "requirement.md"
            card.write_text("# 卡\n\n## 目标\n\n- 更好用\n\n## 验收判据\n\n- 体验好\n", encoding="utf-8")
            before = sorted(path.name for path in (host / "harness" / "plans").glob("*.md"))
            proc = harness(host, "intake", "--file", "requirement.md")
            self.assertEqual(2, proc.returncode, proc.stdout + proc.stderr)
            self.assertIn("验收判据不可执行", proc.stderr)
            self.assertEqual(before, sorted(path.name for path in (host / "harness" / "plans").glob("*.md")))

    def test_release_without_evidence_exit_two(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            host = init_host(Path(tmp), "release-empty")
            proc = harness(host, "release", "--check")
            self.assertEqual(2, proc.returncode, proc.stdout + proc.stderr)
            self.assertIn("== release: FAIL ==", proc.stdout)

    def test_release_passes_with_fresh_rerunnable_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            host = init_host(Path(tmp), "release-pass")
            (host / "harness" / "runs").mkdir(parents=True, exist_ok=True)
            (host / "harness" / "runs" / "junit.xml").write_text(
                '<testsuite name="s" tests="1"><testcase classname="t" name="ok"/></testsuite>',
                encoding="utf-8",
            )
            commit = git(host, "rev-parse", "--short=12", "HEAD").stdout.strip()
            evidence = {
                "schemaVersion": 1,
                "id": "20260101T000000Z-tests-pass",
                "claim": "tests-pass",
                "createdAt": "2026-01-01T00:00:00Z",
                "git": {"commit": commit, "dirty": False},
                "command": "make test",
                "environment": {"project": "CLI Demo", "toolchain": "python", "os": "test"},
                "result": {
                    "status": "SUCCEEDED", "passed": 1, "failed": 0, "skipped": 0,
                    "durationSec": 0.1, "artifacts": ["harness/runs/junit.xml"],
                },
                "verdict": "PASS",
                "verifier": "kit-test",
            }
            (host / "harness" / "evidence" / "20260101T000000Z-tests-pass.json").write_text(
                json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            proc = harness(host, "release", "--check")
            self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)
            self.assertIn("== release: PASS ==", proc.stdout)


class MinimalProfileTests(unittest.TestCase):
    def test_status_works_and_start_fails_without_plans(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            host = init_host(Path(tmp), "minimal-host", profile="minimal", adapters="none")
            status = harness(host, "status")
            self.assertEqual(0, status.returncode, status.stdout + status.stderr)
            self.assertIn("无 active 计划", status.stdout)
            start = harness(host, "start", "--topic", "x")
            self.assertEqual(2, start.returncode, start.stdout + start.stderr)
            self.assertIn("plans", start.stderr)


if __name__ == "__main__":
    unittest.main()
