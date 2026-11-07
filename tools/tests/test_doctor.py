#!/usr/bin/env python3
"""`tools/doctor.py` 报告 / 建议 / 退出码回归测试（unittest，仅标准库，不依赖真实 Xcode）。

覆盖：
  1) 全 OK → 不输出「建议」区；
  2) 每个 FAIL/WARN/显式 SKIP 项的建议行固定格式 `→ 影响：…；如何补：…` + 「必需/可选」；
  3) 五个关键检查项的文案要点（xcodebuild / simctl runtime / mobilebuildmcp / TEAM_RULES / git 仓库）；
  4) 未知项通用兜底、OK 行不产生建议、同名校验只列一次；
  5) render 输出顺序稳定（建议在统计之后）与 exit_code 语义（0 / 2）不变；
  6) main() 用 mock 模拟真实缺失场景 → exit 2，可选缺失 → exit 0 仍带建议。

运行：python3 -m unittest tools.tests.test_doctor -v
"""
from __future__ import annotations

import contextlib
import io
import sys
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools import doctor  # noqa: E402

KEY_CHECKS = (
    ("xcodebuild", doctor.FAIL, "[必需]"),
    ("simctl runtime", doctor.WARN, "[必需]"),  # 任务口径：runtime 缺失阻断动态验证
    ("mobilebuildmcp", doctor.WARN, "[可选]"),
    ("TEAM_RULES", doctor.SKIP, "[可选]"),
    ("git 仓库", doctor.FAIL, "[必需]"),
)


class SuggestionMappingTests(unittest.TestCase):
    """建议映射：影响/如何补/必需·可选，缺一不可。"""

    def test_every_key_check_has_fixed_suggestion_format(self):
        for name, level, label in KEY_CHECKS:
            with self.subTest(name=name):
                report = doctor.Report()
                report.add(level, name, "模拟缺失")
                lines = report.suggestions({"sim_os": "26.4.1"})
                self.assertEqual(len(lines), 1)
                line = lines[0]
                self.assertTrue(line.startswith(f"  {label} {name}："), line)
                self.assertIn("→ 影响：", line)
                self.assertIn("；如何补：", line)
                # 影响与如何补都必须有实际内容（不是空模板）
                impact = line.split("→ 影响：", 1)[1].split("；如何补：", 1)[0]
                fix = line.split("；如何补：", 1)[1].split("；替代：", 1)[0]
                self.assertGreaterEqual(len(impact), 8)
                self.assertGreaterEqual(len(fix), 8)

    def test_xcodebuild_required_with_xcode_select_and_static_alternative(self):
        line = self._single_suggestion(doctor.FAIL, "xcodebuild")
        self.assertIn("[必需]", line)
        self.assertIn("动态验证不可执行", line)
        self.assertIn("xcode-select", line)
        self.assertIn("make verify-static", line)

    def test_simctl_runtime_required_formats_sim_os_and_download_hint(self):
        line = self._single_suggestion(doctor.WARN, "simctl runtime", {"sim_os": "26.4.1"})
        self.assertIn("[必需]", line)
        self.assertIn("iOS 26.4.1", line)
        self.assertIn("xcodebuild -downloadPlatform iOS", line)
        self.assertIn("SIM_OS=", line)
        self.assertIn("make verify-static", line)

    def test_mobilebuildmcp_optional_points_to_docs_and_static_gate(self):
        line = self._single_suggestion(doctor.WARN, "mobilebuildmcp")
        self.assertIn("[可选]", line)
        self.assertIn("CONTRIBUTING.md", line)
        self.assertIn("references/verification.md", line)
        self.assertIn("静态门禁", line)

    def test_team_rules_missing_is_optional_and_actionable(self):
        line = self._single_suggestion(doctor.SKIP, "TEAM_RULES")
        self.assertIn("[可选]", line)
        self.assertIn("TEAM_RULES=", line)

    def test_git_repo_required_with_clone_hint(self):
        line = self._single_suggestion(doctor.FAIL, "git 仓库")
        self.assertIn("[必需]", line)
        self.assertIn("clone", line)

    def test_unknown_fail_uses_generic_required_fallback(self):
        line = self._single_suggestion(doctor.FAIL, "未知检查")
        self.assertIn("未知检查", line)  # 名称保留在建议行
        self.assertIn("[必需]", line)
        self.assertIn("→ 影响：", line)
        self.assertIn("；如何补：", line)

    def test_unknown_warn_uses_generic_optional_fallback(self):
        line = self._single_suggestion(doctor.WARN, "未知检查")
        self.assertIn("[可选]", line)
        self.assertIn("make verify-static", line)

    def test_unregistered_skip_has_no_suggestion(self):
        report = doctor.Report()
        report.add(doctor.SKIP, "其他不适用项", "n/a")
        self.assertEqual(report.suggestions(), [])

    def test_all_ok_has_no_suggestion_section(self):
        report = doctor.Report()
        for name, _, _ in KEY_CHECKS:
            report.add(doctor.OK, name, "可用")
        report.add(doctor.OK, "python3", "3.14.7")
        self.assertEqual(report.suggestions(), [])
        text = report.render()
        self.assertNotIn("建议（", text)
        self.assertNotIn("→ 影响：", text)
        self.assertIn("统计：OK 6 / WARN 0 / FAIL 0 / SKIP 0", text)

    def test_ok_rows_never_generate_suggestions(self):
        report = doctor.Report()
        report.add(doctor.OK, "xcodebuild", "可用")
        report.add(doctor.FAIL, "git 仓库", "不是仓库")
        suggestion_text = "\n".join(report.suggestions())
        self.assertIn("git 仓库", suggestion_text)
        self.assertNotIn("xcodebuild", suggestion_text)

    def test_duplicate_failed_rows_render_single_suggestion(self):
        report = doctor.Report()
        report.add(doctor.FAIL, "git 仓库", "第一次")
        report.add(doctor.FAIL, "git 仓库", "第二次")
        self.assertEqual(len(report.suggestions()), 1)

    def _single_suggestion(self, level: str, name: str, context=None) -> str:
        report = doctor.Report()
        report.add(level, name, "模拟缺失")
        lines = report.suggestions(context)
        self.assertEqual(len(lines), 1, f"{name} 应有且仅有一条建议")
        return lines[0]


class RenderFormatTests(unittest.TestCase):
    """原有 OK/WARN/FAIL/SKIP 行与统计行保持稳定；建议区在统计之后。"""

    def test_rows_and_stats_format_stable(self):
        report = doctor.Report()
        report.add(doctor.OK, "python3", "3.14.7")
        report.add(doctor.WARN, "mobilebuildmcp", "不在 PATH")
        text = report.render()
        lines = text.splitlines()
        self.assertTrue(any(line.startswith("[OK] python3") for line in lines), text)
        self.assertTrue(any(line.startswith("[WARN] mobilebuildmcp") for line in lines), text)
        self.assertIn("统计：OK 1 / WARN 1 / FAIL 0 / SKIP 0", text)

    def test_suggestion_section_comes_after_stats(self):
        report = doctor.Report()
        report.add(doctor.OK, "python3", "ok")
        report.add(doctor.FAIL, "xcodebuild", "不可用")
        lines = report.render().splitlines()
        stats = next(index for index, line in enumerate(lines) if line.startswith("统计："))
        header = next(index for index, line in enumerate(lines) if line.startswith("建议（"))
        self.assertGreater(header, stats)
        self.assertTrue(lines[header + 1].startswith("  [必需] xcodebuild："), lines)

    def test_render_is_deterministic(self):
        report = doctor.Report()
        report.add(doctor.FAIL, "xcodebuild", "不可用")
        report.add(doctor.WARN, "mobilebuildmcp", "不在 PATH")
        self.assertEqual(report.render(), report.render())

    def test_exit_code_semantics_unchanged(self):
        self.assertEqual(doctor.exit_code(True, True), 0)
        self.assertEqual(doctor.exit_code(False, True), 2)
        self.assertEqual(doctor.exit_code(True, False), 2)
        self.assertEqual(doctor.exit_code(False, False), 2)


class MainExitCodeTests(unittest.TestCase):
    """main() 的退出码与建议输出（mock 掉真实命令，不依赖本机 Xcode）。"""

    def _run_main(self, *, xcode_ok=True, runtime_ok=True, mobile_ok=True, team_rules_ok=True):
        def fake_xcode(report: doctor.Report) -> bool:
            report.add(doctor.OK if xcode_ok else doctor.FAIL, "xcodebuild", "mock")
            return xcode_ok

        def fake_simctl(report: doctor.Report, sim_os: str) -> bool:
            report.add(doctor.OK if runtime_ok else doctor.WARN, "simctl runtime", f"mock SIM_OS={sim_os}")
            return runtime_ok

        def fake_mobile(report: doctor.Report) -> None:
            report.add(doctor.OK if mobile_ok else doctor.WARN, "mobilebuildmcp", "mock")

        def fake_git(report: doctor.Report) -> bool:
            report.add(doctor.OK, "git 仓库", "mock")
            return True

        def fake_team_rules(report: doctor.Report, root: Path) -> None:
            report.add(doctor.OK if team_rules_ok else doctor.SKIP, "TEAM_RULES", "mock")

        patches = [
            mock.patch.object(doctor, "check_xcode", fake_xcode),
            mock.patch.object(doctor, "check_simctl", fake_simctl),
            mock.patch.object(doctor, "check_mobilebuildmcp", fake_mobile),
            mock.patch.object(doctor, "check_python", lambda report: report.add(doctor.OK, "python3", "mock")),
            mock.patch.object(doctor, "check_git", fake_git),
            mock.patch.object(doctor, "check_team_rules", fake_team_rules),
            mock.patch.object(doctor, "check_git_status", lambda report: report.add(doctor.OK, "git status", "clean")),
        ]
        for patch in patches:
            patch.start()
        try:
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                code = doctor.main([])
        finally:
            for patch in reversed(patches):
                patch.stop()
        return code, buffer.getvalue()

    def test_missing_xcode_returns_2_with_required_suggestion(self):
        code, output = self._run_main(xcode_ok=False)
        self.assertEqual(code, 2)
        self.assertIn("结论：动态验证不可执行", output)
        self.assertIn("[必需] xcodebuild：", output)
        self.assertIn("→ 影响：", output)

    def test_missing_runtime_returns_2_with_required_suggestion(self):
        code, output = self._run_main(runtime_ok=False)
        self.assertEqual(code, 2)
        self.assertIn("[必需] simctl runtime：", output)
        self.assertIn("如何补：", output)

    def test_ready_environment_returns_0_without_suggestions(self):
        code, output = self._run_main()
        self.assertEqual(code, 0)
        self.assertNotIn("建议（", output)
        self.assertNotIn("→ 影响：", output)
        self.assertIn("结论：动态验证环境就绪", output)

    def test_optional_missing_returns_0_but_prints_suggestion(self):
        code, output = self._run_main(mobile_ok=False, team_rules_ok=False)
        self.assertEqual(code, 0)  # 可选缺失不改变退出码
        self.assertIn("[可选] mobilebuildmcp：", output)
        self.assertIn("[可选] TEAM_RULES：", output)
        self.assertIn("→ 影响：", output)


if __name__ == "__main__":
    unittest.main()
