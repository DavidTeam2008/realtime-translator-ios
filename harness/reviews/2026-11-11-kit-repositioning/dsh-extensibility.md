> 冻结副本：来源 `harness/runs/kit-eval/dsh-extensibility.md`（2026-11-11）；原始命令输出仍在 gitignored 的 `harness/runs/kit-eval/`。
> 本文件为提案/评审冻结稿，实施记录见 `harness/plans/2026-11-06-benchmark-opensource.md` 与 `harness-kit/CHANGELOG.md`。

# DSH 可扩展面评估：harness-kit 封装为 Agent Skills / DSH 插件

> 日期：2026-11-11｜工作区：Duiyi iOS 仓（`harness-kit/` v0.2.11）｜方法：本机 app.asar 抽取 + 官方 deepseek-harness 文档 web_fetch + 本地 kit 只读检查；未安装任何插件、未改 profile。
> 置信度：**高**=官方文档或本机可复核原文；**中**=一手 README/代码或可推导；**低/未证实**单列。本地抽取物在 `harness/runs/kit-eval/_asar/`（gitignore 的 runs 目录）。

## 0. TL;DR（结论）

- **一个 DSH 包能做的远多于 skill**：注册 model tool、人类 slash command、skill（内嵌或 provider）、GUI slot/panel、后台 service 与事件监听、MCP 配置；运行在 Host 进程内、workspace sandbox **之外**。〔高〕
- **skill 不能新增可调用原语**：它只是"给模型的可复用指令文本 + 按需资源"，没有 tool/command/UI/lifecycle 能力。〔高〕
- **kit 现状**：无根 `package.json`（不是 npm 包），`adapters/dsh/` 为空适配（预留），strict 只生成 3 个 skill；`dsh` 适配器不复制任何文件（AGENTS/skills 是 DSH 原生的）。〔高：本地 kit 文件〕
- **推荐 v0.3 主形态：D（CLI）+ B（单总控 skill + references）**——CLI/门禁脚本仍是唯一执行体与逻辑真源，skill 只做入口路由；A 是 B 的降级兜底；**C（DSH bundle 插件）不作为 v0.3 主形态**，仅保留薄实验包（见 C3/C4）。〔中，判断〕
- **最大不确定性**：DSH 0.2.2-rc.1 仍是预发布，插件 API/市场形态可能变；本机未实测安装/调用插件，也未在 Claude Code 上实测 skill 同步（未装 Claude Code）。〔高：未验证清单〕

## A. DSH 可编程面（本地权威）

### A1. 版本、插件模型与生命周期

| 事实 | 证据 | conf |
|---|---|---|
| 本机 DSH = 0.2.2-rc.1（Desktop `desktopVersion`）；CLI `dsh --version` 输出 `0.2.2-rc.1` | `/Applications/DeepSeek Harness.app/Contents/Resources/runtime/primary-runtime/runtime.json`；CLI 实跑 | 高 |
| 插件 = TypeScript/JS 模块，导出 `apply(ctx)`（函数/对象/class 三种形态）；依赖用 `inject` 声明；资源用 `ctx.effect()` 清理；Fiber 状态机 PENDING→ACTIVE→DISPOSED，HMR 可热替换 | [framework/index.md](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/user/develop/framework/index.md)、[basic/index.md](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/user/develop/basic/index.md) | 高 |
| **hooks 不是本机能力**：asar 内 `@deepseek-ai/*` 无 `dsh-hook-*` 包；扩展点靠插件内 `ctx.on` / waterfall listener（`agent/pre-step`、`tools/pre-execute` 等），不是用户级 hooks 配置文件 | asar 包清单扫描（`_asar/` 抽取方法见附录） | 高（本机缺包）/ 中（未来版本可能加） |

### A2. 一个 plugin/bundle 包能注册什么

| 能力 | 注册接口（最小形态） | 证据 | conf |
|---|---|---|---|
| **model tool** | `inject=['tools']`；`ctx.tools.register(defineTool({name, description, parameters, output:{schema,render}, execute}))` | [basic/tool.md](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/user/develop/basic/tool.md)；本地 `_asar/@deepseek-ai/dsh-tools/README.md:43` | 高 |
| **人类 slash command**（不产生 model message） | `ctx.commands.register({name, description, input?, handler})`；命中记录 `command/run`/`command/done` | [commands.md](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/commands.md)；本地 `_asar/@deepseek-ai/dsh-commands/README.md:32` | 高 |
| **skill（内嵌）** | `ctx.skills.register({name, description, content, resourceBase?, invocation?})` | [skills.md](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/skills.md) | 高 |
| **skill（打包 provider）** | `ctx.skills.registerProvider(control => ({name, list, get}))`；skill 正文/资源随包分发，`resourceBase` 支持 directory/url/opaque | skills.md；本地 `_asar/@deepseek-ai/dsh-skill-badge/lib/index.js`（badge provider 实例） | 高 |
| **GUI panel/slot** | `package.json` 加 `dsh.client`（platform/immediately/inject/external）+ `./client` 导出；`ctx.slots.inject` / `ctx.slots.register` 注册 React 组件 | 本地 `_asar/.../cordis-plugin-development/references/ui-plugin.md:3,11` | 高 |
| **后台 service / 事件钩子** | class 组件默认导出 `Service`；`ctx.on(...)`、`ctx.effect(...)`、`agent/pre-step` 等 waterfall listener、`ctx.systemPrompt.section()` | framework/index.md；本地 `references/practices.md:16-22` | 高 |
| **MCP 工具** | 配置型 bundle：patch 内插入 `@deepseek-ai/dsh-mcp-client` row（streamable-http/stdio），无 Host/Client 代码 | 本地 `references/mcp-bundle.md:3`；[guide/mcp-memory.md](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/user/guide/mcp-memory.md) | 高 |

### A3. bundle / profile manifest 与安装（准确形态）

```json
// 可分发单元 = bundle（dsh.bundle 而非 dsh.profile）
{"name":"dsh-hello-plugin","version":"0.1.0","type":"module","main":"index.js","files":["index.js","cordis.patch.yml"],
 "dsh":{"bundle":{"patch":"./cordis.patch.yml"}},"engines":{"dsh":">=0.2.0 <0.3.0"}}
```
```yaml
# cordis.patch.yml：insert/override 行，row 用包名（Node 解析到已安装代码）
- insert: [{ id: hello, name: dsh-hello-plugin }]
```

| 项 | 事实 | 证据 | conf |
|---|---|---|---|
| `dsh` 字段 | `dsh.bundle.patch`（string 或有序数组）；可选 `dsh.manifestVersion`（当前 1）、`dsh.bundle.platforms`、`dsh.client`、`listedByDefault`、`icon`/locale 展示元数据 | publish.md；本地 `_asar/@deepseek-ai/dsh-package-manifest/README.md:39-56`；`references/host-plugin.md:5-53` | 高 |
| 版本门槛 | 安装与 profile 启动都校验 `engines.dsh`，否则校验 `@deepseek-ai/dsh*` peer 范围；不满足则拒绝；豁免 = profile `compatibility.json` 里 exact `pkg@ver` ↔ exact DSH runtime，需 `acceptRisk` | publish.md；本地 `_asar/.../dsh-plugin-manager/README.md:75-83`、`_asar/@deepseek-ai/dsh/README.md:39`；实例：`dsh-subagent-codex@0.2.1-rc.3` peer 全为 `0.2.1-rc.3` vs runtime `0.2.2-rc.1` → 不可兼容〔高〕 | 高 |
| 安装 spec | `dsh plugin --profile <p> add <spec>`（转发 pnpm）；spec 支持 npm 名/范围/tag/alias、本地目录 `./pkg`、tarball `./pkg.tgz`、git `github:you/repo#sha`；`plugin_manager.install_bundle` 同族（registry/local absolute/git/tarball，可带 `approvedBuilds`） | publish.md；本地 `dsh-plugin-manager/README.md:31,46,50` | 高 |
| 启用/禁用 | profile `package.json` 的 `dsh.profile.bundles` 有序列表选择 bundle；单个 plugin row 用 `disabled` 覆盖（profile `cordis.patch.yml`）；GUI Plugins 页/`plugin_manager` 工具持久化 | 本地 plugin-manager README:31,40；publish.md | 高 |
| HMR | `dsh-hmr`（launcher 有 profileContext 时启用，web profile `patchReload: live`）：配置/recomposition 与 linked 包改动可不重启生效；否则 `restart-required`；包安装本身在 HMR 队列之外 | 本地 `_asar/@deepseek-ai/dsh-hmr/README.md:27,49`；`~/.dsh/profiles/web/package.json` | 高 |
| 第三方分发 | 官方入口：npm/Registry + Official on-demand catalog；第三方：**experimental** "Custom plugin indexes"（format 1 JSON，npm/git source，`engines.dsh`），默认关闭，索引未签名，"DSH checks the file format but not those claims. Add only sources you trust" | [guide/plugin-market.md](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/user/guide/plugin-market.md) | 高 |

### A4. skills 机制（DSH 原生）

| 事实 | 证据 | conf |
|---|---|---|
| 发现根（rank 100→600）：项目 `.dsh/skills`、项目 `.agents/skills`、custom dirs、用户 `~/.dsh/skills`、用户 `~/.agents/skills`、bundled；项目根 = 最近 `.git` 祖先 | [skills.md](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/skills.md)（Local discovery priority）；本机实测 `.dsh/skills` 6 个、`~/.agents/skills` 用户级存在 | 高 |
| 形态：`<name>/SKILL.md` 目录 bundle 或 `<name>.md` 平铺；**只扫一层**，嵌套 `**/SKILL.md` 不发现 | skills.md；本地 `_asar/@deepseek-ai/dsh-skill-filesystem/README.md:36,147` | 高 |
| frontmatter：必填 `name`（kebab-case）+ `description`；可选 `whenToUse`、`metadata`、`disable-model-invocation`、`user-invocable`；正文每次加载重读 | 本地 skill-filesystem README:36-38；skills.md（SkillSummary 含 whenToUse） | 高 |
| 触发：启动后 durable catalog 只给模型 `name` + 截断 description（默认 500 字符，**`whenToUse` 不进 catalog/加载包装**）；模型按 description 调 `skill({name})` 取正文；用户可用 `/name` 显式调用（user-invocable） | skills.md；本地 `_asar/@deepseek-ai/dsh-tool-skill/README.md:54-56,263`、`dsh-client-ui-skill/README.md:12` | 高 |
| 附属资源：支持 `references/`/`scripts/`/`assets/`，`skill` 结果给"Base directory for this skill: <path>"，按需自行读取；资源改动不触发 catalog 刷新；正文无大小上限 | skills.md；本地 tool-skill README:199-204,264-265；skill-filesystem README:81 | 高 |
| 插件分发 skill：内嵌 `ctx.skills.register` 或打包 provider（badge/office 先例）；bundle 可依赖 provider 包并 insert 其 row；**profile 级安装对使用该 profile 的所有项目生效**，不是仓库级 | skills.md；`_asar/@deepseek-ai/dsh-experimental-badge-skill-bundle/package.json`、`_asar/@deepseek-ai/dsh-sdk-app/README.md`（skill-office row） | 高 |

### A5. 安全模型（插件 vs skill 的关键差异）

- **插件执行任意代码**：`apply` 是普通 Node 模块；官方文档明确 git 安装的 build-script 放行 = "permission to execute the package's code on your machine at install time, **outside any sandbox** the agent runs under"；本地 plugin-manager README:31 亦明确 "installed Host code executes **in-process outside the workspace sandbox**"。〔高〕
- **安装需要高权限/审批**：`plugin_manager` 每个 action（含 list）需 `danger-full-access` 或该次调用审批；build script 还需单独 `approvedBuilds`；服务只校验名称，不校验对话审批。〔高：本地 plugin-manager README:31,72〕
- **配置层也执行代码**：patch 支持 `!!js` 表达式（在组合时执行）；profile/home patch 是受信应用组合。〔高：本地 host-plugin.md:3、`ds-harness-remote/cordis.patch.yml` 实例〕
- **第三方索引不受信**：索引/插件元数据未签名，安装确认是唯一信任闸门；market 仍 experimental、默认关闭。〔高：plugin-market.md〕
- skill 的风险面小得多：只读文本+资源读取，不注册代码/工具；但仍可包含任意指令（prompt injection 面），且资源路径由 provider 决定。〔中：由机制推导〕

### A6. kit 现状与 skill-only 先例

- kit v0.2.11：无根 `package.json`（不能直接 `npm publish` / 无 bin）；`adapters/manifest.json` 的 `dsh` 为 `[]`；strict profile 渲染 `.dsh/skills/{verify-change,handoff,red-team}`；`tools/adapters.py` 单源同步到 `.claude/skills`。〔高：本地 kit 文件〕本仓已有 6 个项目级 skill 且被本会话 DSH catalog 实时发现（session-bootstrap/verify-change/handoff/red-team/harness-audit/device-verify）。〔高：本地 runtime〕
- skill-only bundle 先例：`@deepseek-ai/dsh-experimental-badge-skill-bundle`（bundle 依赖 `dsh-skill-badge` provider，row 挂 provider；skill 正文+PNG 在 provider 包资产里）；`dsh-sdk-app` 的 patch 挂 `skill-office` provider（`assetRoot` 可配置）。〔高：本地 `_asar/` + sdk-app README〕

## B. 方案对比

| | 形态 | 安装/升级 | 跨 agent | 能力上限 | 用户成本 | 主要失败模式 |
|---|---|---|---|---|---|---|
| **A. 纯 skill 文件** | kit 生成/写入目标仓 `.dsh/skills/`；adapters 镜像到 `.claude/skills/` | git tag/CLI；文件随仓库版本 | 最好（DSH/Claude Code/Codex 等 SKILL.md 生态） | 仅指令+资源；无 tool/command/UI/lifecycle | 最低：无运行时代码、无审批 | 描述路由失败（catalog 只看 name+desc）；skill 多了占 catalog token；行为无强制 |
| **B. 单总控 skill + references** | 1 个入口 skill（"何时用 kit/五子系统路由"）+ `references/` 按需读（接入/日常/验收/审计） | 同 A（纯文件） | 最好（标准字段 + 资源目录） | 同 A（references 是文件读取，不是可执行） | 低；catalog 只有 1 条 | 路由 skill 描述不佳会漏触发；references 需模型主动读、多一步；正文大时一次载入成本高 |
| **C. DSH bundle 插件** | npm 包 + `dsh.bundle.patch`；可含 skill provider/内嵌 skill + tool + command + UI + service | `plugin_manager`/`dsh plugin add`；版本门槛 `engines.dsh`；HMR 或重启 | **仅 DSH**（profile 级；Claude Code 需另一套插件） | 最高：可注册 tool/command/UI/service/事件；模型可直接调用 | 高：装到用户 profile、需 full-access/审批、代码 sandbox 外、升级受 DSH 版本约束 | 版本不兼容被拒/需豁免；安装审批摩擦；profile 全局影响所有项目；API 预发布漂移；插件代码信任风险 |
| **D. CLI-only** | kit 脚本（`harness-init/adopt/selftest/prompt`）+ 目标仓 Makefile/门禁 | git clone/tag；升级路径已验证（v0.2.2→v0.2.3） | 最好（任何能跑 shell 的 agent） | 无 model 原生原语；靠 shell 工具调用 | 最低；但 agent 需自行发现命令 | 模型不知道何时跑/跑错命令；输出非结构化；无 catalog 路由 |
| **E. MCP server（补充）** | kit 提供 MCP server（tools: init/verify/evidence），由 DSH 的 `dsh-mcp-client` 或各 agent MCP 配置接入 | MCP 配置 + 进程；跨 agent MCP 生态好 | 较好（MCP 通用） | 仅 tools（无 GUI/command/skill/lifecycle） | 中：需起 server/配 MCP；网络/进程管理 | 传输/生命周期/权限复杂；多一个运行时；kit 无需引入（CLI 已够） |

> 说明：C 的"能力上限"最高，但 kit 的核心价值（指令+门禁+证据）已被 D 与 B 覆盖；C 的增量主要是"调用形态"和"分发便利"，不是能力缺口。

## C. 结论与推荐

### C1. 对 DSH，封装成插件的收益（vs 只发 skill）

1. **模型可直接调用**：`defineTool` 暴露 `harness_check`/`harness_evidence` 等，带参数 schema/输出渲染/policy hook，比让模型拼 shell 命令更稳。〔高：tool.md〕
2. **人类入口**：`/harness` 等 slash command 直接跑，不消耗 model message。〔高：commands.md〕
3. **能力形态扩展**：GUI 面板（评分卡/审计）、后台 service/事件（agent pre-step 注入状态）、MCP 配置、skill 打包分发。〔高：A2〕
4. **版本化安装与升级**：`plugin_manager` 管依赖/选择/更新，`engines.dsh` 门槛 + 官方/第三方索引，比"克隆 git 再跑脚本"更像产品分发；且 profile 级一次安装对该 profile 下所有项目生效（对"通用 kit"是收益，对"每仓生成"是错位——见 C2）。〔高：plugin-manager/plugin-market 文档〕

### C2. 成本 / 风险

- **信任与权限**：安装即执行任意代码、sandbox 外、需 full-access/审批、git 安装还需放行 build script；企业/多人环境需要额外安全评审。〔高〕
- **版本耦合**：DSH 0.2.2-rc.1 预发布，插件 API/市场仍 experimental；kit 的 140 个 kit 测试无法覆盖 DSH 版本矩阵，`engines.dsh` 只挡住不兼容，不保证 API 可用。〔高（版本）/ 中（API 稳定性判断）〕
- **定位冲突**：kit 明示"不是依赖、生成物可整目录删除、不 import 进业务运行时、薄适配/可退出"（governance §1 #6/#9）；插件是 profile 级运行时代码，违反"可退出"直觉。〔高：kit governance〕
- **作用域错位**：插件对 profile 内**所有项目**生效；而 kit 的 AGENTS/plans/evidence 是**每仓生成**的。通用 skill/流程可做成插件，仓库特定指令与门禁仍必须落仓 → 双轨真源风险。〔高（机制）/ 中（设计判断）〕
- **跨 agent 归零 + 分发基建缺失**：C 只服务 DSH（A/B/D 可服务 Claude Code/Codex/Cursor 等，跨 agent 是 kit 卖点）；且 kit 无 npm `package.json`/发布流程，做 C 需新增打包、registry/索引、版本发布、安全审查整套运维。〔高：本地 kit 文件〕

### C3. 推荐（v0.3 主形态）与"只有插件能做"清单

**推荐：D 为底座 + B 为入口（CLI + 单总控 skill + references）；A 作为降级/兼容兜底；C 不在 v0.3 主路径，只做可选实验包。**

理由：
1. kit 的差异化是"完成声明可机械否证"——执行体应是 CLI/门禁/证据 JSON，skill 只是路由与动作提示；C 不能替代，只会让逻辑分散到两处（违反单一真源）。〔中，判断〕
2. 跨 agent 与"可退出"是 kit 的定位与采用门槛；A/B/D 全满足，C 只满足 DSH。〔高〕
3. D 的升级路径已有真实证据（v0.2.2→v0.2.3 在 Android 存量仓验证），C 无历史且受预发布版本与审批摩擦影响；若未来 DSH 插件 API 稳定、用户明确要"agent 直接调用门禁"，先把 **C 做成薄壳**（tool/command 只调 CLI，不搬逻辑）再评估。〔高：kit README/governance〕

**只有插件能做（skill/CLI 做不到或明显更差）**：
- 注册 model-callable tool（参数校验、输出渲染、policy hook、PTC 兼容）；〔高〕
- 注册人类 slash command（不产生 model message、可带 attachments）；〔高〕
- GUI slot/panel（评分卡、审计页）与 theme/locale 集成；〔高〕
- 后台 service 与 agent 生命周期/工具前后置事件监听（`agent/pre-step`、`tools/pre-execute`、`systemPrompt.section`）；〔高〕
- 把 skill 以 provider/内嵌形式**随 profile 安装分发**（含资产）；〔高〕
- MCP 配置型 bundle（无代码也可配置 server）；〔高〕
- 能力组合/替换 provider（同一 service 多 provider 通过 cordis 层切换）。〔高〕

skill 做不到的边界：新增可调用原语、拦截/改写工具调用、注入每次请求的上下文（除非插件）、渲染 UI、管理安装/权限。

### C4. v0.3 最小可行验证（若试 C，建议放 v0.4 实验分支）

1. **spike 包**：临时目录建 `kit-plugin-spike/`（不进 kit 发布物）：`package.json`（`dsh.bundle.patch`、`engines.dsh: ">=0.2.2-rc.1 <0.3.0"`、无 dependencies/build script、纯 JS）+ `cordis.patch.yml`（insert row）+ `index.js`（`inject=['tools']`，`harness_check` tool 调 `make check` 返回 exit/stdout，只读 cwd）；可选 `/harness` command。
2. **隔离安装**：用独立 `DSH_HOME`/非默认 profile（避免污染本机 web/desktop），`dsh plugin --profile spike-eval add ./kit-plugin-spike` 或 `plugin_manager install_bundle`（target=绝对目录；本机未实测，预期需 full-access/审批）。
3. **验证**：`dsh --profile spike-eval --dump-config` 出现自己的 layer；新会话工具列表出现 `harness_check` 且能调用并返回 exit code；`/harness` 命令可执行；`plugin_manager list_bundles` 显示安装态；卸载后 row/依赖清理干净。
4. **skill 侧并行验证 + 证据**：临时空白仓 `harness-init --profile strict` → 新 DSH 会话确认 catalog 出现 3 个 skill、`/verify-change` 可用；`tools/adapters.py sync` 生成 `.claude/skills`（无 Claude Code，标未验证）。工具输出/退出码、`--dump-config` 片段、安装/卸载前后 diff 写入 `harness/runs/kit-eval/`（不入库）；结论只写有证据的部分。

## 证据与未验证

**本地证据（只读抽取，gitignored）**
- `harness/runs/kit-eval/_asar/@deepseek-ai/{dsh-plugin-manager,dsh-skill,dsh-skill-filesystem,dsh-tool-skill,dsh-hmr,dsh-commands,dsh-tools,dsh-package-manifest,dsh-sdk-app,dsh-skill-badge}/README.md`（0.2.2-rc.1 原文）
- `harness/runs/kit-eval/_asar/@deepseek-ai/dsh-agent-preset/skills/cordis-plugin-development/{SKILL.md,references/*.md}`（DSH 官方插件开发技能，含 manifest/tool/UI/MCP/安全说明）
- `harness/runs/kit-eval/_asar/@deepseek-ai/dsh-experimental-badge-skill-bundle/package.json`（skill-only bundle 先例）
- kit：`harness-kit/adapters/manifest.json`（`dsh: []`）、`harness-kit/adapters/dsh/README.md`、`harness-kit/profiles/strict.json`（3 skills）、`harness-kit/tools/...`（无 package.json 的 kit 根）
- 抽取方法：Node 读 asar header（`app.asar` 前 8 字节 header size + JSON 索引），按 offset 取文件；脚本与清单见本目录 `_asar/`。

**官方 URL（2026-11-11 抓取）**
- 插件入门/工具/打包：[basic/index.md](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/user/develop/basic/index.md)、[basic/tool.md](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/user/develop/basic/tool.md)、[basic/publish.md](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/user/develop/basic/publish.md)
- 生命周期/HMR：[framework/index.md](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/user/develop/framework/index.md)｜skills：[subsystems/skills.md](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/skills.md)
- commands：[subsystems/commands.md](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/commands.md)｜第三方分发：[user/guide/plugin-market.md](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/user/guide/plugin-market.md)

**未验证 / 低置信度**
1. 未实际安装/运行任何 DSH 插件（本机 profile 未改）；C4 步骤是计划，不是已执行证据。
2. 未验证 `plugin_manager` GUI/工具的完整审批流程（仅文档+本会话工具 schema）。
3. hooks：本机安装包无 `dsh-hook-*` 包，但历史 profile `node_modules` 有指向已删除 dev checkout 的 `dsh-hook-protocol`/`dsh-hooks-*` 断链——未来版本可能支持，不能作为 v0.3 依赖。
4. DSH 是否加入 Agent Skills/AAIF 标准列表未证实（research-ecosystem §F）。
5. Claude Code 侧 skill 实际发现未验证（未装 Claude Code）。6. DSH 插件 API 在 0.3 的稳定性/兼容策略未知；`dsh.manifestVersion` 当前仅声明、安装器不强制。
