---
name: verify-change
description: 对译 Duiyi 完成声明前的验证闸门：按变更类型选命令（Domain/VM→make test，UI→make test-ui，语音/翻译/TTS/音频/持久化→make device-test，文档/规则/工具→make verify-static），记录命令/退出码/环境/证据并给出 PASS/FAIL/UNVERIFIED。无证据或未运行必须写"未验证"，不得声称通过。
whenToUse: 任何"完成/修好/已验证/测试通过"声明之前；提交前；填写计划验证证据或 handoff 前。
---

# verify-change · 完成前验证

先定变更类型，再跑最小充分验证。测不出/跑不了 = UNVERIFIED，不是 PASS。

## 1. 按变更类型选命令（映射细则见 `references/verification.md`）

| 变更 | 命令 | 说明 |
|---|---|---|
| Domain 纯逻辑 / 文本工具 | `make test` | 模拟器单元 |
| ViewModel 策略 | `make test` | 用假引擎/假 store/假合成器 |
| UI 导航 / 布局 | `make test-ui` | 模拟器语音用例 skip 是预期 |
| 语音 / 翻译 / TTS / 音频 | `make device-test` | 必须真机，模拟器不能替代 |
| SwiftData / 任务留存 | `make test` + 杀进程重开 | 迁移需演练 |
| 启动 / 性能 | Release 真机 `measure-launch.sh`，n≥10 | 不用模拟器证性能 |
| 文档 / 规则 / 工具 / skills | `make verify-static` | 秒级静态门禁 |

改动跨类时取并集；只改文档不要跑 xcodebuild。

## 2. 记录（可复核才算证据）

每条验证记录四元组：命令 | 结果（退出码、passed/failed/skipped） | 环境（Xcode 版本 + 模拟器 runtime 或真机型号 + iOS） | 证据 id。
Phase 1 起 evidence id 唯一：真机由 `harness/tools/device-test.sh` 自动写 `harness/evidence/`；其他用 `python3 tools/evidence.py write ...` 生成（`make evidence` 只列出，`make check-evidence` 校验 schema）。
有证据文件后跑 `make verify-claim` 取三值判定，并把 evidence id / 命令原文回填计划"验证证据"表。

## 3. 判定与声明

- PASS：命令 exit 0 且有 evidence id / 可复核记录。
- FAIL：exit ≠ 0 → 先定位；不得改既有断言、放宽 skip 或删测试来变绿。
- UNVERIFIED：未运行、环境不可用（`make doctor` 退出 2）、无 evidence id → 声明里明确写"未验证"+ 手动步骤。
- 禁止：把"环境跑不了"写成"代码通过"；用模拟器结果替代真机；省略 skip 数。

## 4. 失败停止规则

同一失败修复 2 次仍红，或同一子任务 3 轮无进展：停止，按 `references/workflow.md` 阻塞报告上报，并把尝试写进计划"尝试记录"。
