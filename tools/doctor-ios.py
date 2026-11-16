#!/usr/bin/env python3
"""环境自检（doctor）：Xcode / 模拟器 runtime / 真机入口 / python / git / 模板仓。

用法：
  PYTHONDONTWRITEBYTECODE=1 python3 tools/doctor.py [--root <repo>]

环境变量：
  SIM_OS      期望的模拟器 runtime（默认 26.4.1，与 Makefile 一致）
  SIM_NAME    期望的模拟器设备名（默认 iPhone 17 Pro Max，仅用于展示）
  TEAM_RULES  团队规则模板仓路径（默认 ../../agent/template，相对仓库根）

每项输出 OK / WARN / FAIL / SKIP：
  OK    可用
  WARN  非阻塞缺失（例如真机入口 mobilebuildmcp 不在 PATH）
  FAIL  阻塞（例如不是 git 仓库）
  SKIP  不适用或未配置（例如没有模板仓）

建议区（Phase 3.4 新增）：
  只要出现有建议的非 OK 项，报告末尾追加「建议」区，每项固定为：
    [必需|可选] <检查项>：→ 影响：…；如何补：…[；替代：…]
  - 必需：缺失会阻断动态验证或关键门禁（xcodebuild、基线 simctl runtime、git 仓库）；
    不修复时动态验证结论只能是“未验证”。
  - 可选：只影响真机入口/团队基线等增强能力（mobilebuildmcp、TEAM_RULES、git status），
    不影响 make verify-static 静态门禁。
  - 未被专用映射覆盖的 WARN/FAIL 走通用兜底文案；显式登记过的 SKIP（目前只有 TEAM_RULES）
    按可选列出；未登记的 SKIP 视为不适用、保持安静；全部 OK 时不输出建议区。

退出码（不变）：
  0 = 静态环境就绪（可能有 WARN；本命令不运行测试/真机 → 代码行为仍为“未验证”）
  2 = 动态验证不可用（xcodebuild 或 simctl runtime 缺失）→ 代码行为结论 = “未验证”
      环境问题不等于代码问题：不要把“跑不了”写成“测试通过”。

注意：doctor 只查环境，不跑 xcodebuild 测试、不装依赖、不改任何文件。
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

OK, WARN, FAIL, SKIP = "OK", "WARN", "FAIL", "SKIP"

DEFAULT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SIM_OS = "26.4.1"
DEFAULT_SIM_NAME = "iPhone 17 Pro Max"
DEFAULT_TEAM_RULES = "../../agent/template"

ROOT = DEFAULT_ROOT


@dataclass(frozen=True)
class Suggestion:
    """缺失/降级项的修复建议：必需性 + 影响 + 如何补（可选替代方案）。

    required=True 表示「必需」：不修则动态验证不可用；False 表示「可选」：不影响静态门禁。
    impact/fix/alternative 支持 {sim_os} 占位符，由 render(context) 替换。
    """

    required: bool
    impact: str
    fix: str
    alternative: str = ""

    @property
    def label(self) -> str:
        return "必需" if self.required else "可选"

    def render(self, context: Mapping[str, str] | None = None) -> str:
        values = {"sim_os": DEFAULT_SIM_OS}
        if context:
            values.update({key: str(value) for key, value in context.items()})

        def fill(text: str) -> str:
            return text.replace("{sim_os}", values["sim_os"])

        line = f"→ 影响：{fill(self.impact)}；如何补：{fill(self.fix)}"
        if self.alternative:
            line += f"；替代：{fill(self.alternative)}"
        return line


# 检查项名 → 建议（Phase 3.4：缺失时说明“影响什么、怎么补、必需还是可选”）。
SUGGESTIONS: dict[str, Suggestion] = {
    "xcodebuild": Suggestion(
        required=True,
        impact="模拟器/真机动态验证不可执行（make test / make test-ui / make device-test 都会失败）",
        fix="安装 Xcode（App Store 或 developer.apple.com）后执行 "
        "`sudo xcode-select -s /Applications/Xcode.app`，再重跑 make doctor",
        alternative="只跑 make verify-static（静态门禁）；动态验证放到有 Xcode 的机器/CI",
    ),
    "simctl runtime": Suggestion(
        required=True,
        impact="make test 的 SIM_DEST 找不到基线模拟器，模拟器单测/UI 测试不可执行",
        fix="Xcode → Settings → Components（Platforms）下载 iOS {sim_os} runtime，"
        "或执行 `xcodebuild -downloadPlatform iOS`；也可用 SIM_OS=<已有版本> 覆盖",
        alternative="只跑 make verify-static；或用已有 runtime 的 SIM_OS 重跑",
    ),
    "mobilebuildmcp": Suggestion(
        required=False,
        impact="真机测试入口 make device-test / harness/tools/device-test.sh 不可用，"
        "真机验证结论只能写“未验证”",
        fix="按 CONTRIBUTING.md / references/verification.md 安装 mobilebuildmcp，并确保它在 PATH",
        alternative="不影响静态门禁；真机验证改用手动步骤",
    ),
    "TEAM_RULES": Suggestion(
        required=False,
        impact="make check-agents 无法校验团队基线（按团队约定 SKIP，不阻断本地门禁）",
        fix="忽略；或设置 TEAM_RULES=<模板仓路径> 后重跑 make check-agents / make doctor",
    ),
    "git 仓库": Suggestion(
        required=True,
        impact="计划状态、证据与所有 git 相关门禁不可用（make verify-static / plan.py check 会失败）",
        fix="在仓库根运行 doctor；若目录不完整，重新 clone 仓库",
    ),
    "git status": Suggestion(
        required=False,
        impact="无法确认工作区是否清洁（收尾/交接时的未提交改动判断受影响）",
        fix="确认 git 可用并能读取仓库元数据后重跑 make doctor",
    ),
}

# 未登记检查项的通用兜底：FAIL 按必需、WARN 按可选处理。
FALLBACK_FAIL = Suggestion(
    required=True,
    impact="该必需检查项失败会阻断对应的门禁/验证链路（详见上方 detail 行）",
    fix="按上方 detail 修复；不确定时先跑 make verify-static 缩小范围",
)
FALLBACK_WARN = Suggestion(
    required=False,
    impact="该可选检查项缺失只影响对应增强能力，不阻断静态门禁（详见上方 detail 行）",
    fix="按上方 detail 修复或忽略；静态门禁可用 make verify-static",
)


def suggestion_for(name: str, level: str) -> Suggestion | None:
    """按检查项名/级别取建议；SKIP 只对显式登记项给建议（不适用项保持安静）。"""
    suggestion = SUGGESTIONS.get(name)
    if suggestion is not None:
        return suggestion
    if level == FAIL:
        return FALLBACK_FAIL
    if level == WARN:
        return FALLBACK_WARN
    return None


def exit_code(xcode_ok: bool, runtime_ok: bool) -> int:
    """退出码语义（保持不变）：动态验证不可用（缺 Xcode 或基线 runtime）→ 2，否则 0。"""
    return 0 if xcode_ok and runtime_ok else 2


def run(cmd: list[str], timeout: int = 30, cwd: Path | None = None) -> tuple[int, str, str]:
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd or ROOT
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except FileNotFoundError:
        return 127, "", "命令不存在"
    except subprocess.TimeoutExpired:
        return 124, "", f"超时（{timeout}s）"
    except OSError as exc:  # pragma: no cover - 极端环境
        return 126, "", str(exc)


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
        """非 OK 行的建议行（每个检查项一行；同名校验只列一次）。"""
        lines: list[str] = []
        seen: set[str] = set()
        for level, name, _ in self.rows:
            if level == OK or name in seen:
                continue
            suggestion = suggestion_for(name, level)
            if suggestion is None:
                continue
            seen.add(name)
            lines.append(f"  [{suggestion.label}] {name}：{suggestion.render(context)}")
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
            lines.append("建议（缺失/降级项：影响与修复方式；必需项不修则动态验证不可用）：")
            lines.extend(suggestions)
        return "\n".join(lines)


def first_line(text: str) -> str:
    return text.splitlines()[0].strip() if text.strip() else ""


def check_xcode(report: Report) -> bool:
    code, out, err = run(["xcodebuild", "-version"])
    if code != 0:
        detail = first_line(err) or first_line(out) or f"exit {code}"
        report.add(FAIL, "xcodebuild", f"不可用：{detail}；动态验证不可执行")
        return False
    version = " ".join(line.strip() for line in out.splitlines()[:2] if line.strip())
    developer = ""
    dev_code, dev_out, _ = run(["xcode-select", "-p"])
    if dev_code == 0 and dev_out.strip():
        developer = f"；developer: {dev_out.strip()}"
    report.add(OK, "xcodebuild", version + developer)
    return True


def check_simctl(report: Report, sim_os: str) -> bool:
    code, out, err = run(["xcrun", "simctl", "list", "runtimes"])
    if code != 0:
        detail = first_line(err) or first_line(out) or f"exit {code}"
        report.add(FAIL, "simctl runtime", f"xcrun simctl 不可用：{detail}；动态验证不可执行")
        return False
    runtime_lines = [line.strip() for line in out.splitlines() if line.strip()]
    ios_lines = [line for line in runtime_lines if line.startswith("iOS ")]
    matched = [line for line in ios_lines if sim_os in line]
    available = ", ".join(re.sub(r"\s+-.*$", "", line) for line in ios_lines) or "无 iOS runtime"
    if matched:
        report.add(OK, "simctl runtime", f"iOS {sim_os} 可用（SIM_OS={sim_os}）：{matched[0]}")
        return True
    report.add(
        WARN,
        "simctl runtime",
        f"未找到 iOS {sim_os}（SIM_OS={sim_os}）；可用：{available}；"
        f"用 SIM_OS=<version> 覆盖，或安装对应 runtime（make test 的 SIM_DEST 依赖它）",
    )
    return False


def check_mobilebuildmcp(report: Report) -> None:
    found = shutil.which("mobilebuildmcp")
    if found:
        report.add(OK, "mobilebuildmcp", found)
    else:
        report.add(
            WARN,
            "mobilebuildmcp",
            "不在 PATH；make device-test / harness/tools/device-test.sh 不可用（真机验证结论=未验证）",
        )


def check_python(report: Report) -> None:
    version = sys.version.split()[0]
    executable = shutil.which("python3") or sys.executable
    report.add(OK, "python3", f"{version}（{executable}）")


def check_git(report: Report) -> bool:
    code, out, err = run(["git", "rev-parse", "--is-inside-work-tree"])
    if code != 0 or out.strip() != "true":
        detail = first_line(err) or first_line(out) or f"exit {code}"
        report.add(FAIL, "git 仓库", f"不是 git 仓库或 git 不可用：{detail}")
        return False
    branch = ""
    _, branch_out, _ = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    if branch_out.strip():
        branch = f"branch={branch_out.strip()}"
    commit = ""
    _, commit_out, _ = run(["git", "rev-parse", "--short", "HEAD"])
    if commit_out.strip():
        commit = f"HEAD={commit_out.strip()}"
    detail = "，".join(part for part in (commit, branch) if part) or "仓库可用"
    report.add(OK, "git 仓库", detail)
    return True


def check_team_rules(report: Report, root: Path) -> None:
    configured = os.environ.get("TEAM_RULES", "").strip()
    label = configured or DEFAULT_TEAM_RULES
    candidate = Path(configured) if configured else root / DEFAULT_TEAM_RULES
    if not candidate.is_absolute():
        candidate = (root / candidate).resolve()
    if not candidate.is_dir():
        report.add(
            SKIP,
            "TEAM_RULES",
            f"模板仓不存在：{label}（make check-agents 会 SKIP，不阻断；设置 TEAM_RULES=<path> 可复跑）",
        )
        return
    sync_script = candidate / "scripts" / "sync_team_baseline.py"
    if sync_script.is_file():
        report.add(OK, "TEAM_RULES", f"{label}（模板仓存在，含 sync_team_baseline.py）")
    else:
        report.add(WARN, "TEAM_RULES", f"{label}（目录存在但缺 scripts/sync_team_baseline.py）")


def check_git_status(report: Report) -> None:
    code, out, _ = run(["git", "status", "--short"])
    if code != 0:
        report.add(WARN, "git status", "无法读取 git status")
        return
    count = len([line for line in out.splitlines() if line.strip()])
    if count:
        report.add(OK, "git status", f"工作区有 {count} 项未提交改动（开发中正常；收尾用 make end 核对计划）")
    else:
        report.add(OK, "git status", "工作区 clean")


def main(argv: list[str]) -> int:
    global ROOT
    args = list(argv)
    if "--root" in args:
        index = args.index("--root")
        try:
            ROOT = Path(args[index + 1]).expanduser().resolve()
        except IndexError:
            sys.exit("用法：python3 tools/doctor.py [--root <repo>]")
        del args[index: index + 2]
    if args and args[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    if not ROOT.is_dir():
        sys.exit(f"[FAIL] 仓库根不存在：{ROOT}")

    sim_os = os.environ.get("SIM_OS", DEFAULT_SIM_OS).strip() or DEFAULT_SIM_OS
    sim_name = os.environ.get("SIM_NAME", DEFAULT_SIM_NAME).strip() or DEFAULT_SIM_NAME

    report = Report()
    xcode_ok = check_xcode(report)
    runtime_ok = check_simctl(report, sim_os)
    check_mobilebuildmcp(report)
    check_python(report)
    git_ok = check_git(report)
    check_team_rules(report, ROOT)
    if git_ok:
        check_git_status(report)

    code = exit_code(xcode_ok, runtime_ok)

    print("对译 Duiyi · 环境自检（doctor）")
    print(f"仓库：{ROOT}")
    print(f"目标模拟器：{sim_name} / iOS {sim_os}（SIM_OS / SIM_NAME 可覆盖）")
    print(report.render({"sim_os": sim_os}))
    print()
    if code == 2:
        failures = []
        if not xcode_ok:
            failures.append("xcodebuild 不可用")
        if not runtime_ok:
            failures.append("simctl runtime 不可用或缺少基线版本")
        print("结论：动态验证不可执行（" + "、".join(failures) + "）→ 代码行为结论=未验证。")
        print("      这是环境问题，不是代码问题：不要在无 Xcode 的机器上把 make test 失败归因于代码。")
        print("      改用：make verify-static（静态）+ 有 Xcode 的机器/CI 跑动态验证。")
        return code
    print("结论：动态验证环境就绪（Xcode + 基线模拟器可用）。")
    print("      本命令不运行测试/真机 —— 代码行为结论仍为“未验证”；需要跑 make test / make test-ui / make device-test。")
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
