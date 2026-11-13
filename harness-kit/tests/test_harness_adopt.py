#!/usr/bin/env python3
"""Acceptance tests for harness-kit/scripts/harness-adopt (read-only adoption inventory).

Contract: harness-kit/SPEC.md §8 (script conventions) / §9 (tests).
Runs the real CLI against temporary git fixtures; no network, no Xcode, no third-party deps.

Run: python3 -m unittest discover -s harness-kit/tests -q
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
ADOPT = KIT / "scripts" / "harness-adopt"
PLACEHOLDER_RE = re.compile(r"\{\{[A-Z0-9_]+\}\}")
LOCAL_PATH_RE = re.compile(r"/(?:Users|Volumes|home)/")


# ── helpers ───────────────────────────────────────────────────────────────
def run(cmd: list[str], cwd: Path | str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd, cwd=str(cwd), capture_output=True, text=True, timeout=120
    )


def git(target: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return run(["git", "-C", str(target), *args], cwd=target)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def make_fixture(root: Path) -> Path:
    """Minimal legacy project with the exact findings the report must surface."""
    target = root / "demo-project"
    (target / "docs").mkdir(parents=True)
    (target / "build").mkdir()
    (target / "src").mkdir()
    write(target / "README.md", "# Demo project\n\nA legacy project for inventory tests.\n")
    write(target / "NOTES.md", "# Scratch notes\n\nKeep this file out of the doc tree.\n")
    write(target / "docs" / "README.md", "# Docs index\n\n- [Guide](guide.md)\n")
    write(target / "docs" / "guide.md", "# Guide\n")
    write(target / "docs" / "extra.md", "# Extra doc\n\nNot linked from the docs index.\n")
    write(target / "docs" / "broken.md", "# Broken\n\n- [Missing](does-not-exist.md)\n")
    write(
        target / "docs" / "fence.md",
        "# Fence\n\n```text\nopened and never closed\n",
    )
    # Build the fixture path from parts so no absolute local path literal lands in the repo.
    write(target / "docs" / "local.md", "# Local\n\nPath: " + "/Us" + "ers/alice/demo-project\n")
    write(
        target / "docs" / "stale.md",
        "# Stale\n\n此方案已废弃，等待清理。\n\n写于实现之前，已被推翻；尚未编译，待真机验证。\n",
    )
    write(target / "src" / "app.py", "def main():\n    return 0\n")
    write(target / "build.gradle", "plugins {}\n")
    write(target / "build" / "output.bin", "binary-ish artifact\n")
    # Gradle wrapper files are legitimate tracked tooling even though they look build-like.
    write(target / "gradlew", "#!/bin/sh\n")
    write(target / "gradle" / "wrapper" / "gradle-wrapper.jar", "wrapper jar\n")
    write(target / "gradle" / "wrapper" / "gradle-wrapper.jar.sha256", "0" * 64 + "\n")
    write(target / ".gitignore", "build/\n")
    os.symlink("/tmp", target / "abs-link")
    run(["git", "init", "-q"], cwd=target)
    git(target, "config", "user.name", "kit-test")
    git(target, "config", "user.email", "kit-test@example.invalid")
    git(target, "add", "-A")
    git(target, "add", "-f", "build/output.bin")  # simulate a tracked build artifact
    git(target, "commit", "-q", "-m", "init")
    return target


def make_kit(root: Path, *, template: str | None = None) -> Path:
    kit = root / "fake-kit"
    (kit / "core" / "templates" / "harness" / "plans").mkdir(parents=True)
    (kit / "VERSION").write_text("9.9.9\n", encoding="utf-8")
    if template is not None:
        (kit / "core" / "templates" / "harness" / "plans" / "_adoption.md.template").write_text(
            template, encoding="utf-8"
        )
    return kit


ADOPTION_TEMPLATE = """---
id: <date>-<topic>
status: <status>
level: L2
owner: <owner>
updated: <date>
scope:
  allow:
    - .
acceptance:
  - <fill me>
verify:
  - make check
---

# {{PROJECT_NAME}} · harness-kit 接入计划

- 建议 profile：{{PROFILE}}
- test 命令：`{{TEST_COMMAND}}`
- 盘点摘要：{{SUMMARY}}

## 发现

{{FINDINGS}}

## 风险

{{RISKS}}

## 下一步

{{NEXT_STEPS}}
"""


def snapshot(root: Path) -> dict[str, tuple]:
    """Content snapshot of everything except .git (used to prove the default run is read-only)."""
    result: dict[str, tuple] = {}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if rel == ".git" or rel.startswith(".git/"):
            continue
        if path.is_symlink():
            result[rel] = ("link", os.readlink(path))
        elif path.is_file():
            result[rel] = ("file", path.stat().st_size, path.read_bytes())
        else:
            result[rel] = ("dir",)
    return result


class HarnessAdoptTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.target = make_fixture(self.tmp)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def invoke(
        self, *args: str, target: Path | None = None, env: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, str(ADOPT), "--target", str(target or self.target), *args]
        return subprocess.run(
            command, cwd=str(KIT), capture_output=True, text=True, timeout=120,
            env={**os.environ, **(env or {})},
        )

    def shim_dir(self, *programs: str) -> tuple[Path, dict[str, str]]:
        bindir = self.tmp / "shim-bin"
        bindir.mkdir(exist_ok=True)
        for program in programs:
            path = bindir / program
            path.write_text("#!/bin/sh\necho \"%s 0.0.0\"\nexit 0\n" % program, encoding="utf-8")
            path.chmod(0o755)
        env = {"PATH": str(bindir) + os.pathsep + os.environ.get("PATH", "")}
        return bindir, env

    # ── packaging / CLI guard ────────────────────────────────────────
    def test_script_is_executable_with_shebang(self) -> None:
        self.assertTrue(ADOPT.is_file(), "harness-adopt is missing")
        self.assertTrue(os.access(ADOPT, os.X_OK), "harness-adopt must be executable")
        first_line = ADOPT.read_text(encoding="utf-8").splitlines()[0]
        self.assertTrue(first_line.startswith("#!"), first_line)
        self.assertIn("python3", first_line)

    def test_invalid_target_exits_one(self) -> None:
        proc = self.invoke(target=self.tmp / "does-not-exist")
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("target directory does not exist", proc.stderr)
        self.assertTrue(ADOPT.is_file())

    # ── default read-only Markdown run ───────────────────────────────
    def test_default_run_is_read_only_and_reports_findings(self) -> None:
        before = snapshot(self.target)
        started = time.monotonic()
        proc = self.invoke()
        elapsed = time.monotonic() - started
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertLess(elapsed, 5.0, "inventory should be fast")
        self.assertEqual(before, snapshot(self.target), "default run must not modify the target")
        report = proc.stdout
        for heading in (
            "## 概览", "## 文档盘点", "## 卫生盘点", "## 建议", "## 下一步", "## 反馈 kit 问题",
        ):
            self.assertIn(heading, report)
        self.assertIn("harness-engineering-kit/issues", report)
        for expected in (
            "NOTES.md",             # root markdown outside the documented entry set
            "docs/extra.md",        # doc missing from docs/README.md index
            "does-not-exist.md",    # broken relative link sample
            "build/output.bin",     # tracked build artifact
            "abs-link",             # absolute symlink
            "断链",                 # broken-link section
            "围栏",                 # odd code-fence section
            "过期",                 # stale marker section
            "本机路径",             # machine-local path section
            "既有门禁文件",         # existing gates
            "- [ ]",                # next-step checklist
        ):
            self.assertIn(expected, report)
        self.assertIn("本机路径样本", report)
        self.assertIn("/<local>/", report)  # local paths are masked in the report
        self.assertNotIn("alice", report, "report must not leak the raw local path")

    # ── JSON contract ────────────────────────────────────────────────
    def test_json_output_contract(self) -> None:
        proc = self.invoke("--json")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        data = json.loads(proc.stdout)
        for key in (
            "target", "kitVersion", "generatedAt", "readOnly",
            "overview", "docs", "hygiene", "recommendation", "nextSteps", "writePlan", "feedback",
        ):
            self.assertIn(key, data)
        self.assertIn("harness-engineering-kit/issues", data["feedback"]["url"])
        self.assertTrue(data["readOnly"])
        self.assertIn("android", data["overview"]["languages"])  # build.gradle → android
        self.assertEqual("./gradlew testDebugUnitTest", data["recommendation"]["testCommand"])
        self.assertTrue(data["overview"]["git"]["isRepo"])
        self.assertGreaterEqual(data["overview"]["git"]["tracked"], 10)
        self.assertIn("docs/extra.md", data["docs"]["unregistered"])
        self.assertTrue(data["docs"]["hasIndex"])  # docs/README.md exists
        self.assertIn("build/output.bin", data["hygiene"]["trackedBuildArtifacts"])
        tracked = data["hygiene"]["trackedBuildArtifacts"]
        for allowed in (
            "gradlew",
            "gradle/wrapper/gradle-wrapper.jar",
            "gradle/wrapper/gradle-wrapper.jar.sha256",
        ):
            self.assertNotIn(allowed, tracked, f"{allowed} is legitimate wrapper tooling")
        stale = "\n".join(data["docs"]["staleMarkers"])
        self.assertIn("已被推翻", stale)
        self.assertIn("待真机验证", stale)
        absolute = [item["path"] for item in data["hygiene"]["absoluteSymlinks"]]
        self.assertIn("abs-link", absolute)
        self.assertTrue(data["hygiene"]["localPathHits"])
        recommendation = data["recommendation"]
        self.assertEqual("standard", recommendation["recommended"])
        self.assertIn(recommendation["alternative"], (None, "strict"))
        self.assertIn("standard", recommendation["why"])
        self.assertIn("testCommand", recommendation)
        self.assertIn("testCommandSource", recommendation)
        self.assertIsInstance(recommendation["testCommandExecutable"], bool)
        self.assertTrue(data["recommendation"]["risks"])
        self.assertFalse(data["writePlan"]["written"])

    # ── --report ────────────────────────────────────────────────────
    def test_report_written_to_requested_path(self) -> None:
        before = snapshot(self.target)
        report_path = self.tmp / "reports" / "adopt.md"
        report_path.parent.mkdir()
        proc = self.invoke("--report", str(report_path))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertTrue(report_path.is_file())
        self.assertIn("## 概览", report_path.read_text(encoding="utf-8"))
        self.assertIn("[OK] report written", proc.stdout)
        self.assertEqual(before, snapshot(self.target), "--report must not modify the target")

    # ── --write-plan ────────────────────────────────────────────────
    def test_write_plan_requires_plans_dir(self) -> None:
        before = snapshot(self.target)
        proc = self.invoke("--write-plan")
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("harness/plans", proc.stderr)
        self.assertEqual(before, snapshot(self.target))

    def test_write_plan_renders_kit_template(self) -> None:
        kit = make_kit(self.tmp, template=ADOPTION_TEMPLATE)
        (self.target / "harness" / "plans").mkdir(parents=True)
        before = snapshot(self.target)
        proc = self.invoke("--write-plan", "--root", str(kit))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        plans = sorted((self.target / "harness" / "plans").glob("*-adopt-harness.md"))
        self.assertEqual(len(plans), 1, proc.stdout)
        plan = plans[0].read_text(encoding="utf-8")
        self.assertNotRegex(plan, PLACEHOLDER_RE)
        self.assertIn("demo-project", plan)
        self.assertIn("profile", plan)
        self.assertRegex(plans[0].name, r"^\d{4}-\d{2}-\d{2}-adopt-harness\.md$")
        after = snapshot(self.target)
        new_files = set(after) - set(before)
        self.assertEqual(new_files, {f"harness/plans/{plans[0].name}"})
        self.assertIn("[OK] adoption plan written", proc.stdout)

    def test_write_plan_missing_template_reports_error(self) -> None:
        kit = make_kit(self.tmp, template=None)
        (self.target / "harness" / "plans").mkdir(parents=True)
        proc = self.invoke("--write-plan", "--root", str(kit))
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("adoption plan template not found", proc.stderr)
        self.assertFalse(list((self.target / "harness" / "plans").glob("*.md")))

    def test_write_plan_refuses_to_overwrite(self) -> None:
        kit = make_kit(self.tmp, template=ADOPTION_TEMPLATE)
        (self.target / "harness" / "plans").mkdir(parents=True)
        first = self.invoke("--write-plan", "--root", str(kit))
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        plans = list((self.target / "harness" / "plans").glob("*-adopt-harness.md"))
        self.assertEqual(len(plans), 1)
        original = plans[0].read_text(encoding="utf-8")
        second = self.invoke("--write-plan", "--root", str(kit))
        self.assertEqual(second.returncode, 1, second.stdout + second.stderr)
        self.assertIn("refusing to overwrite", second.stderr)
        self.assertEqual(original, plans[0].read_text(encoding="utf-8"))

    def test_android_command_falls_back_without_gradlew(self) -> None:
        plain = self.tmp / "android-no-wrapper"
        write(plain / "build.gradle", "plugins {}\n")
        proc = self.invoke("--json", target=plain)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        data = json.loads(proc.stdout)
        self.assertEqual("gradle testDebugUnitTest", data["recommendation"]["testCommand"])

    def test_json_with_write_plan_keeps_stdout_pure_json(self) -> None:
        kit = make_kit(self.tmp, template=ADOPTION_TEMPLATE)
        (self.target / "harness" / "plans").mkdir(parents=True)
        proc = self.invoke("--write-plan", "--json", "--root", str(kit))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        data = json.loads(proc.stdout)  # raises if any non-JSON line leaked into stdout
        self.assertTrue(data["writePlan"]["written"])
        self.assertEqual(1, len(list((self.target / "harness" / "plans").glob("*-adopt-harness.md"))))

    # ── Python test-command detection (O3) ─────────────────────────
    def _python_target(self, name: str) -> Path:
        target = self.tmp / name
        (target / "src").mkdir(parents=True)
        write(target / "pyproject.toml", "[project]\nname = \"demo\"\n")
        write(target / "src" / "app.py", "def main():\n    return 0\n")
        return target

    def test_python_venv_and_pytest_detection(self) -> None:
        target = self._python_target("py-venv")
        write(target / "requirements.txt", "pytest==8.0.0\n")
        venv_python = target / ".venv" / "bin" / "python"
        write(
            venv_python,
            "#!/bin/sh\n"
            'if [ "$1" = "-m" ] && [ "$2" = "pytest" ] && [ "$3" = "--version" ]; then\n'
            '  echo "pytest 8.0.0"; exit 0\n'
            "fi\n"
            'echo "Python 3.12.0"; exit 0\n',
        )
        os.chmod(venv_python, 0o755)
        proc = self.invoke("--json", target=target)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        recommendation = json.loads(proc.stdout)["recommendation"]
        self.assertEqual(".venv/bin/python -m pytest -q", recommendation["testCommand"])
        self.assertIn("venv", recommendation["testCommandSource"])
        self.assertIn("pytest", recommendation["testCommandSource"])
        self.assertTrue(recommendation["testCommandExecutable"])

    def test_python_uv_lock_suggestion(self) -> None:
        target = self._python_target("py-uv")
        write(target / "pyproject.toml", '[tool.pytest.ini_options]\naddopts = "-q"\n')
        write(target / "uv.lock", "")
        _bindir, env = self.shim_dir("uv")
        proc = self.invoke("--json", target=target, env=env)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        recommendation = json.loads(proc.stdout)["recommendation"]
        self.assertEqual("uv run -m pytest -q", recommendation["testCommand"])
        self.assertIn("uv.lock", recommendation["testCommandSource"])

    def test_python_poetry_lock_suggestion(self) -> None:
        target = self._python_target("py-poetry")
        (target / "tests").mkdir()
        write(target / "poetry.lock", "")
        _bindir, env = self.shim_dir("poetry")
        proc = self.invoke("--json", target=target, env=env)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        recommendation = json.loads(proc.stdout)["recommendation"]
        self.assertEqual("poetry run -m unittest discover -s tests -q", recommendation["testCommand"])
        self.assertIn("poetry.lock", recommendation["testCommandSource"])

    def test_python_plain_python3_fallback(self) -> None:
        target = self._python_target("py-plain")
        proc = self.invoke("--json", target=target)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        recommendation = json.loads(proc.stdout)["recommendation"]
        self.assertEqual("python3 -m unittest discover -q", recommendation["testCommand"])
        self.assertIn("系统 python3", recommendation["testCommandSource"])

    def test_test_command_override_is_probed(self) -> None:
        proc = self.invoke("--json", "--test-command", "missing-program-xyz --flag")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        recommendation = json.loads(proc.stdout)["recommendation"]
        self.assertEqual("missing-program-xyz --flag", recommendation["testCommand"])
        self.assertIn("--test-command", recommendation["testCommandSource"])
        self.assertFalse(recommendation["testCommandExecutable"])
        self.assertIn("未找到", recommendation["testCommandProbe"])
        report = self.invoke("--test-command", "missing-program-xyz --flag").stdout
        self.assertIn("可执行探测", report)
        self.assertIn("未验证（smoke=not-run）", report)
        self.assertIn("使用命令", report)
        # K04：探测（--version）不能被称为「已验证命令」
        self.assertNotIn("已验证命令", report)

    # ── K03 / K04 / K05 / K06 / K11（存量接入反馈）─────────────────
    def _git_repo(self, name: str) -> Path:
        target = self.tmp / name
        target.mkdir(parents=True)
        write(target / "README.md", "# Demo\n")
        run(["git", "init", "-q"], cwd=target)
        git(target, "config", "user.name", "kit-test")
        git(target, "config", "user.email", "kit-test@example.invalid")
        git(target, "add", "-A")
        git(target, "commit", "-q", "-m", "init")
        return target

    def test_probe_is_not_a_verified_command(self) -> None:
        """K04：--version 探测不能被报告/JSON 宣称成「已验证命令」。"""
        proc = self.invoke("--json")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        recommendation = json.loads(proc.stdout)["recommendation"]
        self.assertEqual("not-run", recommendation["testCommandSmoke"])
        self.assertTrue(recommendation["testCommandProbeOnly"])
        self.assertNotIn("testCommandVerified", recommendation)
        report = self.invoke().stdout
        self.assertNotIn("已验证命令", report)

    def test_agents_assessment_recommends_move_for_oversized_agents(self) -> None:
        """K03：盘点要给出 AGENTS 超预算诊断与 move 迁移命令。"""
        target = self._git_repo("agents-over")
        write(target / "AGENTS.md", "规则。" * 700)  # ≈1400 tokens > 默认预算 1200
        git(target, "add", "-A")
        git(target, "commit", "-q", "-m", "big agents")
        proc = self.invoke("--json", target=target)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        data = json.loads(proc.stdout)
        agents = data["overview"]["agents"]
        self.assertTrue(agents["overBudget"])
        self.assertGreater(agents["overBy"], 0)
        self.assertEqual("move", agents["recommendedMode"])
        report = self.invoke(target=target).stdout
        self.assertIn("## AGENTS 迁移建议", report)
        self.assertIn("--agents-mode move", report)
        self.assertIn("--agents-archive-path", report)

    def test_default_branch_drift_is_detected(self) -> None:
        """K05：当前在 feature 分支、默认分支是 main 时要提示 --default-branch。"""
        target = self._git_repo("branch-drift")
        run(["git", "update-ref", "refs/remotes/origin/main", "HEAD"], cwd=target)
        run(
            ["git", "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main"],
            cwd=target,
        )
        run(["git", "checkout", "-q", "-b", "feature/x"], cwd=target)
        proc = self.invoke("--json", target=target)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        data = json.loads(proc.stdout)
        self.assertEqual("main", data["overview"]["git"]["defaultBranch"])
        self.assertTrue(data["overview"]["git"]["branchDrift"])
        self.assertTrue(any("--default-branch main" in step for step in data["nextSteps"]))
        report = self.invoke(target=target).stdout
        self.assertIn("当前分支与默认分支不一致", report)

    def test_untracked_docs_index_counts_as_present(self) -> None:
        """K06：git 未跟踪但磁盘存在的 docs/README.md 不能报「缺失」。"""
        target = self._git_repo("untracked-index")
        write(target / "docs" / "README.md", "# Docs index\n\n- [Guide](guide.md)\n")
        write(target / "docs" / "guide.md", "# Guide\n")
        proc = self.invoke("--json", target=target)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        docs = json.loads(proc.stdout)["docs"]
        self.assertTrue(docs["hasIndex"])
        self.assertFalse(docs["hasIndexTracked"])

    def test_gitignore_expectations_are_language_aware(self) -> None:
        """K11：Node 项目不应被建议补 .build/、*.xcresult 等 Swift 条目。"""
        target = self._git_repo("node-ignore")
        write(target / "package.json", json.dumps({"name": "node-app"}))
        proc = self.invoke("--json", target=target)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        missing = json.loads(proc.stdout)["hygiene"]["gitignoreMissing"]
        self.assertIn("node_modules/", missing)
        self.assertNotIn(".build/", missing)
        self.assertNotIn("*.xcresult", missing)
        self.assertNotIn("DerivedData/", missing)

    def test_node_typescript_suggestion_avoids_bare_node_test(self) -> None:
        """K04 真实触发条件：有 tsx 依赖时建议 tsx --test，而不是 node --test。"""
        target = self._git_repo("node-tsx")
        write(
            target / "package.json",
            json.dumps({"name": "node-app", "devDependencies": {"tsx": "^4.19.0"}}),
        )
        proc = self.invoke("--json", target=target)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        recommendation = json.loads(proc.stdout)["recommendation"]
        self.assertIn("tsx --test", recommendation["testCommandSuggested"])
        self.assertIn("ERR_MODULE_NOT_FOUND", recommendation["testCommandSource"])

    def test_profile_guidance_defaults_to_standard(self) -> None:
        proc = self.invoke("--json")
        data = json.loads(proc.stdout)
        recommendation = data["recommendation"]
        self.assertEqual("standard", recommendation["recommended"])
        self.assertIn("存量仓库默认 standard", recommendation["why"])
        report = self.invoke().stdout
        self.assertIn("推荐 profile：**standard**", report)
        self.assertIn("备选 profile", report)
        self.assertIn("strict", report)

    def test_strict_is_only_an_alternative_for_signal_rich_repos(self) -> None:
        target = self.tmp / "rich-repo"
        (target / "docs").mkdir(parents=True)
        write(target / "AGENTS.md", "# Rules\n")
        write(target / "docs" / "README.md", "# Docs\n")
        for index in range(12):
            write(target / f"docs\u002fdoc-{index}.md", f"# Doc {index}\n")
        write(target / ".github" / "workflows" / "ci.yml", "name: ci\n")
        write(target / ".githooks" / "pre-push", "#!/bin/sh\n")
        write(target / "tests" / "test_app.py", "def test_ok():\n    assert True\n")
        proc = self.invoke("--json", target=target)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        recommendation = json.loads(proc.stdout)["recommendation"]
        self.assertEqual("standard", recommendation["recommended"])
        self.assertEqual("strict", recommendation["alternative"])
        self.assertIn("显式", recommendation["why"])
        self.assertIn("理由", recommendation["why"])

    # ── --archive-report (O3) ───────────────────────────────────────
    def test_archive_report_copies_without_rescan(self) -> None:
        report = self.tmp / "inventory-report.md"
        write(report, "# Baseline inventory\n\n- tracked: 42\n")
        before = snapshot(self.target)
        proc = self.invoke("--archive-report", str(report))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("[OK] adoption report archived", proc.stdout)
        archived = list((self.target / "harness" / "reports").glob("adoption-*.md"))
        self.assertEqual(1, len(archived), proc.stdout)
        archived_text = archived[0].read_text(encoding="utf-8")
        self.assertIn("> sanitized：", archived_text)
        self.assertIn("来源命令", archived_text)
        self.assertIn("# Baseline inventory", archived_text)
        self.assertIn("tracked: 42", archived_text)
        after = snapshot(self.target)
        new_entries = set(after) - set(before)
        new_files = {entry for entry in new_entries if (self.target / entry).is_file()}
        self.assertEqual(new_files, {f"harness/reports/{archived[0].name}"})
        # 第二次归档拒绝覆盖
        second = self.invoke("--archive-report", str(report))
        self.assertEqual(second.returncode, 1, second.stdout + second.stderr)
        self.assertIn("拒绝覆盖", second.stderr)
        # 源文件缺失有可读错误
        missing = self.invoke("--archive-report", str(self.tmp / "nope.md"))
        self.assertEqual(missing.returncode, 1, missing.stdout + missing.stderr)
        self.assertIn("不存在", missing.stderr)

    def test_broken_venv_falls_back_to_next_candidate(self) -> None:
        target = self._python_target("py-broken-venv")
        write(target / "requirements.txt", "pytest==8.0.0\n")
        broken = target / ".venv" / "bin" / "python"
        write(broken, "#!/bin/sh\nexit 127\n")
        os.chmod(broken, 0o755)
        proc = self.invoke("--json", target=target)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        recommendation = json.loads(proc.stdout)["recommendation"]
        self.assertTrue(recommendation["testCommand"].startswith("python3"), recommendation)
        probe = recommendation["testCommandProbe"]
        self.assertIn("失败", probe)
        self.assertIn(".venv/bin/python", probe)
        self.assertIn("候选探测通过", recommendation["testCommandSource"])
        report = self.invoke(target=target).stdout
        self.assertIn("可执行探测", report)
        self.assertIn("未验证（smoke=not-run）", report)
        self.assertNotIn("已验证命令", report)

    def test_archive_report_sanitizes_local_paths(self) -> None:
        report = self.tmp / "leaky-report.md"
        host_path = "/Us" + "ers/alice/secret-project"
        volumes_path = "/Vol" + "umes/ExternalDK/data"
        home_path = "/ho" + "me/bob/work"
        write(
            report,
            f"# Inventory\n\n- repo: {self.target}\n- a: {host_path}\n"
            f"- b: {volumes_path}\n- c: {home_path}\n",
        )
        proc = self.invoke("--archive-report", str(report), "--json")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        data = json.loads(proc.stdout)
        self.assertTrue(data["sanitized"])
        archived = self.target / data["path"]
        text = archived.read_text(encoding="utf-8")
        self.assertNotIn("alice", text)
        self.assertNotIn("bob", text)
        self.assertNotIn("ExternalDK", text)
        self.assertIn("$HOME", text)
        self.assertIn("<local-path>", text)
        self.assertNotIn(str(self.target.resolve()), text)

    # ── non-git target ──────────────────────────────────────────────
    def test_non_git_target_is_scanned_without_git(self) -> None:
        plain = self.tmp / "plain"
        write(plain / "README.md", "# Plain\n")
        write(plain / "docs" / "README.md", "# Docs\n")
        os.symlink("/tmp", plain / "absolute-link")
        proc = self.invoke("--json", target=plain)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        data = json.loads(proc.stdout)
        self.assertFalse(data["overview"]["git"]["isRepo"])
        self.assertTrue(any(item["path"] == "absolute-link" for item in data["hygiene"]["symlinks"]))
        self.assertTrue(data["hygiene"]["absoluteSymlinks"])


if __name__ == "__main__":
    unittest.main()
