# harness/ · Agent 工作区索引

> 这是**过程档案层**，不是产品文档，也不是 App 运行时目录。
> 产品行为/架构在 `docs/`；Agent 规则细则在 `references/`；执行状态与证据在 `harness/`。

## 目录

| 路径 | 职责 | 入库 |
| --- | --- | --- |
| `plans/` | 跨会话计划（唯一进度真源）；`_template.md` 起稿模板 | 是 |
| `evidence/` | 可复核证据：schema、模板、摘要 JSON | 是（1–3KB/条） |
| `tools/` | 真机测试 / 启动测量脚本（把踩过的坑固化成代码） | 是 |
| `test-baseline.json` | 测试计数与 skip 白名单基线（`make check-tests`） | 是 |
| `runs/` | 原始测量产物、日志、截图 | **否**（gitignore，可由脚本重建） |
| `reviews/` | 独立审查 / 月度审计报告（按需创建） | 是 |

## 边界

- `docs/` 写当前事实与理由；`references/` 写 Agent 规则；`harness/` 写某次任务的执行状态、证据与审查。
- active 计划是**跨会话进度唯一真源**；完成声明必须能指向 `evidence/` 的 evidence id。
- 目录名来自 2026-09 启动测量工作区（APM），2026-11 更名为 `harness/` 并收敛；历史过程文档与数据已从小树移除，原始记录见 git 历史。

## 常用命令

```bash
make resume           # 接手：active 计划 + git 状态 + 下一步
make evidence         # 列出证据
make verify-claim     # PASS / FAIL / UNVERIFIED 三值判定
make check-plan       # 计划状态机与未提交改动核对
make end              # 收尾门禁 + 计划检查
make harness-audit    # 月度五子系统审计入口（人工打分）
```

目录级协议见 [`AGENTS.md`](AGENTS.md)；证据规范见 [`evidence/README.md`](evidence/README.md)；系统地图见 [`../HARNESS.md`](../HARNESS.md)。
