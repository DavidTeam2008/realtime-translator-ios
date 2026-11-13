#!/usr/bin/env python3
"""Kit hygiene tests: no project-specific references, docs links resolve, versions consistent.

Contract: harness-kit/SPEC.md §9. Standard library only.
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
FORBIDDEN = re.compile(r"(?i)duiyi|对译|TranslationSession|SwiftData|DuiyiTests")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
# Top-level kit docs whose relative links must resolve inside the kit.
KIT_DOCS = ("README.md", "SPEC.md", "docs/playbook.md", "docs/adoption.md", "docs/agent-prompts.md", "docs/governance.md", "docs/why.md", "docs/cases/fcnsystem-adoption.md")
ALLOWED_DUIYI_FILES = {"README.md"}  # origin-case section only


class NoProjectSpecificRefsTests(unittest.TestCase):
    def scan_dirs(self) -> list[Path]:
        roots = [
            KIT / "core", KIT / "adapters", KIT / "profiles", KIT / "scripts",
            KIT / "prompts", KIT / "skills", KIT / ".github",
        ]
        files: list[Path] = []
        for root in roots:
            if not root.exists():
                continue
            files.extend(path for path in root.rglob("*") if path.is_file())
        return files

    def test_no_project_specific_references(self) -> None:
        offenders = []
        for path in self.scan_dirs():
            text = path.read_text(encoding="utf-8", errors="ignore")
            for match in FORBIDDEN.finditer(text):
                offenders.append(f"{path.relative_to(KIT)}: {match.group(0)}")
        self.assertEqual([], offenders, "kit core/adapters/profiles/scripts must stay project-agnostic")

    def test_version_single_source(self) -> None:
        version = (KIT / "VERSION").read_text(encoding="utf-8").strip()
        self.assertRegex(version, r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$")

    def test_version_references_consistent(self) -> None:
        version = (KIT / "VERSION").read_text(encoding="utf-8").strip()
        readme = (KIT / "README.md").read_text(encoding="utf-8")
        spec = (KIT / "SPEC.md").read_text(encoding="utf-8")
        self.assertIn(f"版本：`{version}`", readme)
        self.assertIn(f"kit 版本 `{version}`", readme)
        self.assertIn(f'"kitVersion": "{version}"', spec)
        for profile in sorted((KIT / "profiles").glob("*.json")):
            data = json.loads(profile.read_text(encoding="utf-8"))
            self.assertIn("name", data)
            self.assertIn("files", data)
            self.assertIsInstance(data["files"], list)
            for item in data["files"]:
                self.assertIn("src", item)
                self.assertIn("dst", item)

    def test_token_budget_constants_match_docs(self) -> None:
        # 防漂移：模板预算常量必须与 README/governance 的说明一致（v0.5.2 修过一次漂移）。
        template = (KIT / "core" / "templates" / "harness" / "config.json.template").read_text(encoding="utf-8")
        self.assertIn('"{{ROOT_AGENTS}}": 1200', template)
        self.assertIn('"{{REFERENCES_DIR}}/contracts.md": 700', template)
        self.assertIn('"{{DOCS_DIR}}/README.md": 1000', template)
        self.assertIn('"nestedMaxTokens": 1000', template)
        self.assertIn("{{HARNESS_BUDGET}}", template)
        init = (KIT / "scripts" / "harness-init").read_text(encoding="utf-8")
        self.assertIn('"HARNESS.md": 1500', init)
        readme = (KIT / "README.md").read_text(encoding="utf-8")
        governance = (KIT / "docs" / "governance.md").read_text(encoding="utf-8")
        for name, doc in (("README.md", readme), ("docs/governance.md", governance)):
            for fragment in ("≈1200", "≈700", "≈1500", "≈1000"):
                self.assertIn(fragment, doc, f"{name} 的预算说明与模板默认值漂移：缺 {fragment}")

    def test_profile_files_exist(self) -> None:
        missing = []
        for profile in sorted((KIT / "profiles").glob("*.json")):
            data = json.loads(profile.read_text(encoding="utf-8"))
            sources = [item["src"] for item in data.get("files") or []]
            if data.get("makefile"):
                sources.append(data["makefile"])
            for src in sources:
                if not (KIT / src).is_file():
                    missing.append(f"{profile.name}: {src}")
        adapters = json.loads((KIT / "adapters" / "manifest.json").read_text(encoding="utf-8"))
        for name, items in adapters.items():
            for item in items:
                if not (KIT / item["src"]).is_file():
                    missing.append(f"adapters/{name}: {item['src']}")
        self.assertEqual([], missing, "profile/adapters reference missing kit files")

    def test_kit_docs_relative_links(self) -> None:
        missing = []
        for rel in KIT_DOCS:
            path = KIT / rel
            if not path.is_file():
                missing.append(f"{rel}: file missing")
                continue
            text = re.sub(r"```.*?```", "", path.read_text(encoding="utf-8"), flags=re.S)
            for target in LINK_RE.findall(text):
                target = target.strip()
                if target.startswith(("http://", "https://", "mailto:", "#", "{{")):
                    continue
                local = target.split("#", 1)[0]
                if not local:
                    continue
                if not (path.parent / local).exists():
                    missing.append(f"{rel}: broken link {target}")
        self.assertEqual([], missing)

    def test_feedback_channel_consistent(self) -> None:
        """v0.5.2：宿主可见的反馈入口必须指向同一个公开 issue 地址，且 issue 模板存在。"""
        url = "https://github.com/DavidTeam2008/harness-engineering-kit/issues"
        rels = (
            "README.md",
            "SPEC.md",
            "docs/adoption.md",
            "skills/harness/SKILL.md",
            "skills/harness/references/feedback.md",
            "prompts/feedback.md",
            "scripts/harness-init",
            "scripts/harness-adopt",
            "core/templates/AGENTS.md.template",
        )
        for rel in rels:
            text = (KIT / rel).read_text(encoding="utf-8")
            self.assertIn(url, text, f"{rel} 缺少统一的 kit 反馈入口")
        template = KIT / ".github" / "ISSUE_TEMPLATE" / "kit-feedback.yml"
        self.assertTrue(template.is_file(), "镜像仓 issue 模板缺失")
        template_text = template.read_text(encoding="utf-8")
        for key in ("kit 版本", "profile 与宿主技术栈", "命令与退出码", "期望 vs 实际", "最小复现"):
            self.assertIn(key, template_text)

    def test_readme_origin_section(self) -> None:
        readme = KIT / "README.md"
        if not readme.is_file():
            self.skipTest("kit README not written yet")
        text = readme.read_text(encoding="utf-8")
        self.assertIn("来源案例", text)
        self.assertLessEqual(len(FORBIDDEN.findall(text)), 1, "Duiyi may appear only in the origin-case section")


if __name__ == "__main__":
    unittest.main()
