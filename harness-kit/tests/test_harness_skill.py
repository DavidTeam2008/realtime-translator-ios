#!/usr/bin/env python3
"""Acceptance tests for `scripts/harness-skill` (router skill install/check).

Uses real `harness-init` hosts in temporary git repos; no network, no Xcode.
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
SKILL = KIT / "scripts" / "harness-skill"
VERSION = (KIT / "VERSION").read_text(encoding="utf-8").strip()


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=300)


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return run(["git", *args], cwd=repo)


def init_host(root: Path, name: str) -> Path:
    host = root / name
    host.mkdir(parents=True, exist_ok=True)
    assert git(host, "init", "-q").returncode == 0
    for key, value in (("user.name", "kit-test"), ("user.email", "kit-test@example.invalid")):
        assert git(host, "config", key, value).returncode == 0
    (host / "README.md").write_text("# Host\n", encoding="utf-8")
    assert git(host, "add", "-A").returncode == 0
    assert git(host, "commit", "-q", "-m", "init").returncode == 0
    proc = run(
        [sys.executable, str(INIT), "--profile", "standard", "--target", str(host),
         "--name", "Skill Demo", "--language", "python", "--test-command", "make test",
         "--adapters", "none", "--force", "--no-check"],
        cwd=KIT,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert git(host, "add", "-A").returncode == 0
    assert git(host, "commit", "-q", "-m", "scaffold").returncode == 0
    return host


def skill(host: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return run([sys.executable, str(SKILL), "--target", str(host), *args], cwd=KIT)


class SkillInstallTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.tmp = Path(cls._tmp.name)
        cls.host = init_host(cls.tmp, "skill-host")
        installed = skill(cls.host, "install", "--agent", "dsh,claude-code")
        if installed.returncode != 0:
            raise AssertionError("skill install failed: " + installed.stdout + installed.stderr)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_install_check_list_and_manifest(self) -> None:
        proc = skill(self.host, "install", "--agent", "dsh")
        self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)
        self.assertTrue((self.host / ".dsh" / "skills" / "harness" / "SKILL.md").is_file())
        self.assertTrue((self.host / ".dsh" / "skills" / "harness" / "references" / "verify.md").is_file())
        manifest = json.loads((self.host / ".harness-manifest.json").read_text(encoding="utf-8"))
        recorded = manifest["skills"]["harness"]
        self.assertEqual(VERSION, recorded["kitVersion"])
        self.assertEqual(["dsh"], recorded["agents"])
        self.assertIn("SKILL.md", recorded["files"])
        check = skill(self.host, "check")
        self.assertEqual(0, check.returncode, check.stdout + check.stderr)
        self.assertIn("in sync", check.stdout)
        listing = skill(self.host, "list", "--json")
        self.assertEqual(0, listing.returncode)
        data = json.loads(listing.stdout)
        self.assertTrue(any(row["agent"] == "dsh" and row["installed"] for row in data["agents"]))

    def test_check_detects_drift(self) -> None:
        path = self.host / ".dsh" / "skills" / "harness" / "references" / "verify.md"
        original = path.read_text(encoding="utf-8")
        try:
            path.write_text(original + "\nlocal edit\n", encoding="utf-8")
            proc = skill(self.host, "check")
            self.assertEqual(1, proc.returncode, proc.stdout + proc.stderr)
            self.assertIn("verify.md", proc.stdout)
        finally:
            path.write_text(original, encoding="utf-8")
            self.assertEqual(0, skill(self.host, "check").returncode)

    def test_install_conflict_and_force(self) -> None:
        path = self.host / ".dsh" / "skills" / "harness" / "SKILL.md"
        original = path.read_text(encoding="utf-8")
        try:
            path.write_text(original + "\nlocal edit\n", encoding="utf-8")
            conflict = skill(self.host, "install", "--agent", "dsh")
            self.assertEqual(2, conflict.returncode, conflict.stdout + conflict.stderr)
            self.assertIn("--force", conflict.stderr)
            forced = skill(self.host, "install", "--agent", "dsh", "--force")
            self.assertEqual(0, forced.returncode, forced.stdout + forced.stderr)
            self.assertEqual(original, path.read_text(encoding="utf-8"))
        finally:
            path.write_text(original, encoding="utf-8")
            skill(self.host, "install", "--agent", "dsh", "--force")

    def test_dry_run_writes_nothing(self) -> None:
        host = init_host(self.tmp, "dry-host")
        before = sorted(p.relative_to(host).as_posix() for p in host.rglob("*") if p.is_file())
        proc = skill(host, "install", "--dry-run")
        self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)
        self.assertIn("RENDER", proc.stdout)
        after = sorted(p.relative_to(host).as_posix() for p in host.rglob("*") if p.is_file())
        self.assertEqual(before, after)
        self.assertFalse((host / ".dsh").exists())

    def test_legacy_target_without_manifest(self) -> None:
        host = init_host(self.tmp, "legacy-skill")
        (host / ".harness-manifest.json").unlink()
        proc = skill(host, "install", "--agent", "claude-code")
        self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)
        self.assertIn("legacy", proc.stdout)
        self.assertTrue((host / ".claude" / "skills" / "harness" / "SKILL.md").is_file())
        self.assertEqual(0, skill(host, "check").returncode)

    def test_check_not_installed_exit_two(self) -> None:
        host = init_host(self.tmp, "not-installed")
        proc = skill(host, "check")
        self.assertEqual(2, proc.returncode, proc.stdout + proc.stderr)
        self.assertIn("未安装", proc.stdout)


class SkillContentTests(unittest.TestCase):
    def test_skill_front_matter_and_budget(self) -> None:
        base = KIT / "skills" / "harness"
        text = (base / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\n"))
        front = text.split("---", 2)[1]
        self.assertIn("name: harness", front)
        self.assertIn("description:", front)
        self.assertLessEqual(len(text.splitlines()), 120)
        refs = sorted((base / "references").glob("*.md"))
        self.assertGreaterEqual(len(refs), 6)
        total = sum(len(path.read_text(encoding="utf-8").splitlines()) for path in refs)
        self.assertLessEqual(total, 1200)
        for path in refs:
            self.assertNotIn("Duiyi", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
