# Agent 适配层（DSH / Claude Code / 其它）

> 设计原则：**规范与证据不绑定 Agent 工具**。`AGENTS.md`、skills、门禁与 evidence 是仓库唯一源；工具差异只放在本目录的薄适配层。

## 目录

| 路径 | 作用 | 是否默认加载 |
| --- | --- | --- |
| `dsh/README.md` | DSH 原生能力与项目约定（AGENTS 链、`.dsh/skills`） | 说明文档 |
| `claude-code/CLAUDE.md.template` | Claude Code 入口模板：`@AGENTS.md` + Claude 专用提示 | 用户按需复制为仓库根 `CLAUDE.md` |
| `claude-code/settings.hooks.example.json` | Claude Code hooks 示例：PostToolUse→`make check`，Stop→`make verify-static` | 需用户合并到 `.claude/settings.json` |
| `claude-code/agents/red-team.md` | 独立复核 subagent 示例 | 需用户复制到 `.claude/agents/` |

## 单源与同步

- 规范源：仓库根 `AGENTS.md` 指令树（DSH 原生读取；Claude Code v2.1.277+ 原生读取）。
- 动作源：`.dsh/skills/*/SKILL.md`（DSH 原生发现）。Claude Code 使用 `.claude/skills/`，由 `make adapters-sync` 从单源生成；`make adapters-check` 校验无漂移。
- 生成物 `.claude/skills/` 与 `.claude/settings.local.json` 已在 `.gitignore`，不提交。

## 使用

```bash
make adapters-check   # 校验单源 skills、hooks 示例、CLAUDE.md/agent 示例（静态门禁已包含）
make adapters-sync    # 在安装 Claude Code 的本机生成 .claude/skills/
```

模型可替换：门禁与证据与模型无关。Claude Code + DeepSeek 使用官方 Anthropic 兼容配置（`ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic` 等），仓库不保存任何 key。
