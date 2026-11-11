#!/usr/bin/env python3
"""Acceptance tests for `.harness-manifest.json` + `scripts/harness-upgrade` (read-only upgrade).

Uses a real `harness-init --profile standard` host in a temporary git repo and the real CLI.
No network, no Xcode; standard library only.
Run: python3 -m unittest discover -s harness-kit/tests -q
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
INIT = KIT / "scripts" / "harness-init"
UPGRADE = KIT / "scripts" / "harness-upgrade"
VERSION = (KIT / "VERSION").read_text(encoding="utf-8").strip()
MANIFEST = ".harness-manifest.json"


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


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def init_host(root: Path, name: str, *, profile: str = "standard", adapters: str = "ci,githooks") -> Path:
    host = root / name
    init_git(host)
    cmd = [
        sys.executable, str(INIT),
        "--profile", profile,
        "--target", str(host),
        "--name", "Upgrade Demo",
        "--language", "python",
        "--test-command", "make test",
        "--adapters", adapters,
        "--force",
        "--no-check",
    ]
    proc = run(cmd, cwd=KIT)
    if proc.returncode != 0:
        raise AssertionError(f"harness-init failed:\n{proc.stdout}\n{proc.stderr}")
    assert git(host, "add", "-A").returncode == 0
    assert git(host, "commit", "-q", "-m", "scaffold").returncode == 0
    return host


def load_manifest(host: Path) -> dict:
    return json.loads((host / MANIFEST).read_text(encoding="utf-8"))


def save_manifest(host: Path, manifest: dict) -> None:
    (host / MANIFEST).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def upgrade(host: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return run([sys.executable, str(UPGRADE), "--target", str(host), *args], cwd=KIT)


class ManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.tmp = Path(cls._tmp.name)
        cls.host = init_host(cls.tmp, "manifest-host")

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_manifest_records_version_profile_options_and_hashes(self) -> None:
        manifest = load_manifest(self.host)
        self.assertEqual(1, manifest["schemaVersion"])
        self.assertEqual(VERSION, manifest["kitVersion"])
        self.assertEqual("standard", manifest["profile"])
        self.assertEqual(
            {"name": "Upgrade Demo", "language": "python", "testCommand": "make test",
             "adapters": ["ci", "githooks"]},
            {key: manifest["options"][key] for key in ("name", "language", "testCommand", "adapters")},
        )
        self.assertIn("branch", manifest["options"])
        paths = {item["path"] for item in manifest["files"]}
        for required in ("AGENTS.md", "HARNESS.md", "Makefile", "harness/config.json", "tools/verify_claim.py"):
            self.assertIn(required, paths)
        self.assertNotIn(MANIFEST, paths)  # manifest does not manage itself
        for item in manifest["files"]:
            self.assertEqual(sha256(self.host / item["path"]), item["sha256"], item["path"])
        appends = {item["path"]: item for item in manifest["appends"]}
        self.assertIn(".gitignore", appends)
        self.assertIn("# harness-kit", (self.host / ".gitignore").read_text(encoding="utf-8"))

    def test_manifest_not_written_on_dry_run(self) -> None:
        host = self.tmp / "dry-host"
        init_git(host)
        proc = run(
            [sys.executable, str(INIT), "--profile", "minimal", "--target", str(host),
             "--language", "python", "--test-command", "make test", "--dry-run"],
            cwd=KIT,
        )
        self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)
        self.assertFalse((host / MANIFEST).exists())


class UpgradeCheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.tmp = Path(cls._tmp.name)
        cls.host = init_host(cls.tmp, "check-host")

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_check_in_sync(self) -> None:
        proc = upgrade(self.host, "--check")
        self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)
        self.assertIn("IN SYNC", proc.stdout)

    def test_check_reports_local_drift(self) -> None:
        path = self.host / "AGENTS.md"
        original = path.read_text(encoding="utf-8")
        try:
            path.write_text(original + "\nlocal edit\n", encoding="utf-8")
            proc = upgrade(self.host, "--check")
            self.assertEqual(1, proc.returncode, proc.stdout + proc.stderr)
            self.assertIn("LOCAL_CHANGED", proc.stdout)
            self.assertIn("AGENTS.md", proc.stdout)
        finally:
            path.write_text(original, encoding="utf-8")

    def test_check_reports_version_mismatch_exit_three(self) -> None:
        config_path = self.host / "harness" / "config.json"
        original = config_path.read_text(encoding="utf-8")
        try:
            config = json.loads(original)
            config["kitVersion"] = "0.2.3"
            config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
            proc = upgrade(self.host, "--check")
            self.assertEqual(3, proc.returncode, proc.stdout + proc.stderr)
            self.assertIn("VERSION_MISMATCH", proc.stdout)
        finally:
            config_path.write_text(original, encoding="utf-8")

    def test_check_reports_append_block_missing(self) -> None:
        path = self.host / ".gitignore"
        original = path.read_text(encoding="utf-8")
        try:
            lines = [line for line in original.splitlines() if "harness-kit" not in line]
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            proc = upgrade(self.host, "--check")
            self.assertEqual(1, proc.returncode, proc.stdout + proc.stderr)
            self.assertIn("APPEND_MISSING", proc.stdout)
        finally:
            path.write_text(original, encoding="utf-8")

    def test_check_legacy_target_exit_two(self) -> None:
        legacy = self.tmp / "legacy-host"
        init_git(legacy)
        proc = upgrade(legacy, "--check")
        self.assertEqual(2, proc.returncode, proc.stdout + proc.stderr)
        self.assertIn("manifest", proc.stdout + proc.stderr)


class UpgradePlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.tmp = Path(cls._tmp.name)
        cls.host = init_host(cls.tmp, "plan-host")

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def status(self, host: Path) -> str:
        return git(host, "status", "--porcelain", "--untracked-files=all").stdout

    def test_plan_in_sync_is_read_only(self) -> None:
        before = self.status(self.host)
        proc = upgrade(self.host, "--plan")
        self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)
        self.assertIn("SAME", proc.stdout)
        self.assertIn("read-only", proc.stdout)
        self.assertEqual(before, self.status(self.host))
        self.assertFalse(list(self.host.glob(".harness-upgrade-*")))

    def test_plan_classifies_actions(self) -> None:
        host = init_host(self.tmp, "classify")
        manifest = load_manifest(host)
        files = {item["path"]: item for item in manifest["files"]}
        # UPGRADE: local content equals the recorded old hash, upstream differs.
        (host / "AGENTS.md").write_text("old generated\n", encoding="utf-8")
        files["AGENTS.md"]["sha256"] = hashlib.sha256(b"old generated\n").hexdigest()
        # CONFLICT: local edit differs from both old hash and upstream render.
        (host / "HARNESS.md").write_text("local edit\n", encoding="utf-8")
        files["HARNESS.md"]["sha256"] = hashlib.sha256(b"other old\n").hexdigest()
        # LOCAL_ONLY: recorded old hash == upstream render; local file was edited.
        docs = host / "docs" / "AGENTS.md"
        original = docs.read_bytes()
        files["docs/AGENTS.md"]["sha256"] = hashlib.sha256(original).hexdigest()
        docs.write_text("local-only edit\n", encoding="utf-8")
        # ADD: drop a manifest entry and remove the file; upstream render adds it back.
        added = "tools/token_estimate.py"
        (host / added).unlink()
        files.pop(added)
        # OBSOLETE: entry that no longer exists upstream.
        files["docs/legacy.md"] = {"path": "docs/legacy.md", "sha256": "0" * 64,
                                   "src": "legacy", "render": True}
        manifest["files"] = list(files.values())
        manifest["skipped"] = []
        save_manifest(host, manifest)
        before = self.status(host)
        proc = upgrade(host, "--plan")
        self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)
        output = proc.stdout
        for action in ("UPGRADE", "CONFLICT", "LOCAL_ONLY", "ADD", "OBSOLETE"):
            self.assertIn(action, output, f"missing {action} in:\n{output}")
        self.assertEqual(before, self.status(host), "upgrade --plan must not modify the target")

    def test_plan_legacy_target_lists_conflicts_read_only(self) -> None:
        host = init_host(self.tmp, "legacy-plan")
        (host / MANIFEST).unlink()
        path = host / "AGENTS.md"
        path.write_text(path.read_text(encoding="utf-8") + "\nlegacy edit\n", encoding="utf-8")
        before = self.status(host)
        proc = upgrade(
            host, "--plan", "--profile", "standard", "--name", "Upgrade Demo",
            "--language", "python", "--test-command", "make test", "--adapters", "ci,githooks",
        )
        self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)
        self.assertIn("CONFLICT", proc.stdout)
        self.assertIn("legacy", proc.stdout)
        self.assertEqual(before, self.status(host))

    def test_plan_fail_on_conflict_exit_one(self) -> None:
        host = init_host(self.tmp, "fail-conflict")
        (host / MANIFEST).unlink()
        (host / "AGENTS.md").write_text("different\n", encoding="utf-8")
        proc = upgrade(host, "--plan", "--profile", "minimal", "--fail-on-conflict")
        self.assertEqual(1, proc.returncode, proc.stdout + proc.stderr)


class UpgradeCliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.tmp = Path(cls._tmp.name)
        cls.host = init_host(cls.tmp, "cli-host")

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_apply_is_explicitly_unimplemented(self) -> None:
        proc = upgrade(self.host, "--apply")
        self.assertEqual(2, proc.returncode, proc.stdout + proc.stderr)
        self.assertIn("未实现", proc.stderr)

    def test_check_json_contract(self) -> None:
        proc = upgrade(self.host, "--check", "--json")
        self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)
        data = json.loads(proc.stdout)
        for key in ("mode", "target", "kitVersion", "manifestKitVersion", "configKitVersion",
                    "problems", "drift", "inSync"):
            self.assertIn(key, data)
        self.assertTrue(data["inSync"])

    def test_plan_json_contract(self) -> None:
        proc = upgrade(self.host, "--plan", "--json")
        self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)
        data = json.loads(proc.stdout)
        for key in ("mode", "target", "kitVersion", "profile", "rows", "summary", "readOnly"):
            self.assertIn(key, data)
        self.assertTrue(data["readOnly"])
        actions = {row["action"] for row in data["rows"]}
        self.assertIn("SAME", actions)


if __name__ == "__main__":
    unittest.main()
