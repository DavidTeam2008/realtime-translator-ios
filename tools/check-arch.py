#!/usr/bin/env python3
"""架构铁律静态扫描 R1–R6（纯标准库，秒级，可 ubuntu CI）。

用法：
    python3 tools/check-arch.py [--root PATH]
默认 root 为脚本上级目录（仓库根）。违规输出 `file:line: rule` 并 exit 1；
白名单/规则配置集中在下方常量（新增白名单需 L1 审查）。

规则（依据：references/contracts.md §1–§5、docs/02-architecture.md §1）：
    R1 Duiyi/Domain/**      禁止 import SwiftUI/语音/翻译/SwiftData（允许 Foundation/CoreGraphics 等）
    R2 Duiyi/Features/**    禁止 import 语音/音频/翻译/SwiftData；*TranslationHostView.swift 是
                            Translation 的唯一例外（.translationTask 锚点）
    R3 Duiyi/Services/**    禁止引用 ViewModel（去注释后匹配）
    R4 TranslationSession   只允许出现在 *TranslationHostView.swift
    R5 BilingualSpeechEngine( 实例化只允许 Duiyi/App/AppEnvironment.swift（单一语音引擎）
    R6 Duiyi/Features/**    禁止 @Query/modelContainer/ModelContext 直读 SwiftData
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from fnmatch import fnmatch
from pathlib import Path

DEFAULT_ROOT = Path(__file__).resolve().parent.parent

# --- 白名单与规则配置（改这里需 L1 审查；当前 HEAD 全部 0 违规）---------------------
# R1：Domain 是纯模型层；语音/音频模块按 contracts §1“语音”口径一并禁止。
R1_FORBIDDEN_MODULES = frozenset(
    {"SwiftUI", "Speech", "Translation", "SwiftData", "AVFoundation", "AVFAudio"}
)
# R2：Features 不得直接摸语音/音频/翻译/SwiftData 实现。
R2_FORBIDDEN_MODULES = frozenset(
    {"Speech", "AVFoundation", "AVFAudio", "Translation", "SwiftData"}
)
# R2/R4：翻译锚 View 的唯一例外（单向/面对面 Host View 都以此后缀结尾）。
TRANSLATION_HOST_SUFFIX = "*TranslationHostView.swift"
# R5：唯一允许实例化 BilingualSpeechEngine 的位置（AppEnvironment 组装点）。
R5_ALLOWED_FILES = frozenset({"Duiyi/App/AppEnvironment.swift"})
# R6：Features 不得直读 SwiftData。
R6_FORBIDDEN_PATTERN = re.compile(r"@Query\b|\bmodelContainer\b|\bModelContext\b")

# 形如 `import X`、`@preconcurrency import X`、`import class X.Y`。
IMPORT_RE = re.compile(
    r"^\s*(?:@[A-Za-z_][A-Za-z0-9_]*\s+)*import\s+"
    r"(?:class\s+|struct\s+|enum\s+|protocol\s+|func\s+|var\s+|let\s+|typealias\s+)?"
    r"([A-Za-z_][A-Za-z0-9_]*)"
)
VIEWMODEL_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*ViewModel\b")
TRANSLATION_SESSION_RE = re.compile(r"\bTranslationSession\b")
BILINGUAL_INIT_RE = re.compile(r"\bBilingualSpeechEngine\s*\(")


def strip_comments(text: str) -> str:
    """把 `//` 与 `/* */` 注释替换成空格，保留换行与原始行号。

    跳过 `https://` 里的 `//`（前一字符是 `:`）；Swift 块注释可嵌套。
    行号对齐：注释替换只写等量空字符，换行原样保留。
    """
    out: list[str] = []
    i, size = 0, len(text)
    in_block = 0
    while i < size:
        char = text[i]
        nxt = text[i + 1] if i + 1 < size else ""
        if in_block:
            if char == "/" and nxt == "*":
                in_block += 1
                out.append("  ")
                i += 2
                continue
            if char == "*" and nxt == "/":
                in_block -= 1
                out.append("  ")
                i += 2
                continue
            out.append("\n" if char == "\n" else " ")
            i += 1
            continue
        if char == "/" and nxt == "/" and not (i > 0 and text[i - 1] == ":"):
            while i < size and text[i] != "\n":
                out.append(" ")
                i += 1
            continue
        if char == "/" and nxt == "*":
            in_block = 1
            out.append("  ")
            i += 2
            continue
        out.append(char)
        i += 1
    return "".join(out)


def import_module(line: str) -> str | None:
    match = IMPORT_RE.match(line)
    return match.group(1) if match else None


def swift_files(root: Path) -> list[Path]:
    base = root / "Duiyi"
    return sorted(path for path in base.rglob("*.swift") if path.is_file())


def scan(root: Path, files: list[Path]) -> list[str]:
    """返回按 file:line: rule 格式化的违规列表。"""
    violations: list[str] = []
    for path in files:
        rel = path.relative_to(root).as_posix()
        basename = path.name
        text = path.read_text(encoding="utf-8", errors="replace")
        raw_lines = text.splitlines()
        code_lines = strip_comments(text).splitlines()

        in_domain = rel.startswith("Duiyi/Domain/")
        in_features = rel.startswith("Duiyi/Features/")
        in_services = rel.startswith("Duiyi/Services/")
        is_translation_host = fnmatch(basename, TRANSLATION_HOST_SUFFIX)

        for lineno, raw in enumerate(raw_lines, 1):
            module = import_module(raw)
            if module is None:
                continue
            if in_domain and module in R1_FORBIDDEN_MODULES:
                violations.append(f"{rel}:{lineno}: R1 Domain 禁止 import {module}")
            if in_features:
                if module in R2_FORBIDDEN_MODULES and not (
                    module == "Translation" and is_translation_host
                ):
                    violations.append(f"{rel}:{lineno}: R2 Features 禁止 import {module}")

        for lineno, code in enumerate(code_lines, 1):
            if in_services:
                for match in VIEWMODEL_RE.finditer(code):
                    violations.append(
                        f"{rel}:{lineno}: R3 Services 禁止引用 ViewModel（{match.group(0)}）"
                    )
                    break
            if not is_translation_host:
                for _ in TRANSLATION_SESSION_RE.finditer(code):
                    violations.append(
                        f"{rel}:{lineno}: R4 TranslationSession 只允许出现在 {TRANSLATION_HOST_SUFFIX}"
                    )
                    break
            if rel not in R5_ALLOWED_FILES:
                for _ in BILINGUAL_INIT_RE.finditer(code):
                    violations.append(
                        f"{rel}:{lineno}: R5 BilingualSpeechEngine( 只允许在 Duiyi/App/AppEnvironment.swift"
                    )
                    break
            if in_features:
                match = R6_FORBIDDEN_PATTERN.search(code)
                if match:
                    violations.append(
                        f"{rel}:{lineno}: R6 Features 禁止直读 SwiftData（{match.group(0)}）"
                    )
    return violations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="架构铁律 R1–R6 静态扫描")
    parser.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_ROOT,
        help="仓库根（默认脚本上级目录，用于 fixture 测试）",
    )
    args = parser.parse_args(argv)
    root = args.root.resolve()

    if not (root / "Duiyi").is_dir():
        print(f"[FAIL] 找不到 {root / 'Duiyi'}（请检查 --root）")
        return 2

    started = time.perf_counter()
    files = swift_files(root)
    violations = scan(root, files)
    elapsed = time.perf_counter() - started

    print(f"check-arch · 架构铁律 R1–R6（扫描 {len(files)} 个 Swift 文件，{elapsed:.2f}s）")
    if violations:
        for violation in violations:
            print(violation)
        print(f"[FAIL] {len(violations)} 处架构违规（exit 1）")
        return 1
    print("[PASS] R1–R6 全部通过：0 违规")
    return 0


if __name__ == "__main__":
    sys.exit(main())
