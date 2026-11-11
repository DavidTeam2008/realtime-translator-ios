#!/usr/bin/env python3
"""v0.4.0 scorecard tests: generate draft / --json / --check-stale (age, commits, ancestry, strict).

Contract: plan §O4 + red-team requirement 5. Standard library only; runs the real
`tools/scorecard.py` CLI against temp projects.

Run: cd harness-kit && PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_kit_scorecard_v04 -q
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
TOOL = KIT / "core" / "tools" / "scorecard.py"
KIT_TOOLS = KIT / "core" / "tools"
COPY_TOOLS = (
    "token_estimate.py",
    "check_docs.py",
    "check_agents.py",
    "check_plan.py",
    "check_hygiene.py",
    "check_layers.py",
    "verify_claim.py",
)
DATE_PREFIX_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def iso(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def run_tool(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(TOOL), *args],
        cwd=str(cwd or KIT),
        capture_output=True,
        text=True,
        timeout=180,
    )


class ScorecardCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="kit-scorecard-")
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    # --- fixture ---------------------------------------------------------
    def write(self, rel: str, text: str) -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def git(self, *args: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(self.root), *args], capture_output=True, text=True
        )
        if result.returncode != 0:
            self.fail(f"git {' '.join(args)} 失败：{result.stderr}")
        return result.stdout.strip()

    def init_git(self) -> None:
        self.git("init", "-q")
        self.git("config", "user.name", "kit-test")
        self.git("config", "user.email", "kit-test@example.invalid")

    def commit(self, message: str = "fixture") -> str:
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)
        return self.git("rev-parse", "--short", "HEAD")

    def build_project(self, *, max_age: int = 30, max_commits: int = 50) -> None:
        tools_dir = self.root / "tools"
        tools_dir.mkdir(parents=True)
        for name in COPY_TOOLS:
            (tools_dir / name).write_text(
                (KIT_TOOLS / name).read_text(encoding="utf-8"), encoding="utf-8"
            )
        config = {
            "kitVersion": "0.4.0",
            "project": {"name": "Fixture", "language": "python"},
            "paths": {
                "docs": "docs",
                "references": "references",
                "harness": "harness",
                "plans": "harness/plans",
                "evidence": "harness/evidence",
                "reviews": "harness/reviews",
                "tools": "tools",
                "rootDocs": ["AGENTS.md"],
            },
            "instructions": {
                "root": "AGENTS.md",
                "nested": [],
                "nestedMaxBytes": 8192,
                "budgets": {},
                "sensitivePatterns": [],
            },
            "commands": {"test": "echo ok"},
            "claims": [
                {
                    "name": "tests-pass",
                    "type": "test-count",
                    "baseline": "harness/test-baseline.json",
                    "floor": "unit.floor",
                    "expectedSkipped": "unit.expectedSkipped",
                    "command": "echo ok",
                },
                {"name": "docs-pass", "type": "static", "command": "echo ok"},
            ],
            "freshness": {},
            "scorecard": {"maxAgeDays": max_age, "maxCommits": max_commits},
        }
        self.write("harness/config.json", json.dumps(config, ensure_ascii=False, indent=2))
        self.write("AGENTS.md", "# Rules\n")
        self.write("docs/README.md", "# Docs\n\n- [AGENTS](AGENTS.md)\n")
        self.write("docs/AGENTS.md", "# Docs rules\n")
        self.write("references/contracts.md", "# Contracts\n")
        self.write("harness/plans/_template.md", "# Plan template\n")
        self.write("harness/test-baseline.json", json.dumps({"unit": {"floor": 1, "expectedSkipped": 0}}))

    def write_scorecard(self, *, checked_at: str, commit: str | None, suffix: str = "2026-01-01") -> Path:
        lines = [f"# fixture scorecard {suffix}", "", f"- checkedAt: {checked_at}"]
        if commit is not None:
            lines.append(f"- commit: {commit}")
        return self.write(f"harness/reviews/{suffix}-scorecard.md", "\n".join(lines) + "\n")

    # --- CLI helpers -----------------------------------------------------
    def generate_json(self) -> dict:
        proc = run_tool("--root", str(self.root), "--generate", "--json")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return json.loads(proc.stdout)

    def stale(self, *extra: str) -> subprocess.CompletedProcess[str]:
        return run_tool("--root", str(self.root), "--check-stale", *extra)


class GenerateTests(ScorecardCase):
    def test_generate_creates_draft_with_facts_only(self) -> None:
        self.build_project()
        proc = run_tool("--root", str(self.root), "--generate")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        expected = self.root / "harness" / "reviews" / f"{utc_now().strftime('%Y-%m-%d')}-scorecard.md"
        self.assertTrue(expected.is_file(), proc.stdout)
        text = expected.read_text(encoding="utf-8")
        for fragment in (
            "- checkedAt: ",
            "- commit:",
            "- evidence:",
            "- 测试基线：",
            "- 文档计数：",
            "## 1. 门禁快照（自动）",
            "自评（1–5）",
            "独立复评（1–5）",
            "TBD",
            "自评不是认证",
            "不算完成证据",
        ):
            self.assertIn(fragment, text)
        self.assertNotRegex(text, r"\| [1-5] \| [1-5] \|", "生成器不得自动打分")

    def test_generate_json_contract(self) -> None:
        self.build_project()
        data = self.generate_json()
        for key in ("checkedAt", "commit", "dirty", "kitVersion", "gates", "evidence", "testBaseline", "docsCount", "scorecard"):
            self.assertIn(key, data)
        self.assertEqual(6, len(data["gates"]))
        for gate in data["gates"]:
            self.assertIn("command", gate)
            self.assertIn("exitCode", gate)
            self.assertIn("keyOutput", gate)
        self.assertIsInstance(data["docsCount"], int)
        self.assertGreaterEqual(data["docsCount"], 3)
        self.assertTrue(DATE_PREFIX_RE.fullmatch(Path(data["scorecard"]).name[:10]))
        self.assertTrue((self.root / data["scorecard"]).is_file())

    def test_generate_is_idempotent_on_same_day(self) -> None:
        self.build_project()
        first = run_tool("--root", str(self.root), "--generate")
        second = run_tool("--root", str(self.root), "--generate")
        self.assertEqual(0, first.returncode, first.stdout + first.stderr)
        self.assertEqual(0, second.returncode, second.stdout + second.stderr)


class CheckStaleTests(ScorecardCase):
    def test_missing_scorecard_warns_and_is_non_blocking(self) -> None:
        self.build_project()
        proc = self.stale()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("[WARN]", proc.stdout)
        self.assertIn("未找到 scorecard", proc.stdout)
        data = json.loads(self.stale("--json").stdout)
        self.assertEqual("missing", data["status"])
        strict = self.stale("--strict")
        self.assertEqual(1, strict.returncode, strict.stdout + strict.stderr)

    def test_fresh_scorecard_passes(self) -> None:
        self.build_project()
        self.init_git()
        commit = self.commit()
        self.write_scorecard(checked_at=iso(utc_now()), commit=commit)
        proc = self.stale()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("[OK] scorecard 新鲜", proc.stdout)
        data = json.loads(self.stale("--json").stdout)
        self.assertEqual("fresh", data["status"])
        self.assertEqual(0, data["ageDays"])
        self.assertEqual(0, data["commitsSince"])
        self.assertEqual(0, self.stale("--strict").returncode)

    def test_expired_by_age_warns_and_strict_fails(self) -> None:
        self.build_project(max_age=30)
        self.init_git()
        commit = self.commit()
        old = utc_now() - timedelta(days=40)
        self.write_scorecard(checked_at=iso(old), commit=commit)
        proc = self.stale()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("天未更新", proc.stdout)
        self.assertEqual(1, self.stale("--strict").returncode)

    def test_expired_by_commits_warns_and_strict_fails(self) -> None:
        self.build_project(max_commits=1)
        self.init_git()
        commit = self.commit()
        self.write_scorecard(checked_at=iso(utc_now()), commit=commit)
        self.write("notes-1.md", "one\n")
        self.commit("second")
        self.write("notes-2.md", "two\n")
        self.commit("third")
        proc = self.stale()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("新增 2 个提交", proc.stdout)
        self.assertEqual(1, self.stale("--strict").returncode)

    def test_non_ancestor_commit_warns_and_strict_fails(self) -> None:
        self.build_project()
        self.init_git()
        self.commit("base")
        main_branch = self.git("rev-parse", "--abbrev-ref", "HEAD")
        self.git("checkout", "-q", "-b", "feature")
        self.write("feature.md", "feature\n")
        feature_commit = self.commit("feature")
        self.git("checkout", "-q", main_branch)
        self.write_scorecard(checked_at=iso(utc_now()), commit=feature_commit)
        proc = self.stale()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("不是 HEAD 祖先", proc.stdout)
        self.assertEqual(1, self.stale("--strict").returncode)

    def test_missing_commit_line_warns(self) -> None:
        self.build_project()
        self.write_scorecard(checked_at=iso(utc_now()), commit=None)
        proc = self.stale()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("缺少可解析 commit", proc.stdout)
        self.assertEqual(1, self.stale("--strict").returncode)

    def test_strict_requires_check_stale(self) -> None:
        self.build_project()
        proc = run_tool("--root", str(self.root), "--generate", "--strict")
        self.assertEqual(2, proc.returncode, proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
