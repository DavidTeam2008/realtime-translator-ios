#!/usr/bin/env python3
"""harness-kit end-to-end acceptance: init each profile into a blank git repo.

Contract: harness-kit/SPEC.md §9. No network, no Xcode, standard library only.
Runs real subprocesses (harness-init + make) against temp directories.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
INIT = KIT / "scripts" / "harness-init"
PROFILES = ("minimal", "standard", "strict")
PLACEHOLDER_LEFT = re.compile(r"\{\{[A-Z0-9_]+\}\}")


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)


def init_target(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    run(["git", "init", "-q"], cwd=path)
    for key, value in (("user.name", "kit-test"), ("user.email", "kit-test@example.invalid")):
        run(["git", "config", key, value], cwd=path)
    (path / "README.md").write_text("# Test Project\n", encoding="utf-8")
    (path / "app.py").write_text("def main():\n    return 0\n", encoding="utf-8")
    run(["git", "add", "-A"], cwd=path)
    run(["git", "commit", "-q", "-m", "init"], cwd=path)
    return path


def tree_files(root: Path) -> list[Path]:
    files = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in (".git", ".harness-init-backup") for part in path.parts):
            continue
        files.append(path)
    return files


class HarnessInitProfileTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def invoke(self, *args: str, target: Path) -> subprocess.CompletedProcess[str]:
        return run(
            [sys.executable, str(INIT), "--target", str(target), *args],
            cwd=KIT,
        )

    def test_profiles_init_and_check(self) -> None:
        if not INIT.is_file():
            self.skipTest("harness-init is not present")
        for profile in PROFILES:
            with self.subTest(profile=profile):
                target = init_target(self.tmp / profile)
                proc = self.invoke(
                    "--profile", profile, "--name", "Test Project", "--test-command", "echo ok",
                    target=target,
                )
                self.assertEqual(proc.returncode, 0, f"{profile} init failed:\n{proc.stdout}\n{proc.stderr}")
                self.assertIn("post-init check: PASS", proc.stdout)
                self.assertTrue((target / "AGENTS.md").is_file())
                self.assertTrue((target / "harness" / "config.json").is_file())
                if profile in ("standard", "strict"):
                    self.assertTrue((target / "harness" / "plans" / "_template.md").is_file())
                    self.assertTrue((target / "tools" / "verify_claim.py").is_file())
                    static = run(["make", "verify-static"], cwd=target)
                    self.assertEqual(static.returncode, 0, f"{profile} verify-static failed:\n{static.stdout}\n{static.stderr}")
                if profile == "strict":
                    self.assertTrue((target / "docs" / "harness-scorecard.md").is_file())
                    self.assertTrue((target / ".dsh" / "skills" / "red-team" / "SKILL.md").is_file())
                # no unresolved placeholders / Duiyi terms in the generated tree
                for path in tree_files(target):
                    text = path.read_text(encoding="utf-8", errors="ignore")
                    if "/tools/" not in path.as_posix():
                        # copied scripts may legitimately contain {{PLACEHOLDER}} literals
                        # used for runtime substitution (e.g. plan template keys)
                        self.assertIsNone(PLACEHOLDER_LEFT.search(text), f"placeholder left in {path}")
                    self.assertNotRegex(text, r"(?i)duiyi|对译|TranslationSession|SwiftData", f"Duiyi reference in {path}")

    def test_standalone_copy_init(self) -> None:
        """Kit 目录复制到仓库外后仍可 init（无来源仓库依赖）。"""
        if not INIT.is_file():
            self.skipTest("harness-init is not present")
        standalone = self.tmp / "standalone-kit"
        shutil.copytree(KIT, standalone, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        target = init_target(self.tmp / "standalone-target")
        proc = run(
            [sys.executable, str(standalone / "scripts" / "harness-init"),
             "--profile", "minimal", "--target", str(target), "--name", "Standalone"],
            cwd=self.tmp,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("post-init check: PASS", proc.stdout)

    def test_test_command_inference(self) -> None:
        """--language inference: node scripts.test / node --test / swift Package.swift / xcodeproj."""
        if not INIT.is_file():
            self.skipTest("harness-init is not present")
        cases = []
        node_with_script = self.tmp / "node-with-script"
        node_with_script.mkdir()
        (node_with_script / "package.json").write_text(
            json.dumps({"name": "x", "scripts": {"test": "node --test"}}), encoding="utf-8"
        )
        cases.append((node_with_script, "node", "test=npm test", "scripts.test"))
        node_no_script = self.tmp / "node-no-script"
        node_no_script.mkdir()
        (node_no_script / "package.json").write_text(json.dumps({"name": "x"}), encoding="utf-8")
        cases.append((node_no_script, "node", "test=node --test", "no scripts.test"))
        swift_pkg = self.tmp / "swift-pkg"
        swift_pkg.mkdir()
        (swift_pkg / "Package.swift").write_text("// swift-tools-version:5.9\n", encoding="utf-8")
        cases.append((swift_pkg, "swift", "test=swift test", "Package.swift"))
        xcode = self.tmp / "xcode-app"
        xcode.mkdir()
        (xcode / "App.xcodeproj").mkdir()
        (xcode / "App.xcodeproj" / "project.pbxproj").write_text("// stub\n", encoding="utf-8")
        cases.append((xcode, "swift", "test=xcodebuild test", "cannot infer the scheme"))
        for target, language, expected, note in cases:
            with self.subTest(case=target.name):
                proc = self.invoke(
                    "--profile", "minimal", "--language", language, "--dry-run", target=target
                )
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                self.assertIn(expected, proc.stdout)
                self.assertIn(note, proc.stdout)

    def test_gitignore_covers_common_build_artifacts(self) -> None:
        if not INIT.is_file():
            self.skipTest("harness-init is not present")
        target = init_target(self.tmp / "ignore")
        proc = self.invoke(
            "--profile", "minimal", "--name", "Ignore", "--test-command", "echo ok", target=target
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        gitignore = (target / ".gitignore").read_text(encoding="utf-8")
        for entry in ("node_modules/", ".build/", ".swiftpm/", "__pycache__/"):
            self.assertIn(entry, gitignore)

    def test_standard_evidence_lifecycle(self) -> None:
        """standard/strict 的「测试 → 证据 → 三值判定」链路必须端到端可用。"""
        if not INIT.is_file():
            self.skipTest("harness-init is not present")
        target = init_target(self.tmp / "evidence")
        proc = self.invoke(
            "--profile", "standard", "--name", "Evidence Demo", "--test-command", "echo ok",
            target=target,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        for cmd in (["git", "add", "-A"], ["git", "commit", "-q", "-m", "harness scaffold"]):
            done = run(cmd, cwd=target)
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        draft = {
            "schemaVersion": 1,
            "claim": "tests-pass",
            "command": "echo ok",
            "environment": {"project": "Evidence Demo", "toolchain": "python", "os": "test"},
            "result": {"status": "SUCCEEDED", "passed": 1, "failed": 0, "skipped": 0, "durationSec": 0.1},
            "verdict": "PASS",
            "verifier": "kit-test",
        }
        draft_path = self.tmp / "draft.json"
        draft_path.write_text(json.dumps(draft), encoding="utf-8")
        write = run([sys.executable, "tools/evidence.py", "write", "--from-json", str(draft_path)], cwd=target)
        self.assertEqual(write.returncode, 0, write.stdout + write.stderr)
        claim = run([sys.executable, "tools/verify_claim.py", "--all"], cwd=target)
        self.assertEqual(claim.returncode, 0, claim.stdout + claim.stderr)
        self.assertRegex(claim.stdout, r"CLAIM .*: PASS — ")

    def test_strict_release_check_after_evidence(self) -> None:
        if not INIT.is_file():
            self.skipTest("harness-init is not present")
        target = init_target(self.tmp / "release")
        proc = self.invoke(
            "--profile", "strict", "--name", "Release Demo", "--test-command", "echo ok",
            target=target,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        for cmd in (["git", "add", "-A"], ["git", "commit", "-q", "-m", "harness scaffold"]):
            done = run(cmd, cwd=target)
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        draft = {
            "schemaVersion": 1,
            "claim": "tests-pass",
            "command": "echo ok",
            "environment": {"project": "Release Demo", "toolchain": "python", "os": "test"},
            "result": {"status": "SUCCEEDED", "passed": 1, "failed": 0, "skipped": 0, "durationSec": 0.1},
            "verdict": "PASS",
            "verifier": "kit-test",
        }
        draft_path = self.tmp / "draft.json"
        draft_path.write_text(json.dumps(draft), encoding="utf-8")
        write = run([sys.executable, "tools/evidence.py", "write", "--from-json", str(draft_path)], cwd=target)
        self.assertEqual(write.returncode, 0, write.stdout + write.stderr)
        release = run(["make", "release-check"], cwd=target)
        self.assertEqual(release.returncode, 0, release.stdout + release.stderr)

    def test_dry_run_writes_nothing(self) -> None:
        if not INIT.is_file():
            self.skipTest("harness-init is not present")
        target = init_target(self.tmp / "dry")
        before = sorted(p.relative_to(target).as_posix() for p in tree_files(target))
        proc = self.invoke("--profile", "minimal", "--dry-run", target=target)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("dry-run", proc.stdout)
        after = sorted(p.relative_to(target).as_posix() for p in tree_files(target))
        self.assertEqual(before, after)

    def test_conflict_refused_and_force_backs_up(self) -> None:
        if not INIT.is_file():
            self.skipTest("harness-init is not present")
        target = init_target(self.tmp / "conflict")
        first = self.invoke("--profile", "minimal", "--name", "X", "--test-command", "echo ok", target=target)
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        second = self.invoke("--profile", "minimal", "--name", "X", target=target)
        self.assertEqual(second.returncode, 1, second.stdout + second.stderr)
        self.assertIn("CONFLICT", second.stdout + second.stderr)
        agents = target / "AGENTS.md"
        agents.write_text("# locally edited\n", encoding="utf-8")
        forced = self.invoke(
            "--profile", "minimal", "--name", "X", "--test-command", "echo ok", "--force", "--no-check",
            target=target,
        )
        self.assertEqual(forced.returncode, 0, forced.stdout + forced.stderr)
        backup_root = target / ".harness-init-backup"
        self.assertTrue(backup_root.is_dir(), "backup directory missing")
        backups = list(backup_root.rglob("AGENTS.md"))
        self.assertTrue(backups, "AGENTS.md backup missing")
        self.assertEqual(backups[0].read_text(encoding="utf-8"), "# locally edited\n")
        self.assertNotEqual(agents.read_text(encoding="utf-8"), "# locally edited\n")

    def test_existing_makefile_gets_fragment(self) -> None:
        if not INIT.is_file():
            self.skipTest("harness-init is not present")
        target = init_target(self.tmp / "makefile")
        original = "all:\n\t@echo original\n"
        (target / "Makefile").write_text(original, encoding="utf-8")
        proc = self.invoke("--profile", "minimal", "--name", "X", "--test-command", "echo ok", target=target)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual((target / "Makefile").read_text(encoding="utf-8"), original)
        self.assertTrue((target / "Makefile.harness").is_file())
        self.assertIn("include Makefile.harness", proc.stdout)
        check = run(["make", "-f", "Makefile.harness", "check"], cwd=target)
        self.assertEqual(check.returncode, 0, check.stdout + check.stderr)

    def test_unknown_profile_fails(self) -> None:
        target = init_target(self.tmp / "bad")
        proc = self.invoke("--profile", "does-not-exist", target=target)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("ERROR", proc.stderr)


if __name__ == "__main__":
    unittest.main()
