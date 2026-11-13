#!/usr/bin/env python3
"""harness-kit end-to-end acceptance: init each profile into a blank git repo.

Contract: harness-kit/SPEC.md §9. No network, no Xcode, standard library only.
Runs real subprocesses (harness-init + make) against temp directories.
"""
from __future__ import annotations

import io
import json
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
INIT = KIT / "scripts" / "harness-init"
PROFILES = ("minimal", "standard", "strict")
PLACEHOLDER_LEFT = re.compile(r"\{\{[A-Z0-9_]+\}\}")


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)


def init_target(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    run(["git", "init", "-q"], cwd=path)
    for key, value in (("user.name", "kit-test"), ("user.email", "kit-test@example.invalid")):
        run(["git", "config", key, value], cwd=path)
    (path / "README.md").write_text("# Test Project\n", encoding="utf-8")
    (path / "app.py").write_text("def main():\n    return 0\n", encoding="utf-8")
    run(["git", "add", "-A"], cwd=path)
    run(["git", "commit", "-q", "-m", "init"], cwd=path)
    return path


def tree_files(root: Path) -> list[Path]:
    files = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in (".git", ".harness-init-backup") for part in path.parts):
            continue
        files.append(path)
    return files


class HarnessInitProfileTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def invoke(self, *args: str, target: Path) -> subprocess.CompletedProcess[str]:
        return run(
            [sys.executable, str(INIT), "--target", str(target), *args],
            cwd=KIT,
        )

    def test_profiles_init_and_check(self) -> None:
        if not INIT.is_file():
            self.skipTest("harness-init is not present")
        for profile in PROFILES:
            with self.subTest(profile=profile):
                target = init_target(self.tmp / profile)
                proc = self.invoke(
                    "--profile", profile, "--name", "Test Project", "--test-command", "echo ok",
                    target=target,
                )
                self.assertEqual(proc.returncode, 0, f"{profile} init failed:\n{proc.stdout}\n{proc.stderr}")
                self.assertIn("post-init check: PASS", proc.stdout)
                # v0.5.2 反馈通道：init 收尾提示 + 渲染后的根 AGENTS 都写明上游 issue 入口。
                self.assertIn("harness-engineering-kit/issues", proc.stdout)
                self.assertTrue((target / "AGENTS.md").is_file())
                agents_text = (target / "AGENTS.md").read_text(encoding="utf-8")
                self.assertIn("harness-engineering-kit/issues", agents_text)
                self.assertIn("kit 自身缺陷", agents_text)
                self.assertTrue((target / "harness" / "config.json").is_file())
                config = json.loads((target / "harness" / "config.json").read_text(encoding="utf-8"))
                instructions = config["instructions"]
                self.assertEqual(1000, instructions["nestedMaxTokens"])
                self.assertEqual(1000, instructions["budgets"]["docs/README.md"])
                self.assertEqual(
                    profile in ("standard", "strict"),
                    "HARNESS.md" in instructions["budgets"],
                    f"{profile} 的 HARNESS.md 预算渲染不符合预期",
                )
                checked = run(["make", "check"], cwd=target)
                self.assertEqual(
                    checked.returncode, 0, f"{profile} make check failed:\n{checked.stdout}\n{checked.stderr}"
                )
                self.assertIn("（余 ", checked.stdout)
                self.assertIn("nestedMaxTokens=1000", checked.stdout)
                self.assertIn("token 预算：AGENTS.md ≈", checked.stdout)
                if profile in ("standard", "strict"):
                    self.assertTrue((target / "harness" / "plans" / "_template.md").is_file())
                    self.assertTrue((target / "tools" / "verify_claim.py").is_file())
                    # v0.4.0：scorecard / selftest / 评分卡模板进入 standard（strict 继承）
                    self.assertTrue((target / "tools" / "scorecard.py").is_file())
                    self.assertTrue((target / "tools" / "harness_selftest").is_file())
                    self.assertTrue((target / "docs" / "harness-scorecard.md").is_file())
                    makefile = target / (
                        "Makefile.harness" if (target / "Makefile.harness").is_file() else "Makefile"
                    )
                    makefile_text = makefile.read_text(encoding="utf-8")
                    for target_name in ("selftest:", "upgrade-check:", "scorecard:"):
                        self.assertIn(target_name, makefile_text)
                    static = run(["make", "verify-static"], cwd=target)
                    self.assertEqual(static.returncode, 0, f"{profile} verify-static failed:\n{static.stdout}\n{static.stderr}")
                    scorecard = run(["make", "scorecard"], cwd=target)
                    self.assertEqual(
                        scorecard.returncode, 0,
                        f"{profile} make scorecard failed:\n{scorecard.stdout}\n{scorecard.stderr}",
                    )
                    reviews = sorted((target / "harness" / "reviews").glob("*-scorecard.md"))
                    self.assertEqual(1, len(reviews), scorecard.stdout)
                    self.assertIn("checkedAt:", reviews[0].read_text(encoding="utf-8"))
                if profile == "strict":
                    self.assertTrue((target / ".dsh" / "skills" / "red-team" / "SKILL.md").is_file())
                # no unresolved placeholders / Duiyi terms in the generated tree
                for path in tree_files(target):
                    text = path.read_text(encoding="utf-8", errors="ignore")
                    if "/tools/" not in path.as_posix():
                        # copied scripts may legitimately contain {{PLACEHOLDER}} literals
                        # used for runtime substitution (e.g. plan template keys)
                        self.assertIsNone(PLACEHOLDER_LEFT.search(text), f"placeholder left in {path}")
                    self.assertNotRegex(text, r"(?i)duiyi|对译|TranslationSession|SwiftData", f"Duiyi reference in {path}")

    def test_standalone_copy_init(self) -> None:
        """Kit 目录复制到仓库外后仍可 init（无来源仓库依赖）。"""
        if not INIT.is_file():
            self.skipTest("harness-init is not present")
        standalone = self.tmp / "standalone-kit"
        shutil.copytree(KIT, standalone, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        target = init_target(self.tmp / "standalone-target")
        proc = run(
            [sys.executable, str(standalone / "scripts" / "harness-init"),
             "--profile", "minimal", "--target", str(target), "--name", "Standalone"],
            cwd=self.tmp,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("post-init check: PASS", proc.stdout)

    def test_test_command_inference(self) -> None:
        """--language inference: node scripts.test / node --test / swift Package.swift / xcodeproj."""
        if not INIT.is_file():
            self.skipTest("harness-init is not present")
        cases = []
        node_with_script = self.tmp / "node-with-script"
        node_with_script.mkdir()
        (node_with_script / "package.json").write_text(
            json.dumps({"name": "x", "scripts": {"test": "node --test"}}), encoding="utf-8"
        )
        cases.append((node_with_script, "node", "test=npm test", "scripts.test"))
        node_no_script = self.tmp / "node-no-script"
        node_no_script.mkdir()
        (node_no_script / "package.json").write_text(json.dumps({"name": "x"}), encoding="utf-8")
        cases.append((node_no_script, "node", "test=node --test", "no scripts.test"))
        swift_pkg = self.tmp / "swift-pkg"
        swift_pkg.mkdir()
        (swift_pkg / "Package.swift").write_text("// swift-tools-version:5.9\n", encoding="utf-8")
        cases.append((swift_pkg, "swift", "test=swift test", "Package.swift"))
        xcode = self.tmp / "xcode-app"
        xcode.mkdir()
        (xcode / "App.xcodeproj").mkdir()
        (xcode / "App.xcodeproj" / "project.pbxproj").write_text("// stub\n", encoding="utf-8")
        cases.append((xcode, "swift", "test=xcodebuild test", "cannot infer the scheme"))
        for target, language, expected, note in cases:
            with self.subTest(case=target.name):
                proc = self.invoke(
                    "--profile", "minimal", "--language", language, "--dry-run", target=target
                )
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                self.assertIn(expected, proc.stdout)
                self.assertIn(note, proc.stdout)

    def test_android_gradle_detection(self) -> None:
        """--language auto: settings.gradle(.kts)/build.gradle(.kts) → android, checked before python."""
        if not INIT.is_file():
            self.skipTest("harness-init is not present")
        for filename in ("settings.gradle", "settings.gradle.kts", "build.gradle", "build.gradle.kts"):
            with self.subTest(entry=filename):
                target = self.tmp / f"android-{filename.replace('.', '-')}"
                target.mkdir()
                (target / filename).write_text("rootProject.name = 'demo'\n", encoding="utf-8")
                # mixed repo: a python helper must not win over the Gradle build
                (target / "helper.py").write_text("print('x')\n", encoding="utf-8")
                proc = self.invoke("--profile", "minimal", "--dry-run", target=target)
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                output = proc.stdout
                self.assertIn("language=android", output)
                self.assertIn("test=./gradlew testDebugUnitTest", output)
                self.assertIn("Gradle project detected", output)
                self.assertIn("JDK 17-21", output)
                self.assertIn("--test-command", output)
                self.assertIn("does not run or parse test output", output)

        # explicit --language android must be accepted even without Gradle files
        explicit = self.tmp / "android-explicit"
        explicit.mkdir()
        proc = self.invoke(
            "--profile", "minimal", "--language", "android", "--dry-run", target=explicit
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("language=android", proc.stdout)
        self.assertIn("test=./gradlew testDebugUnitTest", proc.stdout)

    def test_gitignore_is_language_specific_and_deduped(self) -> None:
        """K11：只追加与语言相关的条目，且不重复项目已有的行。"""
        if not INIT.is_file():
            self.skipTest("harness-init is not present")
        cases = {
            "node": (("node_modules/", "__pycache__/"), (".swiftpm/", ".pytest_cache/")),
            "python": (("__pycache__/", ".pytest_cache/", ".venv/"), ("node_modules/", ".build/")),
            "swift": ((".build/", ".swiftpm/", "__pycache__/"), ("node_modules/", ".pytest_cache/")),
        }
        for language, (expected, absent) in cases.items():
            with self.subTest(language=language):
                target = init_target(self.tmp / f"ignore-{language}")
                if language == "node":  # 已有行必须去重，不能重复追加
                    (target / ".gitignore").write_text("node_modules/\n", encoding="utf-8")
                proc = self.invoke(
                    "--profile", "minimal", "--name", "Ignore", "--language", language,
                    "--test-command", "echo ok", target=target,
                )
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                gitignore = (target / ".gitignore").read_text(encoding="utf-8")
                for entry in expected:
                    self.assertIn(entry, gitignore)
                for entry in absent:
                    self.assertNotIn(entry, gitignore)
                if language == "node":
                    self.assertEqual(1, gitignore.count("node_modules/"), gitignore)

    def test_json_is_escaped_and_validated(self) -> None:
        """K01：含双引号/反斜杠的测试命令必须渲染成合法 JSON（并在 init 阶段校验）。"""
        if not INIT.is_file():
            self.skipTest("harness-init is not present")
        command = 'pnpm exec tsx --test "src/**/*.test.ts" --import \'./setup.ts\''
        target = init_target(self.tmp / "json-escape")
        proc = self.invoke(
            "--profile", "minimal", "--name", "Quote", "--language", "node",
            "--test-command", command, "--no-check", target=target,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        config_path = target / "harness" / "config.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        self.assertEqual(command, config["commands"]["test"])
        self.assertIn('\\"src/**/*.test.ts\\"', config_path.read_text(encoding="utf-8"))

    def test_default_branch_and_hooks_flags(self) -> None:
        """K05/K10：--default-branch 写进 CI/manifest；--install-hooks 真正设置 core.hooksPath。"""
        if not INIT.is_file():
            self.skipTest("harness-init is not present")
        target = init_target(self.tmp / "branch-hooks")
        proc = self.invoke(
            "--profile", "standard", "--name", "Branch", "--default-branch", "develop",
            "--install-hooks", "--no-check", target=target,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        workflow = (target / ".github" / "workflows" / "verify.yml").read_text(encoding="utf-8")
        self.assertIn("- develop", workflow)
        self.assertIn("pull_request:", workflow)
        manifest = json.loads((target / ".harness-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual("develop", manifest["options"]["branch"])
        self.assertEqual("--default-branch", manifest["options"]["branchSource"])
        hooks = run(["git", "config", "--get", "core.hooksPath"], cwd=target)
        self.assertEqual(".githooks", hooks.stdout.strip())

    def test_agents_mode_move_preserves_history_and_registers_docs(self) -> None:
        """K03：存量 AGENTS.md 用 --agents-mode move 迁移，保留 git 历史并登记索引。"""
        if not INIT.is_file():
            self.skipTest("harness-init is not present")
        target = init_target(self.tmp / "agents-move")
        legacy = "# Legacy rules\n\n- 存量规则一\n"
        (target / "AGENTS.md").write_text(legacy, encoding="utf-8")
        run(["git", "add", "-A"], cwd=target)
        run(["git", "commit", "-q", "-m", "legacy agents"], cwd=target)
        proc = self.invoke(
            "--profile", "minimal", "--name", "Legacy", "--agents-mode", "move", "--no-check",
            target=target,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        moved = target / "docs" / "legacy-agents.md"
        self.assertTrue(moved.is_file())
        self.assertEqual(legacy, moved.read_text(encoding="utf-8"))
        self.assertIn("# AGENTS.md · Legacy", (target / "AGENTS.md").read_text(encoding="utf-8"))
        config = json.loads((target / "harness" / "config.json").read_text(encoding="utf-8"))
        self.assertIn("docs/legacy-agents.md", config["docs"]["publicWhitelist"])
        index = (target / "docs" / "README.md").read_text(encoding="utf-8")
        self.assertIn("legacy-agents.md", index)
        status = run(["git", "status", "--porcelain"], cwd=target).stdout
        self.assertIn("R  AGENTS.md -> docs/legacy-agents.md", status)

    def test_agents_mode_keep_leaves_existing_agents_untouched(self) -> None:
        """K03：keep 模式不覆盖现有 AGENTS.md，并在 manifest.skipped 记录。"""
        if not INIT.is_file():
            self.skipTest("harness-init is not present")
        target = init_target(self.tmp / "agents-keep")
        keep = "# Keep me\n"
        (target / "AGENTS.md").write_text(keep, encoding="utf-8")
        run(["git", "add", "-A"], cwd=target)
        run(["git", "commit", "-q", "-m", "agents"], cwd=target)
        proc = self.invoke(
            "--profile", "minimal", "--name", "Keep", "--agents-mode", "keep", "--no-check",
            target=target,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("KEEP    AGENTS.md", proc.stdout)
        self.assertEqual(keep, (target / "AGENTS.md").read_text(encoding="utf-8"))
        manifest = json.loads((target / ".harness-manifest.json").read_text(encoding="utf-8"))
        self.assertIn("AGENTS.md", manifest["skipped"])

    def test_agents_mode_move_conflict_aborts_before_moving(self) -> None:
        """半改造防护：其他文件冲突时必须在移动 AGENTS.md 之前失败。"""
        if not INIT.is_file():
            self.skipTest("harness-init is not present")
        target = init_target(self.tmp / "agents-conflict")
        (target / "AGENTS.md").write_text("# Legacy\n", encoding="utf-8")
        (target / "docs").mkdir()
        (target / "docs" / "README.md").write_text("# Host docs index\n", encoding="utf-8")
        run(["git", "add", "-A"], cwd=target)
        run(["git", "commit", "-q", "-m", "legacy"], cwd=target)
        proc = self.invoke(
            "--profile", "minimal", "--name", "Conflict", "--agents-mode", "move", "--no-check",
            target=target,
        )
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("CONFLICT docs/README.md", proc.stdout)
        self.assertTrue((target / "AGENTS.md").is_file())
        self.assertFalse((target / "docs" / "legacy-agents.md").exists())

    def test_verify_static_prints_claim_hint_and_verify_all_exists(self) -> None:
        """K08：verify-static 必须显式说明未跑证据判定；verify-all = static + claim。"""
        if not INIT.is_file():
            self.skipTest("harness-init is not present")
        target = init_target(self.tmp / "claim-hint")
        proc = self.invoke(
            "--profile", "standard", "--name", "Claim", "--test-command", "echo ok", "--no-check",
            target=target,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        static = run(["make", "verify-static"], cwd=target)
        self.assertEqual(static.returncode, 0, static.stdout + static.stderr)
        self.assertIn("verify-static 不含证据三值判定", static.stdout)
        self.assertIn("make verify-all", static.stdout)
        all_claims = run(["make", "verify-all"], cwd=target)
        self.assertNotEqual(all_claims.returncode, 0, "fresh init 没有证据，verify-all 必须红")

    def test_standard_evidence_lifecycle(self) -> None:
        """standard/strict 的「测试 → 证据 → 三值判定」链路必须端到端可用。"""
        if not INIT.is_file():
            self.skipTest("harness-init is not present")
        target = init_target(self.tmp / "evidence")
        proc = self.invoke(
            "--profile", "standard", "--name", "Evidence Demo", "--test-command", "echo ok",
            target=target,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        for cmd in (["git", "add", "-A"], ["git", "commit", "-q", "-m", "harness scaffold"]):
            done = run(cmd, cwd=target)
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        (target / "harness" / "runs").mkdir(parents=True, exist_ok=True)
        (target / "harness" / "runs" / "junit.xml").write_text(
            '<testsuite name="s" tests="1"><testcase classname="t" name="ok"/></testsuite>',
            encoding="utf-8",
        )
        draft = {
            "schemaVersion": 1,
            "claim": "tests-pass",
            "command": "echo ok",
            "environment": {"project": "Evidence Demo", "toolchain": "python", "os": "test"},
            "result": {"status": "SUCCEEDED", "passed": 1, "failed": 0, "skipped": 0, "durationSec": 0.1, "artifacts": ["harness/runs/junit.xml"]},
            "verdict": "PASS",
            "verifier": "kit-test",
        }
        draft_path = self.tmp / "draft.json"
        draft_path.write_text(json.dumps(draft), encoding="utf-8")
        write = run([sys.executable, "tools/evidence.py", "write", "--from-json", str(draft_path)], cwd=target)
        self.assertEqual(write.returncode, 0, write.stdout + write.stderr)
        # v0.4.0：证据与 artifact 必须被 git 跟踪，verify_claim 才可复核；提交后再写 docs-pass 证据。
        for cmd in (["git", "add", "-A"], ["git", "add", "-f", "harness/runs/junit.xml"],
                    ["git", "commit", "-q", "-m", "test evidence"]):
            done = run(cmd, cwd=target)
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        docs_draft = {
            "schemaVersion": 1,
            "claim": "docs-pass",
            "command": "python3 tools/check_docs.py",
            "environment": {"project": "Evidence Demo", "toolchain": "python", "os": "test"},
            "result": {"status": "SUCCEEDED", "passed": 0, "failed": 0, "skipped": 0, "durationSec": 0.0},
            "verdict": "PASS",
            "verifier": "kit-test",
        }
        docs_path = self.tmp / "docs-draft.json"
        docs_path.write_text(json.dumps(docs_draft), encoding="utf-8")
        docs_write = run([sys.executable, "tools/evidence.py", "write", "--from-json", str(docs_path)], cwd=target)
        self.assertEqual(docs_write.returncode, 0, docs_write.stdout + docs_write.stderr)
        for cmd in (["git", "add", "-A"], ["git", "commit", "-q", "-m", "docs evidence"]):
            done = run(cmd, cwd=target)
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        claim = run([sys.executable, "tools/verify_claim.py", "--all"], cwd=target)
        self.assertEqual(claim.returncode, 0, claim.stdout + claim.stderr)
        self.assertRegex(claim.stdout, r"CLAIM .*: PASS — ")

    def test_strict_release_check_after_evidence(self) -> None:
        if not INIT.is_file():
            self.skipTest("harness-init is not present")
        target = init_target(self.tmp / "release")
        proc = self.invoke(
            "--profile", "strict", "--name", "Release Demo", "--test-command", "echo ok",
            target=target,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        for cmd in (["git", "add", "-A"], ["git", "commit", "-q", "-m", "harness scaffold"]):
            done = run(cmd, cwd=target)
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        (target / "harness" / "runs").mkdir(parents=True, exist_ok=True)
        (target / "harness" / "runs" / "junit.xml").write_text(
            '<testsuite name="s" tests="1"><testcase classname="t" name="ok"/></testsuite>',
            encoding="utf-8",
        )
        draft = {
            "schemaVersion": 1,
            "claim": "tests-pass",
            "command": "echo ok",
            "environment": {"project": "Release Demo", "toolchain": "python", "os": "test"},
            "result": {"status": "SUCCEEDED", "passed": 1, "failed": 0, "skipped": 0, "durationSec": 0.1, "artifacts": ["harness/runs/junit.xml"]},
            "verdict": "PASS",
            "verifier": "kit-test",
        }
        draft_path = self.tmp / "draft.json"
        draft_path.write_text(json.dumps(draft), encoding="utf-8")
        write = run([sys.executable, "tools/evidence.py", "write", "--from-json", str(draft_path)], cwd=target)
        self.assertEqual(write.returncode, 0, write.stdout + write.stderr)
        for cmd in (["git", "add", "-A"], ["git", "add", "-f", "harness/runs/junit.xml"],
                    ["git", "commit", "-q", "-m", "test evidence"]):
            done = run(cmd, cwd=target)
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        docs_draft = {
            "schemaVersion": 1,
            "claim": "docs-pass",
            "command": "python3 tools/check_docs.py",
            "environment": {"project": "Release Demo", "toolchain": "python", "os": "test"},
            "result": {"status": "SUCCEEDED", "passed": 0, "failed": 0, "skipped": 0, "durationSec": 0.0},
            "verdict": "PASS",
            "verifier": "kit-test",
        }
        docs_path = self.tmp / "docs-draft.json"
        docs_path.write_text(json.dumps(docs_draft), encoding="utf-8")
        docs_write = run([sys.executable, "tools/evidence.py", "write", "--from-json", str(docs_path)], cwd=target)
        self.assertEqual(docs_write.returncode, 0, docs_write.stdout + docs_write.stderr)
        for cmd in (["git", "add", "-A"], ["git", "commit", "-q", "-m", "docs evidence"]):
            done = run(cmd, cwd=target)
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        scorecard = run(["make", "scorecard"], cwd=target)
        self.assertEqual(scorecard.returncode, 0, scorecard.stdout + scorecard.stderr)
        release = run(["make", "release-check"], cwd=target)
        self.assertEqual(release.returncode, 0, release.stdout + release.stderr)

    def test_dry_run_writes_nothing(self) -> None:
        if not INIT.is_file():
            self.skipTest("harness-init is not present")
        target = init_target(self.tmp / "dry")
        before = sorted(p.relative_to(target).as_posix() for p in tree_files(target))
        proc = self.invoke("--profile", "minimal", "--dry-run", target=target)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("dry-run", proc.stdout)
        after = sorted(p.relative_to(target).as_posix() for p in tree_files(target))
        self.assertEqual(before, after)

    def test_conflict_refused_and_force_backs_up(self) -> None:
        if not INIT.is_file():
            self.skipTest("harness-init is not present")
        target = init_target(self.tmp / "conflict")
        first = self.invoke("--profile", "minimal", "--name", "X", "--test-command", "echo ok", target=target)
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        second = self.invoke("--profile", "minimal", "--name", "X", target=target)
        self.assertEqual(second.returncode, 1, second.stdout + second.stderr)
        self.assertIn("CONFLICT", second.stdout + second.stderr)
        agents = target / "AGENTS.md"
        agents.write_text("# locally edited\n", encoding="utf-8")
        forced = self.invoke(
            "--profile", "minimal", "--name", "X", "--test-command", "echo ok", "--force", "--no-check",
            target=target,
        )
        self.assertEqual(forced.returncode, 0, forced.stdout + forced.stderr)
        backup_root = target / ".harness-init-backup"
        self.assertTrue(backup_root.is_dir(), "backup directory missing")
        backups = list(backup_root.rglob("AGENTS.md"))
        self.assertTrue(backups, "AGENTS.md backup missing")
        self.assertEqual(backups[0].read_text(encoding="utf-8"), "# locally edited\n")
        self.assertNotEqual(agents.read_text(encoding="utf-8"), "# locally edited\n")

    def test_gitattributes_export_ignore_adapter(self) -> None:
        if not INIT.is_file():
            self.skipTest("harness-init is not present")
        target = init_target(self.tmp / "gitattributes")
        args = (
            "--profile", "standard", "--name", "Test Project", "--test-command", "echo ok",
            "--adapters", "gitattributes",
        )
        proc = self.invoke(*args, target=target)
        self.assertEqual(proc.returncode, 0, f"init failed:\n{proc.stdout}\n{proc.stderr}")
        attrs = target / ".gitattributes"
        self.assertTrue(attrs.is_file(), "gitattributes adapter did not create .gitattributes")
        text = attrs.read_text(encoding="utf-8")
        for marker in ("/harness/ export-ignore", "/tools/ export-ignore", "HARNESS.md", "harness-kit"):
            self.assertIn(marker, text)
        manifest = json.loads((target / ".harness-manifest.json").read_text(encoding="utf-8"))
        self.assertIn(".gitattributes", [item["path"] for item in manifest.get("appends") or []])
        # append 幂等：重复 init（--force）不得重复写入块
        again = self.invoke(*args, "--force", target=target)
        self.assertEqual(again.returncode, 0, f"re-init failed:\n{again.stdout}\n{again.stderr}")
        self.assertEqual(1, attrs.read_text(encoding="utf-8").count("/harness/ export-ignore"))
        # git archive 实际排除（GitHub Source zip 遵循同一机制）
        self.assertEqual(0, run(["git", "add", "-A"], cwd=target).returncode)
        commit = run(["git", "commit", "-m", "adopt with export-ignore"], cwd=target)
        self.assertEqual(commit.returncode, 0, commit.stdout + commit.stderr)
        archive = subprocess.run(["git", "archive", "HEAD"], cwd=str(target), capture_output=True)
        self.assertEqual(archive.returncode, 0, archive.stderr.decode("utf-8", "replace"))
        with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as tar:
            names = set(tar.getnames())
        self.assertEqual(set(), {name for name in names if name.startswith(("harness/", "tools/"))})
        self.assertNotIn("HARNESS.md", names)
        self.assertIn("AGENTS.md", names)
        self.assertIn(".gitattributes", names)

    def test_existing_makefile_gets_fragment(self) -> None:
        if not INIT.is_file():
            self.skipTest("harness-init is not present")
        target = init_target(self.tmp / "makefile")
        original = "all:\n\t@echo original\n"
        (target / "Makefile").write_text(original, encoding="utf-8")
        proc = self.invoke("--profile", "minimal", "--name", "X", "--test-command", "echo ok", target=target)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual((target / "Makefile").read_text(encoding="utf-8"), original)
        self.assertTrue((target / "Makefile.harness").is_file())
        self.assertIn("include Makefile.harness", proc.stdout)
        check = run(["make", "-f", "Makefile.harness", "check"], cwd=target)
        self.assertEqual(check.returncode, 0, check.stdout + check.stderr)

    def test_unknown_profile_fails(self) -> None:
        target = init_target(self.tmp / "bad")
        proc = self.invoke("--profile", "does-not-exist", target=target)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("ERROR", proc.stderr)


if __name__ == "__main__":
    unittest.main()
