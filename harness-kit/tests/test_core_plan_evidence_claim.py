#!/usr/bin/env python3
"""harness-kit core 脚本回归测试：check_plan / evidence / verify_claim（unittest，仅标准库）。

用 `tempfile` 建最小目标仓（harness/config.json、plans、evidence、schema、test-baseline），
在仓库内 `git init` + commit，然后用 `--root` 跑真实 CLI（subprocess），断言 exit code 与输出。
不依赖本机 Xcode / 真机 / 网络。
运行：python3 -m unittest discover -s harness-kit/tests -q
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[1]
TOOLS = KIT_ROOT / "core" / "tools"
CHECK_PLAN = TOOLS / "check_plan.py"
EVIDENCE = TOOLS / "evidence.py"
VERIFY_CLAIM = TOOLS / "verify_claim.py"

VALID_EVIDENCE_ID = "20260101T000000Z-docs-pass"


# ── helpers ───────────────────────────────────────────────────────────────
def run(cmd: list[str], *, cwd: Path | str | None = None, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd, cwd=str(cwd) if cwd else None, capture_output=True, text=True, input=stdin
    )


def git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return run(["git", "-C", str(root), *args])


def head_short(root: Path, length: int = 7) -> str:
    return git(root, "rev-parse", f"--short={length}", "HEAD").stdout.strip()


def init_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    if git(path, "init", "-q").returncode != 0:
        raise AssertionError("git init 失败")
    for key, value in (("user.name", "test"), ("user.email", "test@example.invalid")):
        if git(path, "config", key, value).returncode != 0:
            raise AssertionError(f"git config {key} 失败")
    (path / "README.md").write_text("# demo\n", encoding="utf-8")
    if git(path, "add", "-A").returncode != 0 or git(path, "commit", "-q", "-m", "init").returncode != 0:
        raise AssertionError("初始提交失败")


def base_config(claims: list[dict], freshness: dict | None = None) -> dict:
    return {
        "kitVersion": "0.1.0",
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
        "instructions": {
            "root": "AGENTS.md",
            "nested": [],
            "nestedMaxBytes": 8192,
            "budgets": {},
            "sensitivePatterns": ["sk-"],
        },
        "docs": {"publicWhitelist": ["README.md"], "publicBudget": 12, "rootMarkdownAllowed": ["README.md"]},
        "commands": {"check": "make check", "verify": "make verify-static", "test": "make test"},
        "claims": claims,
        "freshness": freshness or {},
    }


EVIDENCE_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["id", "claim", "createdAt", "git", "command", "environment", "result", "verdict", "verifier"],
    "additionalProperties": True,
    "properties": {
        "schemaVersion": {"type": "integer", "const": 1},
        "id": {"type": "string", "pattern": "^[0-9]{8}T[0-9]{6}Z-[a-z0-9-]+$"},
        "claim": {"type": "string", "pattern": "^[a-z0-9][a-z0-9-]*$"},
        "createdAt": {"type": "string", "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"},
        "git": {
            "type": "object",
            "required": ["commit", "dirty"],
            "properties": {
                "commit": {"type": "string", "pattern": "^[0-9a-f]{7,40}$"},
                "dirty": {"type": "boolean"},
            },
        },
        "command": {"type": "string", "minLength": 1},
        "environment": {"type": "object"},
        "result": {
            "type": "object",
            "required": ["status", "passed", "failed", "skipped"],
            "properties": {
                "status": {"enum": ["SUCCEEDED", "FAILED", "SKIPPED", "UNVERIFIED"]},
                "passed": {"type": "integer", "minimum": 0},
                "failed": {"type": "integer", "minimum": 0},
                "skipped": {"type": "integer", "minimum": 0},
                "durationSec": {"type": "number", "minimum": 0},
                "xcresultPath": {"type": ["string", "null"]},
            },
        },
        "verdict": {"type": "string", "enum": ["PASS", "FAIL", "UNVERIFIED"]},
        "verifier": {"type": "string", "minLength": 1},
    },
}

STATIC_CLAIM = {"name": "docs-pass", "type": "static", "command": "true"}
STATIC_CLAIM_FAIL = {"name": "docs-fail", "type": "static", "command": "false"}
STATIC_CLAIM_NO_CMD = {"name": "docs-nocmd", "type": "static"}
TEST_COUNT_CLAIM = {
    "name": "tests-pass",
    "type": "test-count",
    "baseline": "harness/test-baseline.json",
    "floor": "unit.floor",
    "expectedSkipped": "unit.expectedSkipped",
    "command": "make test",
}


def plan_front(status: str = "active", *, submitted: str | None = None, scope: bool = True) -> str:
    lines = [
        "id: 2026-01-01-demo",
        f"status: {status}",
        "level: L2",
        "owner: test",
        "updated: 2026-01-01",
    ]
    if scope:
        lines += ["scope:", "  allow:", "    - harness/"]
    lines += ["acceptance:", "  - make check 通过", "verify:", "  - python3 tools/check_plan.py check"]
    if submitted is not None:
        lines.append(f"submitted: {submitted}")
    return "\n".join(lines)


def plan_body(
    rows: str,
    *,
    evidence_section: bool = True,
    uncommitted: bool = True,
    target: bool = True,
    acceptance: bool = True,
    next_step: bool = True,
) -> str:
    parts = ["# 测试计划", ""]
    if target:
        parts += ["## 目标与非目标", "", "- 目标：验证 harness-kit 脚本", ""]
    if acceptance:
        parts += ["## 验收", "", "- python3 -m unittest 通过", ""]
    if evidence_section:
        parts += [
            "## 验证证据",
            "",
            "| 命令 | 结果 | 环境 | 证据ID |",
            "| --- | --- | --- | --- |",
            rows,
            "",
        ]
    if uncommitted:
        parts += ["## 未提交改动", "", "- 无未提交改动（测试仓库）", ""]
    if next_step:
        parts += ["## 下一步", "", "1. 继续", ""]
    return "\n".join(parts)


def evidence_doc(
    evidence_id: str,
    claim: str,
    verdict: str = "PASS",
    *,
    commit: str = "0000000",
    dirty: bool = False,
    result: dict | None = None,
    command: str = "true",
) -> dict:
    payload_result = {
        "status": "SUCCEEDED",
        "passed": 1,
        "failed": 0,
        "skipped": 0,
        "durationSec": 0.1,
        "xcresultPath": None,
    }
    if result:
        payload_result.update(result)
    return {
        "schemaVersion": 1,
        "id": evidence_id,
        "claim": claim,
        "createdAt": "2026-01-01T00:00:00Z",
        "git": {"commit": commit, "dirty": dirty},
        "command": command,
        "environment": {"xcode": None, "simulator": None, "device": None},
        "result": payload_result,
        "verdict": verdict,
        "verifier": "tools/evidence.py@test",
    }


class KitCoreTest(unittest.TestCase):
    """最小目标仓 fixture（每个用例独立 tempfile + git 仓库）。"""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "harness" / "plans").mkdir(parents=True)
        (self.root / "harness" / "evidence").mkdir(parents=True)
        init_repo(self.root)
        self.base = head_short(self.root)
        self.write_config()
        (self.root / "harness" / "evidence" / "schema.json").write_text(
            json.dumps(EVIDENCE_SCHEMA, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def tearDown(self) -> None:
        self._tmp.cleanup()

    # ── fixture 写入 ─────────────────────────────────────────────────
    def write_config(self, claims: list[dict] | None = None, freshness: dict | None = None) -> None:
        config = base_config(claims or [dict(STATIC_CLAIM)], freshness)
        (self.root / "harness" / "config.json").write_text(
            json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def write_baseline(self, floor: int = 120, expected_skipped: int = 1) -> None:
        baseline = {"unit": {"floor": floor, "expectedSkipped": expected_skipped}}
        (self.root / "harness" / "test-baseline.json").write_text(
            json.dumps(baseline), encoding="utf-8"
        )

    def write_plan(self, body: str, *, status: str = "active", submitted: str | None = None, name: str = "2026-01-01-demo") -> Path:
        path = self.root / "harness" / "plans" / f"{name}.md"
        path.write_text(
            f"---\n{plan_front(status, submitted=submitted)}\n---\n\n{body}", encoding="utf-8"
        )
        return path

    def write_plan_id(self, front: str, body: str, name: str) -> Path:
        path = self.root / "harness" / "plans" / f"{name}.md"
        path.write_text(f"---\n{front}\n---\n\n{body}", encoding="utf-8")
        return path

    def write_evidence(self, doc: dict) -> Path:
        path = self.root / "harness" / "evidence" / f"{doc['id']}.json"
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def commit_all(self, message: str = "fixtures") -> str:
        if git(self.root, "add", "-A").returncode != 0 or git(self.root, "commit", "-q", "-m", message).returncode != 0:
            raise AssertionError("fixtures 提交失败")
        return head_short(self.root)

    def commit_change(self, relative: str, content: str, message: str = "change") -> str:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return self.commit_all(message)

    # ── CLI 调用 ─────────────────────────────────────────────────────
    def check_plan(self, *args: str) -> subprocess.CompletedProcess[str]:
        return run([sys.executable, str(CHECK_PLAN), *args, "--root", str(self.root)], cwd=self.root)

    def evidence(self, *args: str, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
        return run([sys.executable, str(EVIDENCE), *args, "--root", str(self.root)], cwd=self.root, stdin=stdin)

    def verify_claim(self, *args: str) -> subprocess.CompletedProcess[str]:
        return run(
            [sys.executable, str(VERIFY_CLAIM), *args, "--root", str(self.root)], cwd=self.root
        )

    def assert_fail(self, proc: subprocess.CompletedProcess[str], *needles: str) -> None:
        self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        for needle in needles:
            self.assertIn(needle, proc.stdout, f"缺少输出：{needle}\n{proc.stdout}")

    # ══ check_plan ═══════════════════════════════════════════════════
    def test_check_plan_passes_with_process_annotation(self) -> None:
        rows = "| `make check` | **PASS** | 本机 | —（过程记录：手工冒烟） |"
        self.write_plan(plan_body(rows))
        self.commit_all()
        proc = self.check_plan("check")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("结论：PASS", proc.stdout)
        self.assertIn("[WARN]", proc.stdout)  # active 无真实 evidence ID，只告警

    def test_check_plan_brief_prints_active_plan(self) -> None:
        rows = "| `make check` | 基线盘点 | 本机 | —（基线盘点） |"
        self.write_plan(plan_body(rows))
        self.commit_all()
        proc = self.check_plan("brief")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        for label in ("计划：", "## 目标与非目标", "## 验收", "## 下一步"):
            self.assertIn(label, proc.stdout)

    def test_check_plan_fails_missing_evidence_id_file(self) -> None:
        rows = f"| `make test` | **PASS** | 本机 | {VALID_EVIDENCE_ID} |"
        self.write_plan(plan_body(rows))
        self.commit_all()
        self.assert_fail(self.check_plan("check"), "证据 ID 不存在")

    def test_check_plan_fails_evidence_verdict_not_pass(self) -> None:
        self.write_evidence(
            evidence_doc(VALID_EVIDENCE_ID, "docs-pass", "UNVERIFIED", commit=self.base)
        )
        rows = f"| `make test` | **PASS** | 本机 | {VALID_EVIDENCE_ID} |"
        self.write_plan(plan_body(rows))
        self.commit_all()
        self.assert_fail(self.check_plan("check"), "证据 verdict 非 PASS")

    def test_check_plan_fails_placeholder_without_whitelist(self) -> None:
        rows = "| `make check` | **PASS** | 本机 | —（Phase 3.1） |"
        self.write_plan(plan_body(rows))
        self.commit_all()
        self.assert_fail(self.check_plan("check"), "不是可解析的 evidence id")

    def test_check_plan_whitelist_accepts_baseline_annotation(self) -> None:
        rows = "| `make check` | **PASS** | 本机 | —（基线盘点） |"
        self.write_plan(plan_body(rows))
        self.commit_all()
        proc = self.check_plan("check")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_check_plan_done_requires_submitted(self) -> None:
        self.write_evidence(evidence_doc(VALID_EVIDENCE_ID, "docs-pass", "PASS", commit=self.base))
        rows = f"| `make test` | **PASS** | 本机 | {VALID_EVIDENCE_ID} |"
        self.write_plan(plan_body(rows, uncommitted=False), status="done")
        self.commit_all()
        self.assert_fail(self.check_plan("check"), "缺少 front matter submitted")

    def test_check_plan_done_valid_passes(self) -> None:
        self.write_evidence(evidence_doc(VALID_EVIDENCE_ID, "docs-pass", "PASS", commit=self.base))
        rows = f"| `make test` | **PASS** | 本机 | {VALID_EVIDENCE_ID} |"
        self.write_plan(plan_body(rows, uncommitted=False), status="done", submitted=self.base)
        self.commit_all()
        proc = self.check_plan("check")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("结论：PASS", proc.stdout)

    def test_check_plan_done_requires_ancestor_submitted(self) -> None:
        self.write_evidence(evidence_doc(VALID_EVIDENCE_ID, "docs-pass", "PASS", commit=self.base))
        rows = f"| `make test` | **PASS** | 本机 | {VALID_EVIDENCE_ID} |"
        self.write_plan(plan_body(rows, uncommitted=False), status="done", submitted="deadbee")
        self.commit_all()
        self.assert_fail(self.check_plan("check"), "submitted 中的 commit 不存在")

    def test_check_plan_requires_single_active(self) -> None:
        rows = "| `make check` | 基线盘点 | 本机 | —（基线盘点） |"
        body = plan_body(rows)
        self.write_plan(body, name="2026-01-01-demo")
        front = plan_front("active").replace("id: 2026-01-01-demo", "id: 2026-01-02-other")
        self.write_plan_id(front, body, "2026-01-02-other")
        self.commit_all()
        self.assert_fail(self.check_plan("check"), "只允许 1 个")

    def test_check_plan_active_uncommitted_mismatch_fails(self) -> None:
        rows = "| `make check` | 基线盘点 | 本机 | —（基线盘点） |"
        self.write_plan(plan_body(rows))
        self.commit_all()
        # scope.allow 内出现未声明改动 → FAIL
        (self.root / "harness" / "config.json").write_text(
            (self.root / "harness" / "config.json").read_text(encoding="utf-8") + "\n",
            encoding="utf-8",
        )
        self.assert_fail(self.check_plan("check"), "计划声明无未提交改动")

    def test_check_plan_out_of_scope_change_fails(self) -> None:
        rows = "| `make check` | 基线盘点 | 本机 | —（基线盘点） |"
        self.write_plan(plan_body(rows))
        self.commit_all()
        (self.root / "src").mkdir()
        (self.root / "src" / "app.py").write_text("print('x')\n", encoding="utf-8")
        self.assert_fail(self.check_plan("check"), "scope.allow 之外的未提交改动")

    def test_check_plan_new_uses_template(self) -> None:
        template = (
            "---\nid: <date>-<topic>\nstatus: <active|done|blocked|archived>\n"
            "level: L2\nowner: <owner>\nupdated: <date>\nscope:\n  allow:\n    - harness/\n"
            "acceptance:\n  - <criteria>\nverify:\n  - <command>\n---\n\n# <主题> · 计划\n"
        )
        (self.root / "harness" / "plans" / "_template.md").write_text(template, encoding="utf-8")
        proc = self.check_plan("new", "demo-topic")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        files = list((self.root / "harness" / "plans").glob("*-demo-topic.md"))
        self.assertEqual(len(files), 1, proc.stdout)
        text = files[0].read_text(encoding="utf-8")
        self.assertRegex(text, r"id: \d{4}-\d{2}-\d{2}-demo-topic")
        self.assertIn("status: active", text)
        self.assertRegex(text, r"updated: \d{4}-\d{2}-\d{2}")
        self.assertNotIn("{{", text)

    # ══ evidence ════════════════════════════════════════════════════
    def test_evidence_write_clean_then_dirty_refused(self) -> None:
        self.write_config([dict(STATIC_CLAIM)])
        self.commit_all()
        payload = {
            "schemaVersion": 1,
            "claim": "docs-pass",
            "command": "make check",
            "environment": {"xcode": None, "simulator": None, "device": None},
            "result": {"status": "SUCCEEDED", "passed": 1, "failed": 0, "skipped": 0, "durationSec": 0.1},
            "verdict": "PASS",
        }
        proc = self.evidence("write", "--claim", "docs-pass", "--from-json", "-", stdin=json.dumps(payload))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        files = list((self.root / "harness" / "evidence").glob("*-docs-pass.json"))
        self.assertEqual(len(files), 1)
        doc = json.loads(files[0].read_text(encoding="utf-8"))
        self.assertEqual(doc["id"], files[0].stem)
        self.assertRegex(doc["id"], r"^\d{8}T\d{6}Z-docs-pass$")
        self.assertEqual(doc["git"]["dirty"], False)
        self.assertTrue(doc["git"]["commit"].startswith(head_short(self.root)[:7]))
        self.assertIn("0.1.0", doc["verifier"])
        # 脏树拒绝写入
        (self.root / "dirty.txt").write_text("x\n", encoding="utf-8")
        payload["verdict"] = "PASS"
        proc = self.evidence("write", "--claim", "docs-pass", "--from-json", "-", stdin=json.dumps(payload))
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("工作树不 clean", proc.stdout)

    def test_evidence_write_rejects_unknown_claim(self) -> None:
        self.write_config([dict(STATIC_CLAIM)])
        self.commit_all()
        payload = {"claim": "not-declared", "command": "true", "environment": {}, "result": {"status": "SUCCEEDED", "passed": 1, "failed": 0, "skipped": 0}, "verdict": "PASS"}
        proc = self.evidence("write", "--claim", "not-declared", "--from-json", "-", stdin=json.dumps(payload))
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("claim 不在 config.claims", proc.stdout)

    def test_evidence_validate_detects_schema_and_semantic_errors(self) -> None:
        self.write_config([dict(STATIC_CLAIM)])
        good = evidence_doc("20260101T000000Z-docs-pass", "docs-pass", "PASS", commit=self.base)
        self.write_evidence(good)
        proc = self.evidence("validate")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("[OK]", proc.stdout)
        # verdict 非法 → schema 失败
        bad = evidence_doc("20260101T000001Z-docs-pass", "docs-pass", "BROKEN", commit=self.base)
        bad["verdict"] = "BROKEN"
        self.write_evidence(bad)
        proc = self.evidence("validate")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("[FAIL]", proc.stdout)
        # PASS + dirty=true → 语义失败
        dirty = evidence_doc("20260101T000002Z-docs-pass", "docs-pass", "PASS", commit=self.base, dirty=True)
        self.write_evidence(dirty)
        proc = self.evidence("validate")
        self.assertIn("dirty", proc.stdout.lower())

    def test_evidence_ls_lists_and_filters(self) -> None:
        self.write_config([dict(STATIC_CLAIM), {"name": "arch-pass", "type": "static", "command": "true"}])
        self.write_evidence(evidence_doc("20260101T000000Z-docs-pass", "docs-pass", "PASS", commit=self.base))
        self.write_evidence(evidence_doc("20260101T000001Z-arch-pass", "arch-pass", "UNVERIFIED", commit=self.base))
        proc = self.evidence("ls")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("20260101T000000Z-docs-pass", proc.stdout)
        self.assertIn("20260101T000001Z-arch-pass", proc.stdout)
        proc = self.evidence("ls", "--claim", "docs-pass")
        self.assertIn("20260101T000000Z-docs-pass", proc.stdout)
        self.assertNotIn("20260101T000001Z-arch-pass", proc.stdout)

    # ══ verify_claim ════════════════════════════════════════════════
    def test_verify_claim_static_three_values_and_aggregate(self) -> None:
        self.write_config([dict(STATIC_CLAIM), dict(STATIC_CLAIM_FAIL), dict(STATIC_CLAIM_NO_CMD)])
        self.commit_all()
        self.write_evidence(evidence_doc("20260101T000000Z-docs-pass", "docs-pass", "PASS", commit=self.base))
        self.write_evidence(evidence_doc("20260101T000001Z-docs-fail", "docs-fail", "PASS", commit=self.base))
        self.write_evidence(evidence_doc("20260101T000002Z-docs-nocmd", "docs-nocmd", "PASS", commit=self.base))
        proc = self.verify_claim("--all")
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertRegex(proc.stdout, r"CLAIM 20260101T000000Z-docs-pass: PASS — ")
        self.assertRegex(proc.stdout, r"CLAIM 20260101T000001Z-docs-fail: FAIL — ")
        self.assertRegex(proc.stdout, r"CLAIM 20260101T000002Z-docs-nocmd: UNVERIFIED — ")

    def test_verify_claim_all_pass_exit_zero(self) -> None:
        self.write_config([dict(STATIC_CLAIM)])
        self.commit_all()
        self.write_evidence(evidence_doc("20260101T000000Z-docs-pass", "docs-pass", "PASS", commit=self.base))
        proc = self.verify_claim("--all")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("结论：PASS", proc.stdout)

    def test_verify_claim_recorded_unverified_is_exit_two(self) -> None:
        self.write_config([dict(STATIC_CLAIM)])
        self.commit_all()
        self.write_evidence(evidence_doc("20260101T000000Z-docs-pass", "docs-pass", "UNVERIFIED", commit=self.base))
        proc = self.verify_claim("--all")
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertRegex(proc.stdout, r"CLAIM 20260101T000000Z-docs-pass: UNVERIFIED — ")

    def test_verify_claim_test_count_rules(self) -> None:
        self.write_config([dict(TEST_COUNT_CLAIM)])
        self.write_baseline(floor=120, expected_skipped=1)
        self.commit_all()
        # 正常：passed=120、skipped=1、xcresultPath 存在
        good = evidence_doc(
            "20260101T000000Z-tests-pass",
            "tests-pass",
            "PASS",
            commit=self.base,
            result={"passed": 120, "failed": 0, "skipped": 1, "xcresultPath": "build/test.xcresult"},
        )
        self.write_evidence(good)
        proc = self.verify_claim("--all")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertRegex(proc.stdout, r"tests-pass: PASS — ")
        # 默认不要求产物路径（通用项目）：缺 artifact 仍 PASS
        no_path = evidence_doc(
            "20260101T000001Z-tests-pass",
            "tests-pass",
            "PASS",
            commit=self.base,
            result={"passed": 120, "failed": 0, "skipped": 1, "xcresultPath": None},
        )
        (self.root / "harness" / "evidence" / f"{no_path['id']}.json").write_text(
            json.dumps(no_path), encoding="utf-8"
        )
        proc = self.verify_claim("--all")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        # claim.requireArtifact=true 时缺产物 → UNVERIFIED
        strict_claim = dict(TEST_COUNT_CLAIM, requireArtifact=True)
        self.write_config([strict_claim])
        (self.root / "harness" / "evidence" / f"{no_path['id']}.json").write_text(
            json.dumps(no_path), encoding="utf-8"
        )
        (self.root / "harness" / "evidence" / "20260101T000000Z-tests-pass.json").unlink()
        proc = self.verify_claim("--all")
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertRegex(proc.stdout, r"tests-pass: UNVERIFIED — .*requireArtifact")
        # 低于 floor → FAIL
        low = evidence_doc(
            "20260101T000002Z-tests-pass",
            "tests-pass",
            "PASS",
            commit=self.base,
            result={"passed": 100, "failed": 0, "skipped": 1, "xcresultPath": "build/test.xcresult"},
        )
        (self.root / "harness" / "evidence" / f"{low['id']}.json").write_text(
            json.dumps(low), encoding="utf-8"
        )
        proc = self.verify_claim("--all")
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("passed=100", proc.stdout)

    def test_verify_claim_freshness_ignores_process_dirs(self) -> None:
        # evidence / plans / reviews 是过程状态，不使 claim 失效
        self.write_config([dict(STATIC_CLAIM)], freshness={"docs-pass": ["harness/**"]})
        head = self.commit_all()
        self.write_evidence(evidence_doc("20260101T000000Z-docs-pass", "docs-pass", "PASS", commit=head))
        (self.root / "harness" / "plans").mkdir(parents=True, exist_ok=True)
        (self.root / "harness" / "plans" / "note.md").write_text("draft\n", encoding="utf-8")
        proc = self.verify_claim("--all", "--fresh")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertNotIn("STALE", proc.stdout)
        # 非过程文件变脏 → STALE
        (self.root / "harness" / "notes.md").write_text("scratch\n", encoding="utf-8")
        proc = self.verify_claim("--all", "--fresh")
        self.assertIn("STALE", proc.stdout)

    def test_verify_claim_freshness_clean_and_dirty(self) -> None:
        self.write_config([dict(STATIC_CLAIM)], freshness={"docs-pass": ["docs/**"]})
        self.write_evidence(evidence_doc("20260101T000000Z-docs-pass", "docs-pass", "PASS", commit=self.base))
        self.commit_all()
        proc = self.verify_claim("--all", "--fresh")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertNotIn("STALE", proc.stdout)
        # 相关路径变脏 → STALE（不加 --strict：仍 PASS，但提示）
        (self.root / "docs").mkdir()
        (self.root / "docs" / "note.md").write_text("# note\n", encoding="utf-8")
        proc = self.verify_claim("--all", "--fresh")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("STALE", proc.stdout)
        # --strict → PASS 降级 UNVERIFIED
        proc = self.verify_claim("--all", "--fresh", "--strict")
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertRegex(proc.stdout, r"CLAIM 20260101T000000Z-docs-pass: UNVERIFIED — .*STALE")

    def test_verify_claim_no_evidence_is_unverified(self) -> None:
        self.write_config([dict(STATIC_CLAIM)])
        self.commit_all()
        proc = self.verify_claim("--all")
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("未找到证据文件", proc.stdout)

    def test_scripts_work_after_copy_into_target_tools(self) -> None:
        """init 会把这 3 个脚本复制到目标项目 tools/；默认根 = tools/ 的父目录。"""
        import shutil

        tools_dir = self.root / "tools"
        tools_dir.mkdir(exist_ok=True)
        for script in (CHECK_PLAN, EVIDENCE, VERIFY_CLAIM):
            shutil.copy(script, tools_dir / script.name)
        rows = "| `make check` | 基线盘点 | 本机 | —（基线盘点） |"
        self.write_plan(plan_body(rows))
        self.commit_all()
        proc = run([sys.executable, str(tools_dir / "check_plan.py")], cwd=self.root)  # 默认 check
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        proc = run([sys.executable, str(tools_dir / "evidence.py"), "ls"], cwd=self.root)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        proc = run([sys.executable, str(tools_dir / "verify_claim.py"), "--all"], cwd=self.root)
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)  # 无证据 → UNVERIFIED

    def test_missing_config_fails_readably(self) -> None:
        (self.root / "harness" / "config.json").unlink()
        proc = self.check_plan("check")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("缺少配置", proc.stdout)


if __name__ == "__main__":
    unittest.main()
