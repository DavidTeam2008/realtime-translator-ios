#!/usr/bin/env python3
"""harness-kit core 脚本回归测试：check_docs / check_agents / doctor。

覆盖：链接死链、代码围栏、docs 索引、公开文档白名单/上限、token 预算、
AGENTS 存在性/字节上限/敏感串/§ 引用（正确与错误）、doctor 正常/缺 git/降级。

方式：在 tempfile 目标仓里写最小 config/docs/references/harness/AGENTS，
再用 subprocess 调用 kit 源脚本并断言退出码与关键输出。仅标准库、不联网、
不依赖本机测试框架/Xcode。

运行：python3 -m unittest discover -s harness-kit/tests -q
"""
from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[1]
CORE_TOOLS = KIT_ROOT / "core" / "tools"
SCRIPTS = {
    "docs": CORE_TOOLS / "check_docs.py",
    "agents": CORE_TOOLS / "check_agents.py",
    "doctor": CORE_TOOLS / "doctor.py",
}

BASE_CONFIG: dict = {
    "kitVersion": "0.1.0",
    "project": {"name": "Demo", "language": "python"},
    "paths": {
        "docs": "docs",
        "references": "references",
        "harness": "harness",
        "plans": "harness/plans",
        "evidence": "harness/evidence",
        "tools": "tools",
        "rootDocs": ["README.md", "AGENTS.md"],
    },
    "instructions": {
        "root": "AGENTS.md",
        "nested": ["docs/AGENTS.md"],
        "nestedMaxBytes": 4096,
        "budgets": {"AGENTS.md": 400, "references/contracts.md": 200},
        "sensitivePatterns": ["/Users/", "sk-"],
    },
    "docs": {
        "publicWhitelist": ["README.md", "AGENTS.md", "docs/README.md", "docs/AGENTS.md", "docs/guide.md"],
        "publicBudget": 6,
        "rootMarkdownAllowed": ["README.md", "AGENTS.md"],
    },
    "commands": {"check": "make check", "verify": "make verify-static", "test": "python3 -m unittest"},
    "claims": [{"name": "docs-pass", "type": "static", "command": "python3 tools/check_docs.py"}],
}

AGENTS_MD = """# 项目 AGENTS

## 1. 目标

- 契约见 `references/contracts.md` §1。
- 流程见 `references/workflow.md` 第 2 节。

## 2. 验证

- 本节 §2 是验证入口（根文件自引用）。

## 3. 交付

- 再次引用 `references/contracts.md` §1。
"""

README_MD = """# Demo

- 文档索引：[docs/README.md](docs/README.md)。
"""

DOCS_README_MD = """# 文档索引

- [指南](guide.md)
- [docs AGENTS](AGENTS.md)
"""

DOCS_AGENTS_MD = """# docs AGENTS

- 文档页见 [指南](guide.md)。
- 根规则见 根 AGENTS §1。
- 契约见 `references/contracts.md` §1。
"""

DOCS_GUIDE_MD = """# 指南

返回 [索引](README.md)。
"""

REFERENCES_CONTRACTS_MD = """# 契约

## 1. 分层与依赖

纯文本内容。
"""

REFERENCES_WORKFLOW_MD = """# 流程

## 2. 日常流程

纯文本内容。
"""

HARNESS_README_MD = """# Harness

- 计划模板见 [plans/_template.md](plans/_template.md)。
"""

PLAN_TEMPLATE_MD = """# 计划模板

占位。
"""


class ProjectCase(unittest.TestCase):
    """每个用例一个最小目标项目（tempfile）；kit 脚本通过 --root 指向它。"""

    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory(prefix="harness-kit-")
        self.root = Path(self._temp.name)
        self.config = copy.deepcopy(BASE_CONFIG)
        self.build_project()

    def tearDown(self) -> None:
        self._temp.cleanup()

    # --- 项目构造 -------------------------------------------------------
    def write(self, rel: str, content: str) -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def write_config(self) -> None:
        self.write("harness/config.json", json.dumps(self.config, ensure_ascii=False, indent=2))

    def build_project(self) -> None:
        self.write("AGENTS.md", AGENTS_MD)
        self.write("README.md", README_MD)
        self.write("docs/README.md", DOCS_README_MD)
        self.write("docs/AGENTS.md", DOCS_AGENTS_MD)
        self.write("docs/guide.md", DOCS_GUIDE_MD)
        self.write("references/contracts.md", REFERENCES_CONTRACTS_MD)
        self.write("references/workflow.md", REFERENCES_WORKFLOW_MD)
        self.write("harness/README.md", HARNESS_README_MD)
        self.write("harness/plans/_template.md", PLAN_TEMPLATE_MD)
        self.write_config()

    def git_init(self) -> None:
        result = subprocess.run(
            ["git", "-C", str(self.root), "init", "-q"], capture_output=True, text=True
        )
        if result.returncode != 0:
            self.skipTest(f"git init 不可用：{result.stderr.strip()}")

    # --- 运行 -----------------------------------------------------------
    def run_script(self, name: str, *extra: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, str(SCRIPTS[name]), "--root", str(self.root), *extra],
            capture_output=True,
            text=True,
            cwd=str(cwd or self.root),
            timeout=60,
        )
        return result

    def run_script_without_root(self, name: str) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, str(SCRIPTS[name])],
            capture_output=True,
            text=True,
            cwd=str(self.root),
            timeout=60,
        )
        return result

    def combined(self, result: subprocess.CompletedProcess[str]) -> str:
        return (result.stdout or "") + (result.stderr or "")

    def assert_ok(self, result: subprocess.CompletedProcess[str], *fragments: str) -> None:
        output = self.combined(result)
        self.assertEqual(result.returncode, 0, output)
        self.assertIn("[OK]", output)
        self.assertNotIn("[FAIL]", output)
        for fragment in fragments:
            self.assertIn(fragment, output)

    def assert_failed(self, result: subprocess.CompletedProcess[str], *fragments: str) -> None:
        output = self.combined(result)
        self.assertEqual(result.returncode, 1, output)
        self.assertIn("[FAIL]", output)
        for fragment in fragments:
            self.assertIn(fragment, output)


class CheckDocsTests(ProjectCase):
    def test_valid_project_passes(self) -> None:
        self.assert_ok(self.run_script("docs"), "check_docs 通过")

    def test_dead_relative_link_fails(self) -> None:
        self.write("docs/bad.md", "# 坏链\n\n[死链](../missing.md)\n")
        self.write("docs/README.md", DOCS_README_MD + "- [坏链](bad.md)\n")
        self.assert_failed(self.run_script("docs"), "链接不存在", "docs/bad.md")

    def test_unclosed_code_fence_fails(self) -> None:
        self.write("docs/bad.md", "# 坏围栏\n\n```python\nprint(1)\n")
        self.write("docs/README.md", DOCS_README_MD + "- [坏](bad.md)\n")
        self.assert_failed(self.run_script("docs"), "代码围栏未闭合")

    def test_unregistered_docs_page_fails(self) -> None:
        self.write("docs/extra.md", "# 未登记\n\n内容。\n")
        self.assert_failed(self.run_script("docs"), "未登记到 docs/README.md")

    def test_root_markdown_outside_allowlist_fails(self) -> None:
        self.write("NOTES.md", "# 笔记\n\n内容。\n")
        self.assert_failed(self.run_script("docs"), "rootMarkdownAllowed", "NOTES.md")

    def test_unlisted_public_doc_fails(self) -> None:
        self.write("docs/extra.md", "# 额外\n\n内容。\n")
        self.write("docs/README.md", DOCS_README_MD + "- [额外](extra.md)\n")
        self.assert_failed(self.run_script("docs"), "公开文档不在 publicWhitelist", "docs/extra.md")

    def test_missing_whitelist_entry_is_tolerated(self) -> None:
        self.config["docs"]["publicWhitelist"].append("docs/not-created-yet.md")
        self.write_config()
        self.assert_ok(self.run_script("docs"), "check_docs 通过")

    def test_public_budget_is_enforced(self) -> None:
        self.config["docs"]["publicBudget"] = 2
        self.write_config()
        self.assert_failed(self.run_script("docs"), "超过上限", "publicBudget=2")

    def test_token_budget_exceeded_fails(self) -> None:
        self.config["instructions"]["budgets"]["AGENTS.md"] = 1
        self.write_config()
        self.assert_failed(self.run_script("docs"), "token 超预算", "AGENTS.md")

    def test_missing_config_is_readable_error(self) -> None:
        (self.root / "harness" / "config.json").unlink()
        self.assert_failed(self.run_script("docs"), "配置不可用", "缺少配置文件")

    def test_default_root_is_script_parent(self) -> None:
        target_tools = self.root / "tools"
        target_tools.mkdir(parents=True, exist_ok=True)
        for name in ("token_estimate.py", "check_docs.py", "check_agents.py", "doctor.py"):
            shutil.copy2(CORE_TOOLS / name, target_tools / name)
        result = subprocess.run(
            [sys.executable, str(target_tools / "check_docs.py")],
            capture_output=True,
            text=True,
            cwd=str(self.root),
            timeout=60,
        )
        self.assert_ok(result, "check_docs 通过")


class CheckAgentsTests(ProjectCase):
    def test_valid_project_passes(self) -> None:
        self.assert_ok(self.run_script("agents"), "check_agents 通过")

    def test_token_budget_exceeded_fails(self) -> None:
        self.config["instructions"]["budgets"]["AGENTS.md"] = 1
        self.write_config()
        self.assert_failed(self.run_script("agents"), "token 超预算", "AGENTS.md")

    def test_sensitive_absolute_path_fails(self) -> None:
        self.write("AGENTS.md", AGENTS_MD + "\n- 本机路径：/Users/example/project\n")
        self.assert_failed(self.run_script("agents"), "敏感串", "绝对路径")

    def test_sensitive_sk_key_fails(self) -> None:
        self.write("AGENTS.md", AGENTS_MD + "\n- 临时密钥：sk-example0123456789\n")
        self.assert_failed(self.run_script("agents"), "敏感串", "sk-")

    def test_wrong_section_number_fails(self) -> None:
        self.write("AGENTS.md", AGENTS_MD + "\n- 另见 `references/contracts.md` §99。\n")
        self.assert_failed(self.run_script("agents"), "§99", "缺少", "编号标题")

    def test_unresolved_section_ref_in_nested_file_fails(self) -> None:
        self.write("docs/AGENTS.md", DOCS_AGENTS_MD + "- 另见 §5。\n")
        self.assert_failed(self.run_script("agents"), "无法定位目标文件", "§5")

    def test_missing_nested_instruction_file_fails(self) -> None:
        (self.root / "docs" / "AGENTS.md").unlink()
        self.assert_failed(self.run_script("agents"), "嵌套指令文件不存在")

    def test_oversized_nested_instruction_file_fails(self) -> None:
        self.config["instructions"]["nestedMaxBytes"] = 32
        self.write_config()
        self.assert_failed(self.run_script("agents"), "嵌套指令文件超长")

    def test_missing_config_is_readable_error(self) -> None:
        (self.root / "harness" / "config.json").unlink()
        self.assert_failed(self.run_script("agents"), "配置不可用", "缺少配置文件")


@unittest.skipUnless(shutil.which("git"), "doctor 测试需要 git")
class DoctorTests(ProjectCase):
    def git_available_test_command(self) -> None:
        self.config["commands"]["test"] = f"{sys.executable} -m unittest"
        self.write_config()

    def test_git_repo_passes(self) -> None:
        self.git_init()
        self.git_available_test_command()
        result = self.run_script("doctor")
        output = self.combined(result)
        self.assertEqual(result.returncode, 0, output)
        self.assertIn("[OK] python3", output)
        self.assertIn("[OK] git 仓库", output)
        self.assertNotIn("[FAIL]", output)

    def test_missing_git_repo_exits_2(self) -> None:
        self.git_available_test_command()
        result = self.run_script("doctor")
        output = self.combined(result)
        self.assertEqual(result.returncode, 2, output)
        self.assertIn("[FAIL] git 仓库", output)
        self.assertIn("exit 2", output)

    def test_missing_config_degrades_with_suggestion(self) -> None:
        self.git_init()
        (self.root / "harness" / "config.json").unlink()
        result = self.run_script("doctor")
        output = self.combined(result)
        self.assertEqual(result.returncode, 0, output)
        self.assertIn("[WARN] config", output)
        self.assertIn("→ 影响：", output)
        self.assertIn("如何补：", output)

    def test_missing_test_program_warns(self) -> None:
        self.git_init()
        self.config["commands"]["test"] = "definitely-not-a-real-program-xyz --run"
        self.write_config()
        result = self.run_script("doctor")
        output = self.combined(result)
        self.assertEqual(result.returncode, 0, output)
        self.assertIn("[WARN] 测试命令", output)
        self.assertIn("首" "个程序不在 PATH", output)


if __name__ == "__main__":
    unittest.main()
