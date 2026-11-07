#!/usr/bin/env python3
"""`tools/verify-claim.py` 的三值判定回归测试（unittest，仅标准库）。

判定接口是进程级契约，因此用 subprocess 走真实 CLI：
- PASS=0 / FAIL=1 / UNVERIFIED=2
- 需要 git 的 case 用真实仓库 HEAD 或临时 git 仓库；
- 静态门禁 claim 用临时仓库里的假脚本，避免依赖本机脚本输出；
- 不跑 xcodebuild / 真机 / 测量。

运行：python3 -m unittest discover -s tools/tests -q
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS = REPO_ROOT / "tools"
VERIFY_CLAIM = TOOLS / "verify-claim.py"


# ── helpers ────────────────────────────────────────────────────────────────
def run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, capture_output=True, text=True)


def git(root: Path, *args: str) -> str:
    proc = run(["git", "-C", str(root), *args])
    if proc.returncode != 0:
        raise AssertionError(f"git {args} 失败：{proc.stderr}")
    return proc.stdout.strip()


def head(root: Path = REPO_ROOT) -> str:
    return git(root, "rev-parse", "HEAD")


def head_short(root: Path = REPO_ROOT, length: int = 7) -> str:
    return git(root, "rev-parse", f"--short={length}", "HEAD")


def init_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    run(["git", "-C", str(path), "init", "-q"])
    proc = run(
        [
            "git",
            "-C",
            str(path),
            "-c",
            "user.name=test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "--allow-empty",
            "-q",
            "-m",
            "init",
        ]
    )
    if proc.returncode != 0:
        raise AssertionError(f"临时 git 仓库初始化失败：{proc.stderr}")


def base_evidence(claim: str = "unit-tests-pass", commit: str | None = None) -> dict:
    return {
        "schemaVersion": 1,
        "id": "20260101T000000Z-" + claim,
        "claim": claim,
        "createdAt": "2026-01-01T00:00:00Z",
        "git": {"commit": commit or head_short(), "dirty": False},
        "command": "make test",
        "environment": {
            "xcode": "Xcode 27.1",
            "simulator": "iOS 26.4.1",
            "device": None,
            "build": "Debug",
        },
        "result": {
            "status": "SUCCEEDED",
            "passed": 120,
            "failed": 0,
            "skipped": 0,
            "durationSec": 1.0,
            "xcresultPath": None,
            "metricsPath": None,
        },
        "verdict": "UNVERIFIED",
        "verifier": "tools/evidence.py@1",
        "notes": "",
    }


def write_json(path: Path, data: dict) -> Path:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def fake_script(root: Path, rel: str, exit_code: int) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"import sys\nsys.exit({exit_code})\n", encoding="utf-8")
    return path


class VerifyClaimTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.xcresult = self.tmp / "run.xcresult"
        self.xcresult.mkdir()
        self.evidence_path = self.tmp / "evidence.json"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    # ── 通用执行 ──────────────────────────────────────────────────────────
    def verify(
        self,
        doc: dict,
        *,
        root: Path = REPO_ROOT,
        extra: tuple[str, ...] = (),
    ) -> subprocess.CompletedProcess[str]:
        write_json(self.evidence_path, doc)
        return run(
            [
                sys.executable,
                str(VERIFY_CLAIM),
                str(self.evidence_path),
                "--root",
                str(root),
                *extra,
            ]
        )

    def assert_verdict(self, proc: subprocess.CompletedProcess[str], code: int, verdict: str) -> None:
        self.assertEqual(proc.returncode, code, msg=f"stdout={proc.stdout!r} stderr={proc.stderr!r}")
        self.assertIn(f": {verdict} —", proc.stdout)

    # ── PASS ──────────────────────────────────────────────────────────────
    def test_unit_pass(self) -> None:
        doc = base_evidence()
        doc["result"]["xcresultPath"] = str(self.xcresult)
        self.assert_verdict(self.verify(doc), 0, "PASS")

    def test_unit_pass_with_temp_repo_relative_xcresult(self) -> None:
        root = self.tmp / "repo"
        init_repo(root)
        (root / "harness").mkdir()
        (root / "harness" / "test-baseline.json").write_text(
            (REPO_ROOT / "harness" / "test-baseline.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        (root / "artifacts").mkdir()
        (root / "artifacts" / "run.xcresult").write_text("stub", encoding="utf-8")
        doc = base_evidence(commit=git(root, "rev-parse", "HEAD"))
        doc["result"]["xcresultPath"] = "artifacts/run.xcresult"
        self.assert_verdict(self.verify(doc, root=root), 0, "PASS")

    def test_ancestor_commit_pass(self) -> None:
        if git(REPO_ROOT, "rev-parse", "--is-shallow-repository").strip() == "true":
            self.skipTest("浅克隆缺少父提交；先 `git fetch --unshallow` 再跑 verify-static")
        doc = base_evidence(commit=git(REPO_ROOT, "rev-parse", "HEAD~1"))
        doc["result"]["xcresultPath"] = str(self.xcresult)
        self.assert_verdict(self.verify(doc), 0, "PASS")

    def test_fresh_detects_dirty_worktree_in_claim_scope(self) -> None:
        root = self.tmp / "repo"
        init_repo(root)
        (root / "harness").mkdir(exist_ok=True)
        (root / "harness" / "test-baseline.json").write_text(
            (REPO_ROOT / "harness" / "test-baseline.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        source = root / "Duiyi" / "App.swift"
        source.parent.mkdir()
        source.write_text("// v1\n", encoding="utf-8")
        for args in (("add", "-A"), ("commit", "-q", "-m", "v1")):
            proc = run(["git", "-C", str(root), "-c", "user.name=test", "-c", "user.email=test@example.invalid", *args])
            if proc.returncode != 0:
                raise AssertionError(f"git {args} 失败：{proc.stderr}")
        doc = base_evidence(commit=git(root, "rev-parse", "HEAD"))
        doc["result"]["xcresultPath"] = str(self.xcresult)
        clean = self.verify(doc, root=root, extra=("--fresh",))
        self.assertEqual(clean.returncode, 0, clean.stdout)
        self.assertNotIn("STALE", clean.stdout)
        source.write_text("// v2\n", encoding="utf-8")
        dirty = self.verify(doc, root=root, extra=("--fresh",))
        self.assertEqual(dirty.returncode, 0, dirty.stdout)
        self.assertIn("STALE", dirty.stdout)
        strict = self.verify(doc, root=root, extra=("--fresh", "--strict"))
        self.assertEqual(strict.returncode, 2, strict.stdout)

    def test_ui_simulator_expected_skip_one_pass(self) -> None:
        # 真实模拟器结果：3 executed = 2 passed + 1 expected skip；floor 是"用例总数"。
        doc = base_evidence(claim="ui-tests-pass")
        doc["result"].update({"passed": 2, "skipped": 1, "xcresultPath": str(self.xcresult)})
        self.assert_verdict(self.verify(doc), 0, "PASS")

    def test_ui_executed_below_floor_fail(self) -> None:
        doc = base_evidence(claim="ui-tests-pass")
        doc["result"].update({"passed": 1, "skipped": 1, "xcresultPath": str(self.xcresult)})
        self.assert_verdict(self.verify(doc), 1, "FAIL")

    def test_device_claim_pass(self) -> None:
        doc = base_evidence(claim="device-tests-pass")
        doc["environment"]["device"] = "physical"
        doc["environment"]["simulator"] = None
        doc["result"].update({"passed": 123, "skipped": 0, "xcresultPath": str(self.xcresult)})
        self.assert_verdict(self.verify(doc), 0, "PASS")

    # ── FAIL ──────────────────────────────────────────────────────────────
    def test_passed_below_floor_fail(self) -> None:
        doc = base_evidence()
        doc["result"].update({"passed": 119, "xcresultPath": str(self.xcresult)})
        self.assert_verdict(self.verify(doc), 1, "FAIL")

    def test_failed_nonzero_fail(self) -> None:
        doc = base_evidence()
        doc["result"].update({"failed": 1, "passed": 119, "xcresultPath": str(self.xcresult)})
        self.assert_verdict(self.verify(doc), 1, "FAIL")

    def test_skipped_mismatch_fail(self) -> None:
        doc = base_evidence()
        doc["result"].update({"skipped": 1, "xcresultPath": str(self.xcresult)})
        self.assert_verdict(self.verify(doc), 1, "FAIL")

    def test_dirty_true_fail(self) -> None:
        doc = base_evidence()
        doc["git"]["dirty"] = True
        doc["result"]["xcresultPath"] = str(self.xcresult)
        self.assert_verdict(self.verify(doc), 1, "FAIL")

    def test_unknown_commit_fail(self) -> None:
        doc = base_evidence(commit="deadbeef")
        doc["result"]["xcresultPath"] = str(self.xcresult)
        self.assert_verdict(self.verify(doc), 1, "FAIL")

    def test_missing_required_field_fail(self) -> None:
        doc = base_evidence()
        del doc["command"]
        doc["result"]["xcresultPath"] = str(self.xcresult)
        self.assert_verdict(self.verify(doc), 1, "FAIL")

    def test_unknown_claim_fail(self) -> None:
        doc = base_evidence(claim="manual-pass")
        self.assert_verdict(self.verify(doc), 1, "FAIL")

    def test_missing_evidence_file_fail(self) -> None:
        missing = self.tmp / "missing.json"
        proc = run([sys.executable, str(VERIFY_CLAIM), str(missing), "--root", str(REPO_ROOT)])
        self.assert_verdict(proc, 1, "FAIL")

    def test_device_claim_without_device_fail(self) -> None:
        doc = base_evidence(claim="device-tests-pass")
        doc["result"].update({"passed": 123, "xcresultPath": str(self.xcresult)})
        self.assert_verdict(self.verify(doc), 2, "UNVERIFIED")

    # ── UNVERIFIED ────────────────────────────────────────────────────────
    def test_missing_xcresult_path_unverified(self) -> None:
        self.assert_verdict(self.verify(base_evidence()), 2, "UNVERIFIED")

    def test_xcresult_not_exists_unverified(self) -> None:
        doc = base_evidence()
        doc["result"]["xcresultPath"] = str(self.tmp / "gone.xcresult")
        self.assert_verdict(self.verify(doc), 2, "UNVERIFIED")

    # ── docs / arch 静态复跑 ──────────────────────────────────────────────
    def test_docs_pass_rerun_pass(self) -> None:
        root = self.tmp / "fake-repo"
        init_repo(root)
        fake_script(root, "tools/check-docs.py", 0)
        doc = base_evidence(claim="docs-pass", commit=git(root, "rev-parse", "HEAD"))
        doc["command"] = "python3 tools/check-docs.py"
        self.assert_verdict(self.verify(doc, root=root), 0, "PASS")

    def test_docs_pass_rerun_fail(self) -> None:
        root = self.tmp / "fake-repo"
        init_repo(root)
        fake_script(root, "tools/check-docs.py", 1)
        doc = base_evidence(claim="docs-pass", commit=git(root, "rev-parse", "HEAD"))
        self.assert_verdict(self.verify(doc, root=root), 1, "FAIL")

    def test_arch_pass_real_repo(self) -> None:
        doc = base_evidence(claim="arch-pass")
        self.assert_verdict(self.verify(doc), 0, "PASS")

    # ── perf ──────────────────────────────────────────────────────────────
    def _perf_evidence(
        self,
        samples: list[float],
        *,
        context_commit: str | None = None,
        context_build: str = "Release",
        metrics_path: Path | None = None,
    ) -> dict:
        metrics = {
            "context": {
                "commit": context_commit if context_commit is not None else head_short(),
                "build": context_build,
                "command": "harness/tools/measure-launch.sh",
            },
            "metrics": [
                {
                    "name": "startup.cold.first_frame",
                    "unit": "ms",
                    "direction": "lower_is_better",
                    "samples": samples,
                    "minEffect": 30,
                }
            ],
        }
        path = metrics_path or (self.tmp / "metrics.json")
        write_json(path, metrics)
        doc = base_evidence(claim="perf-measurement")
        doc["environment"]["build"] = "Release"
        doc["result"].update({"passed": len(samples), "metricsPath": str(path), "durationSec": 60.0})
        return doc

    def test_perf_pass(self) -> None:
        samples = [250, 251, 249, 250, 252, 248, 250, 251, 249, 250]
        self.assert_verdict(self.verify(self._perf_evidence(samples)), 0, "PASS")

    def test_perf_n_below_10_unverified(self) -> None:
        self.assert_verdict(self.verify(self._perf_evidence([250, 251, 249, 250, 252])), 2, "UNVERIFIED")

    def test_perf_cv_high_unverified(self) -> None:
        samples = [100, 900, 120, 880, 110, 890, 130, 870, 140, 860]
        self.assert_verdict(self.verify(self._perf_evidence(samples)), 2, "UNVERIFIED")

    def test_perf_missing_metrics_unverified(self) -> None:
        doc = base_evidence(claim="perf-measurement")
        doc["environment"]["build"] = "Release"
        self.assert_verdict(self.verify(doc), 2, "UNVERIFIED")

    def test_perf_context_mismatch_fail(self) -> None:
        samples = [250, 251, 249, 250, 252, 248, 250, 251, 249, 250]
        doc = self._perf_evidence(samples, context_build="Debug")
        self.assert_verdict(self.verify(doc), 1, "FAIL")

    # ── --all 聚合 ───────────────────────────────────────────────────────
    def _all(self, directory: Path) -> subprocess.CompletedProcess[str]:
        return run(
            [
                sys.executable,
                str(VERIFY_CLAIM),
                "--all",
                "--root",
                str(REPO_ROOT),
                "--evidence-dir",
                str(directory),
            ]
        )

    def test_all_with_unverified_is_exit_2(self) -> None:
        directory = self.tmp / "evidence"
        directory.mkdir()
        passing = base_evidence()
        passing["result"]["xcresultPath"] = str(self.xcresult)
        write_json(directory / "20260101T000000Z-unit-tests-pass.json", passing)
        # 无 xcresult → UNVERIFIED（文件名=id，--all 会做语义校验）
        write_json(
            directory / "20260101T000000Z-device-tests-pass.json",
            base_evidence(claim="device-tests-pass"),
        )
        proc = self._all(directory)
        self.assertEqual(proc.returncode, 2, msg=proc.stdout + proc.stderr)
        self.assertIn("SUMMARY:", proc.stdout)

    def test_all_with_fail_is_exit_1(self) -> None:
        directory = self.tmp / "evidence"
        directory.mkdir()
        passing = base_evidence()
        passing["result"]["xcresultPath"] = str(self.xcresult)
        write_json(directory / "20260101T000000Z-unit-tests-pass.json", passing)
        failing = base_evidence(claim="ui-tests-pass")
        failing["result"].update({"passed": 1, "xcresultPath": str(self.xcresult)})
        write_json(directory / "20260101T000000Z-ui-tests-pass.json", failing)
        proc = self._all(directory)
        self.assertEqual(proc.returncode, 1, msg=proc.stdout + proc.stderr)

    def test_all_empty_evidence_dir_fail(self) -> None:
        directory = self.tmp / "empty"
        directory.mkdir()
        proc = self._all(directory)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("未验证的声明", proc.stdout)

    # ── CLI ───────────────────────────────────────────────────────────────
    def test_help(self) -> None:
        proc = run([sys.executable, str(VERIFY_CLAIM), "--help"])
        self.assertEqual(proc.returncode, 0)
        self.assertIn("UNVERIFIED", proc.stdout)


if __name__ == "__main__":
    unittest.main()
