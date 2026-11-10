#!/usr/bin/env python3
"""Regression tests for host sensors: `check_hygiene.py` / `check_layers.py`.

Each case builds a temporary git fixture with `harness/config.json`, runs the
tool as a subprocess, and asserts exit code + readable output. No network, no
third-party dependencies.

Run: cd harness-kit && PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -q
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
TOOLS = KIT / "core" / "tools"

HYGIENE = {
    "trackedArtifactGlobs": ["**/build/**", "*.log"],
    "rootAllowlist": ["README.md"],
    "localPathPatterns": ["/Users/", "/Volumes/", "/home/"],
    "maxTrackedFileBytes": 1024 * 1024,
    "skipLocalPathScan": ["harness/config.json"],
    "forbidAbsoluteSymlinks": True,
}


def run_tool(tool: str, root: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(TOOLS / tool), "--root", str(root), *extra],
        capture_output=True,
        text=True,
        timeout=60,
    )


class HostSensorCase(unittest.TestCase):
    """临时 git 仓 + harness/config.json 的最小宿主项目。"""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="kit-host-")
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    # --- fixture helpers -------------------------------------------------
    def write(self, rel: str, content: str | bytes) -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")
        return path

    def write_config(self, **sections: object) -> None:
        config: dict = {
            "kitVersion": "0.3.0",
            "project": {"name": "Fixture", "language": "other"},
            "paths": {
                "docs": "docs",
                "references": "references",
                "harness": "harness",
                "plans": "harness/plans",
                "evidence": "harness/evidence",
                "tools": "tools",
            },
            "commands": {"test": "echo ok"},
            "claims": [{"name": "tests-pass", "type": "test-count"}],
        }
        config.update(sections)
        self.write("harness/config.json", json.dumps(config, ensure_ascii=False, indent=2))

    def git(self, *args: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(self.root), *args], capture_output=True, text=True
        )
        if result.returncode != 0:
            self.fail(f"git {' '.join(args)} 失败：{result.stderr}")
        return result.stdout

    def init_repo(self) -> None:
        self.git("init", "-q")
        self.git("config", "user.name", "kit-test")
        self.git("config", "user.email", "kit-test@example.invalid")

    def commit(self) -> None:
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "fixture")

    def assert_result(
        self, result: subprocess.CompletedProcess[str], code: int, *fragments: str
    ) -> str:
        output = (result.stdout or "") + (result.stderr or "")
        self.assertEqual(result.returncode, code, output)
        for fragment in fragments:
            self.assertIn(fragment, output)
        return output

    # --- base fixtures ---------------------------------------------------
    def clean_project(self, **sections: object) -> None:
        self.init_repo()
        self.write("README.md", "# Demo\n")
        self.write("src/app.py", "import os\n")
        self.write_config(**sections)
        self.commit()


class CheckHygieneTests(HostSensorCase):
    def test_clean_project_passes(self) -> None:
        self.clean_project(hygiene=HYGIENE)
        result = run_tool("check_hygiene.py", self.root)
        self.assert_result(result, 0, "[OK]", "0 违规")

    def test_tracked_build_artifact_fails(self) -> None:
        self.clean_project(hygiene=HYGIENE)
        self.write("app/build/out.bin", b"binary")
        self.commit()
        result = run_tool("check_hygiene.py", self.root)
        self.assert_result(result, 1, "构建产物", "app/build/out.bin")

    def test_root_file_outside_allowlist_fails(self) -> None:
        self.clean_project(hygiene=HYGIENE)
        self.write("NOTES.md", "# notes\n")
        self.commit()
        result = run_tool("check_hygiene.py", self.root)
        self.assert_result(result, 1, "rootAllowlist", "NOTES.md")

    def test_absolute_symlink_fails(self) -> None:
        self.clean_project(hygiene=HYGIENE)
        (self.root / "link.txt").symlink_to("/tmp/kit-host-tools-target")
        self.commit()
        result = run_tool("check_hygiene.py", self.root)
        self.assert_result(result, 1, "绝对符号链接", "link.txt")

    def test_local_machine_path_in_tracked_text_fails(self) -> None:
        self.clean_project(hygiene=HYGIENE)
        self.write("docs/note.md", "外接盘示例：/Volumes/External/src 不应入库\n")
        self.commit()
        result = run_tool("check_hygiene.py", self.root)
        self.assert_result(result, 1, "本机路径", "docs/note.md", "/Volumes/")

    def test_home_pattern_has_identifier_boundary(self) -> None:
        # features/home/ 与 docs/home/ 不是 /home/ 绝对路径，不应误报。
        self.clean_project(hygiene={**HYGIENE, "localPathPatterns": ["/home/"]})
        self.write("docs/note.md", "相对目录：features/home/cache 与 docs/home/index\n")
        self.commit()
        result = run_tool("check_hygiene.py", self.root)
        self.assert_result(result, 0, "[OK]")
        self.assertNotIn("[FAIL]", (result.stdout or "") + (result.stderr or ""))

    def test_oversized_tracked_file_fails(self) -> None:
        self.clean_project(hygiene={**HYGIENE, "maxTrackedFileBytes": 16})
        self.write("assets/big.txt", "x" * 64)
        self.commit()
        result = run_tool("check_hygiene.py", self.root)
        self.assert_result(result, 1, "超过 16 bytes", "assets/big.txt")

    def test_missing_hygiene_section_skips(self) -> None:
        self.clean_project()
        result = run_tool("check_hygiene.py", self.root)
        self.assert_result(result, 0, "[SKIP]", "未配置 hygiene")

    def test_missing_config_fails_readably(self) -> None:
        self.init_repo()
        self.write("README.md", "# Demo\n")
        self.commit()
        result = run_tool("check_hygiene.py", self.root)
        self.assert_result(result, 1, "缺少配置文件", "harness/config.json")

    def test_default_root_is_script_parent(self) -> None:
        self.clean_project()
        target_tools = self.root / "tools"
        target_tools.mkdir(parents=True, exist_ok=True)
        for name in ("check_hygiene.py", "check_layers.py"):
            (target_tools / name).write_text(
                (TOOLS / name).read_text(encoding="utf-8"), encoding="utf-8"
            )
        result = subprocess.run(
            [sys.executable, str(target_tools / "check_hygiene.py")],
            cwd=str(self.root),
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assert_result(result, 0, "[SKIP]", "未配置 hygiene")


class CheckLayersTests(HostSensorCase):
    def base_layers(self, **overrides: object) -> dict:
        layers = {
            "sourceRoot": "src",
            "extensions": [".kt", ".py"],
            "rules": [
                {
                    "name": "domain",
                    "pathPrefix": "src/domain/",
                    "forbiddenImports": ["android.", "androidx.", "features.", "services."],
                }
            ],
        }
        layers.update(overrides)
        return layers

    def test_forbidden_import_fails(self) -> None:
        self.clean_project(layers=self.base_layers())
        self.write(
            "src/domain/Foo.kt",
            "package demo\n\nimport androidx.compose.runtime.Composable\n",
        )
        self.commit()
        result = run_tool("check_layers.py", self.root)
        self.assert_result(result, 1, "src/domain/Foo.kt:domain", "androidx.compose.runtime.Composable")

    def test_allowed_imports_override_forbidden(self) -> None:
        layers = self.base_layers()
        layers["rules"][0]["allowedImports"] = ["androidx.compose.runtime"]
        self.clean_project(layers=layers)
        self.write(
            "src/domain/Foo.kt",
            "package demo\n\nimport androidx.compose.runtime.Composable\n",
        )
        self.commit()
        result = run_tool("check_layers.py", self.root)
        self.assert_result(result, 0, "[OK]", "0 违规")

    def test_python_from_import_fails(self) -> None:
        self.clean_project(layers=self.base_layers())
        self.write("src/domain/foo.py", "from android.os import Build\n")
        self.commit()
        result = run_tool("check_layers.py", self.root)
        self.assert_result(result, 1, "src/domain/foo.py:domain")
        self.assertIn("android.os", (result.stdout or "") + (result.stderr or ""))

    def test_symbol_guard_respects_allowed_paths_and_comments(self) -> None:
        layers = self.base_layers(
            symbolGuards=[
                {"name": "engine", "classes": ["Engine"], "allowedPaths": ["src/services/**"]}
            ]
        )
        self.clean_project(layers=layers)
        self.write("src/features/Feature.kt", "val engine = Engine()\n")
        self.write("src/features/Comment.kt", "// val engine = Engine()\n")
        self.write("src/services/Engine.kt", "class Engine\n")
        self.commit()
        output = self.assert_result(run_tool("check_layers.py", self.root), 1, "src/features/Feature.kt:engine")
        self.assertNotIn("src/features/Comment.kt", output)
        self.assertNotIn("src/services/Engine.kt:engine", output)

    def test_missing_layers_section_skips(self) -> None:
        self.clean_project()
        result = run_tool("check_layers.py", self.root)
        self.assert_result(result, 0, "[SKIP]", "未配置 layers")

    def test_missing_source_root_fails_readably(self) -> None:
        self.clean_project(layers={"sourceRoot": "missing-src", "rules": []})
        result = run_tool("check_layers.py", self.root)
        self.assert_result(result, 1, "源码目录不存在", "missing-src")


if __name__ == "__main__":
    unittest.main()
