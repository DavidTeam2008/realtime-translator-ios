#!/usr/bin/env python3
"""Regression tests for harness-kit/core/tools/adapters.py (stdlib only)."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ADAPTERS = REPO_ROOT / "harness-kit" / "core" / "tools" / "adapters.py"


def run(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ADAPTERS), *args],
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
    )


class AdaptersTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "harness").mkdir()
        (self.root / "harness" / "config.json").write_text(
            json.dumps({
                "kitVersion": "0.1.0",
                "project": {"name": "t", "language": "python"},
                "paths": {"docs": "docs", "references": "references", "harness": "harness",
                          "plans": "harness/plans", "evidence": "harness/evidence", "tools": "tools"},
                "commands": {"test": "echo ok"},
                "claims": [{"name": "docs-pass", "type": "static", "command": "python3 -c 'pass'"}],
                "adapters": {"claudeCode": {"skillsSource": ".dsh/skills", "skillsTarget": ".claude/skills"}},
            }),
            encoding="utf-8",
        )
        skill = self.root / ".dsh" / "skills" / "demo" / "SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("---\nname: demo\ndescription: d\n---\n\n# demo\n", encoding="utf-8")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_check_without_target_is_ok(self) -> None:
        proc = run("check", "--root", str(self.root))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("not installed", proc.stdout)

    def test_sync_then_check_passes(self) -> None:
        sync = run("sync", "--root", str(self.root))
        self.assertEqual(sync.returncode, 0, sync.stdout + sync.stderr)
        generated = self.root / ".claude" / "skills" / "demo" / "SKILL.md"
        self.assertTrue(generated.is_file())
        check = run("check", "--root", str(self.root))
        self.assertEqual(check.returncode, 0, check.stdout + check.stderr)

    def test_drift_fails(self) -> None:
        run("sync", "--root", str(self.root))
        generated = self.root / ".claude" / "skills" / "demo" / "SKILL.md"
        generated.write_text("tampered\n", encoding="utf-8")
        check = run("check", "--root", str(self.root))
        self.assertEqual(check.returncode, 1)
        self.assertIn("modified", check.stdout)

    def test_missing_config_fails(self) -> None:
        (self.root / "harness" / "config.json").unlink()
        proc = run("check", "--root", str(self.root))
        self.assertEqual(proc.returncode, 1)
        self.assertIn("missing config", proc.stderr)


if __name__ == "__main__":
    unittest.main()
