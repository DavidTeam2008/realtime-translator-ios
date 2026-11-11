#!/usr/bin/env python3
"""harness-kit core 脚本回归测试：check_plan / evidence / verify_claim（unittest，仅标准库）。

用 `tempfile` 建最小目标仓（harness/config.json、plans、evidence、schema、test-baseline），
在仓库内 `git init` + commit，然后用 `--root` 跑真实 CLI（subprocess），断言 exit code 与输出。
不依赖本机 Xcode / 真机 / 网络。
运行：python3 -m unittest discover -s harness-kit/tests -q
"""
from __future__ import annotations

import datetime as dt
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


def plan_front(
    status: str = "active",
    *,
    submitted: str | None = None,
    scope: bool = True,
    extra_scope: tuple[str, ...] = (),
) -> str:
    lines = [
        "id: 2026-01-01-demo",
        f"status: {status}",
        "level: L2",
        "owner: test",
        "updated: 2026-01-01",
    ]
    if scope:
        lines += ["scope:", "  allow:", "    - harness/"]
        lines += [f"    - {entry}" for entry in extra_scope]
    lines += ["acceptance:", "  - make check 通过", "verify:", "  - python3 tools/check_plan.py check"]
    if submitted is not None:
        lines.append(f"submitted: {submitted}")
    return "\n".join(lines)


def plan_front_allow(
    allow: tuple[str, ...],
    *,
    status: str = "active",
    submitted: str | None = None,
    exceptions: tuple[str, ...] = (),
) -> str:
    lines = [
        "id: 2026-01-01-demo",
        f"status: {status}",
        "level: L2",
        "owner: test",
        "updated: 2026-01-01",
        "scope:",
        "  allow:",
    ]
    lines += [f"    - {item}" for item in allow]
    lines += ["  deny: []"]
    if exceptions:
        lines += ["  exceptions:"] + [f"    - {item}" for item in exceptions]
    lines += [
        "acceptance:",
        "  - make check 通过",
        "verify:",
        "  - python3 tools/check_plan.py check",
    ]
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


def junit_xml(*, passed: int, failed: int = 0, skipped: int = 0) -> str:
    """Minimal JUnit XML fixture that the verifier can recompute counts from."""
    cases: list[str] = []
    for _ in range(passed):
        cases.append('<testcase classname="t" name="ok"/>')
    for _ in range(failed):
        cases.append('<testcase classname="t" name="bad"><failure message="x"/></testcase>')
    for _ in range(skipped):
        cases.append('<testcase classname="t" name="skip"><skipped/></testcase>')
    total = passed + failed + skipped
    return f'<testsuite name="suite" tests="{total}">' + "".join(cases) + "</testsuite>"


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
        submitted = self.commit_change("harness/notes.md", "notes\n", "in-scope change")
        self.write_evidence(evidence_doc(VALID_EVIDENCE_ID, "docs-pass", "PASS", commit=submitted))
        rows = f"| `make test` | **PASS** | 本机 | {VALID_EVIDENCE_ID} |"
        self.write_plan(plan_body(rows, uncommitted=False), status="done", submitted=submitted)
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

    def test_check_plan_declares_extensionless_root_file(self) -> None:
        """Makefile 等无扩展名根文件必须能被「未提交改动」声明（回归：曾被通用路径规则丢弃）。"""
        rows = "| `make check` | 基线盘点 | 本机 | —（基线盘点） |"
        self.write_plan(plan_body(rows))
        makefile = self.root / "Makefile"
        makefile.write_text("all:\n\t@true\n", encoding="utf-8")
        self.commit_all("track Makefile")
        front = plan_front("active", extra_scope=("Makefile",))
        body = plan_body(rows).replace(
            "- 无未提交改动（测试仓库）", "- `Makefile` / 构建目标 / 可丢弃"
        )
        self.write_plan_id(front, body, "2026-01-01-demo")
        self.commit_all("declare Makefile")
        makefile.write_text("all:\n\t@true\n# modified\n", encoding="utf-8")
        proc = self.check_plan("check")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_check_plan_undeclared_extensionless_root_file_fails(self) -> None:
        rows = "| `make check` | 基线盘点 | 本机 | —（基线盘点） |"
        front = plan_front("active", extra_scope=("Makefile",))
        self.write_plan_id(front, plan_body(rows), "2026-01-01-demo")
        makefile = self.root / "Makefile"
        makefile.write_text("all:\n\t@true\n", encoding="utf-8")
        self.commit_all("track Makefile")
        makefile.write_text("all:\n\t@true\n# modified\n", encoding="utf-8")
        self.assert_fail(self.check_plan("check"), "git 有未提交改动但计划未声明：Makefile")

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

    def test_check_plan_lenient_uncommitted_warns_only(self) -> None:
        rows = "| `make check` | 基线盘点 | 本机 | —（基线盘点） |"
        self.write_plan(plan_body(rows))
        self.commit_all()
        (self.root / "harness" / "config.json").write_text(
            (self.root / "harness" / "config.json").read_text(encoding="utf-8") + "\n",
            encoding="utf-8",
        )
        proc = self.check_plan("check", "--lenient-uncommitted")
        self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)
        self.assertIn("daily-warn", proc.stdout)

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
        proc = self.verify_claim("--all", "--allow-untracked")
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertRegex(proc.stdout, r"CLAIM 20260101T000000Z-docs-pass: PASS — ")
        self.assertRegex(proc.stdout, r"CLAIM 20260101T000001Z-docs-fail: FAIL — ")
        self.assertRegex(proc.stdout, r"CLAIM 20260101T000002Z-docs-nocmd: UNVERIFIED — ")

    def test_verify_claim_all_pass_exit_zero(self) -> None:
        self.write_config([dict(STATIC_CLAIM)])
        self.commit_all()
        self.write_evidence(evidence_doc("20260101T000000Z-docs-pass", "docs-pass", "PASS", commit=self.base))
        proc = self.verify_claim("--all", "--allow-untracked")
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
        self.write_config([dict(TEST_COUNT_CLAIM, requireArtifact=True)])
        self.write_baseline(floor=120, expected_skipped=1)
        (self.root / "build").mkdir()
        (self.root / "build" / "junit.xml").write_text(junit_xml(passed=120, skipped=1), encoding="utf-8")
        self.commit_all()
        # 正常：artifact 存在，自报 counts 与 JUnit 重算一致 → PASS
        good = evidence_doc(
            "20260101T000000Z-tests-pass",
            "tests-pass",
            "PASS",
            commit=self.base,
            result={"passed": 120, "failed": 0, "skipped": 1, "artifacts": ["build/junit.xml"]},
        )
        self.write_evidence(good)
        proc = self.verify_claim("--all", "--allow-untracked")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertRegex(proc.stdout, r"tests-pass: PASS — .*重算")
        # requireArtifact 缺省为 true：缺 artifact → UNVERIFIED
        no_artifact = evidence_doc(
            "20260101T000001Z-tests-pass",
            "tests-pass",
            "PASS",
            commit=self.base,
            result={"passed": 120, "failed": 0, "skipped": 1},
        )
        self.write_evidence(no_artifact)
        (self.root / "harness" / "evidence" / "20260101T000000Z-tests-pass.json").unlink()
        proc = self.verify_claim("--all", "--allow-untracked")
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertRegex(proc.stdout, r"tests-pass: UNVERIFIED — .*requireArtifact")
        # 自报 counts 与 artifact 重算不一致 → FAIL（伪造 PASS 的核心路径）
        forged = evidence_doc(
            "20260101T000002Z-tests-pass",
            "tests-pass",
            "PASS",
            commit=self.base,
            result={"passed": 9999, "failed": 0, "skipped": 1, "artifacts": ["build/junit.xml"]},
        )
        self.write_evidence(forged)
        (self.root / "harness" / "evidence" / "20260101T000001Z-tests-pass.json").unlink()
        proc = self.verify_claim("--all", "--allow-untracked")
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("与 artifact 重算不一致", proc.stdout)
        # 非 XML artifact（如 xcresult）无法独立重算 → UNVERIFIED
        (self.root / "build" / "test.xcresult").mkdir()
        xc = evidence_doc(
            "20260101T000003Z-tests-pass",
            "tests-pass",
            "PASS",
            commit=self.base,
            result={"passed": 120, "failed": 0, "skipped": 1, "artifacts": ["build/test.xcresult"]},
        )
        self.write_evidence(xc)
        (self.root / "harness" / "evidence" / "20260101T000002Z-tests-pass.json").unlink()
        proc = self.verify_claim("--all", "--allow-untracked")
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("无法独立重算", proc.stdout)
        # legacy opt-out（requireArtifact=false）且无 artifact：provenance 通过后接受自报 counts
        self.write_config([dict(TEST_COUNT_CLAIM, requireArtifact=False)])
        self.write_evidence(no_artifact)
        (self.root / "harness" / "evidence" / "20260101T000003Z-tests-pass.json").unlink()
        proc = self.verify_claim("--all", "--allow-untracked")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("legacy", proc.stdout)
        # 低于 floor（artifact 重算 100） → FAIL
        (self.root / "build" / "junit-low.xml").write_text(junit_xml(passed=100, skipped=1), encoding="utf-8")
        low = evidence_doc(
            "20260101T000004Z-tests-pass",
            "tests-pass",
            "PASS",
            commit=self.base,
            result={"passed": 100, "failed": 0, "skipped": 1, "artifacts": ["build/junit-low.xml"]},
        )
        self.write_evidence(low)
        (self.root / "harness" / "evidence" / "20260101T000001Z-tests-pass.json").unlink()
        proc = self.verify_claim("--all", "--allow-untracked")
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("passed=100", proc.stdout)

    def test_verify_claim_rejects_forged_pass_without_artifact(self) -> None:
        """P0 回归：0 测试 + passed=9999 + 无 artifact + HEAD commit 必须被拒绝。"""
        self.write_config([dict(TEST_COUNT_CLAIM)])
        self.write_baseline(floor=120, expected_skipped=1)
        head = self.commit_all()
        forged = evidence_doc(
            "20260101T000000Z-tests-pass",
            "tests-pass",
            "PASS",
            commit=head,
            result={"passed": 9999, "failed": 0, "skipped": 1},
        )
        self.write_evidence(forged)
        proc = self.verify_claim("--all")
        self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertRegex(proc.stdout, r"tests-pass: UNVERIFIED — .*artifact")

    def test_verify_claim_rejects_bad_commit_and_dirty(self) -> None:
        self.write_config([dict(TEST_COUNT_CLAIM)])
        self.write_baseline(floor=1, expected_skipped=0)
        (self.root / "build").mkdir()
        (self.root / "build" / "junit.xml").write_text(junit_xml(passed=1), encoding="utf-8")
        head = self.commit_all()
        # commit 不存在 → FAIL
        bad_commit = evidence_doc(
            "20260101T000000Z-tests-pass",
            "tests-pass",
            "PASS",
            commit="deadbeef",
            result={"passed": 1, "failed": 0, "skipped": 0, "artifacts": ["build/junit.xml"]},
        )
        self.write_evidence(bad_commit)
        proc = self.verify_claim("--all")
        self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("git.commit 无法解析", proc.stdout)
        # dirty=true 的 PASS 证据 → FAIL
        dirty = evidence_doc(
            "20260101T000001Z-tests-pass",
            "tests-pass",
            "PASS",
            commit=head,
            dirty=True,
            result={"passed": 1, "failed": 0, "skipped": 0, "artifacts": ["build/junit.xml"]},
        )
        (self.root / "harness" / "evidence" / "20260101T000000Z-tests-pass.json").unlink()
        self.write_evidence(dirty)
        proc = self.verify_claim("--all")
        self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("git.dirty", proc.stdout)

    def test_verify_claim_freshness_ignores_process_dirs(self) -> None:
        # evidence / plans / reviews 是过程状态，不使 claim 失效
        self.write_config([dict(TEST_COUNT_CLAIM)], freshness={"tests-pass": ["**/*.py", "harness/**"]})
        self.write_baseline(floor=1, expected_skipped=0)
        (self.root / "build").mkdir()
        (self.root / "build" / "junit.xml").write_text(junit_xml(passed=1), encoding="utf-8")
        head = self.commit_all()
        self.write_evidence(evidence_doc(
            "20260101T000000Z-tests-pass", "tests-pass", "PASS", commit=head,
            result={"passed": 1, "failed": 0, "skipped": 0, "artifacts": ["build/junit.xml"]},
        ))
        self.commit_all("evidence")
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
        self.write_config([dict(TEST_COUNT_CLAIM)], freshness={"tests-pass": ["docs/**"]})
        self.write_baseline(floor=1, expected_skipped=0)
        (self.root / "build").mkdir()
        (self.root / "build" / "junit.xml").write_text(junit_xml(passed=1), encoding="utf-8")
        head = self.commit_all()
        self.write_evidence(evidence_doc(
            "20260101T000000Z-tests-pass", "tests-pass", "PASS", commit=head,
            result={"passed": 1, "failed": 0, "skipped": 0, "artifacts": ["build/junit.xml"]},
        ))
        self.commit_all("evidence")
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
        self.assertRegex(proc.stdout, r"CLAIM 20260101T000000Z-tests-pass: UNVERIFIED — .*STALE")

    def test_verify_claim_static_freshness_not_applicable(self) -> None:
        self.write_config([dict(STATIC_CLAIM)], freshness={"docs-pass": ["docs/**"]})
        self.write_evidence(evidence_doc("20260101T000000Z-docs-pass", "docs-pass", "PASS", commit=self.base))
        self.commit_all()
        (self.root / "docs").mkdir()
        (self.root / "docs" / "note.md").write_text("# note\n", encoding="utf-8")
        proc = self.verify_claim("--all", "--fresh")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("freshness 不适用", proc.stdout)

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


    # ── v0.4.0：submitted scope / 归档 / done 未验证项 ─────────────
    def test_submitted_scope_out_of_allow_fails(self) -> None:
        self.commit_all("fixtures")
        submitted = self.commit_change("src/app.py", "x = 1\n", "out of scope")
        rows = "| `make check` | 基线 | 本机 | —（过程记录） |"
        self.write_plan_id(
            plan_front_allow(("harness/",), submitted=submitted),
            plan_body(rows), "2026-01-01-demo",
        )
        self.commit_all("plan")
        self.assert_fail(self.check_plan("check"), "submitted commit", "src/app.py")

    def test_submitted_scope_exceptions_allow(self) -> None:
        self.commit_all("fixtures")
        submitted = self.commit_change("src/app.py", "x = 1\n", "explicit exception")
        rows = "| `make check` | 基线 | 本机 | —（过程记录） |"
        self.write_plan_id(
            plan_front_allow(("harness/",), submitted=submitted, exceptions=("src/",)),
            plan_body(rows), "2026-01-01-demo",
        )
        self.commit_all("plan")
        proc = self.check_plan("check")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_submitted_scope_process_paths_exempt(self) -> None:
        self.commit_all("fixtures")
        submitted = self.commit_change("harness/evidence/notes.json", "{}\n", "evidence")
        rows = "| `make check` | 基线 | 本机 | —（过程记录） |"
        self.write_plan_id(
            plan_front_allow(("src/",), submitted=submitted),
            plan_body(rows), "2026-01-01-demo",
        )
        self.commit_all("plan")
        proc = self.check_plan("check")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)



    def test_submitted_scope_self_relax_after_commit_fails(self) -> None:
        self.commit_all("fixtures")
        rows = "| `make check` | 基线 | 本机 | —（过程记录） |"
        self.write_plan_id(plan_front_allow(("harness/",)), plan_body(rows), "2026-01-01-demo")
        self.commit_all("plan v1")
        submitted = self.commit_change("src/app.py", "x = 1\n", "out of scope")
        self.write_plan_id(
            plan_front_allow(("harness/", "src/"), submitted=submitted),
            plan_body(rows), "2026-01-01-demo",
        )
        self.commit_all("plan v2")
        self.assert_fail(self.check_plan("check"), "scope.allow/例外之外", "src/app.py")

    def test_submitted_scope_plan_created_after_commit_strict_fails(self) -> None:
        self.commit_all("fixtures")
        submitted = self.commit_change("src/app.py", "x = 1\n", "before plan")
        rows = "| `make check` | 基线 | 本机 | —（过程记录） |"
        self.write_plan_id(
            plan_front_allow(("src/",), submitted=submitted),
            plan_body(rows), "2026-01-01-demo",
        )
        self.commit_all("plan")
        daily = self.check_plan("check")
        self.assertEqual(daily.returncode, 0, daily.stdout + daily.stderr)
        self.assertIn("早于计划文件", daily.stdout)
        strict = self.check_plan("check", "--strict")
        self.assertEqual(strict.returncode, 0, strict.stdout + strict.stderr)
        self.assertIn("早于计划文件", strict.stdout)

    def test_strict_archive_fails_but_daily_warns(self) -> None:
        self.commit_all("fixtures")
        submitted = self.commit_change("src/app.py", "x = 1\n", "archived out of scope")
        rows = "| `make check` | 基线 | 本机 | —（过程记录） |"
        archive = self.root / "harness" / "plans" / "_archive"
        archive.mkdir(parents=True, exist_ok=True)
        plan = plan_front_allow(("harness/",), status="done", submitted=submitted)
        (archive / "2026-01-01-old.md").write_text(
            f"---\n{plan}\n---\n\n{plan_body(rows, uncommitted=False)}", encoding="utf-8"
        )
        self.commit_all("archive")
        daily = self.check_plan("check")
        self.assertEqual(daily.returncode, 0, daily.stdout + daily.stderr)
        strict = self.check_plan("check", "--strict")
        self.assertEqual(strict.returncode, 1, strict.stdout + strict.stderr)
        self.assertIn("src/app.py", strict.stdout)

    def test_archived_active_status_fails_even_daily(self) -> None:
        archive = self.root / "harness" / "plans" / "_archive"
        archive.mkdir(parents=True, exist_ok=True)
        plan = plan_front_allow(("harness/",), status="active")
        (archive / "2026-01-01-unfinished.md").write_text(
            f"---\n{plan}\n---\n\n{plan_body('| `make check` | 基线 | 本机 | —（过程记录） |')}",
            encoding="utf-8",
        )
        self.commit_all("archive active")
        proc = self.check_plan("check")
        self.assert_fail(proc, "归档计划 status", "done/archived")

    def test_scope_exception_table_allows(self) -> None:
        self.commit_all("fixtures")
        expires = (dt.date.today() + dt.timedelta(days=30)).isoformat()
        rows = "| `make check` | 基线 | 本机 | —（过程记录） |"
        body = plan_body(rows) + (
            "\n## 提交范围例外\n\n"
            "| 路径 | 理由 | 负责人 | 到期日 |\n| --- | --- | --- | --- |\n"
            f"| src/ | 一次性迁移脚本 | test | {expires} |\n"
        )
        self.write_plan_id(plan_front_allow(("harness/",)), body, "2026-01-01-demo")
        self.commit_all("plan")
        submitted = self.commit_change("src/legacy.py", "x = 1\n", "exception")
        self.write_plan_id(
            plan_front_allow(("harness/",), submitted=submitted), body, "2026-01-01-demo"
        )
        self.commit_all("plan submitted")
        proc = self.check_plan("check")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_submitted_merge_commit_audited_against_first_parent(self) -> None:
        self.commit_all("fixtures")
        branch = git(self.root, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
        self.commit_change("harness/base.md", "base\n", "base")
        assert git(self.root, "checkout", "-q", "-b", "feature").returncode == 0
        self.commit_change("src/feature.py", "x = 1\n", "feature")
        assert git(self.root, "checkout", "-q", branch).returncode == 0
        self.commit_change("harness/main.md", "main\n", "main")
        assert git(self.root, "merge", "--no-ff", "feature", "-m", "merge feature").returncode == 0
        merge = head_short(self.root, 12)
        rows = "| `make check` | 基线 | 本机 | —（过程记录） |"
        self.write_plan_id(
            plan_front_allow(("harness/",), submitted=merge),
            plan_body(rows), "2026-01-01-demo",
        )
        self.commit_all("plan")
        self.assert_fail(self.check_plan("check"), "submitted commit", "src/feature.py")

    def test_archived_plan_scope_issues_are_warn_only(self) -> None:
        self.commit_all("fixtures")
        submitted = self.commit_change("src/app.py", "x = 1\n", "archived out of scope")
        rows = "| `make check` | 基线 | 本机 | —（过程记录） |"
        archive = self.root / "harness" / "plans" / "_archive"
        archive.mkdir(parents=True, exist_ok=True)
        plan = plan_front_allow(("harness/",), status="done", submitted=submitted)
        (archive / "2026-01-01-old.md").write_text(
            f"---\n{plan}\n---\n\n{plan_body(rows, uncommitted=False)}", encoding="utf-8"
        )
        self.commit_all()
        proc = self.check_plan("check")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("归档", proc.stdout)
        self.assertIn("src/app.py", proc.stdout)
        self.assertNotIn("[FAIL]", proc.stdout)

    def _done_plan_with_unverified(self, unverified: str, waiver: str = "") -> None:
        submitted = self.commit_change("harness/notes.md", "notes\n", "in-scope")
        self.write_evidence(evidence_doc(VALID_EVIDENCE_ID, "docs-pass", "PASS", commit=submitted))
        rows = f"| `make test` | **PASS** | 本机 | {VALID_EVIDENCE_ID} |"
        body = plan_body(rows, uncommitted=False) + f"\n## 未验证项\n\n{unverified}\n"
        if waiver:
            body += f"\n## 未验证豁免\n\n{waiver}\n"
        self.write_plan(body, status="done", submitted=submitted)
        self.commit_all()

    def test_done_unverified_without_waiver_fails(self) -> None:
        self._done_plan_with_unverified("- 服务器全量 pytest 未取回")
        self.assert_fail(self.check_plan("check"), "未验证项", "未验证豁免")

    def test_done_unverified_with_valid_waiver_passes(self) -> None:
        self._done_plan_with_unverified(
            "- 服务器全量 pytest 未取回",
            "| 项目 | 理由 | 负责人 | 到期日 |\n| --- | --- | --- | --- |\n"
            f"| 服务器全量 pytest | SSH 门禁恢复前无法跑 | test | {(dt.date.today() + dt.timedelta(days=30)).isoformat()} |",
        )
        proc = self.check_plan("check")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_done_unverified_with_expired_waiver_fails(self) -> None:
        self._done_plan_with_unverified(
            "- 服务器全量 pytest 未取回",
            "| 项目 | 理由 | 负责人 | 到期日 |\n| --- | --- | --- | --- |\n"
            "| 服务器全量 pytest | 过期 | test | 2000-01-01 |",
        )
        self.assert_fail(self.check_plan("check"), "已过期")

    def test_done_unverified_not_covered_by_waiver_fails(self) -> None:
        self._done_plan_with_unverified(
            "- 服务器全量 pytest 未取回",
            "| 项目 | 理由 | 负责人 | 到期日 |\n| --- | --- | --- | --- |\n"
            "| 另一个问题 | 无关 | test | 2099-12-31 |",
        )
        self.assert_fail(self.check_plan("check"), "未被豁免覆盖")

    def test_missing_config_fails_readably(self) -> None:
        (self.root / "harness" / "config.json").unlink()
        proc = self.check_plan("check")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("缺少配置", proc.stdout)


if __name__ == "__main__":
    unittest.main()
