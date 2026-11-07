#!/usr/bin/env python3
"""`tools/evidence.py` 的 ls / validate / write 回归测试（unittest，仅标准库）。

同样用 subprocess 走 CLI；git 用临时仓库，避免依赖工作树状态。
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
EVIDENCE_TOOL = TOOLS / "evidence.py"


def run(cmd: list[str], *, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, input=stdin)


def git(root: Path, *args: str) -> str:
    proc = run(["git", "-C", str(root), *args])
    if proc.returncode != 0:
        raise AssertionError(f"git {args} 失败：{proc.stderr}")
    return proc.stdout.strip()


def init_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    if run(["git", "-C", str(path), "init", "-q"]).returncode != 0:
        raise AssertionError("git init 失败")
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
        raise AssertionError(f"临时 git 提交失败：{proc.stderr}")


def draft(**overrides) -> dict:
    data = {
        "claim": "unit-tests-pass",
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
            "durationSec": 42.5,
            "xcresultPath": None,
            "metricsPath": None,
        },
        "verdict": "PASS",
        "notes": "unit test fixture",
    }
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(data.get(key), dict):
            data[key] = {**data[key], **value}
        else:
            data[key] = value
    return data


class EvidenceToolTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.repo = self.tmp / "repo"
        init_repo(self.repo)
        self.draft_path = self.tmp / "draft.json"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    # ── helpers ───────────────────────────────────────────────────────────
    def write_draft(self, data: dict) -> Path:
        self.draft_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return self.draft_path

    def write(self, data: dict, *, from_file: bool = True) -> subprocess.CompletedProcess[str]:
        if from_file:
            self.write_draft(data)
            cmd = [sys.executable, str(EVIDENCE_TOOL), "write", "--from-json", str(self.draft_path)]
        else:
            cmd = [sys.executable, str(EVIDENCE_TOOL), "write"]
        return run([*cmd, "--root", str(self.repo)])

    def evidence_files(self) -> list[Path]:
        directory = self.repo / "harness" / "evidence"
        return sorted(directory.glob("*.json")) if directory.is_dir() else []

    # ── write ─────────────────────────────────────────────────────────────
    def test_write_from_json_creates_evidence(self) -> None:
        proc = self.write(draft())
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        files = self.evidence_files()
        self.assertEqual(len(files), 1)
        data = json.loads(files[0].read_text(encoding="utf-8"))
        self.assertEqual(data["id"], files[0].stem)
        self.assertRegex(data["id"], r"^[0-9]{8}T[0-9]{6}Z-unit-tests-pass$")
        self.assertEqual(data["git"]["commit"], git(self.repo, "rev-parse", "--short=12", "HEAD"))
        self.assertIs(data["git"]["dirty"], False)
        self.assertEqual(data["verifier"], "tools/evidence.py@1")
        self.assertEqual(data["schemaVersion"], 1)
        self.assertIn(f"harness/evidence/{files[0].name}", proc.stdout)

    def test_write_marks_dirty_worktree(self) -> None:
        (self.repo / "untracked.txt").write_text("x", encoding="utf-8")
        proc = self.write(draft())
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        data = json.loads(self.evidence_files()[0].read_text(encoding="utf-8"))
        self.assertIs(data["git"]["dirty"], True)

    def test_write_derives_verdict_when_missing(self) -> None:
        data = draft()
        del data["verdict"]
        self.assertEqual(self.write(data).returncode, 0)
        written = json.loads(self.evidence_files()[0].read_text(encoding="utf-8"))
        self.assertEqual(written["verdict"], "PASS")

        data = draft()
        del data["verdict"]
        data["result"]["status"] = "FAILED"
        proc = self.write(data)
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        written_path = self.repo / proc.stdout.strip()
        written = json.loads(written_path.read_text(encoding="utf-8"))
        self.assertEqual(written["verdict"], "FAIL")

    def test_write_rejects_unknown_claim(self) -> None:
        proc = self.write(draft(claim="manual-pass"))
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(self.evidence_files(), [])

    def test_write_requires_git_repo(self) -> None:
        plain = self.tmp / "not-a-repo"
        plain.mkdir()
        self.write_draft(draft())
        proc = run(
            [
                sys.executable,
                str(EVIDENCE_TOOL),
                "write",
                "--from-json",
                str(self.draft_path),
                "--root",
                str(plain),
            ]
        )
        self.assertEqual(proc.returncode, 1)
        self.assertIn("git", proc.stderr)
        self.assertFalse((plain / "harness" / "evidence").exists())

    def test_write_rejects_invalid_schema(self) -> None:
        data = draft()
        del data["result"]["passed"]
        proc = self.write(data)
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(self.evidence_files(), [])

    def test_write_strips_non_portable_artifact_path(self) -> None:
        data = draft()
        data["result"]["xcresultPath"] = "/nonexistent-duiyi-test/run.xcresult"
        proc = self.write(data)
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        written = json.loads(self.evidence_files()[0].read_text(encoding="utf-8"))
        self.assertIsNone(written["result"]["xcresultPath"])
        self.assertIn("WARN", proc.stderr)

    def test_write_from_stdin(self) -> None:
        payload = json.dumps(draft(), ensure_ascii=False)
        proc = run(
            [
                sys.executable,
                str(EVIDENCE_TOOL),
                "write",
                "--from-json",
                "-",
                "--root",
                str(self.repo),
            ],
            stdin=payload,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        self.assertEqual(len(self.evidence_files()), 1)

    def test_write_from_cli_args(self) -> None:
        proc = run(
            [
                sys.executable,
                str(EVIDENCE_TOOL),
                "write",
                "--claim",
                "docs-pass",
                "--command",
                "python3 tools/check-docs.py",
                "--status",
                "SUCCEEDED",
                "--passed",
                "1",
                "--verdict",
                "PASS",
                "--root",
                str(self.repo),
            ]
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        data = json.loads(self.evidence_files()[0].read_text(encoding="utf-8"))
        self.assertEqual(data["claim"], "docs-pass")
        self.assertIsNone(data["environment"]["simulator"])

    # ── validate / ls / show ──────────────────────────────────────────────
    def test_validate_ok_and_tampered(self) -> None:
        self.assertEqual(self.write(draft()).returncode, 0)
        ok = run([sys.executable, str(EVIDENCE_TOOL), "validate", "--root", str(self.repo)])
        self.assertEqual(ok.returncode, 0, msg=ok.stderr)
        self.assertIn("[PASS]", ok.stdout)

        path = self.evidence_files()[0]
        data = json.loads(path.read_text(encoding="utf-8"))
        del data["git"]
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        bad = run([sys.executable, str(EVIDENCE_TOOL), "validate", "--root", str(self.repo)])
        self.assertEqual(bad.returncode, 1)

    def test_ls_and_show(self) -> None:
        self.assertEqual(self.write(draft()).returncode, 0)
        ls = run([sys.executable, str(EVIDENCE_TOOL), "ls", "--root", str(self.repo)])
        self.assertEqual(ls.returncode, 0, msg=ls.stderr)
        self.assertIn("unit-tests-pass", ls.stdout)

        evidence_id = self.evidence_files()[0].stem
        show = run(
            [sys.executable, str(EVIDENCE_TOOL), "show", evidence_id, "--root", str(self.repo)]
        )
        self.assertEqual(show.returncode, 0, msg=show.stderr)
        self.assertIn(evidence_id, show.stdout)

    def test_no_subcommand_lists_and_validates(self) -> None:
        self.assertEqual(self.write(draft()).returncode, 0)
        proc = run([sys.executable, str(EVIDENCE_TOOL), "--root", str(self.repo)])
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        self.assertIn("unit-tests-pass", proc.stdout)
        self.assertIn("[PASS]", proc.stdout)

    def test_validate_missing_evidence_dir_fails(self) -> None:
        plain = self.tmp / "plain"
        plain.mkdir()
        proc = run([sys.executable, str(EVIDENCE_TOOL), "validate", "--root", str(plain)])
        self.assertEqual(proc.returncode, 1)
        self.assertIn("FAIL", proc.stderr)


if __name__ == "__main__":
    unittest.main()
