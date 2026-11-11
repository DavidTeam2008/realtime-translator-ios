# DSH 适配器（dsh）

> DSH（DeepSeek Harness）**原生**读取仓库根到 cwd 的 `AGENTS.md` 指令链，并发现项目级 skills；
> 因此本适配器**不复制任何文件**——[`../manifest.json`](../manifest.json) 中 `dsh` 为空列表。

## 为什么是空适配器

- 仓库内可固化的指令就是 `AGENTS.md` 谱系（根 + 嵌套）与 skills（`.dsh/skills/*/SKILL.md`、`.agents/skills/*/SKILL.md`）。
- DSH 的 skill 发现根：项目 `.dsh/skills`（rank 100）→ 项目 `.agents/skills`（200）→ 自定义目录（300）→ 用户 `~/.dsh/skills`（400）→ 用户 `~/.agents/skills`（500）。kit 的入口 skill 用 `harness-skill install --scope user` 装到 `~/.agents/skills/harness/`，一次安装、所有仓库会话可见；项目级同名 skill 优先。
- 其他能力（模型、权限、工具、MCP、hooks）属于用户级 profile 配置，不在项目仓库内，kit 不生成。
- 复制一份 DSH 专用配置会制造第二真源；保持仓库原生文件即可跨 agent 工具共用。

## 接入后你会得到什么

| profile | 仓库内文件 | DSH 行为 |
| --- | --- | --- |
| minimal / standard | 根 `AGENTS.md` + 嵌套 `AGENTS.md` | 冷启动加载根指令，进入子目录后按需加载嵌套规则 |
| strict | 额外 `.dsh/skills/{verify-change,handoff,red-team}/SKILL.md` | 按 skill 名称 / 描述触发对应流程 |

- skill 模板来源见 [`../../core/templates/skills/`](../../core/templates/skills/)；strict profile 渲染后位于目标仓库 `.dsh/skills/`。
- 机器本地差异（路径、设备、账号）不要写进入库文件；使用本地覆盖文件（不入库）。

## 使用建议

1. 先装一次入口 skill：`<kit>/scripts/harness-skill install --scope user`（写 `~/.agents/skills/harness/`；`check --scope user` 应 in sync），再让 agent 执行任务。
2. 先跑 `make verify-static` 确认静态链路可用，再让 agent 执行任务。
3. 完成声明前加载 `verify-change`；交接前加载 `handoff`；高风险 L2 加载 `red-team`。
4. 不要把 `.claude/` 等其它工具的生成物复制给 DSH；各适配器独立。

## 相关

- 构建契约：[`../../SPEC.md`](../../SPEC.md)（§1 目录、§2 目标产物）。
- profile 定义：minimal / standard / strict（见 [`../../profiles/`](../../profiles/)）。
- Claude Code 适配层对照：[`../claude-code/CLAUDE.md.template`](../claude-code/CLAUDE.md.template)。
