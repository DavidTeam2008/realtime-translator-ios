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

退出码：
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
from pathlib import Path

OK, WARN, FAIL, SKIP = "OK", "WARN", "FAIL", "SKIP"

DEFAULT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SIM_OS = "26.4.1"
DEFAULT_SIM_NAME = "iPhone 17 Pro Max"
DEFAULT_TEAM_RULES = "../../agent/template"

ROOT = DEFAULT_ROOT


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

    def render(self) -> str:
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
            "不在 PATH；make device-test / .apm/tools/device-test.sh 不可用（真机验证结论=未验证）",
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

    dynamic_unavailable = not xcode_ok or not runtime_ok

    print("对译 Duiyi · 环境自检（doctor）")
    print(f"仓库：{ROOT}")
    print(f"目标模拟器：{sim_name} / iOS {sim_os}（SIM_OS / SIM_NAME 可覆盖）")
    print(report.render())
    print()
    if dynamic_unavailable:
        failures = []
        if not xcode_ok:
            failures.append("xcodebuild 不可用")
        if not runtime_ok:
            failures.append("simctl runtime 不可用或缺少基线版本")
        print("结论：动态验证不可执行（" + "、".join(failures) + "）→ 代码行为结论=未验证。")
        print("      这是环境问题，不是代码问题：不要在无 Xcode 的机器上把 make test 失败归因于代码。")
        print("      改用：make verify-static（静态）+ 有 Xcode 的机器/CI 跑动态验证。")
        return 2
    print("结论：动态验证环境就绪（Xcode + 基线模拟器可用）。")
    print("      本命令不运行测试/真机 —— 代码行为结论仍为“未验证”；需要跑 make test / make test-ui / make device-test。")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
