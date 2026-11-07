#!/usr/bin/env python3
"""通用 token 估算口径（harness-kit v2）。

规则：CJK 表意字符 + 中文/全角标点（U+3000–303F、U+3400–4DBF、U+4E00–9FFF、
U+FF00–FFEF）按 1 token；其余字符按 4 字符/token 向上取整（空串为 0）。
该口径用于预算相对控制，不是具体模型 tokenizer 的精确计数。

供同目录脚本使用：

    from token_estimate import estimate_tokens

仅标准库；无第三方依赖、不联网。
"""
from __future__ import annotations

WIDE_RANGES = (
    (0x3000, 0x303F),  # CJK 符号与标点
    (0x3400, 0x4DBF),  # CJK 扩展 A
    (0x4E00, 0x9FFF),  # CJK 统一表意文字
    (0xFF00, 0xFFEF),  # 全角/半角形式
)


def is_wide(char: str) -> bool:
    """字符是否按 1 token 计（CJK / 全角）。"""
    code = ord(char)
    return any(low <= code <= high for low, high in WIDE_RANGES)


def estimate_tokens(text: str) -> int:
    """估算文本 token 数：宽字符 1 token，其余 4 字符 1 token，向上取整。"""
    wide = sum(1 for char in text if is_wide(char))
    return wide + -(-(len(text) - wide) // 4)


if __name__ == "__main__":
    print("token_estimate：import 后调用 estimate_tokens(text)；无第三方依赖。")
