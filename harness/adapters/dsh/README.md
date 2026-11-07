# DSH 适配（DeepSeek Harness）

DSH 项目级原生机制只有两类，本仓库都在用：

| 能力 | DSH 行为 | 本仓库落点 |
| --- | --- | --- |
| 指令链 | 根 → cwd 逐层读取 `AGENTS.md`；嵌套目录按需注入；`AGENTS.local.md` 为本机 overlay | 根 `AGENTS.md` + 6 个嵌套 AGENTS |
| 项目 skills | 自动发现 `.dsh/skills/<name>/SKILL.md`（frontmatter `name`/`description`，按需加载） | 6 个动作卡（验证/交接/红队/审计/真机/冷启动） |

其余能力是 profile/会话级，**不要写进仓库规则当作强制能力**（以当前安装版本为准）：

- subagents / Agent Teams / workflow / goals / schedules / worktree / MCP：由用户在本机 profile 启用；
- hooks：本项目安装的 DSH 0.2.1-rc.5 未打包；等价能力用 `.dsh/skills` + pre-push + CI；
- 模型与凭据：profile 配置，不入库。

使用建议：长任务用 `make plan`/`resume`/`end`；L2 高风险改动用只读子 agent 或新会话做独立复核；月度跑 `make harness-audit`。
