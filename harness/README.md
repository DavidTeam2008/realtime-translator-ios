# harness/ · 运行工作区

> 本目录存放计划、证据与配置；目标是让“完成”可被门禁与证据复核，而不是靠口头声明。
> 根指令见 [`../AGENTS.md`](../AGENTS.md)，验证矩阵见 [`../references/verification.md`](../references/verification.md)。

## 1. 本目录有什么

| 路径 | 作用 | 启用 profile |
| --- | --- | --- |
| [`config.json`](config.json) | 路径 / 命令 / 预算 / claims 的唯一配置源 | 全部 |
| `plans/` | 跨会话计划与进度真源 | standard / strict |
| `evidence/` | 结构化验证证据（与原始产物分离） | standard / strict |
| `reviews/` | 独立审查报告 | strict |
| `test-baseline.json` | 测试计数下限与 skip 预期 | standard / strict |

## 2. 日常动作

- 开工：读 active 计划（`plans/`）与 [`config.json`](config.json)，确认改动范围。
- 验证：`make check` 后再跑 `make test`；结果写入计划或证据文件。
- 收尾：更新计划 → `make verify-static` → 记录未验证项。

## 3. 规则

- 路径以 [`config.json`](config.json) 为准，不在脚本里硬编码第二份。
- `runs/` 等原始产物不入库；入库的只有摘要、结论与可复核命令。
- 计划 / 证据中不写本机绝对路径、设备 ID、令牌或密钥。

## 4. 相关阅读

- 目录级规则：[`AGENTS.md`](AGENTS.md)
- 文档索引：[`../docs/README.md`](../docs/README.md)
- 计划与审查流程：[`../references/workflow.md`](../references/workflow.md)
