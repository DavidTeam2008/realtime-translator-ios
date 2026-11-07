#!/usr/bin/env python3
"""`tools/check-harness.py` 的 §/第N节 引用扫描回归测试（unittest，仅标准库）。

覆盖 P1-2 整改：嵌套 AGENTS / skills 扫描、`第 N 节` 语法、文档简写与相对链接解析，
以及「无法定位 / 缺编号标题」的负向用例；全部用临时 fixture 仓库 + subprocess 走 CLI。
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
CHECKER = REPO_ROOT / "tools" / "check-harness.py"
BUDGET = 5000

ROOT_AGENTS = """# AGENTS.md

> 冷启动入口：细节读嵌套 `AGENTS.md`，覆盖只写第 7 节。

## 1. 项目一句话

## 7. 项目级覆盖
"""


def run_checker(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CHECKER), "--root", str(root)],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )


class Fixture:
    """最小 fixture 仓库：根 AGENTS + rules-budget.json；estimator 回退真实仓库脚本。"""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.agents = ROOT_AGENTS
        self.token_budgets: dict[str, int] = {"AGENTS.md": BUDGET}
        self.nested: list[str] = []

    def write(self, rel: str, text: str) -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def add_nested(self, rel: str, text: str) -> None:
        self.write(rel, text)
        self.token_budgets[rel] = BUDGET
        self.nested.append(rel)

    def add_doc(self, rel: str, text: str) -> None:
        self.write(rel, text)
        self.token_budgets[rel] = BUDGET

    def add_skill(self, name: str, body: str) -> None:
        frontmatter = f"---\nname: {name}\ndescription: fixture skill for {name}\n---\n\n"
        self.write(f".dsh/skills/{name}/SKILL.md", frontmatter + body)

    def save(self) -> None:
        if not self.nested:
            # budget 要求 nestedAgents.files 非空；无引用类用例用一个干净占位文件。
            self.add_nested("harness/AGENTS.md", "# nested AGENTS\n")
        self.write("AGENTS.md", self.agents)
        config = {
            "estimator": "fixture",
            "tokenBudgets": self.token_budgets,
            "nestedAgents": {"maxBytes": 8192, "files": self.nested},
            "skills": {
                "root": ".dsh/skills",
                "requiredFields": ["name", "description"],
                "namePattern": "^[a-z0-9]+(?:-[a-z0-9]+)*$",
            },
        }
        self.write("tools/rules-budget.json", json.dumps(config, ensure_ascii=False, indent=2))


class CheckHarnessSectionRefTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.fixture = Fixture(Path(self._tmp.name))

    def run_fixture(self) -> subprocess.CompletedProcess[str]:
        self.fixture.save()
        return run_checker(self.fixture.root)

    def test_nested_agents_md_path_ref_passes(self) -> None:
        self.fixture.add_doc("docs/02-architecture.md", "# 02\n\n## 2. 分层与依赖\n")
        self.fixture.add_nested(
            "harness/AGENTS.md", "# nested\n\n- 数据链路见 `docs/02-architecture.md` §2。\n"
        )
        proc = self.run_fixture()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("处命中", proc.stdout)

    def test_nested_agents_wrong_section_fails(self) -> None:
        self.fixture.add_doc("docs/02-architecture.md", "# 02\n\n## 2. 分层与依赖\n")
        self.fixture.add_nested(
            "harness/AGENTS.md", "# nested\n\n- 数据链路见 `docs/02-architecture.md` §9。\n"
        )
        proc = self.run_fixture()
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("缺少 §9 对应的编号标题", proc.stdout)

    def test_nested_agents_unlocatable_ref_fails(self) -> None:
        self.fixture.add_nested("harness/AGENTS.md", "# nested\n\n- 另见第 7 节。\n")
        proc = self.run_fixture()
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("无法定位 §/第N节 引用目标", proc.stdout)

    def test_root_agents_self_reference_requires_heading(self) -> None:
        proc = self.run_fixture()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        # 删掉 `## 7.` 编号标题后，根 AGENTS 自引用（第 7 节）必须 FAIL
        self.fixture.agents = "# AGENTS.md\n\n> 覆盖只写第 7 节。\n\n## 1. 项目一句话\n"
        proc = self.run_fixture()
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("缺少 第 7 节 对应的编号标题", proc.stdout)

    def test_skill_ref_to_root_agents_passes(self) -> None:
        self.fixture.add_skill("red-team", "范围：仅并发/持久化/发布（`AGENTS.md` §7）。\n")
        proc = self.run_fixture()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("§/第N节 引用", proc.stdout)

    def test_shorthand_doc_ref_passes(self) -> None:
        self.fixture.add_doc("docs/02-architecture.md", "# 02\n\n## 4. 听写\n")
        self.fixture.add_nested("harness/AGENTS.md", "# nested\n\n- 现状见 `docs/02` §4。\n")
        proc = self.run_fixture()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertNotIn("[FAIL]", proc.stdout)

    def test_nested_relative_md_link_ref_passes(self) -> None:
        self.fixture.add_doc("references/contracts.md", "# 契约\n\n## 4. 任务语义\n")
        self.fixture.add_nested(
            "Duiyi/Services/AGENTS.md",
            "# nested\n\n- 读 [`contracts.md`](../../references/contracts.md) §4。\n",
        )
        proc = self.run_fixture()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertNotIn("[FAIL]", proc.stdout)

    def test_chinese_range_requires_both_headings(self) -> None:
        self.fixture.add_doc("docs/02-architecture.md", "# 02\n\n## 3. 音频链路\n")
        self.fixture.add_nested(
            "harness/AGENTS.md", "# nested\n\n- 见 `docs/02-architecture.md` 第 3–4 节。\n"
        )
        proc = self.run_fixture()
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("第 4 节", proc.stdout)
        self.fixture.add_doc(
            "docs/02-architecture.md", "# 02\n\n## 3. 音频链路\n\n## 4. 听写\n"
        )
        proc = self.run_fixture()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_section_range_requires_both_ends(self) -> None:
        self.fixture.add_doc("docs/02-architecture.md", "# 02\n\n## 2. 分层与依赖\n")
        self.fixture.add_nested(
            "harness/AGENTS.md", "# nested\n\n- 见 `docs/02-architecture.md` §2–§4。\n"
        )
        proc = self.run_fixture()
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("§4", proc.stdout)
        self.fixture.add_doc(
            "docs/02-architecture.md", "# 02\n\n## 2. 分层与依赖\n\n## 4. 听写\n"
        )
        proc = self.run_fixture()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_md_path_token_missing_target_fails(self) -> None:
        self.fixture.add_nested(
            "harness/AGENTS.md", "# nested\n\n- 见 `docs/missing.md` §2。\n"
        )
        proc = self.run_fixture()
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("引用目标文件不存在", proc.stdout)

    def test_root_agents_hint_word_resolves_target(self) -> None:
        self.fixture.add_nested("harness/AGENTS.md", "# nested\n\n- 范围见根 AGENTS 第 7 节。\n")
        proc = self.run_fixture()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertNotIn("[FAIL]", proc.stdout)

    def test_zero_refs_warns_without_failing(self) -> None:
        self.fixture.agents = "# AGENTS.md\n\n## 1. 项目一句话\n"
        self.fixture.add_nested("harness/AGENTS.md", "# nested\n\n- 没有节号引用。\n")
        proc = self.run_fixture()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("疑似空转", proc.stdout)
        self.assertIn("0 处命中", proc.stdout)


if __name__ == "__main__":
    unittest.main()
