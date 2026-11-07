#!/usr/bin/env python3
"""`tools/plan.py check` 的证据硬校验 / done 严格 / submitted 绑定回归测试（unittest，仅标准库）。

用 subprocess 走真实 CLI，在 tmp_path 建最小仓库：
  <root>/harness/plans/plan.md
  <root>/harness/evidence/<id>.json
  git init + commit（证据 commit / submitted 用真实短 hash）

断言 exit code 与关键输出，不依赖本机 Xcode / 真机 / 网络。
运行：python3 -m unittest tools.tests.test_plan -v
或：  python3 -m unittest discover -s tools/tests -q
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PLAN_PY = REPO_ROOT / "tools" / "plan.py"
VALID_ID = "20260101T000000Z-unit-tests-pass"


# ── helpers ────────────────────────────────────────────────────────────────
def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True)


def git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return run(["git", "-C", str(root), *args])


def init_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    if git(path, "init", "-q").returncode != 0:
        raise AssertionError("git init 失败")
    for key, value in (("user.name", "test"), ("user.email", "test@example.invalid")):
        if git(path, "config", key, value).returncode != 0:
            raise AssertionError(f"git config {key} 失败")
    (path / "README.md").write_text("# tmp\n", encoding="utf-8")
    if git(path, "add", "-A").returncode != 0 or git(path, "commit", "-q", "-m", "init").returncode != 0:
        raise AssertionError("初始提交失败")


def head_short(root: Path, length: int = 7) -> str:
    return git(root, "rev-parse", f"--short={length}", "HEAD").stdout.strip()


def body_with_rows(rows: str, *, uncommitted: bool = True) -> str:
    """最小合格计划正文；uncommitted=False 时用于 done 计划。"""
    sections = [
        "# 测试计划",
        "",
        "## 目标与非目标",
        "",
        "- 目标：验证 tools/plan.py 机检",
        "",
        "## 验收",
        "",
        "- python3 -m unittest 通过",
        "",
        "## 进度",
        "",
        "- [ ] 待办",
        "",
        "## 验证证据",
        "",
        "| 命令 | 结果 | 环境 | 证据ID |",
        "| --- | --- | --- | --- |",
        rows,
        "",
    ]
    if uncommitted:
        sections += ["## 未提交改动", "", "- 无未提交改动（测试仓库）", ""]
    sections += ["## 下一步", "", "1. 继续", ""]
    return "\n".join(sections)


class PlanCheckTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "harness" / "plans").mkdir(parents=True)
        (self.root / "harness" / "evidence").mkdir(parents=True)
        init_repo(self.root)
        self.base = head_short(self.root)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    # ── fixture helpers ───────────────────────────────────────────────
    def write_plan(
        self,
        *,
        status: str = "active",
        name: str = "plan",
        body: str | None = None,
        submitted: str | None = None,
        scope: bool = True,
        acceptance: bool = True,
    ) -> Path:
        front = [f"id: {name}", f"status: {status}", "level: L2", "owner: test", "updated: 2026-01-01"]
        if scope:
            front += ["scope:", "  allow:", "    - harness/"]
        if acceptance:
            front += ["acceptance:", "  - python3 -m unittest 通过"]
        front += ["verify:", "  - python3 tools/plan.py check"]
        if submitted is not None:
            front.append(f"submitted: {submitted}")
        default_rows = "| `make check` | 基线盘点 | 本机 | —（基线盘点） |"
        path = self.root / "harness" / "plans" / f"{name}.md"
        path.write_text(
            "---\n" + "\n".join(front) + "\n---\n\n" + (body or body_with_rows(default_rows)),
            encoding="utf-8",
        )
        return path

    def write_evidence(
        self,
        evidence_id: str = VALID_ID,
        *,
        commit: str | None = None,
        verdict: str = "PASS",
    ) -> Path:
        doc = {
            "schemaVersion": 1,
            "id": evidence_id,
            "claim": "unit-tests-pass",
            "createdAt": "2026-01-01T00:00:00Z",
            "git": {"commit": commit or self.base, "dirty": False},
            "command": "make test",
            "environment": {"xcode": None, "simulator": None, "device": None},
            "result": {"status": "SUCCEEDED", "passed": 1, "failed": 0, "skipped": 0, "durationSec": 0.1},
            "verdict": verdict,
            "verifier": "tools/evidence.py@1",
        }
        path = self.root / "harness" / "evidence" / f"{evidence_id}.json"
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def commit_all(self, message: str = "fixtures") -> str:
        if git(self.root, "add", "-A").returncode != 0:
            raise AssertionError("git add 失败")
        if git(self.root, "commit", "-q", "-m", message).returncode != 0:
            raise AssertionError("git commit 失败")
        return head_short(self.root)

    def check(self) -> subprocess.CompletedProcess[str]:
        return run([sys.executable, str(PLAN_PY), "--root", str(self.root), "check"])

    def assert_fail(self, proc: subprocess.CompletedProcess[str], *needles: str) -> None:
        self.assertNotEqual(proc.returncode, 0, f"预期 exit≠0：\n{proc.stdout}\n{proc.stderr}")
        for needle in needles:
            self.assertIn(needle, proc.stdout, f"缺少输出：{needle}\n{proc.stdout}")

    def assert_pass(self, proc: subprocess.CompletedProcess[str]) -> None:
        self.assertEqual(proc.returncode, 0, f"预期 exit=0：\n{proc.stdout}\n{proc.stderr}")
        self.assertIn("结论：PASS", proc.stdout)

    # ── done 计划：结构与 submitted 绑定 ──────────────────────────────
    def test_done_valid_bound_evidence_passes(self) -> None:
        self.write_evidence(commit=self.base)
        self.write_plan(
            status="done",
            submitted=self.base,
            body=body_with_rows(f"| `make test` | **PASS** | 本机 | {VALID_ID} |", uncommitted=False),
        )
        self.commit_all()
        self.assert_pass(self.check())

    def test_pass_with_process_annotation_but_dynamic_claim_fails(self) -> None:
        self.write_plan(
            body=body_with_rows(
                "| `make test` | **PASS**：passed=120；unit-tests 全绿 | 本机 | —（过程记录：单测） |"
            ),
        )
        self.commit_all()
        self.assert_fail(self.check(), "绕过证据 ID")

    def test_pass_with_process_annotation_static_claim_passes(self) -> None:
        self.write_plan(
            body=body_with_rows(
                "| `make check` | **PASS**（6 组门禁） | 本机 | —（过程记录：静态门禁） |"
            ),
        )
        self.commit_all()
        self.assert_pass(self.check())

    def test_done_missing_submitted_fails(self) -> None:
        self.write_evidence(commit=self.base)
        self.write_plan(
            status="done",
            submitted=None,
            body=body_with_rows(f"| `make test` | **PASS** | 本机 | {VALID_ID} |", uncommitted=False),
        )
        self.commit_all()
        self.assert_fail(self.check(), "缺少 front matter submitted")

    def test_done_submitted_token_missing_fails(self) -> None:
        self.write_evidence(commit=self.base)
        self.write_plan(
            status="done",
            submitted="deadbee",
            body=body_with_rows(f"| `make test` | **PASS** | 本机 | {VALID_ID} |", uncommitted=False),
        )
        self.commit_all()
        self.assert_fail(self.check(), "submitted 中的 commit 不存在：deadbee")

    def test_done_submitted_token_not_ancestor_fails(self) -> None:
        tree = git(self.root, "rev-parse", "HEAD^{tree}").stdout.strip()
        dangling = git(self.root, "commit-tree", tree, "-m", "dangling").stdout.strip()[:7]
        self.write_evidence(commit=self.base)
        self.write_plan(
            status="done",
            submitted=dangling,
            body=body_with_rows(f"| `make test` | **PASS** | 本机 | {VALID_ID} |", uncommitted=False),
        )
        self.commit_all()
        self.assert_fail(self.check(), "不是 HEAD 或其祖先")

    def test_done_missing_structure_and_evidence_section_fails(self) -> None:
        self.write_plan(
            status="done",
            submitted=self.base,
            acceptance=False,
            body="# 测试计划\n\n## 目标与非目标\n\n- 目标：缺节\n",
        )
        self.commit_all()
        self.assert_fail(
            self.check(),
            "缺少非空“验收”",
            "缺少非空“下一步”",
            "缺少“验证证据”节",
        )

    def test_done_missing_scope_allow_fails(self) -> None:
        self.write_plan(status="done", submitted=self.base, scope=False)
        self.commit_all()
        self.assert_fail(self.check(), "缺少 scope.allow")

    def test_done_without_pass_evidence_fails(self) -> None:
        self.write_plan(
            status="done",
            submitted=self.base,
            body=body_with_rows("| `make check` | 基线盘点 | 本机 | —（基线盘点） |", uncommitted=False),
        )
        self.commit_all()
        self.assert_fail(self.check(), "done 计划没有任何可解析且 verdict=PASS 的 evidence id")

    # ── 证据 ID 硬失败 ──────────────────────────────────────────────
    def test_done_evidence_id_missing_fails(self) -> None:
        # 不写 evidence 文件
        self.write_plan(
            status="done",
            submitted=self.base,
            body=body_with_rows(f"| `make test` | **PASS** | 本机 | {VALID_ID} |", uncommitted=False),
        )
        self.commit_all()
        self.assert_fail(self.check(), "证据 ID 不存在")

    def test_done_evidence_verdict_not_pass_fails(self) -> None:
        self.write_evidence(commit=self.base, verdict="UNVERIFIED")
        self.write_plan(
            status="done",
            submitted=self.base,
            body=body_with_rows(f"| `make test` | **PASS** | 本机 | {VALID_ID} |", uncommitted=False),
        )
        self.commit_all()
        self.assert_fail(self.check(), "证据 verdict 非 PASS")

    def test_done_evidence_commit_not_bound_fails(self) -> None:
        # 证据 commit 指向 base（真实存在且是祖先），但 submitted 指向 base 之后的提交，HEAD 又是第三个
        self.write_evidence(commit=self.base)
        self.write_plan(
            status="done",
            submitted=self.base,
            body=body_with_rows(f"| `make test` | **PASS** | 本机 | {VALID_ID} |", uncommitted=False),
        )
        fixture_head = self.commit_all()
        # 改 submitted 为 fixture 提交，再提交一次 → HEAD 前进，证据 commit(base) 既不等于 HEAD 也不匹配 submitted
        self.write_plan(
            status="done",
            submitted=fixture_head,
            body=body_with_rows(f"| `make test` | **PASS** | 本机 | {VALID_ID} |", uncommitted=False),
        )
        self.commit_all("advance head")
        self.assert_fail(self.check(), "证据 commit 未绑定 submitted/HEAD")

    # ── PASS 占位与白名单 ──────────────────────────────────────────
    def test_active_pass_with_non_whitelisted_placeholder_fails(self) -> None:
        self.write_plan(
            status="active",
            body=body_with_rows("| `make check` | **PASS** | 本机 | —（Phase 3.1） |"),
        )
        self.commit_all()
        self.assert_fail(self.check(), "不是可解析的 evidence id")

    def test_active_pass_with_process_annotation_passes(self) -> None:
        self.write_plan(
            status="active",
            body=body_with_rows("| `make check` | **PASS** | 本机 | —（过程记录：sandbox） |"),
        )
        self.commit_all()
        proc = self.check()
        self.assert_pass(proc)
        self.assertIn("没有可解析且 verdict=PASS", proc.stdout)  # 0 证据 → WARN（不阻断）

    def test_missing_evidence_id_column_fails(self) -> None:
        body = body_with_rows("| `make check` | **PASS** | 本机 |")
        body = body.replace("| 命令 | 结果 | 环境 | 证据ID |", "| 命令 | 结果 | 环境 |")
        self.write_plan(status="active", body=body)
        self.commit_all()
        self.assert_fail(self.check(), "缺少「证据ID」列")

    # ── active：0 证据只 WARN ──────────────────────────────────────
    def test_active_zero_pass_evidence_warns_exit0(self) -> None:
        self.write_plan(
            status="active",
            body=body_with_rows("| `make check` | 基线盘点 | 本机 | —（基线盘点） |"),
        )
        self.commit_all()
        proc = self.check()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("[WARN]", proc.stdout)


if __name__ == "__main__":
    unittest.main()
