#!/usr/bin/env python3
"""Acceptance tests for `scripts/harness-skill` (router skill install/check).

Uses real `harness-init` hosts in temporary git repos; no network, no Xcode.
Run: python3 -m unittest discover -s harness-kit/tests -q
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
INIT = KIT / "scripts" / "harness-init"
SKILL = KIT / "scripts" / "harness-skill"
VERSION = (KIT / "VERSION").read_text(encoding="utf-8").strip()


def run(cmd: list[str], cwd: Path,
        env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=300,
                          env=env)


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


class SkillScopeTests(unittest.TestCase):
    """v0.5.0: user scope (one install, all repos) + `.agents` + uninstall."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.home = self.tmp / "home"
        for name in (".agents", ".dsh", ".claude"):
            (self.home / name).mkdir(parents=True)
        self.env = dict(os.environ)
        self.env.update({
            "HOME": str(self.home),
            "DSH_HOME": str(self.home / ".dsh"),
            "DSH_AGENTS_HOME": str(self.home / ".agents"),
        })
        self.host = init_host(self.tmp, "scope-host")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def skill(self, *args: str, target: bool = True) -> subprocess.CompletedProcess[str]:
        cmd = [sys.executable, str(SKILL)]
        if target:
            cmd += ["--target", str(self.host)]
        return run([*cmd, *args], cwd=KIT, env=self.env)

    def user_skill_dir(self) -> Path:
        return self.home / ".agents" / "skills" / "harness"

    def test_user_install_check_uninstall(self) -> None:
        installed = self.skill("install", "--scope", "user")
        self.assertEqual(0, installed.returncode, installed.stdout + installed.stderr)
        self.assertTrue((self.user_skill_dir() / "SKILL.md").is_file())
        self.assertTrue((self.user_skill_dir() / "references" / "adopt.md").is_file())
        meta = json.loads((self.home / ".agents" / "skills" / ".harness-kit-skill.json")
                          .read_text(encoding="utf-8"))
        self.assertEqual(VERSION, meta["kitVersion"])
        self.assertIn("agents", meta["agents"])
        self.assertEqual(KIT.resolve().as_posix(), meta["kitRoot"])
        check = self.skill("check", "--scope", "user")
        self.assertEqual(0, check.returncode, check.stdout + check.stderr)
        self.assertIn("in sync", check.stdout)
        listing = json.loads(self.skill("list", "--json").stdout)
        row = [item for item in listing["agents"]
               if item["scope"] == "user" and item["agent"] == "agents"][0]
        self.assertTrue(row["installed"])
        drift_path = self.user_skill_dir() / "references" / "adopt.md"
        original = drift_path.read_text(encoding="utf-8")
        try:
            drift_path.write_text(original + "\nlocal edit\n", encoding="utf-8")
            drift = self.skill("check", "--scope", "user")
            self.assertEqual(1, drift.returncode, drift.stdout + drift.stderr)
            self.assertIn("adopt.md", drift.stdout)
        finally:
            drift_path.write_text(original, encoding="utf-8")
        removed = self.skill("uninstall", "--scope", "user")
        self.assertEqual(0, removed.returncode, removed.stdout + removed.stderr)
        self.assertFalse(self.user_skill_dir().exists())
        self.assertFalse((self.home / ".agents" / "skills" / ".harness-kit-skill.json").exists())
        self.assertEqual(2, self.skill("check", "--scope", "user").returncode)

    def test_user_dry_run_writes_nothing(self) -> None:
        proc = self.skill("install", "--scope", "user", "--dry-run")
        self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)
        self.assertIn("RENDER", proc.stdout)
        self.assertFalse((self.home / ".agents" / "skills").exists())

    def test_user_install_claude_code_agent(self) -> None:
        proc = self.skill("install", "--scope", "user", "--agent", "claude-code")
        self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)
        self.assertTrue((self.home / ".claude" / "skills" / "harness" / "SKILL.md").is_file())
        check = self.skill("check", "--scope", "user", "--agent", "claude-code")
        self.assertEqual(0, check.returncode, check.stdout + check.stderr)

    def test_project_agents_scope_install_and_uninstall(self) -> None:
        proc = self.skill("install", "--agent", "agents")
        self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)
        self.assertTrue((self.host / ".agents" / "skills" / "harness" / "SKILL.md").is_file())
        manifest = json.loads((self.host / ".harness-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(["agents"], manifest["skills"]["harness"]["agents"])
        self.assertEqual(0, self.skill("check", "--agent", "agents").returncode)
        removed = self.skill("uninstall", "--agent", "agents")
        self.assertEqual(0, removed.returncode, removed.stdout + removed.stderr)
        manifest = json.loads((self.host / ".harness-manifest.json").read_text(encoding="utf-8"))
        self.assertNotIn("harness", manifest.get("skills", {}))
        self.assertFalse((self.host / ".agents" / "skills" / "harness").exists())
        self.assertEqual(2, self.skill("check", "--agent", "agents").returncode)

    def test_uninstall_refuses_local_edits_without_force(self) -> None:
        assert self.skill("install", "--agent", "dsh").returncode == 0
        path = self.host / ".dsh" / "skills" / "harness" / "SKILL.md"
        path.write_text(path.read_text(encoding="utf-8") + "\nlocal edit\n", encoding="utf-8")
        refused = self.skill("uninstall", "--agent", "dsh")
        self.assertEqual(2, refused.returncode, refused.stdout + refused.stderr)
        self.assertIn("--force", refused.stderr)
        forced = self.skill("uninstall", "--agent", "dsh", "--force")
        self.assertEqual(0, forced.returncode, forced.stdout + forced.stderr)


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
