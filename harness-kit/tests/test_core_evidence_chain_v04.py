#!/usr/bin/env python3
"""harness-kit v0.4.0 evidence-chain tests (E1/E2/E3) — full CLI, standard library only.

Covers:
  - E1: recursive evidence scan, `_archive` SUPERSEDED listing (never silent), only-archive
        => exit 2, git-tracked requirement, `--allow-untracked` escape hatch, nested current.
  - E2: JUnit default sanitize-copy (no hostname/system-out/local paths), counts unchanged.
  - E3: claim.environment matching, expectedSkipped int/range/byEnvironment, invalid config,
        static claim freshness exemption (vs test-count still STALE).

Run: cd harness-kit && PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_core_evidence_chain_v04 -q
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
VERIFY = KIT / "core" / "tools" / "verify_claim.py"
JUNIT = KIT / "core" / "tools" / "evidence_from_junit.py"


# ── helpers ───────────────────────────────────────────────────────────────
def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=120)


def git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return run(["git", *args], cwd=root)


def head_short(root: Path, length: int = 12) -> str:
    return git(root, "rev-parse", f"--short={length}", "HEAD").stdout.strip()


def git_init(root: Path) -> None:
    assert git(root, "init", "-q").returncode == 0
    for key, value in (("user.name", "kit-test"), ("user.email", "kit-test@example.invalid")):
        assert git(root, "config", key, value).returncode == 0


def commit_all(root: Path, message: str) -> str:
    assert git(root, "add", "-A").returncode == 0
    proc = git(root, "commit", "-q", "-m", message)
    assert proc.returncode == 0, proc.stderr
    return head_short(root)


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def base_config(claims: list[dict], freshness: dict | None = None) -> dict:
    return {
        "kitVersion": "0.4.0",
        "project": {"name": "demo", "language": "python"},
        "paths": {
            "docs": "docs",
            "references": "references",
            "harness": "harness",
            "plans": "harness/plans",
            "evidence": "harness/evidence",
            "reviews": "harness/reviews",
            "tools": "tools",
            "rootDocs": ["README.md"],
        },
        "commands": {"check": "make check", "verify": "make verify-static", "test": "make test"},
        "claims": claims,
        "freshness": freshness or {},
    }


def test_count_claim(**overrides: object) -> dict:
    claim: dict = {
        "name": "tests-pass",
        "type": "test-count",
        "baseline": "harness/test-baseline.json",
        "floor": "unit.floor",
        "expectedSkipped": "unit.expectedSkipped",
        "requireArtifact": False,
        "command": "make test",
    }
    claim.update(overrides)
    return claim


def static_claim(**overrides: object) -> dict:
    claim: dict = {"name": "docs-pass", "type": "static", "command": "true"}
    claim.update(overrides)
    return claim


def evidence_doc(
    evidence_id: str,
    claim: str,
    *,
    commit: str,
    verdict: str = "PASS",
    passed: int = 5,
    failed: int = 0,
    skipped: int = 1,
    environment: dict | None = None,
    extras: dict | None = None,
) -> dict:
    doc: dict = {
        "schemaVersion": 1,
        "id": evidence_id,
        "claim": claim,
        "createdAt": "2026-01-01T00:00:00Z",
        "git": {"commit": commit, "dirty": False},
        "command": "make test",
        "environment": environment if environment is not None else {"source": "junit-xml"},
        "result": {
            "status": "SUCCEEDED" if failed == 0 else "FAILED",
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "durationSec": 0.1,
        },
        "verdict": verdict,
        "verifier": "tools/evidence_from_junit.py",
    }
    if extras:
        doc.update(extras)
    return doc


def leaky_xml(root: Path) -> str:
    hostname = "build-server-01"
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<testsuite name="leak" hostname="{hostname}" tests="3" failures="0" skipped="1" time="0.3">\n'
        "  <properties>\n"
        f'    <property name="repo.root" value="{root}"/>\n'
        f'    <property name="pytest.rootdir" value="{root}/build"/>\n'
        '    <property name="os" value="linux"/>\n'
        "  </properties>\n"
        '  <testcase name="t1" classname="A" time="0.1"/>\n'
        '  <testcase name="t2" classname="A" time="0.1"/>\n'
        '  <testcase name="t3" classname="A" time="0.1"><skipped/></testcase>\n'
        f"  <system-out>log at {root}/build/log.txt</system-out>\n"
        "  <system-err>boom</system-err>\n"
        "</testsuite>"
    )


class EvidenceChainTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="evidence-chain-")
        self.root = Path(self._tmp.name) / "repo"
        (self.root / "harness" / "evidence").mkdir(parents=True)
        (self.root / "docs").mkdir(parents=True)
        write(self.root / "docs" / "README.md", "# docs index\n")
        write(self.root / "README.md", "# demo\n")
        (self.root / "harness" / "plans").mkdir(parents=True)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    # ── fixture helpers ──────────────────────────────────────────────
    def prepare(
        self,
        claims: list[dict],
        *,
        baseline: dict | None = None,
        freshness: dict | None = None,
        commit: bool = True,
    ) -> str:
        write(self.root / "harness" / "config.json", json.dumps(base_config(claims, freshness), indent=2))
        if baseline is not None:
            write(self.root / "harness" / "test-baseline.json", json.dumps(baseline, indent=2))
        if not commit:
            return ""
        git_init(self.root)
        return commit_all(self.root, "base")

    def evidence_path(self, evidence_id: str, *, archive: bool = False, subdir: str | None = None) -> Path:
        directory = self.root / "harness" / "evidence"
        if archive:
            directory = directory / "_archive"
        if subdir:
            directory = directory / subdir
        return directory / f"{evidence_id}.json"

    def write_evidence(self, doc: dict, *, archive: bool = False, subdir: str | None = None) -> Path:
        directory = self.root / "harness" / "evidence"
        if archive:
            directory = directory / "_archive"
        if subdir:
            directory = directory / subdir
        return write(directory / f"{doc['id']}.json", json.dumps(doc, indent=2))

    def add_evidence(self, docs: list[dict], *, message: str = "evidence") -> str:
        for doc in docs:
            self.write_evidence(doc)
        return commit_all(self.root, message)

    def verify(self, *flags: str) -> subprocess.CompletedProcess[str]:
        return run([sys.executable, str(VERIFY), "--all", "--root", str(self.root), *flags], self.root)

    def combined(self, proc: subprocess.CompletedProcess[str]) -> str:
        return proc.stdout + proc.stderr

    @staticmethod
    def expect(proc: subprocess.CompletedProcess[str], *needles: str) -> None:
        text = proc.stdout + proc.stderr
        for needle in needles:
            assert needle in text, f"missing {needle!r} in output:\n{text}"

    # ══ E1：归档 / 取代 ═════════════════════════════════════════════
    def test_archive_only_is_unverified(self) -> None:
        self.prepare([static_claim()])
        archived = evidence_doc("20260101T000000Z-docs-pass", "docs-pass", commit=head_short(self.root))
        write(self.evidence_path(archived["id"], archive=True), json.dumps(archived))
        proc = self.verify()
        self.assertEqual(proc.returncode, 2, self.combined(proc))
        self.expect(proc, "验证 0 条当前证据", "SUPERSEDED", "CLAIM <none>: UNVERIFIED")

    def test_archived_fail_without_takeover_is_unverified(self) -> None:
        self.prepare([static_claim()])
        current = evidence_doc("20260101T000001Z-docs-pass", "docs-pass", commit=head_short(self.root))
        archived = evidence_doc(
            "20260101T000000Z-docs-pass", "docs-pass", commit=head_short(self.root), verdict="FAIL"
        )
        write(self.evidence_path(archived["id"], archive=True), json.dumps(archived))
        commit_all(self.root, "archive")
        self.add_evidence([current])
        proc = self.verify()
        self.assertEqual(proc.returncode, 2, self.combined(proc))
        self.expect(
            proc,
            "CLAIM 20260101T000001Z-docs-pass: PASS",
            "CLAIM 20260101T000000Z-docs-pass: UNVERIFIED — 归档FAIL证据未被合法取代",
            "结论：UNVERIFIED",
        )

    def test_archived_fail_with_takeover_passes(self) -> None:
        self.prepare([static_claim()])
        archived_id = "20260101T000000Z-docs-pass"
        current_id = "20260101T000001Z-docs-pass"
        archived = evidence_doc(archived_id, "docs-pass", commit=head_short(self.root), verdict="UNVERIFIED")
        write(self.evidence_path(archived_id, archive=True), json.dumps(archived))
        commit_all(self.root, "archive")
        current = evidence_doc(
            current_id, "docs-pass", commit=head_short(self.root), extras={"supersedes": [archived_id]}
        )
        self.add_evidence([current])
        proc = self.verify()
        self.assertEqual(proc.returncode, 0, self.combined(proc))
        self.expect(
            proc,
            f"CLAIM {archived_id}: SUPERSEDED — 已被 {current_id} 取代",
            "结论：PASS",
        )

    def test_supersedes_reason_from_current(self) -> None:
        self.prepare([static_claim()])
        archived_id = "20260101T000000Z-docs-pass"
        current_id = "20260101T000001Z-docs-pass"
        archived = evidence_doc(archived_id, "docs-pass", commit=head_short(self.root))
        current = evidence_doc(
            current_id, "docs-pass", commit=head_short(self.root), extras={"supersedes": [archived_id]}
        )
        write(self.evidence_path(archived_id, archive=True), json.dumps(archived))
        commit_all(self.root, "archive")
        self.add_evidence([current])
        proc = self.verify()
        self.expect(proc, f"已被 {current_id} 取代")

    def test_superseded_by_reason_from_archive(self) -> None:
        self.prepare([static_claim()])
        archived_id = "20260101T000000Z-docs-pass"
        current_id = "20260101T000001Z-docs-pass"
        current = evidence_doc(current_id, "docs-pass", commit=head_short(self.root))
        archived = evidence_doc(
            archived_id, "docs-pass", commit=head_short(self.root), extras={"supersededBy": current_id}
        )
        write(self.evidence_path(archived_id, archive=True), json.dumps(archived))
        commit_all(self.root, "archive")
        self.add_evidence([current])
        proc = self.verify()
        self.expect(proc, f"已被 {current_id} 取代")

    def test_unparseable_archive_is_still_listed(self) -> None:
        self.prepare([static_claim()])
        write(self.evidence_path("20260101T000000Z-docs-pass", archive=True), "{not valid json")
        commit_all(self.root, "broken archive")
        proc = self.verify()
        self.assertEqual(proc.returncode, 2, self.combined(proc))
        self.expect(proc, "SUPERSEDED — 位于 _archive（未声明取代关系）", "CLAIM <none>: UNVERIFIED")

    def test_nested_current_evidence_is_scanned(self) -> None:
        commit = self.prepare([static_claim()])
        doc = evidence_doc("20260101T000000Z-docs-pass", "docs-pass", commit=commit)
        write(self.evidence_path(doc["id"], subdir="run2"), json.dumps(doc))
        commit_all(self.root, "nested current")
        proc = self.verify()
        self.assertEqual(proc.returncode, 0, self.combined(proc))
        self.expect(proc, "验证 1 条当前证据", "CLAIM 20260101T000000Z-docs-pass: PASS")

    # ══ E1：tracked 要求 ════════════════════════════════════════════
    def test_untracked_pass_evidence_is_unverified(self) -> None:
        commit = self.prepare([static_claim()])
        doc = evidence_doc("20260101T000000Z-docs-pass", "docs-pass", commit=commit)
        self.write_evidence(doc)  # intentionally not committed
        proc = self.verify()
        self.assertEqual(proc.returncode, 2, self.combined(proc))
        self.expect(proc, "UNVERIFIED — command exit 0：true；证据文件未被 git 跟踪（CI 无法复核）")

    def test_allow_untracked_keeps_verdict_with_warning(self) -> None:
        commit = self.prepare([static_claim()])
        doc = evidence_doc("20260101T000000Z-docs-pass", "docs-pass", commit=commit)
        self.write_evidence(doc)
        proc = self.verify("--allow-untracked")
        self.assertEqual(proc.returncode, 0, self.combined(proc))
        self.expect(proc, "[WARN]", "证据文件未被 git 跟踪", "CLAIM 20260101T000000Z-docs-pass: PASS")

    def test_untracked_fail_evidence_keeps_fail(self) -> None:
        commit = self.prepare([static_claim()])
        doc = evidence_doc("20260101T000000Z-docs-pass", "docs-pass", commit=commit, verdict="FAIL")
        self.write_evidence(doc)
        proc = self.verify()
        self.assertEqual(proc.returncode, 1, self.combined(proc))
        self.expect(proc, "FAIL — 证据 verdict=FAIL；证据文件未被 git 跟踪")

    def test_non_git_repo_warns_once_and_skips_tracking(self) -> None:
        self.prepare([static_claim()], commit=False)  # no git init
        doc = evidence_doc("20260101T000000Z-docs-pass", "docs-pass", commit="0000000")
        self.write_evidence(doc)
        proc = self.verify()
        self.assertEqual(proc.returncode, 0, self.combined(proc))
        self.assertEqual(proc.stdout.count("[WARN] 非 git 仓库"), 1, proc.stdout)
        self.expect(proc, "CLAIM 20260101T000000Z-docs-pass: PASS")

    # ══ E3：claim 环境模型 ══════════════════════════════════════════
    def test_environment_mismatch_is_unverified(self) -> None:
        claim = test_count_claim(
            environment={
                "id": "server",
                "requires": ["mysql", "model-cache"],
                "os": "linux",
                "python": "3.12",
            }
        )
        commit = self.prepare([claim], baseline={"unit": {"floor": 5, "expectedSkipped": 1}})
        doc = evidence_doc(
            "20260101T000000Z-tests-pass",
            "tests-pass",
            commit=commit,
            environment={
                "id": "ci",
                "requires": ["postgres"],
                "os": "darwin",
                "python": "3.11",
                "source": "junit-xml",
            },
        )
        self.add_evidence([doc])
        proc = self.verify()
        self.assertEqual(proc.returncode, 2, self.combined(proc))
        self.expect(
            proc,
            "环境不匹配",
            "id 不匹配",
            "requires 未覆盖",
            "environment.os 不匹配",
            "environment.python 不匹配",
        )

    def test_environment_match_passes(self) -> None:
        claim = test_count_claim(
            environment={
                "id": "server",
                "requires": ["mysql"],
                "os": "linux",
                "python": "3.12",
            }
        )
        commit = self.prepare([claim], baseline={"unit": {"floor": 5, "expectedSkipped": 1}})
        doc = evidence_doc(
            "20260101T000000Z-tests-pass",
            "tests-pass",
            commit=commit,
            environment={
                "id": "server",
                "requires": ["mysql", "model-cache"],
                "os": "linux",
                "python": "3.12.4",
            },
        )
        self.add_evidence([doc])
        proc = self.verify()
        self.assertEqual(proc.returncode, 0, self.combined(proc))
        self.expect(proc, "CLAIM 20260101T000000Z-tests-pass: PASS")

    # ══ E3：expectedSkipped 容差 ════════════════════════════════════
    def test_expected_skipped_range(self) -> None:
        commit = self.prepare(
            [test_count_claim()],
            baseline={"unit": {"floor": 5, "expectedSkipped": {"min": 0, "max": 2}}},
        )
        doc = evidence_doc("20260101T000000Z-tests-pass", "tests-pass", commit=commit, skipped=2)
        self.add_evidence([doc])
        proc = self.verify()
        self.assertEqual(proc.returncode, 0, self.combined(proc))
        self.assertIn("in [0,2]", proc.stdout)
        doc["result"]["skipped"] = 3
        write(self.evidence_path(doc["id"]), json.dumps(doc))
        commit_all(self.root, "skipped out of range")
        proc = self.verify()
        self.assertEqual(proc.returncode, 1, self.combined(proc))
        self.expect(proc, "不在 [0,2]")

    def test_expected_skipped_by_environment(self) -> None:
        claim = test_count_claim(
            expectedSkipped={"byEnvironment": {"server": 1, "ci": {"min": 49, "max": 51}}}
        )
        commit = self.prepare([claim], baseline={"unit": {"floor": 5, "expectedSkipped": 1}})
        doc = evidence_doc(
            "20260101T000000Z-tests-pass",
            "tests-pass",
            commit=commit,
            skipped=50,
            environment={"id": "ci"},
        )
        self.add_evidence([doc])
        proc = self.verify()
        self.assertEqual(proc.returncode, 0, self.combined(proc))
        # unknown environment → UNVERIFIED (not FAIL)
        doc["environment"] = {"id": "qa"}
        write(self.evidence_path(doc["id"]), json.dumps(doc))
        commit_all(self.root, "unknown environment")
        proc = self.verify()
        self.assertEqual(proc.returncode, 2, self.combined(proc))
        self.expect(proc, "未定义环境 'qa'")
        # missing evidence environment.id → UNVERIFIED
        doc["environment"] = {"source": "junit-xml"}
        write(self.evidence_path(doc["id"]), json.dumps(doc))
        commit_all(self.root, "missing environment id")
        proc = self.verify()
        self.assertEqual(proc.returncode, 2, self.combined(proc))
        self.expect(proc, "需要证据 environment.id")

    def test_expected_skipped_exact_backward_compatible(self) -> None:
        commit = self.prepare(
            [test_count_claim()],
            baseline={"unit": {"floor": 5, "expectedSkipped": 1}},
        )
        doc = evidence_doc("20260101T000000Z-tests-pass", "tests-pass", commit=commit, skipped=1)
        self.add_evidence([doc])
        self.assertEqual(self.verify().returncode, 0)
        doc["result"]["skipped"] = 2
        write(self.evidence_path(doc["id"]), json.dumps(doc))
        commit_all(self.root, "skipped mismatch")
        proc = self.verify()
        self.assertEqual(proc.returncode, 1, self.combined(proc))
        self.expect(proc, "skipped=2 != unit.expectedSkipped=1")

    def test_invalid_expected_skipped_config_fails(self) -> None:
        commit = self.prepare(
            [test_count_claim(expectedSkipped={"min": 5})],
            baseline={"unit": {"floor": 5, "expectedSkipped": 1}},
        )
        doc = evidence_doc("20260101T000000Z-tests-pass", "tests-pass", commit=commit, skipped=1)
        self.add_evidence([doc])
        proc = self.verify()
        self.assertEqual(proc.returncode, 1, self.combined(proc))
        self.expect(proc, "区间需要整数 min/max")

    # ══ E3：static freshness ════════════════════════════════════════
    def test_static_claim_skips_freshness(self) -> None:
        commit = self.prepare([static_claim()], freshness={"docs-pass": ["docs/**"]})
        doc = evidence_doc("20260101T000000Z-docs-pass", "docs-pass", commit=commit)
        self.add_evidence([doc])
        write(self.root / "docs" / "README.md", "# docs index (dirty)\n")  # uncommitted change
        proc = self.verify("--fresh")
        self.assertEqual(proc.returncode, 0, self.combined(proc))
        self.expect(proc, "CLAIM 20260101T000000Z-docs-pass: PASS", "freshness 不适用")
        self.assertNotIn("STALE", proc.stdout)

    def test_test_count_claim_still_gets_stale_and_strict(self) -> None:
        commit = self.prepare(
            [test_count_claim()],
            baseline={"unit": {"floor": 5, "expectedSkipped": 1}},
            freshness={"tests-pass": ["docs/**"]},
        )
        doc = evidence_doc("20260101T000000Z-tests-pass", "tests-pass", commit=commit)
        self.add_evidence([doc])
        write(self.root / "docs" / "README.md", "# docs index (dirty)\n")
        relaxed = self.verify("--fresh")
        self.assertEqual(relaxed.returncode, 0, self.combined(relaxed))
        self.expect(relaxed, "STALE", "未加 --strict")
        strict = self.verify("--fresh", "--strict")
        self.assertEqual(strict.returncode, 2, self.combined(strict))
        self.expect(strict, "UNVERIFIED", "STALE", "--strict 降级")

    # ══ 红队补强：required claims / artifact tracked / strict ═══════
    def test_missing_required_claim_is_unverified(self) -> None:
        claims = [static_claim(), {"name": "arch-pass", "type": "static", "command": "true"}]
        commit = self.prepare(claims)
        doc = evidence_doc("20260101T000000Z-docs-pass", "docs-pass", commit=commit)
        self.add_evidence([doc])
        proc = self.verify()
        self.assertEqual(proc.returncode, 2, self.combined(proc))
        self.expect(
            proc,
            "CLAIM arch-pass: UNVERIFIED — 缺少当前证据（config.claims.required）",
            "结论：UNVERIFIED",
        )

    def test_required_false_claim_may_be_missing(self) -> None:
        claims = [
            static_claim(),
            {"name": "arch-pass", "type": "static", "command": "true", "required": False},
        ]
        commit = self.prepare(claims)
        doc = evidence_doc("20260101T000000Z-docs-pass", "docs-pass", commit=commit)
        self.add_evidence([doc])
        proc = self.verify()
        self.assertEqual(proc.returncode, 0, self.combined(proc))
        self.assertNotIn("CLAIM arch-pass", proc.stdout)

    def test_untracked_artifact_is_unverified(self) -> None:
        commit = self.prepare([static_claim()])
        doc = evidence_doc("20260101T000000Z-docs-pass", "docs-pass", commit=commit)
        doc["result"]["artifacts"] = ["build/junit.xml"]  # reference committed before the file exists
        self.add_evidence([doc])
        write(self.root / "build" / "junit.xml", "<testsuite/>")  # exists on disk, untracked
        proc = self.verify()
        self.assertEqual(proc.returncode, 2, self.combined(proc))
        self.expect(proc, "artifact 未被 git 跟踪", "CI 无法复核")
        # --strict 下 --allow-untracked 无效
        strict = self.verify("--allow-untracked", "--strict")
        self.assertEqual(strict.returncode, 2, self.combined(strict))
        self.expect(strict, "UNVERIFIED")

    def test_tracked_artifact_passes(self) -> None:
        commit = self.prepare([static_claim()])
        write(self.root / "build" / "junit.xml", "<testsuite/>")
        doc = evidence_doc("20260101T000000Z-docs-pass", "docs-pass", commit=commit)
        doc["result"]["artifacts"] = ["build/junit.xml"]
        self.add_evidence([doc])  # artifact committed together → tracked
        proc = self.verify()
        self.assertEqual(proc.returncode, 0, self.combined(proc))
        self.expect(proc, "CLAIM 20260101T000000Z-docs-pass: PASS")

    def test_strict_disables_allow_untracked_for_evidence(self) -> None:
        commit = self.prepare([static_claim()])
        doc = evidence_doc("20260101T000000Z-docs-pass", "docs-pass", commit=commit)
        self.write_evidence(doc)  # untracked evidence file
        proc = self.verify("--allow-untracked", "--strict")
        self.assertEqual(proc.returncode, 2, self.combined(proc))
        self.expect(proc, "UNVERIFIED", "证据文件未被 git 跟踪")

    # ══ E3：floorByEnvironment / 区间宽度 ═══════════════════════════
    def test_floor_by_environment(self) -> None:
        claim = test_count_claim(floorByEnvironment={"server": 7})
        commit = self.prepare(
            [claim], baseline={"unit": {"floor": 5, "expectedSkipped": 1}}
        )
        doc = evidence_doc(
            "20260101T000000Z-tests-pass", "tests-pass", commit=commit, passed=6,
            environment={"id": "server"},
        )
        self.add_evidence([doc])
        failed = self.verify()
        self.assertEqual(failed.returncode, 1, self.combined(failed))
        self.expect(failed, "passed=6 < unit.floor=7")
        doc["result"]["passed"] = 8
        write(self.evidence_path(doc["id"]), json.dumps(doc))
        commit_all(self.root, "floorByEnvironment pass")
        passed = self.verify()
        self.assertEqual(passed.returncode, 0, self.combined(passed))
        # missing environment id → UNVERIFIED
        doc["environment"] = {"source": "junit-xml"}
        write(self.evidence_path(doc["id"]), json.dumps(doc))
        commit_all(self.root, "missing env id")
        missing = self.verify()
        self.assertEqual(missing.returncode, 2, self.combined(missing))
        self.expect(missing, "floorByEnvironment 需要证据 environment.id")

    def test_skipped_range_too_wide_fails(self) -> None:
        commit = self.prepare(
            [test_count_claim()],
            baseline={"unit": {"floor": 5, "expectedSkipped": {"min": 0, "max": 10}}},
        )
        doc = evidence_doc("20260101T000000Z-tests-pass", "tests-pass", commit=commit, skipped=3)
        self.add_evidence([doc])
        proc = self.verify()
        self.assertEqual(proc.returncode, 1, self.combined(proc))
        self.expect(proc, "区间过宽", "maxSkippedRange")

    def test_skipped_range_width_override(self) -> None:
        config_path = self.root / "harness" / "config.json"
        commit = self.prepare(
            [test_count_claim()],
            baseline={"unit": {"floor": 5, "expectedSkipped": {"min": 0, "max": 10}}},
        )
        config = json.loads(config_path.read_text(encoding="utf-8"))
        config["harden"] = {"maxSkippedRange": 10}
        config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
        commit_all(self.root, "harden range")
        doc = evidence_doc("20260101T000000Z-tests-pass", "tests-pass", commit=commit, skipped=3)
        self.add_evidence([doc])
        proc = self.verify()
        self.assertEqual(proc.returncode, 0, self.combined(proc))

    # ══ E2：JUnit 默认脱敏 ═════════════════════════════════════════
    def test_junit_default_sanitizes_and_copies(self) -> None:
        self.prepare([static_claim()])
        write(self.root / "reports" / "TEST-leak.xml", leaky_xml(self.root))
        proc = run(
            [
                sys.executable,
                str(JUNIT),
                "--root",
                str(self.root),
                "--xml",
                "reports/TEST-leak.xml",
                "--command",
                "make test",
                "--output",
                "payload.json",
            ],
            self.root,
        )
        self.assertEqual(proc.returncode, 0, self.combined(proc))
        payload = json.loads((self.root / "payload.json").read_text(encoding="utf-8"))
        result = payload["result"]
        self.assertEqual(result["artifactMode"], "sanitized-copy")
        self.assertEqual((result["passed"], result["failed"], result["skipped"]), (2, 0, 1))
        artifact = result["artifacts"][0]
        self.assertFalse(Path(artifact).is_absolute(), artifact)
        copied = self.root / artifact
        self.assertTrue(copied.is_file(), f"missing artifact: {artifact}")
        content = copied.read_text(encoding="utf-8")
        for leaked in ("build-server-01", "system-out", "system-err", str(self.root)):
            self.assertNotIn(leaked, content, f"artifact leaks {leaked!r}")


if __name__ == "__main__":
    unittest.main()
