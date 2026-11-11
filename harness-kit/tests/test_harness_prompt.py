#!/usr/bin/env python3
"""v0.4.0 prompt-stage tests: manifest-based adopted/partial/mismatch/legacy + onboarding content.

Contract: plan `harness/reviews/2026-11-11-adoption-feedback-v04/plan.md` §O3
and red-team requirement 2 (`.harness-manifest.json` is the source of truth).
Standard library only; runs the real `harness-prompt` CLI against temp fixtures.

Run: cd harness-kit && PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_harness_prompt -q
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
PROMPT = KIT / "scripts" / "harness-prompt"


def run_prompt(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(PROMPT), *args],
        capture_output=True,
        text=True,
        timeout=120,
    )


def profile_definition(name: str) -> dict:
    path = KIT / "profiles" / f"{name}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    parent_name = data.get("extends")
    if not parent_name:
        return data
    parent = profile_definition(parent_name)
    merged = dict(parent)
    merged.update(data)
    files = {str(item.get("dst")): item for item in parent.get("files") or []}
    files.update({str(item.get("dst")): item for item in data.get("files") or []})
    merged["files"] = list(files.values())
    return merged


class PromptStageCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="kit-prompt-")
        self.tmp = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def write(self, root: Path, rel: str, text: str = "# fixture\n") -> Path:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def install_profile(self, name: str, root: Path, *, skip: set[str] | None = None) -> Path:
        """按 kit profile 的期望文件集建一个拟真目标仓（含 manifest）。"""
        root.mkdir(parents=True, exist_ok=True)
        profile = profile_definition(name)
        files = []
        for item in profile.get("files") or []:
            destination = str(item.get("dst"))
            if skip and destination in skip:
                continue
            self.write(root, destination)
            files.append(
                {"path": destination, "sha256": "0" * 64, "src": str(item.get("src") or "")}
            )
        self.write(root, "Makefile", "# fixture\n")
        manifest = {
            "schemaVersion": 1,
            "kitVersion": "0.4.0",
            "profile": name,
            "generatedAt": "2026-01-01T00:00:00Z",
            "files": files,
            "appends": [{"path": ".gitignore", "marker": "# harness-kit", "sha256": "0" * 64}],
            "skipped": sorted(skip or set()),
        }
        self.write(root, ".harness-manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        if skip:
            self.write(root, ".gitignore", "# fixture\n")
        return root

    def make_adopted_minimal(self) -> Path:
        return self.install_profile("minimal", self.tmp / "minimal")

    def make_partial(self) -> Path:
        root = self.install_profile("standard", self.tmp / "partial", skip={"harness/config.json"})
        return root

    def make_mismatch(self) -> Path:
        root = self.install_profile("minimal", self.tmp / "mismatch")
        self.write(root, "tools/verify_claim.py")  # standard 特征，与 manifest.profile=minimal 冲突
        return root

    def make_legacy(self) -> Path:
        root = self.tmp / "legacy"
        self.write(root, "harness/config.json", "{}\n")
        return root

    def make_unadopted(self) -> Path:
        root = self.tmp / "unadopted"
        root.mkdir(parents=True)
        self.write(root, "README.md")
        return root

    def stage_json(self, target: Path) -> dict:
        proc = run_prompt("list", "--target", str(target), "--json")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return json.loads(proc.stdout)


class StageDetectionTests(PromptStageCase):
    def test_adopted_from_manifest_and_profile_files(self) -> None:
        data = self.stage_json(self.make_adopted_minimal())
        self.assertEqual("adopted", data["targetStage"])
        self.assertEqual([], data["targetMissing"])

    def test_minimal_is_not_partial(self) -> None:
        data = self.stage_json(self.make_adopted_minimal())
        self.assertNotEqual("partial", data["targetStage"])

    def test_partial_reports_missing_profile_files(self) -> None:
        data = self.stage_json(self.make_partial())
        self.assertEqual("partial", data["targetStage"])
        self.assertIn("harness/config.json", data["targetMissing"])

    def test_mismatch_when_manifest_profile_differs_from_installation(self) -> None:
        data = self.stage_json(self.make_mismatch())
        self.assertEqual("mismatch", data["targetStage"])
        self.assertTrue(any("manifest.profile=minimal" in item for item in data["targetMissing"]))

    def test_legacy_without_manifest(self) -> None:
        data = self.stage_json(self.make_legacy())
        self.assertEqual("legacy", data["targetStage"])
        self.assertTrue(any(".harness-manifest.json" in item for item in data["targetMissing"]))

    def test_unadopted_when_nothing_present(self) -> None:
        data = self.stage_json(self.make_unadopted())
        self.assertEqual("unadopted", data["targetStage"])
        self.assertIn("harness/config.json", data["targetMissing"])

    def test_list_text_shows_partial_and_missing(self) -> None:
        proc = run_prompt("list", "--target", str(self.make_partial()))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("部分接入", proc.stdout)
        self.assertIn("缺少/不一致：", proc.stdout)
        self.assertIn("harness/config.json", proc.stdout)


class StageWarningTests(PromptStageCase):
    def test_adopted_scenario_warns_on_partial_target(self) -> None:
        proc = run_prompt("show", "fix-bug", "--target", str(self.make_partial()))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("[WARN]", proc.stderr)
        self.assertIn("部分接入", proc.stderr)
        self.assertIn("接入缺口", proc.stderr)

    def test_adopted_scenario_warns_on_legacy_target(self) -> None:
        proc = run_prompt("show", "fix-bug", "--target", str(self.make_legacy()))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("[WARN]", proc.stderr)
        self.assertIn("legacy", proc.stderr)

    def test_adoption_scenario_matches_unadopted_target_without_warning(self) -> None:
        proc = run_prompt("show", "adopt-brownfield", "--target", str(self.make_unadopted()))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertNotIn("[WARN] 目标仓库看起来", proc.stderr)


class AdoptionPromptContentTests(PromptStageCase):
    def test_adopt_brownfield_prompt_has_v04_guidance(self) -> None:
        proc = run_prompt("show", "adopt-brownfield", "--target", str(self.make_unadopted()))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        text = proc.stdout
        for fragment in (
            "默认 standard",
            "strict",
            "显式",
            "可执行性探测",
            "--test-command",
            "--archive-report",
            "make scorecard",
            "make selftest",
            "未验证豁免",
        ):
            self.assertIn(fragment, text)


if __name__ == "__main__":
    unittest.main()
