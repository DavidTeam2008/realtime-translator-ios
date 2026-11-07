#!/usr/bin/env python3
"""Kit hygiene tests: no project-specific references, docs links resolve, versions consistent.

Contract: harness-kit/SPEC.md §9. Standard library only.
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
KIT = REPO_ROOT / "harness-kit"
FORBIDDEN = re.compile(r"(?i)duiyi|对译|TranslationSession|SwiftData|DuiyiTests")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
# Top-level kit docs whose relative links must resolve inside the kit.
KIT_DOCS = ("README.md", "SPEC.md", "docs/playbook.md")
ALLOWED_DUIYI_FILES = {"README.md"}  # origin-case section only


class NoProjectSpecificRefsTests(unittest.TestCase):
    def scan_dirs(self) -> list[Path]:
        roots = [KIT / "core", KIT / "adapters", KIT / "profiles", KIT / "scripts"]
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
        self.assertRegex(version, r"^\d+\.\d+\.\d+$")
        for profile in sorted((KIT / "profiles").glob("*.json")):
            data = json.loads(profile.read_text(encoding="utf-8"))
            self.assertIn("name", data)
            self.assertIn("files", data)
            self.assertIsInstance(data["files"], list)
            for item in data["files"]:
                self.assertIn("src", item)
                self.assertIn("dst", item)

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
        self.assertEqual([], missing, "profile references missing kit files")

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

    def test_readme_origin_section(self) -> None:
        readme = KIT / "README.md"
        if not readme.is_file():
            self.skipTest("kit README not written yet")
        text = readme.read_text(encoding="utf-8")
        self.assertIn("来源案例", text)
        self.assertLessEqual(len(FORBIDDEN.findall(text)), 1, "Duiyi may appear only in the origin-case section")


if __name__ == "__main__":
    unittest.main()
