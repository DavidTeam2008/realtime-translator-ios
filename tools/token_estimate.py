#!/usr/bin/env python3
"""项目统一的 token 估算口径（v2）。

规则：CJK 统一表意字符 + 中文/全角标点（U+3000–303F、U+3400–4DBF、
U+4E00–9FFF、U+FF00–FFEF）按 1 token；其余字符按 4 字符/token 向上取整。
该口径比旧版（中文标点按 1/4 计）更保守，用来做"预算相对控制"；不是模型
真实 tokenizer 的精确计数。口径变更必须同步 docs/README.md 并走 L1 审查。
"""
from __future__ import annotations

WIDE_RANGES = (
    (0x3000, 0x303F),  # CJK 符号与标点
    (0x3400, 0x4DBF),  # CJK 扩展 A
    (0x4E00, 0x9FFF),  # CJK 统一表意文字
    (0xFF00, 0xFFEF),  # 全角/半角形式
)


def is_wide(ch: str) -> bool:
    code = ord(ch)
    return any(lo <= code <= hi for lo, hi in WIDE_RANGES)


def estimate_tokens(text: str) -> int:
    wide = sum(1 for ch in text if is_wide(ch))
    return wide + -(-(len(text) - wide) // 4)
