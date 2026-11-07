#!/usr/bin/env python3
"""测试基线门禁：防“删测试变绿”、防 skip 白名单漂移、防文档计数漂移。

用法：
    python3 tools/check-test-baseline.py [--root PATH]
默认 root 为脚本上级目录（仓库根）。数据源：`harness/test-baseline.json`。

检查项：
    1. DuiyiTests/**/*.swift 的 `@Test` 出现次数 < unit.floor  -> exit 1
    2. DuiyiUITests/** 的 `func test` 出现次数 < ui.floor        -> exit 1
    3. references/verification.md 的计数锚点与 baseline 一致     -> 不一致 exit 1
       只认 “<n> 单元 + <m> UI” 与 “真机 **<n+m>**” 两种表述（宽松正则）
    4. DuiyiUITests 的 `XCTSkip` 出现次数 > xctSkipOccurrences   -> exit 1
       少于 baseline 只 WARN（删 skip 可能是正常修复，但需要人确认）
    5. baseline 结构/schemaVersion 校验
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

DEFAULT_ROOT = Path(__file__).resolve().parent.parent
BASELINE_REL = "harness/test-baseline.json"
VERIFICATION_REL = "references/verification.md"
SCHEMA_VERSION = 1

TEST_RE = re.compile(r"@Test\b")
UI_TEST_RE = re.compile(r"\bfunc\s+test")
XCTSKIP_RE = re.compile(r"\bXCTSkip\b")
UNIT_UI_RE = re.compile(r"(\d+)\s*单元\s*\+\s*(\d+)\s*UI")
DEVICE_BOLD_RE = re.compile(r"真机\s*\*\*\s*(\d+)\s*\*\*")
DEVICE_LINE_RE = re.compile(r"真机[^\d\n]{0,24}(\d+)")


def count_occurrences(directory: Path, pattern: re.Pattern[str]) -> tuple[int, int, bool]:
    """返回 (命中次数, 文件数, 目录是否存在)。"""
    if not directory.is_dir():
        return 0, 0, False
    files = sorted(path for path in directory.rglob("*.swift") if path.is_file())
    total = 0
    for path in files:
        total += len(pattern.findall(path.read_text(encoding="utf-8", errors="replace")))
    return total, len(files), True


def load_baseline(root: Path) -> tuple[dict | None, list[str]]:
    path = root / BASELINE_REL
    if not path.is_file():
        return None, [f"缺少 {BASELINE_REL}（测试基线数据源）"]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [f"{BASELINE_REL} 不是合法 JSON：{exc}"]
    errors: list[str] = []
    if data.get("schemaVersion") != SCHEMA_VERSION:
        errors.append(
            f"{BASELINE_REL}.schemaVersion={data.get('schemaVersion')!r}，" f"期望 {SCHEMA_VERSION}"
        )
    for key in ("unit", "ui"):
        block = data.get(key)
        if not isinstance(block, dict) or not isinstance(block.get("floor"), int):
            errors.append(f"{BASELINE_REL}.{key}.floor 缺失或不是整数")
    expected = data.get("expectedSkipped")
    if not isinstance(expected, dict) or not all(
        isinstance(expected.get(key), int) for key in ("simulator", "device")
    ):
        errors.append(f"{BASELINE_REL}.expectedSkipped.simulator/device 缺失或不是整数")
    if not isinstance(data.get("xctSkipOccurrences"), int):
        errors.append(f"{BASELINE_REL}.xctSkipOccurrences 缺失或不是整数")
    if not isinstance(data.get("updatedAt"), str) or not data["updatedAt"]:
        errors.append(f"{BASELINE_REL}.updatedAt 缺失")
    return (data if not errors else None), errors


def check_doc_anchor(root: Path, unit_floor: int, ui_floor: int) -> tuple[list[str], list[str]]:
    """校验 references/verification.md 的计数锚点；返回 (errors, messages)。"""
    path = root / VERIFICATION_REL
    if not path.is_file():
        return [f"缺少 {VERIFICATION_REL}"], []
    text = path.read_text(encoding="utf-8")
    errors: list[str] = []
    messages: list[str] = []

    match = UNIT_UI_RE.search(text)
    if not match:
        errors.append(f"{VERIFICATION_REL} 未找到计数锚点“<n> 单元 + <m> UI”")
    else:
        doc_unit, doc_ui = int(match.group(1)), int(match.group(2))
        if (doc_unit, doc_ui) != (unit_floor, ui_floor):
            errors.append(
                f"{VERIFICATION_REL} 计数与 baseline 不一致："
                f"文档 {doc_unit} 单元 + {doc_ui} UI ≠ baseline {unit_floor} 单元 + {ui_floor} UI"
            )
        else:
            messages.append(f"{VERIFICATION_REL} 计数一致：{doc_unit} 单元 + {doc_ui} UI")

    device_expected = unit_floor + ui_floor
    device_match = DEVICE_BOLD_RE.search(text)
    if not device_match:
        for line in text.splitlines():
            if "基线" in line and "真机" in line:
                device_match = DEVICE_LINE_RE.search(line)
                if device_match:
                    break
    if not device_match:
        errors.append(f"{VERIFICATION_REL} 未找到真机计数锚点（期望 真机 **{device_expected}**）")
    else:
        doc_device = int(device_match.group(1))
        if doc_device != device_expected:
            errors.append(
                f"{VERIFICATION_REL} 真机计数与 baseline 不一致："
                f"文档 {doc_device} ≠ {unit_floor}+{ui_floor}={device_expected}"
            )
        else:
            messages.append(f"{VERIFICATION_REL} 真机计数一致：{doc_device}")
    return errors, messages


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="测试计数下限 + skip 白名单 + 文档计数锚点")
    parser.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_ROOT,
        help="仓库根（默认脚本上级目录，用于 fixture 测试）",
    )
    args = parser.parse_args(argv)
    root = args.root.resolve()

    print("check-test-baseline · 测试基线下限")
    baseline, errors = load_baseline(root)
    if baseline is None:
        print(f"[FAIL] {BASELINE_REL} 不可用：")
        for error in errors:
            print(f"- {error}")
        return 1

    unit_floor = baseline["unit"]["floor"]
    ui_floor = baseline["ui"]["floor"]
    skip_limit = baseline["xctSkipOccurrences"]
    warnings: list[str] = []
    problems: list[str] = list(errors)

    unit_count, unit_files, unit_dir_ok = count_occurrences(root / "DuiyiTests", TEST_RE)
    if not unit_dir_ok:
        problems.append("缺少 DuiyiTests/ 目录")
    elif unit_count < unit_floor:
        problems.append(f"DuiyiTests @Test {unit_count} < floor {unit_floor}（禁止删测试）")
    else:
        delta = unit_count - unit_floor
        suffix = f"，高于下限 +{delta}" if delta else ""
        print(f"[OK] unit：@Test {unit_count} ≥ floor {unit_floor}（{unit_files} 个文件{suffix}）")
    baseline_unit_files = baseline["unit"].get("files")
    if isinstance(baseline_unit_files, int) and unit_files != baseline_unit_files:
        warnings.append(
            f"DuiyiTests 文件数 {unit_files} ≠ baseline files {baseline_unit_files}"
            "（只增不减以测试计数为准，成长后请同步 baseline）"
        )

    ui_count, ui_files, ui_dir_ok = count_occurrences(root / "DuiyiUITests", UI_TEST_RE)
    if not ui_dir_ok:
        problems.append("缺少 DuiyiUITests/ 目录")
    elif ui_count < ui_floor:
        problems.append(f"DuiyiUITests func test {ui_count} < floor {ui_floor}（禁止删测试）")
    else:
        delta = ui_count - ui_floor
        suffix = f"，高于下限 +{delta}" if delta else ""
        print(f"[OK] ui：func test {ui_count} ≥ floor {ui_floor}（{ui_files} 个文件{suffix}）")
    baseline_ui_files = baseline["ui"].get("files")
    if isinstance(baseline_ui_files, int) and ui_files != baseline_ui_files:
        warnings.append(
            f"DuiyiUITests 文件数 {ui_files} ≠ baseline files {baseline_ui_files}"
            "（成长后请同步 baseline）"
        )

    doc_errors, doc_messages = check_doc_anchor(root, unit_floor, ui_floor)
    problems.extend(doc_errors)
    for message in doc_messages:
        print(f"[OK] {message}")

    skip_count, _, ui_dir_ok = count_occurrences(root / "DuiyiUITests", XCTSKIP_RE)
    if not ui_dir_ok:
        problems.append("缺少 DuiyiUITests/ 目录（无法统计 XCTSkip）")
    elif skip_count > skip_limit:
        problems.append(
            f"DuiyiUITests XCTSkip 出现 {skip_count} 次 > 白名单 {skip_limit}（新增 skip 需更新 baseline）"
        )
    elif skip_count < skip_limit:
        warnings.append(
            f"DuiyiUITests XCTSkip 出现 {skip_count} 次 < 白名单 {skip_limit}（减少可能是修复，请确认）"
        )
    else:
        print(f"[OK] XCTSkip：{skip_count} 次 == 白名单 {skip_limit}")

    for warning in warnings:
        print(f"[WARN] {warning}")
    if problems:
        for problem in problems:
            print(f"[FAIL] {problem}")
        print(f"[FAIL] 测试基线未通过（{len(problems)} 个问题，exit 1）")
        return 1
    print("[PASS] 测试基线通过（只增不减 + 文档计数 + skip 白名单）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
