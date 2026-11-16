#!/usr/bin/env python3
"""环境自检（doctor）：python3 / git 仓库 / 配置中的测试命令 / 可选适配器。

用法：
    python3 tools/doctor.py [--root PATH] [--agent]

根目录默认「本脚本上级目录」（脚本位于目标项目 `tools/` 下）；`--root` 可覆盖。
配置唯一来源：`<root>/harness/config.json`。配置缺失/字段缺失时 doctor **降级继续**
（WARN + 建议行），其余脚本要求配置齐全（exit 1）。

每项输出 OK / WARN / FAIL / SKIP；失败/降级项在报告末尾给出固定建议行：
    [必需|可选] <检查项>：→ 影响：…；如何补：…

退出码（契约）：
    2 = 缺 python3 或 git 仓库（动态验证不可用）
    0 = 其余情况（含配置缺失的降级 WARN）

仅标准库；不联网、不写文件、不运行测试命令。
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

CONFIG_REL = Path("harness") / "config.json"
OK, WARN, FAIL, SKIP = "OK", "WARN", "FAIL", "SKIP"


@dataclass(frozen=True)
class Suggestion:
    """WARN/FAIL 项建议：必需性 + 影响 + 如何补。"""

    required: bool
    impact: str
    fix: str

    @property
    def label(self) -> str:
        return "必需" if self.required else "可选"

    def render(self) -> str:
        return f"→ 影响：{self.impact}；如何补：{self.fix}"


SUGGESTIONS: dict[str, Suggestion] = {
    "python3": Suggestion(
        required=True,
        impact="所有 Python 门禁脚本不可执行，动态验证不可用",
        fix="安装 Python 3 并确保 `python3` 在 PATH（重新打开终端后重跑 make doctor）",
    ),
    "git 仓库": Suggestion(
        required=True,
        impact="计划状态、证据与所有 git 相关门禁不可用（verify-static / 计划检查会失败）",
        fix="在项目根初始化 git（git init）或重新 clone 仓库后重跑 make doctor",
    ),
    "config": Suggestion(
        required=True,
        impact="其他 harness 脚本无法运行（配置是唯一读取源）；doctor 自身降级继续",
        fix="按 harness/config.json 模板补齐配置（可重跑 harness-init 或手动创建）",
    ),
    "测试命令": Suggestion(
        required=False,
        impact="本机无法直接运行配置的测试命令，测试结论仍为“未验证”",
        fix="安装命令依赖的工具，或修改 config.commands.test 指向本机可用的测试入口",
    ),
    "adapters": Suggestion(
        required=False,
        impact="适配器同步/检查不可用（仅可选集成能力受影响，不阻断静态门禁）",
        fix="按 kit 的 adapters 说明补齐目录或删除 config.adapters 中的对应条目",
    ),
}

FALLBACK_FAIL = Suggestion(
    required=True,
    impact="该必需检查项失败会阻断对应的门禁/验证链路（详见上方 detail 行）",
    fix="按上方 detail 修复后重跑 make doctor",
)
FALLBACK_WARN = Suggestion(
    required=False,
    impact="该可选检查项缺失只影响对应增强能力，不阻断静态门禁（详见上方 detail 行）",
    fix="按上方 detail 修复或忽略",
)


def suggestion_for(name: str, level: str) -> Suggestion | None:
    suggestion = SUGGESTIONS.get(name)
    if suggestion is not None:
        return suggestion
    if level == FAIL:
        return FALLBACK_FAIL
    if level == WARN:
        return FALLBACK_WARN
    return None


class Report:
    def __init__(self) -> None:
        self.rows: list[tuple[str, str, str]] = []

    def add(self, level: str, name: str, detail: str) -> None:
        self.rows.append((level, name, detail))

    def counts(self) -> dict[str, int]:
        result = {OK: 0, WARN: 0, FAIL: 0, SKIP: 0}
        for level, _, _ in self.rows:
            result[level] = result.get(level, 0) + 1
        return result

    def suggestions(self, context: Mapping[str, str] | None = None) -> list[str]:
        lines: list[str] = []
        seen: set[str] = set()
        for level, name, _ in self.rows:
            if level not in (WARN, FAIL) or name in seen:
                continue
            suggestion = suggestion_for(name, level)
            if suggestion is None:
                continue
            seen.add(name)
            lines.append(f"  [{suggestion.label}] {name}：{suggestion.render()}")
        return lines

    def render(self, context: Mapping[str, str] | None = None) -> str:
        width = max((len(name) for _, name, _ in self.rows), default=10)
        lines = [
            f"[{level}] {name.ljust(width)}  {detail}" for level, name, detail in self.rows
        ]
        counts = self.counts()
        lines.append("")
        lines.append(
            "统计："
            + " / ".join(f"{key} {counts.get(key, 0)}" for key in (OK, WARN, FAIL, SKIP))
        )
        suggestions = self.suggestions(context)
        if suggestions:
            lines.append("")
            lines.append("建议（缺失/降级项：影响与修复方式）：")
            lines.extend(suggestions)
        return "\n".join(lines)


def run(cmd: list[str], timeout: int = 15) -> tuple[int, str, str]:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except FileNotFoundError:
        return 127, "", "命令不存在"
    except subprocess.TimeoutExpired:
        return 124, "", f"超时（{timeout}s）"
    except OSError as exc:  # pragma: no cover - 极端环境
        return 126, "", str(exc)


def load_config(root: Path) -> tuple[dict | None, str]:
    """返回 (config, 错误说明)；错误说明为空表示成功。"""
    path = root / CONFIG_REL
    if not path.is_file():
        return None, f"缺少配置文件 {CONFIG_REL.as_posix()}"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, f"{CONFIG_REL.as_posix()} 不是合法 JSON：{exc}"
    if not isinstance(data, dict):
        return None, f"{CONFIG_REL.as_posix()} 顶层必须是 JSON 对象"
    return data, ""


def program_from_command(command: object) -> str:
    """取配置命令的首个可执行程序名（引号/参数安全解析）。"""
    if not isinstance(command, str) or not command.strip():
        return ""
    try:
        parts = shlex.split(command)
    except ValueError:
        return ""
    return parts[0] if parts else ""


def agent_probe(root: Path) -> list[str]:
    """Read-only capability probe for the current AI coding Agent (env/CLI/skill roots)."""
    rows: list[str] = []
    env = os.environ
    hints: list[str] = []
    if env.get("CLAUDECODE") or env.get("CLAUDE_CODE_ENTRYPOINT"):
        hints.append("claude-code（环境变量）")
    if any(key.startswith("DSH_") for key in env):
        hints.append("deepseek-harness（DSH_* 环境变量）")
    if any(key.startswith("CODEX_") for key in env):
        hints.append("codex（CODEX_* 环境变量）")
    if any(key.startswith("CURSOR_") for key in env):
        hints.append("cursor（CURSOR_* 环境变量）")
    rows.append("agent: " + ("、".join(hints) if hints else "未识别（按 AGENTS.md 通用流程执行）"))
    clis = [name for name in ("claude", "dsh", "codex", "cursor-agent") if shutil.which(name)]
    rows.append("可用 CLI: " + ("、".join(f"{name}={shutil.which(name)}" for name in clis) if clis else "无"))
    models = [f"{key}={env[key]}" for key in ("ANTHROPIC_MODEL", "CLAUDE_MODEL", "DEEPSEEK_MODEL", "DSH_MODEL") if env.get(key)]
    rows.append("模型（env）: " + ("、".join(models) if models else "未从环境变量识别"))
    roots = [".dsh/skills", ".claude/skills"]
    present = [name for name in roots if (root / name).is_dir()]
    harness_skills = [name for name in roots if (root / name / "harness" / "SKILL.md").is_file()]
    rows.append("skill 根: " + ("、".join(present) if present else "无") +
                (f"；harness skill 已安装：{'、'.join(harness_skills)}" if harness_skills else "；harness skill 未安装（可选）"))
    manifest = root / ".harness-manifest.json"
    if manifest.is_file():
        try:
            rows.append("manifest: " + json.loads(manifest.read_text(encoding="utf-8")).get("kitVersion", "?"))
        except (OSError, json.JSONDecodeError):
            rows.append("manifest: 无法解析")
    else:
        rows.append("manifest: 无（v0.2.13 之前接入）")
    rows.append("提示: 本探测只读；不安装插件、不调用 Agent。")
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="环境自检（doctor）：python3 / git / 测试命令 / 适配器")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="目标项目根（默认脚本上级目录）",
    )
    parser.add_argument("--agent", action="store_true", help="额外输出 Agent 能力探测（只读；环境变量/CLI/skill 根）")
    args = parser.parse_args(argv)
    root = args.root.expanduser().resolve()
    report = Report()

    python_path = shutil.which("python3")
    python_ok = bool(python_path)
    if python_ok:
        report.add(OK, "python3", f"{sys.version.split()[0]}（{python_path}）")
    else:
        report.add(FAIL, "python3", "PATH 中找不到 python3")

    code, out, err = run(["git", "-C", str(root), "rev-parse", "--is-inside-work-tree"])
    git_ok = code == 0 and out.strip() == "true"
    if git_ok:
        _, branch, _ = run(["git", "-C", str(root), "rev-parse", "--abbrev-ref", "HEAD"])
        _, commit, _ = run(["git", "-C", str(root), "rev-parse", "--short", "HEAD"])
        parts = []
        branch_name = branch.strip()
        if branch_name and branch_name != "HEAD":
            parts.append(f"branch={branch_name}")
        if commit.strip():
            parts.append(f"HEAD={commit.strip()}")
        report.add(OK, "git 仓库", "，".join(parts) or "仓库可用（尚无提交或游离 HEAD）")
    else:
        message = err.splitlines()[0].strip() if err.strip() else f"exit {code}"
        report.add(FAIL, "git 仓库", f"不是 git 仓库或 git 不可用：{message}")

    config, config_error = load_config(root)
    if config is None:
        report.add(WARN, "config", f"{config_error}（doctor 降级：跳过测试命令/适配器检查）")
    else:
        version = config.get("kitVersion", "未知")
        report.add(OK, "config", f"{CONFIG_REL.as_posix()}（kitVersion={version}）")

        commands = config.get("commands")
        test_command = commands.get("test") if isinstance(commands, dict) else None
        program = program_from_command(test_command)
        if not program:
            report.add(WARN, "测试命令", "config.commands.test 缺失或无法解析")
        else:
            resolved = shutil.which(program)
            if resolved:
                report.add(OK, "测试命令", f"{program}（{resolved}）← {test_command}")
            else:
                report.add(
                    WARN,
                    "测试命令",
                    f"首个程序不在 PATH：{program}（config.commands.test={test_command!r}）",
                )

        adapters = config.get("adapters")
        if adapters is None or adapters == {}:
            report.add(SKIP, "adapters", "未配置 adapters（可选集成，跳过）")
        elif not isinstance(adapters, dict):
            report.add(WARN, "adapters", "config.adapters 必须是对象")
        else:
            problems: list[str] = []
            for name, spec in sorted(adapters.items()):
                if not isinstance(spec, dict):
                    problems.append(f"{name} 配置必须是对象")
                    continue
                source = spec.get("skillsSource")
                if source is None:
                    continue
                if not isinstance(source, str) or not source.strip():
                    problems.append(f"{name}.skillsSource 必须是非空字符串")
                elif not (root / source).is_dir():
                    problems.append(f"{name}.skillsSource 目录不存在：{source}")
            if problems:
                for problem in problems:
                    report.add(WARN, "adapters", problem)
            else:
                report.add(OK, "adapters", f"{len(adapters)} 项配置，来源目录可用")

    print("环境自检（doctor）")
    print(f"项目根：{root}")
    print(report.render())
    if args.agent:
        print()
        print("Agent 能力探测（--agent，只读）")
        for row in agent_probe(root):
            print(f"  {row}")
    print()
    code = 2 if (not python_ok or not git_ok) else 0
    if code == 2:
        missing = []
        if not python_ok:
            missing.append("python3")
        if not git_ok:
            missing.append("git 仓库")
        print(f"[FAIL] 环境自检未通过：缺少必需项（{'、'.join(missing)}）→ 动态验证不可用（exit 2）")
        return code
    if config is None:
        print("[WARN] 环境自检降级通过：python3/git 可用，但配置缺失（修好配置后重跑；exit 0）")
    else:
        print("[OK] 环境自检通过（完整工具链可用；本命令不运行测试命令）")
    return code


if __name__ == "__main__":
    sys.exit(main())
