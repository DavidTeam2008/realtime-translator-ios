#!/usr/bin/env python3
"""Acceptance tests for the skill-side kit bootstrap (`skills/harness/scripts/kit-resolve.py`).

v0.5.4: the entry skill can be installed by `npx skills add ...` without a kit
clone; the resolver locates a kit (embedded / adopted fast path / metadata /
cache / pinned annotated-tag clone) and only clones into a user cache when
nothing local matches. No network: clone fixtures are local `file://` git repos.
Run: python3 -m unittest discover -s harness-kit/tests -q
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
VERSION = (KIT / "VERSION").read_text(encoding="utf-8").strip()
SKILL_MD = KIT / "skills" / "harness" / "SKILL.md"
RESOLVE = KIT / "skills" / "harness" / "scripts" / "kit-resolve.py"
OFFICIAL_REPO = "https://github.com/DavidTeam2008/harness-engineering-kit.git"


def skill_metadata() -> dict[str, str]:
    text = SKILL_MD.read_text(encoding="utf-8")
    front = text.split("---", 2)[1]
    meta: dict[str, str] = {}
    for key in ("kit_version", "min_version", "kit_repo"):
        match = re.search(rf"{key}:\s*([^,\n}}]+)", front)
        if match:
            meta[key] = match.group(1).strip()
    return meta


META = skill_metadata()


def run(cmd: list[str], cwd: Path,
        env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True,
                          timeout=300, env=env)


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return run(["git", *args], cwd=repo)


def init_repo(path: Path, version: str, *, annotated_tag: str | None = None,
              lightweight_tag: str | None = None) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    assert git(path, "init", "-q").returncode == 0
    for key, value in (("user.name", "kit-test"), ("user.email", "kit-test@example.invalid")):
        assert git(path, "config", key, value).returncode == 0
    (path / "VERSION").write_text(version + "\n", encoding="utf-8")
    (path / "scripts").mkdir(exist_ok=True)
    (path / "scripts" / "harness-adopt").write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    assert git(path, "add", "-A").returncode == 0
    assert git(path, "commit", "-q", "-m", "kit").returncode == 0
    if annotated_tag:
        assert git(path, "tag", "-a", annotated_tag, "-m", "kit release").returncode == 0
    if lightweight_tag:
        assert git(path, "tag", lightweight_tag).returncode == 0
    return path


def isolated_env(base: Path) -> dict[str, str]:
    home = base / "home"
    home.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env.update({
        "HOME": str(home),
        "XDG_CACHE_HOME": str(base / "cache"),
        "XDG_STATE_HOME": str(base / "state"),
    })
    for key in ("HARNESS_KIT_ROOT", "HARNESS_KIT_CACHE", "HARNESS_KIT_REPO",
                "DSH_HOME", "DSH_AGENTS_HOME"):
        env.pop(key, None)
    return env


class BootstrapTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)
        self.target = self.base / "target"
        self.target.mkdir()
        self.src = init_repo(self.base / "kit-src", META["kit_version"],
                             annotated_tag=f"v{META['kit_version']}")
        self.env = isolated_env(self.base)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def resolve(self, *args: str, expect: int = 0) -> subprocess.CompletedProcess[str]:
        proc = run([sys.executable, str(RESOLVE), "--target", str(self.target),
                    "--repo-url", f"file://{self.src}", *args], cwd=KIT, env=self.env)
        self.assertEqual(expect, proc.returncode, proc.stdout + proc.stderr)
        return proc

    def resolve_json(self, *args: str, expect: int = 0) -> dict:
        proc = self.resolve(*args, "--json", expect=expect)
        return json.loads(proc.stdout)

    def cache_dir(self) -> Path:
        base = Path(self.env["XDG_CACHE_HOME"]) / "harness-kit"
        matches = list(base.glob(f"*/v{META['kit_version']}"))
        self.assertEqual(1, len(matches), f"cache layout unexpected: {matches}")
        return matches[0]

    # ── metadata / packaging ─────────────────────────────────────────────
    def test_metadata_is_consistent_with_kit_version(self) -> None:
        self.assertEqual(VERSION, META["kit_version"])
        self.assertEqual(OFFICIAL_REPO, META["kit_repo"])
        self.assertTrue(META["min_version"])
        self.assertTrue(RESOLVE.is_file())

    # ── clone / cache ────────────────────────────────────────────────────
    def test_clone_from_annotated_tag(self) -> None:
        data = self.resolve_json()
        self.assertEqual("clone", data["source"])
        self.assertTrue(data["cloned"])
        self.assertEqual(META["kit_version"], data["version"])
        self.assertEqual("ok", data["versionStatus"])
        kit_root = Path(data["kitRoot"])
        self.assertEqual(META["kit_version"], (kit_root / "VERSION").read_text().strip())
        marker = json.loads((kit_root / ".harness-kit-cache.json").read_text(encoding="utf-8"))
        head = git(kit_root, "rev-parse", "HEAD").stdout.strip()
        self.assertEqual(head, marker["commitSha"])
        self.assertEqual(f"v{META['kit_version']}", marker["tag"])

    def test_cache_hit_does_not_touch_the_network(self) -> None:
        first = self.resolve_json()
        kit_root = Path(first["kitRoot"])
        # Move the source repository away: a cache hit must still resolve locally.
        self.src.rename(self.base / "kit-src-moved")
        on_proc = run([sys.executable, str(RESOLVE), "--target", str(self.target),
                       "--repo-url", f"file://{self.src}", "--json"], cwd=KIT, env=self.env)
        self.assertEqual(0, on_proc.returncode, on_proc.stdout + on_proc.stderr)
        data = json.loads(on_proc.stdout)
        self.assertEqual("cache", data["source"])
        self.assertTrue(data["cacheHit"])
        self.assertEqual(kit_root.as_posix(), data["kitRoot"])

    def test_offline_without_cache_fails_with_manual_command(self) -> None:
        proc = self.resolve("--offline", "--json", expect=2)
        data = json.loads(proc.stdout)
        self.assertFalse(data["ok"])
        self.assertIn("HARNESS_KIT_ROOT", data["error"])
        self.assertIn("git clone", data["error"])
        self.assertEqual([], list(self.target.iterdir()))

    def test_lightweight_tag_is_rejected(self) -> None:
        self.src = init_repo(self.base / "light-src", META["kit_version"],
                             lightweight_tag=f"v{META['kit_version']}")
        proc = self.resolve("--json", expect=2)
        data = json.loads(proc.stdout)
        self.assertIn("annotated", data["error"])

    def test_tag_version_mismatch_is_rejected(self) -> None:
        self.src = init_repo(self.base / "stale-src", "0.0.1",
                             annotated_tag=f"v{META['kit_version']}")
        proc = self.resolve("--json", expect=2)
        self.assertIn("不一致", json.loads(proc.stdout)["error"])

    def test_tampered_cache_marker_triggers_reclone(self) -> None:
        data = self.resolve_json()
        kit_root = Path(data["kitRoot"])
        marker_path = kit_root / ".harness-kit-cache.json"
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
        marker["commitSha"] = "0" * 40
        marker_path.write_text(json.dumps(marker), encoding="utf-8")
        again = self.resolve_json()
        self.assertEqual("clone", again["source"])
        self.assertTrue(again["cloned"])
        restored = json.loads(marker_path.read_text(encoding="utf-8"))
        self.assertEqual(git(kit_root, "rev-parse", "HEAD").stdout.strip(), restored["commitSha"])

    def test_refresh_reclones_existing_cache(self) -> None:
        self.resolve_json()
        again = self.resolve_json("--refresh")
        self.assertEqual("clone", again["source"])
        self.assertTrue(again["cloned"])

    # ── local sources ────────────────────────────────────────────────────
    def test_embedded_older_kit_warns_but_resolves(self) -> None:
        embedded = self.target / "harness-kit"
        embedded.mkdir()
        (embedded / "VERSION").write_text("0.5.3\n", encoding="utf-8")
        data = self.resolve_json()
        self.assertEqual("embedded", data["source"])
        self.assertEqual("0.5.3", data["version"])
        self.assertEqual("older-than-skill", data["versionStatus"])
        self.assertTrue(data["warnings"])

    def test_embedded_kit_below_min_version_fails(self) -> None:
        embedded = self.target / "harness-kit"
        embedded.mkdir()
        (embedded / "VERSION").write_text("0.4.0\n", encoding="utf-8")
        proc = self.resolve("--json", expect=2)
        self.assertIn("最低版本", json.loads(proc.stdout)["error"])

    def test_adopted_repo_fast_path_is_offline(self) -> None:
        (self.target / "tools").mkdir()
        (self.target / "tools" / "harness.py").write_text("#!/usr/bin/env python3\n")
        data = self.resolve_json("--offline")
        self.assertTrue(data["adopted"])
        self.assertIsNone(data["kitRoot"])
        self.assertEqual("none", data["source"])
        self.assertFalse((Path(self.env["XDG_CACHE_HOME"]) / "harness-kit").exists())

    # ── npx / legacy metadata precedence ─────────────────────────────────
    def test_npx_management_ignores_stale_legacy_metadata(self) -> None:
        stale = self.base / "stale-kit"
        stale.mkdir()
        (stale / "VERSION").write_text("0.5.3\n", encoding="utf-8")
        home = Path(self.env["HOME"])
        meta_dir = home / ".agents" / "skills"
        meta_dir.mkdir(parents=True)
        (meta_dir / ".harness-kit-skill.json").write_text(
            json.dumps({"kitRoot": str(stale), "kitVersion": "0.5.3"}), encoding="utf-8")
        lock_dir = Path(self.env["XDG_STATE_HOME"]) / "skills"
        lock_dir.mkdir(parents=True)
        (lock_dir / ".skill-lock.json").write_text(json.dumps(
            {"skills": {"harness": {"source": "DavidTeam2008/harness-engineering-kit"}}}),
            encoding="utf-8")
        first = self.resolve_json()
        self.assertEqual("npx", first["managedBy"])
        self.assertEqual("clone", first["source"])
        self.assertTrue(any("共存" in item for item in first["warnings"]))
        second = self.resolve_json("--offline")
        self.assertEqual("cache", second["source"])
        self.assertNotEqual("0.5.3", second["version"])

    def test_legacy_metadata_is_used_without_npx(self) -> None:
        legacy = self.base / "legacy-kit"
        legacy.mkdir()
        (legacy / "VERSION").write_text("0.5.3\n", encoding="utf-8")
        meta_dir = Path(self.env["HOME"]) / ".agents" / "skills"
        meta_dir.mkdir(parents=True)
        (meta_dir / ".harness-kit-skill.json").write_text(
            json.dumps({"kitRoot": str(legacy), "kitVersion": "0.5.3"}), encoding="utf-8")
        data = self.resolve_json("--offline")
        self.assertEqual("meta", data["source"])
        self.assertEqual("0.5.3", data["version"])
        self.assertIsNone(data["managedBy"])


if __name__ == "__main__":
    unittest.main()
