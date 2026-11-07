---
id: 2026-11-06-benchmark-opensource
status: active
level: L2
owner: david
updated: 2026-11-06
scope:
  allow:              # 本轮只做「公开面 + 文档 + 过程档案」收敛；不动业务代码
    - README.md
    - LICENSE
    - CONTRIBUTING.md
    - HARNESS.md
    - AGENTS.md
    - AGENTS.local.md.example
    - HANDOFF.md
    - docs/
    - references/
    - .apm/
    - .dsh/
    - tools/
    - .github/
    - .githooks/
    - Makefile
    - .gitignore
    - prototype/
    - Order/
    - Duiyi.xcodeproj/project.pbxproj   # 仅脱敏：移除 DEVELOPMENT_TEAM / 真实签名信息（D-B9）
  deny:
    - Duiyi/**/*.swift
    - DuiyiTests/**/*.swift
    - DuiyiUITests/**/*.swift
    - Duiyi.xcodeproj/xcuserdata/
acceptance:           # 标杆化完成判据（每条可复核；详见正文 §4）
  - 首访 5 分钟测试 5/5 问可答（陌生人只按 README 能回答：是什么/为什么值得看/怎么跑/怎么验证/怎么复制整套 harness；记录卡点）
  - 公开面收敛：根目录 markdown ≤5 个；docs/ 过程与历史文档 0 个；新写/重写文档 ≤300 行（现有 docs/02 保留并加导航）；README ≤120 行（如含英文概览 ≤160）、HARNESS ≤260 行
  - 单一事实源：无 HANDOFF 双入口；docs/README 索引 100% 覆盖；0 死链；`git grep` 无历史文档残留引用；重复测试计数/命令表清零；**公开文档白名单 + 数量上限机检通过**（新增/删除公开文档必须显式改白名单）
  - 脱敏（发布红线）：`git grep` 无真实签名 Team ID、设备 CoreDevice ID、`/Users/` 绝对路径（改为占位符或 AGENTS.local.md）
  - 外部可复现：全新 clone 到 /tmp，仅用 python3 执行 `make check` PASS（不依赖 Xcode；记录命令/退出码/环境）
  - 标杆叙事：HARNESS.md 重写 + `docs/harness-scorecard.md`（五子系统评分 ≥4/5，含独立复评日期与证据）
  - 开源包装：LICENSE + CONTRIBUTING + issue/PR 模板 + 真实截图 + README 徽章；GitHub `v1.0.0` release 已发布
  - 工具无关：同一套 AGENTS/门禁/证据在 DSH 与 Claude Code（+DeepSeek 模型）下均有适配说明；`make adapters-check` PASS；至少一次 Claude Code headless 跑通记录（无环境则标未验证）
  - 模板：`harness-kit` 在空白/真实项目上 10 分钟接入并 `make check` PASS，且无 Duiyi 专用引用（Phase 5）
verify:
  - make verify-static
  - make check-plan
  - python3 -m unittest discover -s tools/tests -q
  - git clone --depth 1 . /tmp/duiyi-fresh && (cd /tmp/duiyi-fresh && make check)
  - make resume
---

# 标杆开源化与文档信息架构重构 · 执行计划（L2）

> 状态：**方案待确认（本轮未执行任何删除/迁移）**　|　级别：L2　|　日期：2026-11-06
> 上游：`.apm/plans/2026-11-05-harness-engineering.md`（Phase 0/1 已完成并提交；Phase 2/3 未执行，见本文 §9 交接）
> 定位：把「Harness Engineering 落地」升级为「可被陌生人看懂、复现、采用的开源标杆」；核心动作是**减法**，不是继续加机制。
> 计划入库规则：不写本机绝对路径、密钥、设备 UDID；只写仓库相对路径。

## 0. 结论摘要（TL;DR）

1. **Harness 评估结论（2026-11-06 现状）**：五子系统 **Instructions 4 / State 4 / Verification 4 / Scope 3.5 / Session Lifecycle 4**（满分 5，综合约 **78–80%**）。改造前独立审计为 **2.5/5**；本轮已把「文档型 harness」升级为「静态门禁 + 结构化证据 + 三值判定 + 四层验证」的可运行闭环。另有一次独立只读审计（2026-11-06，docs 子代理）按「对外标杆成熟度」评 **17/35 = 2.4/5**，并把「证据可审计」压到 3/5：README 头条数字未逐条链到 evidence、部分 evidence 产物换机器不可复核。
2. **等级判定**：已达到「L3 可审计」——agent 的完成声明可被 `make verify-claim` 三值否证；尚未达到「L4 自我改进」（审计未自动打分、无固定指标）与「L5 可复制/可传播」（陌生人看不懂、跑不起来、复制不走）。
3. **距标杆目标的距离**：**内部工程 ≈80%，对外标杆 ≈49%（17/35），加权综合约 60%**。标杆不看"体系是否存在"，只看"陌生人 5 分钟能否理解、10 分钟能否复现、30 分钟能否复制"——这三项目前都不成立。差距不是门禁机制，而是首访入口、开源治理、文档 IA、脱敏与叙事。
4. **最大问题不是缺能力，而是缺减法 + 缺脱敏**：40 个入库 markdown 中约 1/3 是过程/历史文档；HANDOFF 483 行与 docs/21 重复；docs/14–21 共 897 行历史记录混在主线；`.apm` 6.8MB/447 个忽略产物 + 3 个 raw baseline JSON（3114 行）入库；根目录无 LICENSE/CONTRIBUTING/截图/英文概览。**更严重的是：真实签名 Team、设备 CoreDevice ID、`/Users/...` 绝对路径已入库（违反自身铁律 8），开源发布前必须脱敏。**
5. **优化主线（一句话）**：**先做减法（文档 IA）→ 再做叙事（Harness 案例与方法）→ 再做复现（干净环境 10 分钟验证）→ 最后发布与外部验证**；产品行为测试（P0-1/P0-3）独立排期，不阻塞标杆化。
6. **本轮范围**：只改公开面、文档、过程档案与门禁引用；**不改业务代码**（scope.deny 已锁）。分 4 个可回滚阶段，预计 **4–6 个工作会话（约 4–5 人日）**。
7. **待确认**：许可证、HANDOFF 处置、历史文档删除方式、仓库改名与发布节奏，见 §5 决策表；确认后从 Phase 1 开始执行。
8. **工具无关 + 可移植（2026-11-07 补充）**：AGENTS.md 已被 DSH 与 Claude Code 原生读取（Claude Code v2.1.277+ 可直接读 AGENTS.md），因此把规范写成 **AGENTS 树 + CLI 门禁 + 证据**，工具适配只做薄层（skills 同步、Claude hooks 示例、subagent 示例）；Phase 5 抽成 `harness-kit` 模板（profiles + 脚手架），用于其它项目改造。

---

## 1. 现状评估与差距（事实基线，2026-11-06）

### 1.1 五子系统评分（Post Phase 0/1）

| 子系统 | 分数 | 成立依据（可复跑） | 主要缺口 |
| --- | --- | --- | --- |
| Instructions | 4/5 | `make check-harness`：AGENTS ≈1550/1600 token；6 个嵌套 AGENTS；6 个项目 skills；敏感信息 0 命中 | 纯中文；无「规则负载/过期」元数据；HANDOFF 与 docs 仍有重复 |
| State | 4/5 | 计划 front matter/status 机检；`make resume/end`；doctor；证据目录 schema | 唯一计划 744 行实现记录；done 计划、旧 review 未归档；HANDOFF 483 行单文件 |
| Verification | 4/5 | `make verify-static`：docs/架构/计数/harness/计划/证据/脚本单测；`verify-claim` 三值判定；unit/UI/device 三条 clean-tree evidence PASS | 行为测试缺失（P0-1/P0-3）；CI 单测默认 skipped；README 头条数字未逐条链 evidence；外部无法复跑动态层 |
| Scope | 3.5/5 | L0/L1/L2、计划 scope.allow/deny、单 active 计划、红队限定场景 | 无「改动 vs 声明范围」机检；一次一件事靠自觉 |
| Session Lifecycle | 4/5 | session-bootstrap / handoff / verify-change skills；plan brief/resume/end；未验证项单列 | handoff 内容靠自由文本；状态入口多（HANDOFF/docs/21/plan） |
| **综合（自评）** | **≈4/5（78–80%）** | 与改造前独立审计 2.5/5 对比 | 对外标杆维度另评 2.4/5（见 §1.2）；差距在外功不在机制 |

> 口径说明：五子系统分数为自评；「对外标杆成熟度」有 2026-11-06 独立只读审计（17/35）可用，但正式复评仍必须在 Phase 2.3 按评分卡重做并写入 `docs/harness-scorecard.md`；未复评前只能称「自评 78–80%」。

### 1.2 距标杆目标（开源标杆 = 可理解 + 可复现 + 可复制 + 可审计）

| 维度 | 现状（1–5） | 目标 | 差距 |
| --- | --- | --- | --- |
| 体系完整度 | 4 | ≥4 | 已达标（5 静态门禁 + evidence/verify-claim + 6 skills + CI + pre-push） |
| 证据可审计 | 3 | ≥4.5 | 有 3 条 evidence PASS + 三值判定，但 README/文档头条数字未逐条链 evidence，换机器不可复核 |
| 文档可读性/首访体验 | 2 | ≥4 | **最大缺口**：首站=483 行 HANDOFF；3 套文档地图、5 套命令表、897 行历史混排 |
| 开源工程化包装 | 1 | ≥4 | 无 LICENSE/CONTRIBUTING/CHANGELOG/英文/截图/徽章/release |
| 外部可复现 | 2 | ≥4 | 静态门禁任何机器可跑；完整需 Xcode+真机；未验证干净 clone |
| 标杆叙事/采用指南 | 2 | ≥4 | HARNESS 是最强资产但 README 零入口；缺案例、评分卡、"复制到你的仓库" |
| 产品与代码质量 | 3 | ≥4 | 真实 App、120+3 测试、架构 0 违规；P0-1/2/3 未修；无演示素材 |
| **总分（独立审计）** | **17/35 = 2.4/5（≈49%）** | **≥4.2/5（85%）** | 差距集中在外功：入口叙事、开源治理、文档 IA、脱敏与复现 |

> 两个口径分开看：**五子系统自评 78–80%（内部工程）** vs **对外标杆 2.4/5（独立审计）**。这说明"难的一半（门禁/证据/状态）已经做完"，但"对外可见的一半"基本从零开始——这正是本轮主线要补的。

### 1.3 文档面事实（"混乱"的量化证据）

- 入库 markdown **40 个**：根入口 4（README/HANDOFF/HARNESS/AGENTS）、`docs/` 14、`references/` 3、`.apm/` 9、`.dsh/skills/` 6、代码目录嵌套 AGENTS 4。
- `docs/14–21` 是带日期的过程/历史记录，共 **897 行**，但放在文档主线同一层，首访者无法区分「当前规范」与「历史证据」。
- `HANDOFF.md` **483 行**，与 `docs/21-cross-session-handoff.md`（78 行）职责重叠；两者又都与 `.apm/plans/` 的交接职责重叠 → 三处状态源。
- `.apm` 工作区 **6.8MB**：`.apm/runs` 3.9MB/447 个忽略文件；3 个 raw baseline JSON 共 3114 行入库；另有 `report.md`、`issues/`、`reviews/`、`feasibility/`、`white-screen/` 等已过期产物。
- 根目录无 `LICENSE`、`CONTRIBUTING.md`、`.github/ISSUE_TEMPLATE`、真实截图；README 依赖「先读 HANDOFF」，且状态数字有漂移（如设备 iOS 版本）。
- `prototype/` 是 2026-08 的 HTML 视觉稿，已与实现脱节；`docs/diagrams/` 7 张 SVG 有「可能滞后」声明但仍作为事实入口。
- `build/` 705MB（已忽略）与 `Order/`（启动优化暂停后的生成物）属于本机/历史遗留，不影响仓库但影响"简洁"观感。
- **多真源**：3 套文档地图（README / docs/README / HANDOFF §7）、5 套命令表、13 行重复测试计数（违反自身"数字只在 references/verification"规则）、真源优先级口号 3 个版本。
- **发布红线（脱敏）**：真实签名 Team ID（4 个文件）、设备 CoreDevice ID（5 个文件）、`/Users/<name>` 绝对路径（3 个 baseline JSON）已入库；`project.pbxproj` 仍写原开发者 Team/Bundle ID——与根 `AGENTS.md` 铁律 8「签名属本地环境」直接矛盾。
- **命名不可迁移**：`.apm/` 是项目历史缩写（早期 APM 测量），公开/模板无法解释；通用模板需改为可见的 `harness/`（D-B10），并与 `harness-kit` 模板同名，避免"一套方法、两种目录"。

### 1.4 当前流程的"自我阻碍"（为什么必须现在做）

- 新访客路径：README → HANDOFF（483 行）→ docs/README（101 行，含 8 篇历史）→ 迷路；**Harness 的价值反而被过程文档淹没**。
- 任何新访客想验证「这个项目真的可复现吗」时，README 给的是 `open Duiyi.xcodeproj`（需要 Xcode 27.1 + 自己的签名），而不是「无需 Xcode 先跑静态门禁」。
- 过程文档继续增长（本轮 744 行计划、1100 行审计底稿）但没有退出机制 → 仓库越做越"重"，与标杆目标背道而驰。

---

## 2. 目标形态：文档信息架构 v3（四层模型）

### 2.1 分层原则

| 层 | 面向谁 | 内容 | 规则 |
| --- | --- | --- | --- |
| **L1 叙事层** | 首次访问者 / 外部采用者 | README、HARNESS、案例、评分卡 | ≤300 行/篇；一个事实只出现一次；必须能回答"为什么看/怎么跑/怎么复制" |
| **L2 主线层** | 开发者 / 接手者 | docs/01–04、decisions、CONTRIBUTING | 只写当前事实与理由；过程结论压缩成"结论 + 证据 id"，不保留原始记录 |
| **L3 规则层** | AI agent | AGENTS 树、references、skills | 保留；token 预算内；指路不抄写 |
| **L4 档案层** | 维护者 / 审计 | `.apm/`：active plan、evidence、tools、test-baseline、reviews | 不进首屏文档地图；原始产物 gitignore；历史记录只留摘要 |

### 2.2 目标文件树（公开面）

```text
README.md                 # 一屏：定位 + 3 个看点 + 截图 + quickstart + 文档地图（≤160 行，含英文概览）
LICENSE                   # 新增（建议 MIT，见 D-B1）
CONTRIBUTING.md           # 新增：环境/构建/签名/测试/门禁/PR/agent 协作（≤120 行）
CHANGELOG.md              # Phase 4 可选：≤60 行（release notes 为主）
HARNESS.md                # 重写：Harness Engineering 实践案例 + 方法 + 证据 + 采用指南（≤260 行）
AGENTS.md                 # 保留（agent 冷启动；≈1500 token）
AGENTS.local.md.example   # 保留（机器本地事实模板）
docs/
  README.md               # 唯一文档地图（新；≤70 行）
  01-product-design.md    # 保留（产品行为）
  02-architecture.md      # 保留（架构与数据链路）
  03-tech-choices.md      # 保留（选型与理由）
  04-roadmap.md           # 保留（问题/验收/排期唯一源；删除过程记录）
  decisions.md            # 新增：D1–D7 + 本轮决策唯一表（从 HANDOFF §6 迁出）
  case-startup-performance.md  # 新增：由 docs/15–18 蒸馏的"200ms 不可达"完整案例（≤150 行）
  harness-scorecard.md    # 新增（Phase 2）：五子系统评分卡 + 证据 + 复评记录
  images/                 # 新增：真实截图 3–5 张（docs/images/*.png）
  diagrams/               # 保留 2–3 张准确图，删除/更新滞后图
references/
  contracts.md            # 保留（铁律细则）
  verification.md         # 保留（验证矩阵/真机坑；吸收 HANDOFF §2 与 docs/20 的可复用结论）
  workflow.md             # 保留（分级/红队）
.dsh/skills/              # 保留 6 个（标杆展示项目级 skills）
tools/                    # 保留门禁脚本（标杆展示"可机检"）
Makefile                  # 保留命令入口
.githooks/pre-push        # 保留
.github/workflows/        # 保留（Phase 3 合并为单一 verify.yml 并加徽章）
harness/                  # 由 .apm/ git mv 重命名（D-B10）；可见、与模板同名
  README.md               # 档案层索引（与 L1–L3 的边界说明）
  AGENTS.md               # 目录协议
  config.json             # 新增：工具无关配置（路径/预算/命令/evidence claims/adapters）
  plans/                  # active + _template + _archive（旧计划/旧 review 归档）
  evidence/               # schema/TEMPLATE/README + 最近证据摘要
  reviews/                # 只保留与当前/最近复评相关的报告
  tools/                  # device-test.sh / measure-launch.sh（把坑固化成脚本，是标杆资产）
  adapters/               # 新增：claude-code/（CLAUDE.md 可选、hooks 示例、red-team agent）、dsh/（skills 同步说明）
  test-baseline.json      # 保留
.claude/                  # 新增（生成物，可 gitignore 或提交同步副本）：skills 同步、settings.json hooks 示例（D-B11）
```

### 2.3 删除 / 迁移映射（人类可读版）

| 旧位置 | 处置 | 去向 / 理由 |
| --- | --- | --- |
| `HANDOFF.md`（483 行） | **删除**（D-B4 可选保留精简版） | 产品/架构/排期 → 已有 docs/01–04；签名/构建/真机坑 → CONTRIBUTING + references/verification；决策 D1–D7 → docs/decisions.md；交接状态 → active plan（唯一） |
| `docs/21-cross-session-handoff.md` | 删除 | 与 HANDOFF 重复；交接协议已由 `.dsh/skills/handoff` + `make resume/end` 承载 |
| `docs/14`–`18`（启动链） | 蒸馏后删除 | 结论与证据链合并为 `docs/case-startup-performance.md`；原始记录留 git 历史 |
| `docs/19`（持久化修复） | 删除 | 结论进 `docs/04` 已完成区 + evidence id；修复过程留 git 历史 |
| `docs/20`（UI 测试假绿） | 蒸馏后删除 | 设备预热/自动化密码/模拟器能力结论并入 `references/verification.md`；流程案例进 HARNESS 的"坑"一节 |
| `docs/15` 等引用的启动优化原始数据 | 删除入库 JSON | raw baseline 3 个 JSON（3114 行）→ 删；摘要/方法进案例页；原始数据由脚本可重建 |
| `.apm/report.md`、`.apm/feasibility/`、`.apm/white-screen/README.md` | 删除 | 已被 docs/17/18 结论取代；原始记录留 git 历史 |
| `.apm/issues/*.json`（7 个） | 删除 | 问题结论进 docs/04 与 case；issue JSON 可作为历史记录留在 git |
| `.apm/reviews/2026-10-30-*.md`、`.apm/plans/2026-10-30-*.md` | 移入 `.apm/plans/_archive/` | 保留可追溯，不占首屏 |
| `.apm/plans/2026-11-05-harness-engineering.md` | `status: done` + 归档 | Phase 0/1 已完成；Phase 2/3 移交本计划 §9 |
| `.apm/` 目录名 | **重命名 `harness/`（`git mv`，D-B10）** | 公开/模板可解释；与 `harness-kit` 同名；同步更新 tools/plan.py/check-docs/CI/AGENTS 路径 |
| 无（新增） | **`.claude/` + `harness/adapters/claude-code/`（D-B11）** | Claude Code hooks/skills 薄适配，不默认加载；`make adapters-check` 防漂移 |
| `prototype/`（3 个 HTML） | 删除 | 2026-08 视觉稿，与实现脱节；截图替代 |
| `Order/App.order` + `tools/generate-order-file.sh` | 保留（P2 再议） | 启动优化已暂停但 Release 配置可能引用；不在文档首屏 |
| `docs/diagrams/` 7 张 SVG | 精简为 2–3 张 | 保留准确的分层/链路图；滞后图删除或重绘（Phase 1 校验） |

> 净效果：对外可见 markdown（根 + docs + references）**21 → 约 16**；`docs/` 从 14 篇降到 9 篇（历史文档 8 篇 897 行清零，新增 decisions/case/scorecard 3 篇）；全仓库入库 markdown 40 → 约 30–32（`.dsh/skills` 6 篇、`harness/` 过程档案与 adapters 保留）；根目录文档从 4 个内部/混合文档 → 4 个清晰入口 + LICENSE/CONTRIBUTING。

---

### 2.4 工具无关核心 + Agent 适配层（DSH / Claude Code / 其它）

设计原则：**规范与证据不绑定 Agent 工具；工具差异只放在薄适配层**。这样模型换代（V4.1 flash → 新模型）或 agent shell 更换（DSH ↔ Claude Code）都不需要重写仓库。

| 层 | 内容（仓库内唯一源） | DSH | Claude Code | 其它 Agent |
| --- | --- | --- | --- | --- |
| 指令 | `AGENTS.md` 树（根 + 嵌套 + local overlay） | 原生读取（含预算/嵌套发现） | **v2.1.277+ 原生读取 AGENTS.md**（默认 claude-md-or-agents-md） | 多数支持 AGENTS.md |
| 动作 | `skills/*/SKILL.md`（验证/交接/红队/审计/真机） | `.dsh/skills/` 自动发现 | `.claude/skills/`（由同步生成） | 复制/适配 |
| 自动执行 | `make check`（0.3s）/ `make verify-static`（4.3s） | 0.2.1-rc.5 无仓库级 hooks；用 skills + pre-push + CI | `PostToolUse`/`Stop` hooks（`.claude/settings.json` 示例） | CI / pre-commit |
| 状态 | `harness/plans` + `make resume/end` | 仓库文件 + 会话 goal/plan | plan mode + 仓库文件 | 仓库文件 |
| 证据 | `harness/evidence` + `verify-claim` | 仓库脚本 | 仓库脚本 | 仓库脚本 |
| 模型/凭据 | 不写入仓库（`.env.example` + 文档） | profile 配置（用户级） | `ANTHROPIC_BASE_URL` 等环境变量；DeepSeek 官方支持 | 各自配置 |

- **skills 单源**：以 `.dsh/skills/` 为仓内规范源，`make adapters-sync` 生成 `.claude/skills/`，`make adapters-check` 校验无漂移（用 hash/内容比对，不依赖 symlink，规避 Windows 问题）。
- **Claude Code 适配资产**（`harness/adapters/claude-code/`，不默认加载）：`CLAUDE.md`（仅 `@AGENTS.md`，可选）、`settings.hooks.example.json`（**PostToolUse** 跑 `make check`、**Stop** 跑 `make verify-static`，把"验证"变成生命周期强制）、`agents/red-team.md`（独立复核 subagent）。
- **DSH 适配**：当前版本无仓库级 hooks，等价能力 = skills + pre-push + CI + 会话内 `verify-change` skill；`dsh-hooks-claude-code` 包名说明未来可能复用 Claude hooks 配置（预留，不承诺）。
- **模型可换**：门禁与证据与模型无关；evidence schema v2（D-B13）给 `environment` 增加可选 `agent` / `model` / `harnessVersion`，用于跨 agent/模型对比（如 DSH+V4.1 flash vs Claude Code+DeepSeek V4 Pro）。
- **DeepSeek × Claude Code 官方路径**：`ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic` + `ANTHROPIC_AUTH_TOKEN` + 模型映射变量（官方集成文档）；仓库只放示例不放 key。

## 3. 优化主线与优先级

```text
Phase 1 文档 IA 重构（做减法）      ← 用户痛点；最大收益；所有后续阶段的地基
   ├─ 1a 新增入口（README/CONTRIBUTING/LICENSE/decisions）
   ├─ 1b 蒸馏 + 删除历史文档 / HANDOFF / prototype / .apm 过期产物
   ├─ 1c 同步引用与门禁（check-docs/check-harness/CI/AGENTS/skills）
   └─ 1d 真实截图 + 首访测试
Phase 2 标杆叙事（HARNESS 重写 + 评分卡 + 独立复评 + 案例）   ← 决定"像不像标杆"
Phase 3 外部可复现（干净 clone 10 分钟验证 + CI/徽章 + doc 合并） ← 决定"能不能被复制"
Phase 4 发布与外部验证（v1.0.0 + 元数据 + 真实陌生人测试）      ← 决定"是否成为标杆"
Phase 5 模板抽取：`harness-kit`（profiles + adapters + 脚手架 + playbook），其它项目 10 分钟接入
Phase 6（可选，独立排期）产品可信度：P0-1/P0-3 行为测试 + 红队 + 证据
Ongoing  月度 harness 审计 + 文档季度修剪 + 证据保留策略
```

排序理由（Harness Engineering 视角）：

1. **先降 context/导航成本**：文档是 agent 与人的共同前馈；首访失败 = 前馈失败，后面所有门禁都无人看到。
2. **再补叙事**：标杆的差异点是"真实仓库 + 可审计证据"，不是又一套框架；必须用案例讲清楚，而不是罗列机制。
3. **再证可复现**：没有"干净环境跑通"的证据，"开源标杆"只是自述；这是 verification 原则的对外延伸。
4. **最后发布**：发布是外部验证的开始（L5），不是结束；前 3 阶段没做完就发布只会放大噪音。
5. **产品行为测试不阻塞**：它是产品可信度，属于另一条线；避免把"标杆化"拖成"全量测试工程"。

---

## 4. 执行阶段（每阶段 = 一次 L2 子任务 + 可回滚提交）

### Phase 1 · 文档信息架构重构（P0，预计 2–3 个工作会话）

**目标**：陌生人按 README 5 分钟看懂；公开面只保留主线；所有引用与门禁同步为绿。

| # | 任务 | 产出 | 验收 |
| --- | --- | --- | --- |
| 1.1 | 基线冻结与首访测试（改造前） | 首访 5 问答案 + 卡点清单（写入本计划 §验证证据） | 5 问中可答数 ≤2（记录失败证据） |
| 1.2 | 新增入口文件 | `LICENSE`、`CONTRIBUTING.md`、`docs/decisions.md`（D1–D7 迁移）、`.github/ISSUE_TEMPLATE.md` + `PULL_REQUEST_TEMPLATE.md` | 内容 ≤ 目标行数；链接可解析 |
| 1.3 | README 重写 | 新 `README.md`（≤120 行）：定位 / 3 个看点（端侧隐私、Harness 实践、可审计证据）/ 截图 / quickstart（无需 Xcode 先跑 `make check`）/ 文档地图 / 许可证 | 首访 5 问中 5 问可答（自测） |
| 1.4 | 蒸馏历史文档 | `docs/case-startup-performance.md`（≤150 行：目标 → 方法 → A/B → 归因 → 结论"不可达"→ 为什么不继续）；删除 docs/14–21 | 结论与数字可追溯到 evidence id / git commit |
| 1.5 | 拆分 HANDOFF | 决策 → `docs/decisions.md`；构建/签名/测试 → `CONTRIBUTING.md`；坑 → `references/verification.md`；会话状态 → active plan；删除 `HANDOFF.md`（D-B4） | `git grep HANDOFF` 仅剩历史记录/archive |
| 1.6 | `.apm` 减法 + 改名 | `.apm/` → **`harness/`**（`git mv`，D-B10）；新建 `harness/README.md` + `harness/config.json`；删除 report/baseline raw/feasibility/issues/white-screen；旧计划/review 移入 `_archive/`；更新目录职责 | `harness/` 入库文件数下降 ≥40%；`make evidence`/`verify-claim` 仍 PASS；全仓库无 `.apm` 路径残留（git 历史除外） |
| 1.7 | 页面与引用同步 | 重写 `docs/README.md`（唯一索引：Start / Reference / Archive / Harness）；去重：3 套文档地图合一、5 套命令表收敛到 Makefile + CONTRIBUTING、13 行重复测试计数改为引用 `references/verification.md`；更新 docs/01–04 交叉引用；更新根/嵌套 AGENTS、references、skills、HARNESS 链接；更新 tools：`check-docs.py` 扫描根（新增 HARNESS/CONTRIBUTING、移除 HANDOFF）**并增加公开文档白名单 + 数量上限（防删了又长回来）**、`plan.py` 建议阅读、`check-harness.py`、`.github/workflows/verify.yml` 路径过滤 | `make verify-static` PASS；0 死链；`git grep -nE 'HANDOFF|docs/(1[4-9]\|2[01])'` 无有效引用（archive 除外）；测试计数只在 references/verification；新增/删除公开文档未改白名单 → 门禁红 |
| 1.8 | 真实截图 | 模拟器/真机截图 3–5 张（首页、面对面、同传、历史/总结）→ `docs/images/`；README 引用 | 图片存在、路径正确、无隐私信息（无设备 UDID/签名） |
| 1.9 | 改造后首访测试 | 同一 5 问 + 卡点复测 | 5/5 可答；记录耗时与卡点 → 本计划证据 |
| 1.10 | **脱敏（发布红线，P0）** | 移除/占位：`project.pbxproj` 的 `DEVELOPMENT_TEAM` 与真实签名信息；HANDOFF/docs/scripts/baseline/issues 中的 CoreDevice ID、UDID、`/Users/...` 绝对路径；`.apm/tools/*.sh` 改为从环境变量/`AGENTS.local.md` 读取设备参数；Bundle ID 保留但注明"示例，替换为你自己的"（若选 D-B9b 则一并替换） | `git grep` 0 命中真实 Team/设备 ID/绝对路径；`make verify-static` PASS；构建/测试仍可跑（或明确记未验证） |

**门禁与回滚**：
- 每一步后跑 `make check`；1.7 后跑 `make verify-static`；1.9 后跑全量。
- **迁移顺序（采纳独立审计建议，避免中途门禁红）**：① 先加新入口/归档容器（不删旧文件）→ ② 迁移内容，旧文件先留指针 → ③ 更新引用 + CI paths + plan.py 阅读清单 + rules-budget → ④ 跑 `make verify-static` → ⑤ 删除旧文件、更新 docs 索引与 docs/AGENTS → ⑥ 复跑门禁 + 补评分卡。
- 删除动作集中在一个提交（`docs: collapse public surface to mainline`），可用 `git revert` 恢复；历史记录永久保留在 git 历史。
- 风险点：`check-docs` 索引/链接、`check-harness` 的 § 引用、verify.yml paths、plan.py 阅读建议、嵌套 AGENTS 中的 HANDOFF 引用、`check-test-baseline.py` 直读 `references/verification.md` 的计数措辞——1.7 必须逐一 grep 清零。

### Phase 2 · Harness 标杆叙事（预计 1–2 个工作会话）

| # | 任务 | 产出 | 验收 |
| --- | --- | --- | --- |
| 2.1 | 重写 `HARNESS.md` | 结构：① 问题（agent 声称完成但不可否证）② 什么是 harness（Model+Harness；guides+sensors；五子系统）③ 本仓库落地矩阵（子系统→机制→文件→可复跑命令）④ 证据怎么验（三值判定/四层矩阵/evidence id）⑤ 踩坑与取舍（假绿、流程税、真机依赖、token 预算）⑥ 复制到你的仓库（10 步最小版→进阶）⑦ 评分卡与复评 ⑧ 局限与未验证 ⑨ 来源 | ≤260 行；每节有可复跑命令或文件锚点 |
| 2.2 | 评分卡 | `docs/harness-scorecard.md`：五子系统评分 + 每项证据 + 评分方法 + 历史复评记录 + 与改造前 2.5/5 对比 | 每个分数有 file/命令证据；未验证项单列 |
| 2.3 | 独立复评 | 由独立只读审计（fresh agent / 红队式）按评分卡复评并写入 scorecard；标注"独立复评"日期与局限 | 五子系统 ≥4/5；结论可复核 |
| 2.4 | README ↔ HARNESS 互链 | README 的"为什么值得看"指向 HARNESS；HARNESS 提供"5 分钟体验路径" | 首访可 2 跳内到达证据演示 |
| 2.5 | 案例打磨 | `case-startup-performance.md` 增加"证据链"小节（命令、commit、evidence id、环境、n≥10、p 值） | 每个数字可追溯到命令/提交/证据 |
| 2.6 | Agent 适配层 | `harness/adapters/claude-code/`（CLAUDE.md 可选、`settings.hooks.example.json`、`agents/red-team.md`）；`make adapters-sync` + `make adapters-check`（skills 单源 `.dsh/skills` → `.claude/skills`，hash 比对）；HARNESS.md 增加"工具适配矩阵"一节 | `make adapters-check` PASS；在 Claude Code（+DeepSeek）环境跑一次 `make check` 并记录（无环境则标未验证） |
| 2.7 | 证据 schema v2 | `environment` 增加可选 `agent` / `model` / `harnessVersion` 字段（向后兼容） | 现有 3 条 evidence 校验仍 PASS；新字段用于跨 agent/模型对比 |

**验收**：`make check` PASS；HARNESS 读完能回答"这套东西怎么复制"；独立复评分数与自评差异有解释。

### Phase 3 · 外部可复现性（预计 1 个工作会话）

| # | 任务 | 产出 | 验收 |
| --- | --- | --- | --- |
| 3.1 | 干净环境复现实验 | `git clone --depth 1 . /tmp/duiyi-fresh && cd /tmp/duiyi-fresh && make check`（仅 python3 + git，无 Xcode） | exit 0；记录环境/命令/耗时；写入 evidence 或 CONTRIBUTING |
| 3.2 | CONTRIBUTING 分层 | "10 分钟（无 Xcode 可做）" / "30 分钟（完整 iOS 环境）" / "真机验证（可选）"；明确不必先配签名 | 陌生人可按章节推进 |
| 3.3 | CI 收敛 | 合并 `docs.yml` 入 `verify.yml`（避免双 workflow 重复跑 docs）；PR 强制 static；unit 仍可选（`MACOS_CI_ENABLED`）；加 workflow 徽章到 README | CI 全绿；PR 上 static 必跑；README 徽章 live |
| 3.4 | doctor 友好化 | `make doctor` 失败时给出"缺少什么/影响什么/如何补"；区分必需/可选 | 无 Xcode 机器可正确解释"只能跑静态门禁" |

**验收**：干净 clone 复现 PASS（这是"可复制"的第一份证据）；CONTRIBUTING 被 1 名非作者按步骤走通（Phase 4 外部验证时补）。

### Phase 4 · 发布与外部验证（预计 0.5–1 个工作会话）

| # | 任务 | 产出 | 验收 |
| --- | --- | --- | --- |
| 4.1 | GitHub 元数据 | 仓库 description / topics（`ios`, `swift`, `on-device`, `harness-engineering`, `ai-agent`, `translation`, `deepseek-harness`）/ social preview | 由用户在 GitHub 设置（我提供文案） |
| 4.2 | Release | `v1.0.0` tag + release notes（中英，含"如何 10 分钟验证 harness"） | release 页面可访问；tag 在 HEAD 或指定提交 |
| 4.3 | 外部首访测试 | 1–2 名非作者按 README + CONTRIBUTING 走；记录卡点 | 5/5 问可答且 10 分钟复现 PASS（或记录失败并回写） |
| 4.4 | 可选：仓库改名 | 建议改 `duiyi`（品牌化）；改前确认 remote/链接影响 | 由用户决定；本轮默认不改 |

**验收**：release 发布 + 至少 1 次真实外部走查；不通过则回 Phase 1/3 修，不强行发布。

### Phase 5 · harness-kit 模板抽取（预计 2 个工作会话，依赖 Phase 1–3 稳定）

**目标**：把本项目验证过的 harness 抽成与 Duiyi 无关的模板，其它项目可 10 分钟接入。

| # | 任务 | 产出 | 验收 |
| --- | --- | --- | --- |
| 5.1 | 定义模板分层 | `harness-kit/`：`core/`（AGENTS 模板、references 模板、docs IA 模板、`harness/` 工作区、`config.json`、通用门禁脚本）+ `adapters/`（dsh / claude-code / ci / githooks）+ `profiles/`（minimal / standard / strict）+ `scripts/harness-init` | 目录与配置能表达"项目路径、命令、预算、claims、adapters" |
| 5.2 | 脚手架 | `harness-init`：探测语言/命令、按 profile 生成文件、dry-run + 备份、不覆盖已有文件、运行首次 `make check` | 在空白测试仓（或 fork）10 分钟内 init + `make check` PASS |
| 5.3 | profiles 与采用指南 | minimal（AGENTS + 静态门禁）/ standard（+计划/证据/CI）/ strict（+红队/scorecard/月度审计）；`docs/playbook.md` 五步改造法 | 每个 profile 有独立验收脚本；playbook 可由非作者照做 |
| 5.4 | 首个外部试点 | 在作者另一个项目上真实改造一次，记录卡点并回写模板 | 试点项目 1 天内完成接入；卡点进入模板 issue/plan |
| 5.5 | 发布模板 | 独立仓库（推荐 `harness-kit`）或本仓 `harness-kit/`；README 说明与 Duiyi 案例的关系；License 一致 | 模板仓 0 个 Duiyi 专用引用；外部可 clone |

### Phase 6（可选，独立排期）· 产品可信度

- P0-1 并发仲裁红测、P0-3 持久化测试（建议先做）；P0-2 等 D5/D7 产品决策；翻译/听写质量夹具最后做。
- 每个修复走 `red-team`（并发/持久化强制）+ evidence + roadmap 更新。
- 若要把"代码不失控"从「门禁可见」升级为「结构保证」：拆分 SwiftPM 模块/多 target 做编译期分层、覆盖率门槛、CI 强制跑单测（自托管 runner）——成本高，作为独立课题评估。
- 不阻塞标杆化；若用户要求"产品可信度也作为标杆一部分"，单独开计划，避免范围爆炸。

### Ongoing · 维护机制（标杆的"可持续"部分）

- 月度：`make harness-audit` + 更新 `docs/harness-scorecard.md`（评分变化要有证据）。
- 季度：文档修剪（公开文档是否仍 ≤300 行/篇；索引是否 100%；死链 0）。
- 证据保留：`.apm/evidence/` 只保留最近 10 条摘要 + 关键基线；更早的移入 `_archive` 或 git 历史。
- 红队：仅并发/持久化/发布工程（维持 AGENTS §7 现约定）。

---

## 5. 关键决策（执行前需用户确认）

| ID | 决策点 | 推荐 | 备选 | 影响 |
| --- | --- | --- | --- | --- |
| D-B1 | 许可证 | **MIT**（简单、宽松，适合 App 与文档复用） | Apache-2.0（专利授权）；暂不放 | 外部采用者能否合法复用 |
| D-B2 | 公开面语言 | **中文为主 + README 英文概览（15 行）**（审计建议英文优先；若确认面向国际发布则改为英文主 + `README.zh-CN.md`） | 全双语（翻译成本高）；仅中文 | 国际可达性 vs 维护成本 |
| D-B3 | 历史过程文档 | **蒸馏后从树中删除，git 历史保留** | 移到 `docs/archive/`（仍占首屏，不推荐） | 仓库简洁度 vs 可追溯性（git 已足够） |
| D-B4 | HANDOFF | **删除并拆分**（状态→plan，事实→docs/CONTRIBUTING） | 保留精简版 `harness/HANDOFF.md` | 是否彻底消除三处状态源 |
| D-B5 | prototype / Order | **删 `prototype/`；`Order/` 暂留**（Release 配置可能引用；启动优化已暂停） | 都删 / 都留 | 视觉素材 vs 冗余 |
| D-B6 | 仓库改名 | **本轮不改**，发布前再定（`realtimeTranslatorOptimize` → `duiyi`） | 现在就改 | 链接/remote/徽章成本 |
| D-B7 | 发布节奏 | **Phase 1–3 完成后再发 v1.0.0** | 先发 0.x 试水 | 外部第一印象 |
| D-B8 | Phase 6 产品测试 | **独立排期、不阻塞本轮** | 本轮一起做 | 范围与周期 |
| D-B9 | 脱敏范围 | **移除 Team / 设备 ID / 绝对路径；Bundle ID 保留并注明"示例，替换为你自己的"** | (b) Bundle ID 也换 `com.example.duiyi`（需改 pbxproj + 少量源码 + 重跑测试） | 开源合规 vs 改动量/验证成本 |
| D-B10 | 过程区目录名 | **`.apm/` → `harness/`（git mv，可见，与模板同名）** | 保持 `.apm/`；改 `.harness/`（隐藏） | 公开可解释性 vs 迁移成本 |
| D-B11 | 多 Agent 适配 | **单源 AGENTS + skills 同步 `make adapters-check` + Claude hooks 示例（不默认加载）** | 只支持 DSH；或双份维护 | 标杆可复制性 vs 维护成本 |
| D-B12 | 模板抽取 | **Phase 5 做成独立 `harness-kit`（profiles + 脚手架 + 首个外部试点）** | 暂不抽取；只写采用指南 | 其它项目改造成本 |
| D-B13 | 证据 schema v2 | **加可选 `agent`/`model`/`harnessVersion` 字段（向后兼容）** | 不改，证据只记环境 | 跨 agent/模型对比能力 |

默认按"推荐"执行；用户只需回复 `D-B1..D-B13` 的覆盖项（不回复即按推荐）。

## 6. 风险与对策

| 风险 | 概率/影响 | 对策 |
| --- | --- | --- |
| 删除文档破坏门禁（check-docs/check-harness/CI paths/plan.py） | 高 / 中 | Phase 1.7 用 `git grep` 清单逐项清零；每步 `make check`；删除集中一次提交可 revert |
| 删掉仍有价值的信息（设备坑、启动结论） | 中 / 中 | 先蒸馏到 case/references 再删；evidence id 保留；git 历史可追溯 |
| **敏感信息泄露（Team / 设备 ID / 绝对路径）** | 高 / 高（合规红线） | Phase 1.10 全量 grep 清零；脚本改为环境变量；发布前再扫一次；README 注明"示例 Bundle ID" |
| 首访测试"自测通过、外人仍不懂" | 中 / 高 | Phase 4 必须找 1–2 名非作者真实走查；不通过回 Phase 1 |
| 标杆叙事变成"自夸" | 中 / 高 | 评分卡必须由独立复评；HARNESS 必须写局限与未验证；负结果（200ms 不可达）作为案例正面展示 |
| 范围蔓延到产品测试/英文全量翻译 | 中 / 中 | 本计划 scope.deny 锁代码；Phase 6 独立计划；语言决策 D-B2 控制 |
| 删除 raw baseline 后无法复现性能结论 | 低 / 中 | 脚本 `.apm/tools/measure-launch.sh` 可重建；案例页写清口径与命令；关键摘要保留 |
| token 预算/文档注入超限 | 低 / 低 | 新文档不进 AGENTS 预算；AGENTS 仅改路由（≤1600 token 不变） |
| DSH / Claude Code 行为差异导致同一规则效果不同 | 中 / 中 | 适配矩阵写清"工具特性 vs 仓库门禁"边界；`make adapters-check`；门禁不依赖 hooks 可用 |
| 模板抽取把本项目专用假设带出去 | 中 / 高 | Phase 5 验收含"0 个 Duiyi 专用引用"；首个外部试点回写卡点；profiles 按最小起步设计 |

## 7. 工作量与排期（估算，AI 辅助）

| 阶段 | 工作会话 | 人日当量 | 依赖 |
| --- | --- | --- | --- |
| Phase 1 文档 IA | 2–3 | 2–2.5 | 用户确认 D-B1..D-B5 |
| Phase 2 叙事 + 独立复评 | 1–2 | 1 | Phase 1 |
| Phase 3 可复现 | 1 | 0.5 | Phase 1 |
| Phase 4 发布 | 0.5–1 | 0.5 | Phase 2/3 + GitHub 权限 |
| Phase 5 模板抽取 | 2 | 1.5–2 | Phase 1–3 + 外部试点项目 |
| Phase 6（可选） | 2–4 | 2–4 | 产品决策 D5/D7 |
| **合计（不含 Phase 6）** | **6–8** | **≈6–7 人日** | |

## 8. 非目标（明确不做）

- 除 `check-docs` 增加「公开文档白名单 + 数量上限」这一处防回归增强外，不新增任何 harness 机制/门禁/脚本（本轮只做减法、叙事与包装；现有门禁已够用）。
- 不重启启动优化/性能工作（维持"暂停"结论）。
- 不实现 Phase 3 全自动审计打分/指标平台（保留月度人工 + scorecard）。
- 不改业务代码、测试断言、签名信息（scope.deny）。
- 不做完整英文文档（除 README 概览，D-B2）。
- 不把 DSH 用户级配置（Agent Teams/worktree/MCP 等）写成仓库强制项。
- 不追求"更多文档"；目标相反：更少、更准、更可验证。
- 模板抽取（Phase 5）不在本轮 Phase 1–4 开工：先把本项目的 IA/叙事/可复现做稳，再抽取，避免把半成品固化成模板。

## 9. 与上游计划的交接（2026-11-05 harness-engineering）

- 已完成并提交：Phase 0（`d83bb05`：预算修正/嵌套 AGENTS/静态门禁/状态机）、Phase 1（`3935e60` 等：evidence/verify-claim/CI/skills/HARNESS）。
- 未执行、移出本计划范围：
  - Phase 2：P0-1/P0-2/P0-3 行为测试 + 翻译夹具 → 本计划 Phase 6（独立排期）。
  - Phase 3：maker-checker、月度审计自动打分、指标 → 只保留"月度人工审计 + scorecard"（本计划 Ongoing），不做自动化。
- 旧计划置 `status: done` 并归档；本计划为唯一 active。

## 进度

- [x] 现状评估（五子系统 + 对外标杆）+ 文档/敏感信息盘点（2026-11-06）
- [x] 独立只读审计（docs 子代理，2026-11-06，17/35）
- [x] 方案与执行计划（本文）
- [x] Phase 1.1 改造前首访测试（结果 1/5，基线已记录）
- [ ] 用户确认 §5 决策 D-B1–D-B13
- [ ] Phase 1 文档 IA 重构（1.1–1.10），含 `.apm` → `harness/` 重命名
- [ ] Phase 2 标杆叙事 + 独立复评 + Agent 适配层
- [ ] Phase 3 外部可复现
- [ ] Phase 4 发布 + 外部验证
- [ ] Phase 5 `harness-kit` 模板抽取（含首个外部试点）
- [ ] Phase 6（可选）产品可信度

## 验证证据

> 本节记录本方案制定时的基线事实与已执行命令；执行阶段的证据在对应阶段提交时补充。

| 命令 | 结果 | 环境 | 证据ID |
| --- | --- | --- | --- |
| `git ls-files '*.md' \| wc -l`；`git ls-files` | 40 个入库 markdown / 194 个入库文件 | 本机，HEAD `023dc02` | —（基线盘点） |
| `find .apm/runs -type f \| wc -l`；`du -sh .apm` | 447 个忽略文件 / 6.8MB；`.apm/runs` 3.9MB | 本机 | —（基线盘点） |
| `wc -l docs/14..docs/21` | 8 篇历史记录共 897 行；HANDOFF 483 行 | 本机 | —（基线盘点） |
| `make check` | **PASS**（docs/架构/计数/harness/计划；1 个历史 WARN 不阻断） | 本机，Xcode 27.1 | —（基线门禁） |
| `make resume` | 正常输出 active 计划与下一步；`git status` clean | 本机 | —（基线状态） |
| 独立只读审计（docs 子代理，2026-11-06） | **17/35（2.4/5）**；首访 5 问仅 1 问可答；3 套文档地图/5 套命令表/13 行重复计数；真实 Team/UDID/绝对路径入库 | 本机只读，未构建未改文件；底稿 `.apm/runs/benchmark-audit/notes.md`（gitignore） | —（外部审计） |
| 敏感信息扫描（2026-11-06） | Team ID 命中 4 文件；CoreDevice ID 5 文件；`/Users/` 路径 3 个 JSON；Bundle ID 17 文件 | 本机 `git grep` | —（基线盘点） |
| 工具能力核对（2026-11-07） | Claude Code 原生读 AGENTS.md（v2.1.277+）、hooks 生命周期与 `.claude/settings.json` 可提交、skills/subagents；DeepSeek 提供 Anthropic 兼容 API 与 Claude Code 官方集成 | 官方文档（见 §参考）；本机未安装 Claude Code，未实测 | —（外部事实） |
| 首访 5 分钟测试（改造前，作者自测，Phase 1.1） | **1/5 可答 + 2 项部分**：是什么 ✅；为什么值得看 ❌；怎么跑 ⚠️（缺无 Xcode 路径）；怎么验证 ⚠️（README 门禁描述过期）；怎么复制 harness ❌（HARNESS 从 README 不可达） | 本机，仅按 README → docs/README 阅读 | —（基线，不是完成声明） |
| 独立 Harness 复评（改造后） | 待执行（Phase 2.3） | — | — |

## 未验证项

- 首访测试尚未由真实陌生人执行（Phase 1.1/4.3 补）；当前判断来自作者自测 + 一次子代理只读审计（2026-11-06）。
- 独立审计为静态只读（未复跑动态门禁/测试），不等同 Phase 2.3 的正式独立复评；其 17/35 是"对外标杆"口径，与本计划五子系统自评不冲突。
- 五子系统评分 4/5 为自评，未经独立复评（Phase 2.3 补）。
- 干净 clone 可复现性未实测（Phase 3.1 补）；本机为已配置开发环境。
- GitHub 仓库元数据/发布权限、仓库改名影响未验证（Phase 4）。
- 历史文档删除不会丢失未被蒸馏的隐含信息：需在 Phase 1.4/1.5 逐篇对照检查（当前只做了标题级盘点）。
- `Order/` 是否被 Release 构建配置引用未核实（Phase 1 再查；不影响文档主线）。
- Claude Code 环境实测未做（本机未安装）；hooks 示例与 adapters-check 为设计成果，Phase 2.6 补实测或标未验证。
- DSH hooks 能力随版本变化（当前 0.2.1-rc.5 未打包），未来版本可能改变适配策略；模板按"仓库门禁 + CI + 适配层"设计，不依赖 hooks 可用。
- `.apm` → `harness/` 重命名的完整影响面（工具/测试/文档 30+ 处引用）尚未逐一盘点，Phase 1.6/1.7 执行时以 `git grep` 清单为准。

## 参考（外部事实核对，2026-11-07）

- Claude Code Hooks reference（生命周期/hook 事件/`.claude/settings.json` 可提交）：https://code.claude.com/docs/en/hooks
- Claude Code memory（CLAUDE.md 体系；**原生读取 AGENTS.md，v2.1.277+**）：https://code.claude.com/docs/en/memory
- Claude Code 扩展总览（skills/subagents/hooks/MCP/plugins 的选择矩阵）：https://code.claude.com/docs/en/features-overview
- DeepSeek API：Anthropic API 兼容（`base_url=https://api.deepseek.com/anthropic`）：https://api-docs.deepseek.com/guides/anthropic_api
- DeepSeek × Claude Code 官方集成（环境变量/模型映射）：https://api-docs.deepseek.com/quick_start/agent_integrations/claude_code
- DeepSeek Harness 文档入口：https://deepseek-harness.github.io/deepseek-harness/en/guide/quickstart
- DSH 可编程面盘点（本机 0.2.1-rc.5 安装包核查，仓库外底稿）：`.apm/runs/harness-audit/01-research.md`（gitignore，不随仓库发布）

## 尝试记录

| 尝试# | 动作 | 结果 | 时间 |
| --- | --- | --- | --- |
| 1 | 盘点文档面/门禁现状 + 读取上游计划与模板 | 完成，事实写入 §1.3 | 2026-11-06 |
| 2 | 派生独立审计员做双视角首访/标杆评估 | 团队席位已满（8/8）；复用 docs 子代理完成只读审计（17/35；底稿 `.apm/runs/benchmark-audit/notes.md`，未改 tracked 文件） | 2026-11-06 |
| 3 | 盘点敏感信息与 evidence xcresult 路径 | Team/UDID/绝对路径已定位到 file:line；evidence 的 xcresultPath 已是仓库相对路径（换机器会 UNVERIFIED，属设计） | 2026-11-06 |

## 未提交改动

- 无未提交改动（Phase 1 开工前工作区 clean）。

## 下一步

1. 等用户确认 §5 决策 D-B1–D-B13（不回复则按推荐执行）。
2. 确认后从 Phase 1.1（改造前首访测试）开工：按 1.2 → 1.3 → 1.4 → 1.5 → 1.6 → 1.7 → 1.8 → 1.9 → 1.10 推进；每步跑 `make check`，1.7 后跑 `make verify-static`。1.6 含 `.apm/` → `harness/` 的 `git mv`（D-B10）。
3. 若用户只批准部分范围：首批只做 1.2/1.3/1.5/1.7/1.10（入口 + 删 HANDOFF + 同步门禁 + 脱敏），历史文档蒸馏（1.4/1.6）放第二批。
4. 提交前单独询问（团队基线要求）；Phase 1 结束后再决定是否进入 Phase 2。
5. Phase 5（harness-kit 模板）必须在 Phase 1–3 稳定后启动；Phase 6 产品测试始终独立排期。

## 待确认

- D-B1 许可证、D-B2 语言、D-B3 历史文档删除方式、D-B4 HANDOFF 处置、D-B5 prototype/Order、D-B6 仓库改名、D-B7 发布节奏、D-B8 Phase 6 排期、D-B9 脱敏范围、D-B10 `.apm`→`harness/` 改名、D-B11 多 Agent 适配、D-B12 模板抽取、D-B13 证据 schema v2（见 §5）。
- Phase 1 是否按本文分阶段提交、是否允许删除 `HANDOFF.md` 与 `docs/14–21`（删除后可从 git 历史恢复）、是否在本轮就做 `.apm` → `harness/` 重命名。
