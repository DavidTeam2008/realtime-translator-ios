# AI coding Agent 提示词模板（兜底入口：接入 / 开发 / 评审 / 发布 / 交接 / 收尾）

> harness-kit 的**默认入口是入口 skill**：装一次（`<kit>/scripts/harness-skill install --scope user`），任意仓库的 Agent 会话都能通过 skill 路由到接入/计划/验证/发布流程，不需要复制提示词。
>
> 本文是**兜底**提示词库：只在宿主不支持 skills，或你临时想用命令行拿一段文本时使用。模板与具体 Agent 无关（DeepSeek Harness / Claude Code / Codex / Cursor / 自研），前提是它能读文件、跑 shell。
>
> **本文件由 `scripts/harness-prompt render` 从 `prompts/*.md` 生成，不要手改**；改模板请改 `prompts/` 后重新渲染。

## 怎么用：先装 skill（推荐），再用提示词兜底

**推荐（一次）**：在目标仓库根目录执行一次用户级安装，之后直接对 Agent 说「接入这个项目」：

```bash
<kit>/scripts/harness-skill install --scope user   # 装到 ~/.agents/skills；所有仓库可见
```

**兜底（宿主没有 skills 支持时）**：一条命令拿提示词，粘贴给 Agent；下文 `<kit>` 指 kit 克隆路径：

```bash
cd /path/to/your-project
<kit>/scripts/harness-prompt list                     # 看场景清单（会显示目标仓库是否已接入）
<kit>/scripts/harness-prompt copy adopt-brownfield    # 复制到剪贴板，直接粘给 Agent
<kit>/scripts/harness-prompt show fix-bug             # 或打印出来手动复制
```

- `copy` / `show` 会按**所选场景**拼接前置：接入场景用 0B（未接入，含 kit 路径与只读约束），日常场景用 0A（已接入）；并填好 kit 与目标仓库的绝对路径。
- 如果目标仓库看起来与场景阶段不符（例如在未接入仓库里选日常场景），命令会先给 WARN，不会静默贴错前置。
- 需要你补充的信息（如 `<SYMPTOM>`）会列出来；也可以 `--set SYMPTOM="..." --set REPRO="..."` 一次填好。
- 剪贴板：`copy` 依次尝试 `pbcopy` / `clip` / `wl-copy` / `xclip` / `xsel`；都没有时会把提示词打印到 stdout 并给 WARN，可手动复制。
- 可加别名：`alias hp='<kit>/scripts/harness-prompt'`，之后 `hp copy fix-bug`。
- 没有命令行时手工复制：先贴 §0A（已接入）或 §0B（未接入），把 `<kit>` / `<目标仓库路径>` 换成本机路径，再贴场景模板；§1 / §2 是未接入场景，手工复制时也要先贴 0B。

## 0. 公共前置（按项目阶段选一段）

**先判断阶段**：仓库根有 `Makefile`（或 `Makefile.harness`）且存在 `harness/config.json` → 已接入（用 0A）；否则未接入（用 0B）。
由 `harness-prompt show/copy` 自动拼接；手工复制时按上面的规则先贴对应前置。接入完成后的日常任务统一用 0A。
