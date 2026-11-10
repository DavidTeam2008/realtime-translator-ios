---
id: 2026-11-06-benchmark-opensource
status: active
level: L2
owner: david
updated: 2026-11-10
scope:
  allow:              # 本轮只做「公开面 + 文档 + 过程档案」收敛；不动业务代码
    - README.md
    - LICENSE
    - CONTRIBUTING.md
    - HARNESS.md
    - AGENTS.md
    - AGENTS.local.md.example
    - HANDOFF.md
    - .apm/            # 重命名源目录（git mv 后的删除记录）
    - docs/
    - references/
    - harness/
    - harness-kit/        # Phase 5：与 Duiyi 无关的 harness 模板（kit）
    - .dsh/
    - tools/
    - .github/
    - .githooks/
    - Makefile
    - .gitignore
    - Order/
    - prototype/        # 删除（视觉稿由截图替代）
    - Duiyi/Services/AGENTS.md
    - Duiyi/Features/AGENTS.md
    - DuiyiTests/AGENTS.md
    - DuiyiUITests/AGENTS.md
    - DuiyiUITests/SimultaneousFlowTests.swift   # 仅注释路径同步
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

> 状态：**执行中（Phase 2.5 整改；阶段进度见 §4）**　|　级别：L2　|　日期：2026-11-06
> 上游：`harness/plans/2026-11-05-harness-engineering.md`（Phase 0/1 已完成并提交；Phase 2/3 未执行，见本文 §9 交接）
> 定位：把「Harness Engineering 落地」升级为「可被陌生人看懂、复现、采用的开源标杆」；核心动作是**减法**，不是继续加机制。
> 计划入库规则：不写本机绝对路径、密钥、设备 UDID；只写仓库相对路径。

## 目标与非目标

**目标**：把 Duiyi 从「内部工程仓」升级为可理解、可复现、可复制的 Harness Engineering 开源标杆，同时保持"完成声明可被机器否证"。

**非目标**：不新增业务功能；不重启启动优化；不在本轮做产品行为测试（Phase 6）；不做完整英文文档；不引入新的 harness 机制（除已列防回归门禁）。

## 验收（摘要）

完整判据见 front matter `acceptance`；分阶段验收见 §4；最终对外标准见 §4 Phase 4。

## 0. 结论摘要（TL;DR）

1. **Harness 评估结论（2026-11-06 现状）**：五子系统 **Instructions 4 / State 4 / Verification 4 / Scope 3.5 / Session Lifecycle 4**（满分 5，综合约 **78–80%**）。改造前独立审计为 **2.5/5**；本轮已把「文档型 harness」升级为「静态门禁 + 结构化证据 + 三值判定 + 四层验证」的可运行闭环。另有一次独立只读审计（2026-11-06，docs 子代理）按「对外标杆成熟度」评 **17/35 = 2.4/5**，并把「证据可审计」压到 3/5：README 头条数字未逐条链到 evidence、部分 evidence 产物换机器不可复核。
2. **等级判定**：已达到「L3 可审计」——agent 的完成声明可被 `make verify-claim` 三值否证；尚未达到「L4 自我改进」（审计未自动打分、无固定指标）与「L5 可复制/可传播」（陌生人看不懂、跑不起来、复制不走）。
3. **距标杆目标的距离**：**内部工程 ≈80%，对外标杆 ≈49%（17/35），加权综合约 60%**。标杆不看"体系是否存在"，只看"陌生人 5 分钟能否理解、10 分钟能否复现、30 分钟能否复制"——这三项目前都不成立。差距不是门禁机制，而是首访入口、开源治理、文档 IA、脱敏与叙事。
4. **最大问题不是缺能力，而是缺减法 + 缺脱敏**：40 个入库 markdown 中约 1/3 是过程/历史文档；HANDOFF 483 行与 docs/21 重复；docs/14–21 共 897 行历史记录混在主线；`harness` 6.8MB/447 个忽略产物 + 3 个 raw baseline JSON（3114 行）入库；根目录无 LICENSE/CONTRIBUTING/截图/英文概览。**更严重的是：真实签名 Team、设备 CoreDevice ID、`/Users/...` 绝对路径已入库（违反自身铁律 8），开源发布前必须脱敏。**
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

- 入库 markdown **40 个**：根入口 4（README/HANDOFF/HARNESS/AGENTS）、`docs/` 14、`references/` 3、`harness/` 9、`.dsh/skills/` 6、代码目录嵌套 AGENTS 4。
- `docs/14–21` 是带日期的过程/历史记录，共 **897 行**，但放在文档主线同一层，首访者无法区分「当前规范」与「历史证据」。
- `HANDOFF.md` **483 行**，与 `docs/21-cross-session-handoff.md`（78 行）职责重叠；两者又都与 `harness/plans/` 的交接职责重叠 → 三处状态源。
- `harness` 工作区 **6.8MB**：`harness/runs` 3.9MB/447 个忽略文件；3 个 raw baseline JSON 共 3114 行入库；另有 `report.md`、`issues/`、`reviews/`、`feasibility/`、`white-screen/` 等已过期产物。
- 根目录无 `LICENSE`、`CONTRIBUTING.md`、`.github/ISSUE_TEMPLATE`、真实截图；README 依赖「先读 HANDOFF」，且状态数字有漂移（如设备 iOS 版本）。
- `prototype/` 是 2026-08 的 HTML 视觉稿，已与实现脱节；`docs/diagrams/` 7 张 SVG 有「可能滞后」声明但仍作为事实入口。
- `build/` 705MB（已忽略）与 `Order/`（启动优化暂停后的生成物）属于本机/历史遗留，不影响仓库但影响"简洁"观感。
- **多真源**：3 套文档地图（README / docs/README / HANDOFF §7）、5 套命令表、13 行重复测试计数（违反自身"数字只在 references/verification"规则）、真源优先级口号 3 个版本。
- **发布红线（脱敏）**：真实签名 Team ID（4 个文件）、设备 CoreDevice ID（5 个文件）、`/Users/<name>` 绝对路径（3 个 baseline JSON）已入库；`project.pbxproj` 仍写原开发者 Team/Bundle ID——与根 `AGENTS.md` 铁律 8「签名属本地环境」直接矛盾。
- **命名不可迁移**：`harness/` 是项目历史缩写（早期 APM 测量），公开/模板无法解释；通用模板需改为可见的 `harness/`（D-B10），并与 `harness-kit` 模板同名，避免"一套方法、两种目录"。

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
| **L4 档案层** | 维护者 / 审计 | `harness/`：active plan、evidence、tools、test-baseline、reviews | 不进首屏文档地图；原始产物 gitignore；历史记录只留摘要 |

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
harness/                  # 原 APM 工作区（.apm/）2026-11 更名；可见、与模板同名
  README.md               # 档案层索引（与 L1–L3 的边界说明）
  AGENTS.md               # 目录协议
  plans/                  # active + _template（历史计划已删除，git 历史保留）
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
| 原 `harness/report.md`、`baseline/`、`feasibility/`、`white-screen/` | 已删除 | 结论由启动案例与 evidence 承载；原始记录留 git 历史 |
| 原 `harness/issues/*.json`（7 个） | 已删除 | 结论进 `docs/04` 与启动案例；原始记录留 git 历史 |
| 历史计划/审查（2 计划 + 1 审查） | 已删除 | 内容已完成/移交本计划；原始记录留 git 历史 |
| `harness/plans/2026-11-05-harness-engineering.md` | `status: done` + 归档 | Phase 0/1 已完成；Phase 2/3 移交本计划 §9 |
| 原 APM 工作区目录 | **已更名 `harness/`（`git mv`，D-B10）** | 公开/模板可解释；与 `harness-kit` 同名；已同步 tools/CI/AGENTS 路径 |
| 无（新增） | **`.claude/` + `harness/adapters/claude-code/`（D-B11）** | Claude Code hooks/skills 薄适配，不默认加载；`make adapters-check` 防漂移 |
| `prototype/`（3 个 HTML） | 删除 | 2026-08 视觉稿，与实现脱节；截图替代 |
| `Order/App.order` + `tools/generate-order-file.sh` | 保留（P2 再议） | 启动优化已暂停但 Release 配置可能引用；不在文档首屏 |
| `docs/diagrams/` 7 张 SVG | 精简为 2–3 张 | 保留准确的分层/链路图；滞后图删除或重绘（Phase 1 校验） |

> 净效果：对外可见 markdown（根 + docs + references）**21 → 15**；`docs/` 从 14 篇降到 **8 篇**（历史 8 篇 897 行清零，新增 decisions/case 2 篇）；全仓库入库 markdown 40 → 约 27；根目录文档 4 个清晰入口 + LICENSE/CONTRIBUTING。

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
   ├─ 1b 蒸馏 + 删除历史文档 / HANDOFF / prototype / harness 过期产物
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
| 1.4 | 蒸馏历史文档（已完成） | `docs/case-startup-performance.md`（130 行：目标 → 口径 → 方法 → A/B → 归因 → 结论"不可达"→ 排除方向 → 证据线索）；已删除 docs/14–21 | 数字与 commit 可追溯；8 篇历史文档清零 |
| 1.5 | 拆分 HANDOFF | 决策 → `docs/decisions.md`；构建/签名/测试 → `CONTRIBUTING.md`；坑 → `references/verification.md`；会话状态 → active plan；删除 `HANDOFF.md`（D-B4） | `git grep HANDOFF` 仅剩历史记录/archive |
| 1.6 | 目录改名 + 瘦身（已完成） | 原 APM 目录 → **`harness/`**（`git mv`，D-B10）；新增 `harness/README.md`；删除 report/baseline raw/feasibility/issues/white-screen 与历史计划/审查；更新目录职责与全部引用 | `harness/` 入库文件数下降 ≥60%；`make evidence`/`verify-claim` PASS；`git grep` 无旧路径（git 历史除外） |
| 1.7 | 页面与引用同步 | 重写 `docs/README.md`（唯一索引：Start / Reference / Archive / Harness）；去重：3 套文档地图合一、5 套命令表收敛到 Makefile + CONTRIBUTING、13 行重复测试计数改为引用 `references/verification.md`；更新 docs/01–04 交叉引用；更新根/嵌套 AGENTS、references、skills、HARNESS 链接；更新 tools：`check-docs.py` 扫描根（新增 HARNESS/CONTRIBUTING、移除 HANDOFF）**并增加公开文档白名单 + 数量上限（防删了又长回来）**、`plan.py` 建议阅读、`check-harness.py`、`.github/workflows/verify.yml` 路径过滤 | `make verify-static` PASS；0 死链；`git grep -nE 'HANDOFF|docs/(1[4-9]\|2[01])'` 无有效引用（archive 除外）；测试计数只在 references/verification；新增/删除公开文档未改白名单 → 门禁红 |
| 1.8 | 真实截图（已完成） | 4 张模拟器截图（首页/面对面/同传/设置）→ `docs/images/`；README 引用；来源 iPhone 17 Pro Max / iOS 26.4.1 | 图片存在、README 渲染正常、无隐私信息 |
| 1.9 | 改造后首访测试 | 同一 5 问 + 卡点复测 | 5/5 可答；记录耗时与卡点 → 本计划证据 |
| 1.10 | **脱敏（发布红线，P0）** | 移除/占位：`project.pbxproj` 的 `DEVELOPMENT_TEAM` 与真实签名信息；HANDOFF/docs/scripts/baseline/issues 中的 CoreDevice ID、UDID、`/Users/...` 绝对路径；`harness/tools/*.sh` 改为从环境变量/`AGENTS.local.md` 读取设备参数；Bundle ID 保留但注明"示例，替换为你自己的"（若选 D-B9b 则一并替换） | `git grep` 0 命中真实 Team/设备 ID/绝对路径；`make verify-static` PASS；构建/测试仍可跑（或明确记未验证） |

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

### Phase 2.5 · 独立复评整改（P0，Phase 3 前）

> 来源：`harness/reviews/2026-11-07-harness-reaudit.md`（独立复评：综合 ≈3.6/5；L3 标记为"条件成立"）。

| # | 任务 | 状态 |
| --- | --- | --- |
| 2.5.1 | `make end` 默认跑 `verify-claim --all` | 已完成（本批） |
| 2.5.2 | 计划 `scope.allow` 之外的未提交改动必须 FAIL（不再静默过滤） | 已完成（本批） |
| 2.5.3 | 计划补充「目标与非目标」「验收」节，修正 `make resume` 输出 | 已完成（本批） |
| 2.5.4 | 证据时效：按 claim 相关路径比较 `evidence.commit..HEAD`；`--fresh` 告警，`--strict` 判 UNVERIFIED；接入 `make end` 与 `make release-check` | 已完成（本批补 `commit==HEAD/计划 submitted` 硬绑定，见 2.5.8） |
| 2.5.5 | 计划证据 ID 校验：形如 evidence id 的值必须存在且 verdict=PASS；声称 PASS 但 ID 为空 → WARN | 已完成（本批：硬失败 + 占位白名单 + done 严格） |
| 2.5.6 | `§` 引用扫描扩展到嵌套 AGENTS / 支持"第 N 节"；token 预算余量再平衡（AGENTS 24、refs 18–25） | 已完成（本批：13 个指令文件 7 处命中；预算帽 1650/975，余量 43–74） |
| 2.5.7 | CI 合并 `docs.yml` 进 `verify.yml`；clean clone 复现（Phase 3） | 已完成（Phase 3.1/3.3） |
| 2.5.8 | 证据与计划绑定：done 计划必须填 `submitted`，被引用证据 `git.commit` 须等于 HEAD 或前缀匹配 submitted；`make release-check` = 静态（含计划硬校验）+ fresh strict | 已完成（本批；负向验证见验证证据表） |

**负向验收（待做项完成后）**：无新 evidence 的"已完成"应 FAIL/UNVERIFIED；scope 外改动应 FAIL；嵌套 AGENTS 错误节号应 FAIL。

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
| 4.1 | GitHub 元数据 | 仓库 description / topics（`ios`, `swift`, `on-device`, `harness-engineering`, `ai-agent`, `translation`, `deepseek-harness`）/ social preview（素材：`docs/images/social-preview.png`，1280×640）；issue/PR 模板已随仓库提供 | 由用户在 GitHub 设置（我提供文案） |
| 4.2 | Release | `v1.0.0` tag + `harness/release-notes-v1.0.0.md`（中英，含"如何 10 分钟验证 harness"）；release 文案由该文件提供 | release 页面可访问；tag 在 HEAD 或指定提交 |
| 4.3 | 外部首访测试 | AI 代理按公开 clone 走查（已完成，见 review）；再招募 1 名人类非作者按 README + CONTRIBUTING 走 | 5/5 问可答且 10 分钟复现 PASS（当前 AI 代理 4/5；人类待验证） |
| 4.4 | 可选：仓库改名 | 建议改 `duiyi`（品牌化）；改前确认 remote/链接影响 | 由用户决定；本轮默认不改 |

**验收**：release 发布 + 至少 1 次真实外部走查；不通过则回 Phase 1/3 修，不强行发布。

### Phase 5 · harness-kit 模板抽取（预计 2 个工作会话，依赖 Phase 1–3 稳定）

**目标**：把本项目验证过的 harness 抽成与 Duiyi 无关的模板，其它项目可 10 分钟接入。

| # | 任务 | 产出 | 验收 | 状态 |
| --- | --- | --- | --- | --- |
| 5.1 | 定义模板分层 | `harness-kit/`：`core/`（AGENTS 模板、references 模板、docs IA 模板、`harness/` 工作区、`config.json`、通用门禁脚本）+ `adapters/`（dsh / claude-code / ci / githooks）+ `profiles/`（minimal / standard / strict）+ `scripts/harness-init` | 目录与配置能表达"项目路径、命令、预算、claims、adapters" | 已完成（2026-11-07；SPEC/config schema/profiles/adapters） |
| 5.2 | 脚手架 | `harness-init`：探测语言/命令、按 profile 生成文件、dry-run + 备份、不覆盖已有文件、运行首次 `make check` | 在空白测试仓（或 fork）10 分钟内 init + `make check` PASS | 已完成（三档空白仓 init + 首次 `make check` PASS） |
| 5.3 | profiles 与采用指南 | minimal（AGENTS + 静态门禁）/ standard（+计划/证据/CI）/ strict（+红队/scorecard/月度审计）；`docs/playbook.md` 五步改造法 | 每个 profile 有独立验收脚本；playbook 可由非作者照做 | 已完成（`make kit-check` 66 用例覆盖三档；playbook 已写，非作者试点见 5.4） |
| 5.4 | 首个外部试点 | 在作者另一个项目上真实改造一次，记录卡点并回写模板 | 试点项目 1 天内完成接入；卡点进入模板 issue/plan | 已完成（代理试点：空白 Python 项 standard 接入成功、首次 check 一次 PASS、执行 ≈80s；卡点已回写；**真实项目未验证**） |
| 5.5 | 发布模板 | 独立仓库（推荐 `harness-kit`）或本仓 `harness-kit/`；README 说明与 Duiyi 案例的关系；License 一致 | 模板仓 0 个 Duiyi 专用引用；外部可 clone | 已完成：独立仓 <https://github.com/DavidTeam2008/harness-kit>（main `76ac99d`，CI success；clone 后 69 tests OK） |
| 5.7 | 模板仓维护机制 | 上游唯一源 + 独立仓只读镜像：`make kit-publish`（subtree split → 镜像 `main`）、`make kit-drift`（一致性检查）；README/HARNESS 写维护契约；kit `0.2.0` | 镜像与上游可一条命令同步、可机检漂移；镜像仓禁止直接提交 | 已完成（2026-11-09）：本地 `verify-static` PASS；漂移负向验证 DRIFTED→publish→in sync；镜像 `main` `fcc08dc`、tag `v0.2.1`（含 `v0.2.0`）、CI run `42569790859` success |
| 5.6 | 语言/平台覆盖试点 | Node（`node --test`/`npm test`）与 SwiftPM（`swift test`）接入试点；语言支持矩阵；`harness-init` 推断改进（node scripts.test、xcodeproj 提示） | 每语言端到端：init + `make check`/`verify-static` + 证据三值；矩阵写明实测/未实测 | 已完成（Node 24 / Swift 6.4 均 PASS；Go 未安装、Xcode iOS 工程未实测，已入矩阵） |
| 5.8 | 存量项目（brownfield）接入能力（kit `0.2.2`） | `scripts/harness-adopt`（只读盘点/`--json`/`--report`/`--write-plan`）、`--language android` 探测、`tools/evidence_from_junit.py`（standard+）、playbook 七步法、改造计划模板；standard profile 接入 JUnit 工具 | 真实存量仓只读盘点 0 改动且清单可执行；kit 98 tests PASS；镜像发布 `v0.2.2` | 已完成（2026-11-10）：98 tests OK、卫生 0 命中；Android 仓只读试点 PASS（报告 `harness/reviews/2026-11-10-kit-android-adoption-pilot.md`）；镜像 `main` `f0ac5bd` + tag `v0.2.2`，镜像 CI run `42652383140` success，clone 98 tests OK，`kit-drift` in sync |
| 5.9 | 真实项目外部试点（Android 仓，Stage A+B） | 用 kit v0.2.2 对真实存量 Android 仓执行 brownfield 七步法：接入 scaffold、文档蒸馏（11 当前 + 10 归档、D1–D15）、清洁批次、宿主传感器与 JUnit 证据链、负向注入/冷启动验收、计划 done 归档 | 目标仓 `make check`/`verify-static`/`verify-claim`/`check-quality` 全 PASS；65 单测证据 PASS；12/12 负向注入；冷启动 5/5；15 commits 推送且 CI success | **已完成（2026-11-10）**：目标仓 `d313fdf..eaae1b6`（16 commits，历史已 `filter-repo` 清洗）已推送，CI run `42760441698` success；证据 `20261109T163805Z-tests-pass`（commit 回填 `2c3b479`）；分支保护已开（`static gates` 必过、禁 force push/删除）；报告 `harness/reviews/2026-11-10-kit-android-stage-b.md` |
| 5.10 | kit `v0.2.3`：宿主传感器上游化 + 门禁自测 | `check_hygiene.py`/`check_layers.py`（配置化、缺段 SKIP）进入 standard profile 与 Makefile `check-host`（并入 `verify-static`）；`check_plan.py` 支持无扩展名根文件声明；新增 `scripts/harness-selftest`（clone→baseline→M1–M8 注入→断言非 0→恢复复核，exit 0/1/2）；Android/Gradle 矩阵行转 ✅ | kit 121 tests PASS（+23，含三 profile init 回归）；selftest 在标准宿主 `PASS 5 / SKIP 3`、条件宿主 `PASS 8`；镜像 tag `v0.2.3` + CI success | **已完成（2026-11-10）**：121 tests OK（+23）；`make verify-static` 集成 PASS；镜像 `main` `29bf937` + tag `v0.2.3`（annotated），镜像 CI run `42761789282` success，clone 121 tests OK，`kit-drift` in sync |
| 5.11 | kit `v0.2.4`：升级路径实证回写（文档） | playbook 新增「升级路径」：版本升级已验证（临时渲染 → 逐文件 diff → 只回写 kit 管理面 → `verify-static` + `harness-selftest` 复核）与 profile 升级仍未验证；README/SPEC/CHANGELOG/来源案例同步；VERSION `0.2.4` | kit 121 tests PASS；`make verify-static` PASS；镜像 tag `v0.2.4` + CI success + `kit-drift` in sync | **已完成（2026-11-10）**：playbook「升级路径」拆分（版本升级已验证 / profile 升级仍未验证）、README/SPEC/CHANGELOG/来源案例同步、VERSION `0.2.4`；kit **121 tests**；镜像 `main` `c47fdf9` + annotated tag `v0.2.4`，镜像 CI run `42764622139` success，tag clone 121 tests OK，`kit-drift` in sync；iOS CI run `42764499029` success |
| 5.12 | kit `v0.2.5`：接入指南 + 演化治理 + README 重写 | 新增 `docs/adoption.md`（新项目/存量项目/AI coding Agent 接入、Agent bootstrap 提示、反模式；接入前后五子系统评分案例：Android 存量仓自评 6/25→20/25、来源 iOS 仓独立复评 2.5/5→≈4.0/5）与 `docs/governance.md`（反臃肿九原则、版本演化与删除/降级流程、行为级评估 v0.3+ 议题、多人与多 Agent 协作）；README 重写（症状→机制、适合谁、案例、反臃肿/多人摘要）；新文档纳入 kit 链接检查；VERSION `0.2.5` | kit 121 tests PASS；`make verify-static` PASS；镜像 tag `v0.2.5` + CI success + `kit-drift` in sync | **已完成（2026-11-10）**：`docs/adoption.md`/`docs/governance.md` 新增、README 重写、新文档纳入链接检查；kit **121 tests**；镜像 `main` `52b9119` + annotated tag `v0.2.5`，镜像 CI run `42803540280` success，tag clone 121 tests OK，`kit-drift` in sync；iOS CI run `42803400474` success |

### Phase 6（可选，独立排期）· 产品可信度

- P0-1 并发仲裁红测、P0-3 持久化测试（建议先做）；P0-2 等 D5/D7 产品决策；翻译/听写质量夹具最后做。
- 每个修复走 `red-team`（并发/持久化强制）+ evidence + roadmap 更新。
- 若要把"代码不失控"从「门禁可见」升级为「结构保证」：拆分 SwiftPM 模块/多 target 做编译期分层、覆盖率门槛、CI 强制跑单测（自托管 runner）——成本高，作为独立课题评估。
- 不阻塞标杆化；若用户要求"产品可信度也作为标杆一部分"，单独开计划，避免范围爆炸。

### Ongoing · 维护机制（标杆的"可持续"部分）

- 月度：`make harness-audit` + 更新 `docs/harness-scorecard.md`（评分变化要有证据）。
- 季度：文档修剪（公开文档是否仍 ≤300 行/篇；索引是否 100%；死链 0）。
- 证据保留：`harness/evidence/` 只保留最近 10 条摘要 + 关键基线；更早的移入 `_archive` 或 git 历史。
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
| D-B6 | 仓库改名 | **已执行（2026-11-09）：`realtimeTranslatorOptimize` → `realtime-translator-ios`**；README/CONTRIBUTING/kit README 链接与 remote 同步；历史档案（reviews/release-notes/evidence）保留旧名（GitHub 301） | 保持旧名；或 `duiyi-ios` | 实际成本 ≈15 分钟；API 301、`git ls-remote` 旧 URL 均可用；旧名不可再新建仓库 |
| D-B7 | 发布节奏 | **Phase 1–3 完成后再发 v1.0.0** | 先发 0.x 试水 | 外部第一印象 |
| D-B8 | Phase 6 产品测试 | **独立排期、不阻塞本轮** | 本轮一起做 | 范围与周期 |
| D-B9 | 脱敏范围 | **移除 Team / 设备 ID / 绝对路径；Bundle ID 保留并注明"示例，替换为你自己的"** | (b) Bundle ID 也换 `com.example.duiyi`（需改 pbxproj + 少量源码 + 重跑测试） | 开源合规 vs 改动量/验证成本 |
| D-B10 | 过程区目录名 | **原 APM 目录 `.apm/` → `harness/`（git mv，可见，与模板同名）** | 保持原目录；改隐藏目录 | 公开可解释性 vs 迁移成本 |
| D-B11 | 多 Agent 适配 | **单源 AGENTS + skills 同步 `make adapters-check` + Claude hooks 示例（不默认加载）** | 只支持 DSH；或双份维护 | 标杆可复制性 vs 维护成本 |
| D-B12 | 模板抽取 | **Phase 5 做成独立 `harness-kit`（profiles + 脚手架 + 首个外部试点）** | 暂不抽取；只写采用指南 | 其它项目改造成本 |
| D-B13 | 证据 schema v2 | **加可选 `agent`/`model`/`harnessVersion` 字段（向后兼容；不 bump schemaVersion，避免破坏既有证据）** | 不改，证据只记环境 | 跨 agent/模型对比能力 |

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
| 删除 raw baseline 后无法复现性能结论 | 低 / 中 | 脚本 `harness/tools/measure-launch.sh` 可重建；案例页写清口径与命令；关键摘要保留 |
| token 预算/文档注入超限 | 低 / 低 | 新文档不进 AGENTS 预算；AGENTS 仅改路由（预算帽 1650，当前 ≈1576） |
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

- 已完成并提交：Phase 0（`27a89fc`：预算修正/嵌套 AGENTS/静态门禁/状态机）、Phase 1（`dde3f32` 等：evidence/verify-claim/CI/skills/HARNESS）。
- 未执行、移出本计划范围：
  - Phase 2：P0-1/P0-2/P0-3 行为测试 + 翻译夹具 → 本计划 Phase 6（独立排期）。
  - Phase 3：maker-checker、月度审计自动打分、指标 → 只保留"月度人工审计 + scorecard"（本计划 Ongoing），不做自动化。
- 旧计划置 `status: done` 并归档；本计划为唯一 active。

## 进度

- [x] 现状评估（五子系统 + 对外标杆）+ 文档/敏感信息盘点（2026-11-06）
- [x] 独立只读审计（docs 子代理，2026-11-06，17/35）
- [x] 方案与执行计划（本文）
- [x] Phase 1.1 改造前首访测试（结果 1/5，基线已记录）
- [x] 用户确认 §5 决策 D-B1–D-B13（2026-11-07，全量按推荐）
- [x] Phase 1 第一批（1.2/1.3/1.5/1.7/1.10）：入口与 LICENSE、README 重写、HANDOFF 拆分删除、门禁引用同步、脱敏与白名单
- [x] Phase 1 第二批：1.4 历史文档蒸馏删除、1.6 目录更名 `harness/` + 瘦身、1.8 截图
- [x] Phase 1.9 改造后首访测试：4/5 可答（复制指南仍部分，Phase 2 补）
- [x] Phase 2.1/2.2/2.4/2.6/2.7：HARNESS 重写、评分卡、互链、Claude Code 适配层、evidence 可选字段
- [x] Phase 2.3 独立复评：综合 ≈3.6/5（Instructions 4 / State 3.5 / Verification 4 / Scope 3 / Lifecycle 3.5）；L3 条件成立；报告 `harness/reviews/2026-11-07-harness-reaudit.md`
- [x] Phase 3.1 clean clone 复现：`make check` 0.33s PASS；`make verify-static` 4.65s PASS（42 单测，无 Xcode）
- [x] Phase 3.3（部分）：`docs.yml` 合并进 `verify.yml`（`**/*.md`）；README 徽章（verify/MIT/iOS）
- [x] 历史清理·敏感信息：`git filter-repo` 重写 43 commits，敏感项在树/历史/提交消息中 0 命中；强推远程 main
- [x] 历史清理·作者邮箱：`git filter-repo --mailmap` 二次重写 48 commits → GitHub noreply；树内 7 文件 / 16 处 commit 引用按 subject 校验回填；强推 main
- [x] CI 验证：普通推送触发 `verify` run `42344278003`，static gates success，unit-tests skipped（按设计）
- [x] Phase 2.5.1–2.5.4：end 接线、scope 越界 FAIL、计划节修正、证据时效 `--fresh/--strict` + `make release-check`
- [x] Phase 2.5.5–2.5.8：证据 ID 硬失败 / done 严格 / `submitted` 绑定、§/第N节 扫描扩展（13 文件）、token 余量再平衡（1650/975）
- [x] Phase 3.1/3.2/3.3/3.4：clean clone 复现、CONTRIBUTING 三层（10 分钟/完整 iOS/真机）、CI 单 workflow + 徽章、doctor 失败建议区
- [ ] Phase 3 剩余：首次真实 PR / 分支保护设置（需仓库管理员或可用 token；当前 PAT 受组织策略 403）
- [x] Phase 4 发布准备：unit/UI 发布前重跑证据（`20261107T062204Z` / `20261107T062205Z`）；`harness/release-notes-v1.0.0.md` 起草
- [x] Phase 2.5 独立复核（2026-11-07）：P0×3 关闭；综合 ≈4.0/5；L3「达成（有条件）」；报告 `harness/reviews/2026-11-07-phase2.5-reaudit.md`
- [x] 开源包装：issue/PR 模板（`.github/ISSUE_TEMPLATE/`、`.github/PULL_REQUEST_TEMPLATE.md`）
- [x] v1.0.0 annotated tag 已推送（目标 `c78abe8`，main HEAD）；CI run `42347475807` static success；GitHub Release 待用户创建（PAT 403）
- [x] 外部首访（AI 代理，公开 clone）：4/5 可答；发现浅克隆 P0 → 已修（skip + README/CONTRIBUTING unshallow、无 Xcode 边界、采用指南直链、实测耗时）
- [x] Phase 4 发布：GitHub Release `v1.0.0` 已发布（2026-11-09 04:37Z，用户操作）；Duiyi 与 harness-kit 的 description/topics、Duiyi social preview 已设置
- [x] Phase 5.7：模板仓维护机制（`make kit-publish` / `make kit-drift` + 镜像只读契约；kit 升 `0.2.0`、CHANGELOG/README/SPEC 同步；镜像 `main` `fcc08dc` + tag `v0.2.1`，镜像 CI run `42569790859` success，clone 后 69 tests OK）
- [x] 仓库改名：`DavidTeam2008/realtimeTranslatorOptimize` → **`realtime-translator-ios`**（2026-11-09，`gh` 重新登录为 classic token 后由 API 执行；remote/文档/kit 链接同步；API 301 与旧 URL `git ls-remote` 复核通过；Release/tag/star 保留）
- [x] Phase 4 首访反馈整改（2026-11-09，按 README 实跑）：真机预热失败暴露两个问题——①测试 target 无 Team（脱敏预期，但脚本把真实原因吞掉）；②设备未信任开发者证书。已修：脚本打印 `diagnostics.errors` + `APM_TEAM` 传参 + 针对性修复提示；文档前置签名/信任两步
- [x] 真机设备侧验证（2026-11-09）：签名/信任修好后 `device-test.sh unit` 在 iPhone 13 / iOS 27.0.1 上 **120/120 PASS**（证据 `20261109T133618Z-unit-tests-pass`）；UI 仍 UNVERIFIED（网络配对下 exit 74，需设备密码弹窗或 USB 准备 DeviceSupport）；证据生成须在干净工作树（dirty 判 FAIL）
- [x] 真机全套（2026-11-09，设备侧）：密码弹窗处理后 `device-test.sh all` → 预热 5/5 + 目标 **123/123 PASS**（failed=0 skipped=0，171.7s；干净工作树 `git.dirty=false`，commit `66f3372`；证据 `20261109T142307Z-device-tests-pass`）
- [x] **Phase 4 收尾（2026-11-09）**：真机 UI/全套 PASS；人类非作者首访已完成（用户确认，反馈无阻塞；仓库内无该次首访的记录文件，按用户报告记录）
- [x] Phase 5.1–5.3：SPEC/config schema/profiles/`harness-init`/core 脚本/模板/adapters/README/playbook + 66 个 kit 端到端测试
- [x] Phase 5.4：外部试点（AI 代理、空白 Python 仓、standard）：接入成功、首次 check 一次 PASS、执行 ≈80s；3 个文档卡点已回写；报告 `harness/reviews/2026-11-07-kit-pilot.md`（真实项目未验证）
- [x] Phase 5.5：独立模板仓已发布（<https://github.com/DavidTeam2008/harness-kit>，public、CI success、clone 69 tests OK）；本仓 `harness-kit/` 为同步源
- [x] Phase 5.6：语言覆盖试点（Node 24 / SwiftPM 均端到端 PASS；Go 未装、Xcode iOS 工程未实测）；推断改进 + 语言支持矩阵
- [x] Phase 5.8：存量接入能力（kit `0.2.2`）：`harness-adopt` / `--language android` / JUnit XML 适配器 / brownfield playbook / 改造计划模板；kit **98 tests**；镜像 `main` `f0ac5bd` + tag `v0.2.2`（CI run `42652383140` success）、`kit-drift` in sync；Android 真实仓只读试点 PASS（0 改动，报告 `harness/reviews/2026-11-10-kit-android-adoption-pilot.md`）
- [x] Phase 5.9：Android 真实仓 Stage B 完成并推送（`d313fdf..eaae1b6`，16 commits，历史清洗后；CI run `42760441698` success；分支保护已开）：P1 接入/P2 文档蒸馏/P3 清洁/P4 传感器与证据链（`20261109T163805Z-tests-pass` 65/65）/P5 负向注入 12/12 + 冷启动 5/5 + 计划 done 归档；报告 `harness/reviews/2026-11-10-kit-android-stage-b.md`
- [x] Phase 5.10：kit `v0.2.3` 发版完成：宿主卫生/分层传感器上游化并接入 standard profile 与 `make check-host`、`check_plan` 支持 Makefile 等根文件、新增 `scripts/harness-selftest`（门禁自测）、Android 矩阵转 ✅；kit **121 tests**；镜像 `main` `29bf937` + tag `v0.2.3`（CI run `42761789282` success）、`kit-drift` in sync；iOS CI run `42761678626` success
- [x] Phase 5.11：kit `v0.2.4` 发版完成：playbook「升级路径」拆分为版本升级（已验证步骤 1–5）/ profile 升级（仍未验证）；README/SPEC/CHANGELOG/来源案例同步；VERSION `0.2.4`；kit **121 tests**；镜像 `main` `c47fdf9` + tag `v0.2.4`（CI run `42764622139` success）、`kit-drift` in sync；iOS CI run `42764499029` success
- [x] Phase 5.12：kit `v0.2.5` 发版完成：接入指南（adoption.md）+ 演化治理（governance.md）+ README 重写（症状→机制、适合谁、接入前后五子系统评分、反臃肿九原则、多人/多 Agent 协作）；kit **121 tests**；镜像 `main` `52b9119` + tag `v0.2.5`（CI run `42803540280` success）、`kit-drift` in sync；iOS CI run `42803400474` success
- [ ] Phase 6（可选）产品可信度

## 验证证据

> 本节记录本方案制定时的基线事实与已执行命令；执行阶段的证据在对应阶段提交时补充。

| 命令 | 结果 | 环境 | 证据ID |
| --- | --- | --- | --- |
| `git ls-files '*.md' \| wc -l`；`git ls-files` | 40 个入库 markdown / 194 个入库文件 | 本机，HEAD `e5047b3` | —（基线盘点） |
| `find harness/runs -type f \| wc -l`；`du -sh harness` | 447 个忽略文件 / 6.8MB；`harness/runs` 3.9MB | 本机 | —（基线盘点） |
| `wc -l docs/14..docs/21` | 8 篇历史记录共 897 行；HANDOFF 483 行 | 本机 | —（基线盘点） |
| `make check` | **PASS**（docs/架构/计数/harness/计划；1 个历史 WARN 不阻断） | 本机，Xcode 27.1 | —（基线门禁） |
| `make resume` | 正常输出 active 计划与下一步；`git status` clean | 本机 | —（基线状态） |
| 独立只读审计（docs 子代理，2026-11-06） | **17/35（2.4/5）**；首访 5 问仅 1 问可答；3 套文档地图/5 套命令表/13 行重复计数；真实 Team/UDID/绝对路径入库 | 本机只读，未构建未改文件；底稿 `harness/runs/benchmark-audit/notes.md`（gitignore） | —（外部审计） |
| 敏感信息扫描（2026-11-06） | Team ID 命中 4 文件；CoreDevice ID 5 文件；`/Users/` 路径 3 个 JSON；Bundle ID 17 文件 | 本机 `git grep` | —（基线盘点） |
| 工具能力核对（2026-11-07） | Claude Code 原生读 AGENTS.md（v2.1.277+）、hooks 生命周期与 `.claude/settings.json` 可提交、skills/subagents；DeepSeek 提供 Anthropic 兼容 API 与 Claude Code 官方集成 | 官方文档（见 §参考）；本机未安装 Claude Code，未实测 | —（外部事实） |
| 首访 5 分钟测试（改造前，作者自测，Phase 1.1） | **1/5 可答 + 2 项部分**：是什么 ✅；为什么值得看 ❌；怎么跑 ⚠️（缺无 Xcode 路径）；怎么验证 ⚠️（README 门禁描述过期）；怎么复制 harness ❌（HARNESS 从 README 不可达） | 本机，仅按 README → docs/README 阅读 | —（基线，不是完成声明） |
| 首访 5 分钟测试（改造后，作者自测，Phase 1.9） | **4/5 可答 + 1 项部分**：是什么✅ / 为什么值得看✅ / 怎么跑✅ / 怎么验证✅ / 怎么复制 harness⚠️（有机制但缺 10 步采用指南，Phase 2 补）；用时约 3 分钟 | 本机，仅按 README → docs/README 阅读 | —（Phase 1.9） |
| 独立 Harness 复评（改造后，Phase 2.3） | **≈3.6/5**（Instructions 4.0 / State 3.5 / Verification 4.0 / Scope 3.0 / Lifecycle 3.5）；对外标杆 ≈24/35；L3 条件成立 | 独立复跑 check/verify-static/verify-claim/adapters-check；未跑真机/clean clone | `harness/reviews/2026-11-07-harness-reaudit.md` |
| 历史清理·敏感信息（2026-11-07） | `git filter-repo` 重写 43 个 commit；Team/设备 ID/本机路径 0 命中（树/历史/消息）；强推 `main`；备份 `/tmp/duiyi-pre-filter.bundle` | 本机 + GitHub（refs 已更新） | —（历史清理） |
| 历史清理·作者邮箱（2026-11-07） | `git filter-repo --mailmap` 二次重写 48 个 commit（作者/提交者邮箱 → GitHub noreply）；树内 7 文件 / 16 个被引用 commit 逐条按 subject 校验回填；强推 `main`；备份 `/tmp/duiyi-pre-email-filter.bundle` | 本机 + GitHub（refs 已更新） | —（历史清理） |
| CI 绿（2026-11-07） | 强推 `a243173` 未触发 run；普通提交 `47fd6c4` 触发 run `42344278003`：**static gates success；unit-tests skipped（按设计）** | GitHub Actions 公开 API；本地 pre-push `verify-static` PASS | —（外部记录：GitHub Actions run 42344278003） |
| 干净 clone 复现（Phase 3.1） | `git clone . /tmp/duiyi-fresh` → `make check` **PASS 0.33s**；`make verify-static` **PASS 4.65s**（42 单测） | /tmp 干净 clone，无 Xcode；仅 python3+git+make | —（过程记录：Phase 3.1 clean clone） |
| CI 合并与徽章（Phase 3.3） | `docs.yml` 删除；`verify.yml` 增加 `**/*.md`；README 徽章（verify/MIT/iOS） | 本机文件检查；CI 未触发新 run | —（Phase 3.3） |
| `make adapters-check`（2026-11-07） | **PASS**（6 个 skills 单源；hooks 示例/CLAUDE 模板/red-team agent 就绪） | 本机 | —（过程记录：适配层） |
| `make verify-static`（Phase 2 工作树） | **PASS**（新增 adapters-check 后 42 单测仍过） | 本机 | —（过程记录：静态门禁） |
| HARNESS/评分卡指标 | HARNESS 165 行；scorecard 53 行；root/README 已互链 | 本机 `wc -l` | —（文档） |
| 证据时效负向验证（Phase 2.5.4） | `make verify-claim-fresh`：3 条证据均 **STALE**（pbxproj / UI 测试文件变更）但 exit 0；`--fresh --strict` → **UNVERIFIED×3，exit 2** | 本机 | —（负向验证） |
| `make check`（2026-11-07，Phase 1 第一批） | **PASS**（0 error / 0 warn；公开文档白名单 docs 15/16、根 4 个 md） | 本机 macOS + python3 | —（过程记录：静态门禁） |
| `make verify-static`（2026-11-07） | **PASS**（+证据 schema/42 单测/语法；约 4.3s） | 本机 macOS | —（过程记录：静态门禁） |
| `make build`（模拟器 Debug，脱敏后） | **BUILD SUCCEEDED**（`xcodebuild -list` 也能解析工程） | Xcode 27.1 | —（过程记录：构建验证） |
| 脱敏扫描（2026-11-07） | 真实 Team ID / CoreDevice ID / 硬件 UDID / `/Users/` 实际路径 **0 命中**；baseline/issues 已占位符化 | 本机 `git grep` | —（发布红线） |
| 公开面指标（2026-11-07） | 根 md 4 个；README 133 行、CONTRIBUTING 79 行、docs/README 68 行、docs/decisions 34 行 | 本机 `wc -l` + check-docs | —（结构门禁） |
| `make test DERIVED=build/evidence-unit`（发布前重跑 2026-11-07） | **PASS**：passed=120 ≥ floor=120；failed=0；skipped=0；31.9s | 模拟器 iPhone 17 Pro Max / iOS 26.4.1 | `20261107T062204Z-unit-tests-pass` |
| `make test-ui DERIVED=build/evidence-ui`（发布前重跑 2026-11-07） | **PASS**：executed=3 ≥ floor=3；failed=0；skipped=1（预期）；53.9s | 模拟器 iPhone 17 Pro Max / iOS 26.4.1 | `20261107T062205Z-ui-tests-pass` |
| `make device-test`（生成时 PASS；对 HEAD 已 STALE） | passed=123 ≥ floor=123；failed=0；skipped=0（2026-11-06 生成，未重跑） | 真机 iPhone 13 / iOS 26.7 | `20261106T053620Z-device-tests-pass` |
| `python3 -m unittest tools.tests.test_plan -v` | **PASS**：14 用例（tmp git fixture）；done 缺 `submitted`/token 不存在或非祖先、证据 ID 缺失或非 PASS、PASS+占位无白名单 → FAIL；`—（过程记录：…）` → OK | 本机 python3 | —（负向验证） |
| `python3 -m unittest tools.tests.test_check_harness.py -v` | **PASS**：12 用例；嵌套 AGENTS 错节号/无法定位/错范围 → exit 1；根 AGENTS 自引用、skill→根 AGENTS → exit 0 | 本机 python3 | —（负向验证） |
| `python3 -m unittest tools.tests.test_doctor -v` | **PASS**：20 用例；缺 Xcode/runtime → exit 2 + 必需建议；可选缺失 → exit 0 | 本机 python3 | —（负向验证） |
| `make check-harness`（预算/§ 扫描） | **PASS**：AGENTS 1576/1650（余 74）；refs 932/925/929 对 975（余 43–50）；§/第N节 7 处命中（13 指令文件） | 本机 | —（过程记录：预算与 sensor） |
| `python3 tools/verify-claim.py --all --fresh --strict`（发布门禁演练） | exit 2：历史证据 3 条 STALE 判 UNVERIFIED；发布前重跑的新证据未受影响（各自行有 evidence id） | 本机 | —（过程记录：发布门禁） |
| Phase 2.5 独立复核（2026-11-07，非作者只读） | **P0×3 关闭**（验证接线/证据绑定/状态准确性）；上轮 P1 scope/§/token 关闭；新发现 3 个 P1（freshness 不看工作树、end 对 STALE 非阻断、旁注绕过）→ 本轮修 2 项；综合 **≈4.0/5**、L3 达成（有条件） | 独立复跑 HEAD `631d334` + 临时 clone 负向验证；CI run `42346447496` success | —（外部记录：独立复核） |
| 外部首访（2026-11-07，公开 clone @ `631d334`，AI 代理陌生人协议） | 5 问可答 **4/5**（Q5 采用指南在 HARNESS.md，属第 4 文件）；`make check` exit 0（≈1s）；`make verify-static` 浅克隆 exit 2 → `git fetch --unshallow` 后 exit 0（88 单测，≈15s） | 公开 clone；macOS 27.0.1 / python 3.14.7 / make 3.81，无 Xcode | —（外部记录：AI 代理，非人类） |
| 首访整改（2026-11-07） | **PASS**：浅克隆（`--is-shallow-repository=true`）跳过父提交用例；`--depth 1` 模拟提交后 `make check` / `verify-static` exit 0（88 tests，1 skipped）；README/CONTRIBUTING 增加 unshallow、无 Xcode 边界、harness 10 步指南直链与实测耗时 | 本机 /tmp 浅克隆 | —（过程记录：首访整改） |
| `git tag -a v1.0.0` + `git push origin v1.0.0`（2026-11-07） | annotated tag 目标 `c78abe8`（main HEAD）；CI run `42347475807` static success；release notes 见 `harness/release-notes-v1.0.0.md` | 本机 + GitHub | —（外部记录：release tag） |
| `make kit-check`（2026-11-07） | **PASS**：66 用例；3 个 profile 在空白 git 仓 init 后 `make check`/`verify-static` PASS；证据写入→`verify-claim` PASS；strict `release-check` PASS；dry-run/冲突/备份/无 Duiyi 专有引用 | 本机 python3 3.14.7 | —（过程记录：kit 验收） |
| 三档 demo 人工试用（2026-11-07） | minimal/standard/strict 各 init 到 /tmp 空白仓：created 14/26/37 文件；`make check` 全部 exit 0（init 内置首次检查）；standard `verify-static` exit 0；strict 写 tests-pass 证据后 `verify-claim`/`release-check` PASS | 本机 /tmp；无 Xcode | —（过程记录：kit 试用） |
| kit 卫生扫描（2026-11-07） | `harness-kit/{core,adapters,profiles,scripts}` 对 `Duiyi/duiyi/对译/TranslationSession/SwiftData` **0 命中**（唯一允许为 README 来源案例）；`make kit-check` 含专有名词/残留占位符/链接断言 | 本机 | —（过程记录：kit 卫生） |
| Phase 5.4 外部试点（2026-11-07，AI 代理采用者） | **接入成功**：standard 五步闭环；首次 `make check` 一次 PASS；`verify-static` / `verify-claim`(含 `--fresh`) exit 0；执行 ≈80s（端到端 ≈7m20s，含源获取失败重试）；重复 init 冲突（24 CONFLICT 无写入）/ `--force` 备份 / 已有 Makefile → `Makefile.harness` 探测通过 | 空白 Python 宿主；公开 main @`501ae9c`；报告 `harness/reviews/2026-11-07-kit-pilot.md` | —（外部记录：AI 代理） |
| `make verify-static`（Phase 5 集成后，2026-11-07） | **PASS**，约 17s：91 个 Duiyi 脚本单测 + 69 个 kit 端到端测试 + docs/架构/计数/harness/计划/证据/adapters 全过 | 本机 python3 3.14.7 / make 3.81 | —（过程记录：集成门禁） |
| Node 试点（2026-11-07，Node 24 / `node --test`） | **PASS**：blank Node 项目 init standard → 首次 `make check` PASS；`npm test` 两个断言通过；证据记录 2 个通过用例 → `verify-claim` PASS；`verify-static` exit 0 | 本机 node 24.14 / npm 11.9 | —（过程记录：语言试点） |
| Swift 试点（2026-11-07，SwiftPM / `swift test`） | **PASS**：blank SwiftPM 包 init standard → 首次 `make check` PASS；`swift test` Executed 1 test / 0 failures；`.build/` 已被 gitignore 忽略（证据写入不被 dirty 拦）；`verify-claim`/`verify-static` PASS | 本机 Apple Swift 6.4 | —（过程记录：语言试点） |
| kit standalone 布局（2026-11-07） | **PASS**：`cp -r harness-kit` 到仓库外后 `python3 -m unittest discover -s tests -q` 69 tests OK（tests 自动适配 monorepo/独立仓两种根）；独立仓文件（LICENSE/CHANGELOG/.gitignore/CI workflow）就绪 | 本机 /tmp | —（过程记录：独立仓准备） |
| 独立模板仓发布（2026-11-07） | **PASS**：`git subtree split --prefix=harness-kit` → push `main`（`76ac99d`）；公开仓可 clone；clone 内 `python3 -m unittest discover -s tests -q` → 69 tests OK；GitHub Actions run `42374549293` **success** | 本机 + GitHub；<https://github.com/DavidTeam2008/harness-kit> | —（外部记录：模板仓） |

| GitHub Release + 仓库元数据（2026-11-09，用户操作） | Release `v1.0.0` 已发布（title「对译 Duiyi v1.0.0」）；Duiyi description/topics（9 个）与 social preview 已设置；harness-kit description/topics（6 个）已设置 | GitHub 公开 API 读取 + 用户确认 | —（外部记录：GitHub Release） |
| kit 镜像维护机制（2026-11-09） | **PASS**：`make verify-static` PASS（91 脚本单测 + 69 kit 用例）；漂移负向验证 `kit-drift` → DRIFTED（local `3813cdc` vs remote `76ac99d`，exit 2），`make kit-publish` 后 in sync；镜像 `main` = `3813cdc`，tag `v0.2.0`（annotated），临时 clone 内 69 tests OK；GitHub Actions run `42566984847` **success**；Duiyi CI run `42566945977` **success** | 本机 python3 3.14.7 / make 3.81；GitHub Actions | —（外部记录：镜像发布） |
| kit v0.2.2 实施（2026-11-10） | **PASS**：`make verify-static` 全套（91 脚本单测 + **98** kit 用例；新增 adopt 12 / JUnit 16 / Android 推断；三档 profile、证据生命周期、strict release-check 回归通过）；kit 卫生扫描 0 命中；VERSION `0.2.2`；3 个并行 agent 交付 + Lead 集成（复查修正 android 命令对齐、wrapper jar 误报、过期标记词） | 本机 python3 3.14.7 / make 3.81 | —（过程记录：kit 集成门禁） |
| Android 仓只读盘点试点（2026-11-10，Stage A） | **PASS**：`harness-adopt --report` → 语言 `android`、建议 `./gradlew testDebugUnitTest`；缺 docs 索引 + 10 篇未登记文档、1 条跨仓断链、6 处疑似过期标记、1 个绝对符号链接、6 处本机路径、0 构建产物误报；目标仓 **0 改动**；<1s | 目标仓 `d313fdf`（重写后；原 `2ff1fae`，115 跟踪文件）；kit 0.2.2 | —（外部记录：存量仓只读试点；报告 `harness/reviews/2026-11-10-kit-android-adoption-pilot.md`） |
| Android 真实仓 Stage B（2026-11-10，`d313fdf..eaae1b6`） | **PASS**：kit v0.2.2 standard 完整接入；P1 scaffold、P2 文档蒸馏（11 当前 + 10 归档、D1–D15）、P3 清洁（死代码/manifest/符号链接/本机脚本）、P4 `check-host` + `check-quality` + `tests-pass` 证据（65/65）、P5 负向注入 12/12 + 冷启动 5/5 + 计划归档；目标仓 `make check` / `verify-static` / `verify-claim` / `check-quality` 全 PASS；历史 filter-repo 清洗 + 分支保护开启 | Android 仓 main `eaae1b6`（16 commits；重写后）；JDK 17 / Gradle 8.10.2 / AGP 8.7.2；CI run `42760441698` success | 跨仓证据：`realtime-translator-android@eaae1b6` → `harness/evidence/20261109T163805Z-tests-pass.json`（`git.commit` 回填 `2c3b479`） |
| kit v0.2.2 镜像发布（2026-11-10） | **PASS**：`make kit-publish` → 镜像 `main` `fcc08dc..f0ac5bd`；tag `v0.2.2`（annotated）；临时 clone VERSION `0.2.2`、**98 tests OK**；镜像 CI run `42652383140` **success**；`make kit-drift` → in sync（`f0ac5bd`）；iOS 仓 CI run `42652279448` success | 本机 + GitHub；<https://github.com/DavidTeam2008/harness-kit> | —（外部记录：镜像发布） |
| kit v0.2.3 实施（2026-11-10） | **PASS**：121 tests（+23：host tools 16、selftest 5、check_plan 2）；三 profile init + standard/strict `verify-static` 回归；`make verify-static` PASS（iOS 91 + kit 121）；selftest 标准宿主 `PASS 5 / SKIP 3`、条件宿主 `PASS 8` | 本机 python3 3.14.7 / make 3.81 | —（过程记录：kit 集成） |
| kit v0.2.3 镜像发布（2026-11-10） | **PASS**：`make kit-publish` → 镜像 `main` `f0ac5bd..29bf937`；tag `v0.2.3`（annotated）；临时 clone VERSION `0.2.3`、**121 tests OK**；镜像 CI run `42761789282` success；`kit-drift` → in sync（`29bf937`）；iOS 仓 CI run `42761678626` success | 本机 + GitHub；<https://github.com/DavidTeam2008/harness-kit> | —（外部记录：镜像发布） |
| kit v0.2.4 实施（2026-11-10） | **PASS**：`playbook.md`「升级路径」拆分（版本升级已验证 1–5 步 / profile 升级仍未验证）；README 能力表 + 来源案例 + 局限、SPEC §10、CHANGELOG、VERSION `0.2.4`；**121 tests**；`make verify-static` PASS（iOS 91 单测 + kit 121） | 本机 python3 3.14.7 / make 3.81 | —（过程记录：kit 集成） |
| kit v0.2.4 镜像发布（2026-11-10） | **PASS**：`make kit-publish` → 镜像 `main` `29bf937..c47fdf9`；annotated tag `v0.2.4`（`7d44b52` → `c47fdf9`）；tag clone VERSION `0.2.4`、**121 tests OK**；镜像 CI run `42764622139` success；`make kit-drift` → in sync（`c47fdf9`）；iOS 仓 CI run `42764499029` success | 本机 + GitHub；<https://github.com/DavidTeam2008/harness-kit> | —（外部记录：镜像发布） |
| kit v0.2.5 实施（2026-11-10） | **PASS**：`docs/adoption.md`（三条接入路径 + Agent bootstrap/反模式 + 接入前后五子系统评分案例）、`docs/governance.md`（反臃肿九原则/演化机制/多人与多 Agent 协作）、README 重写；新文档纳入 kit 链接检查；**121 tests**；`make verify-static` PASS（iOS 91 单测 + kit 121） | 本机 python3 3.14.7 / make 3.81 | —（过程记录：kit 集成） |
| kit v0.2.5 镜像发布（2026-11-10） | **PASS**：`make kit-publish` → 镜像 `main` `c47fdf9..52b9119`；annotated tag `v0.2.5`（`0785e17` → `52b9119`）；tag clone VERSION `0.2.5`、**121 tests OK**；镜像 CI run `42803540280` success；`make kit-drift` → in sync（`52b9119`）；iOS 仓 CI run `42803400474` success | 本机 + GitHub；<https://github.com/DavidTeam2008/harness-kit> | —（外部记录：镜像发布） |

| 仓库改名（2026-11-09） | **PASS**：`PATCH /repos/...` → `realtime-translator-ios`；`git remote set-url` 后 push 成功；旧名 API `301 → repositories/1349714234`、旧 URL `git ls-remote` 仍返回 `a6e6cf3`；`tags`/`releases`/star 保留（9 topics）；名字相关文档推送 CI run `42569754695` success；kit 链接更新后镜像 `fcc08dc` + tag `v0.2.1`，镜像 CI run `42569790859` success | GitHub API + 本机 git；classic token（`repo`/`workflow`） | —（外部记录：仓库改名） |

| 外部走查·真机路径（2026-11-09，用户按 README） | `APM_DEVICE=… harness/tools/device-test.sh` → 预热 **FAILED passed=0 failed=0 skipped=0（6s）**；根因=测试 target 无 Team（仓库脱敏预期）+ 本地 pbxproj 只改了 App target（未提交，已还原）；脚本当时未打印 `diagnostics.errors` | 本机 Xcode 27.1 / iPhone 13 iOS 27.0.1（网络配对） | —（外部记录：用户走查） |
| 真机脚本诊断改进（2026-11-09） | **PASS（诊断层）**：无 `APM_TEAM` → 打印 `Signing ... requires a development team` 与修复提示；`APM_TEAM=…` 后安装启动推进到 `Developer App Certificate is not trusted`（20s），脚本给证书信任指引；`bash -n` + `make verify-static` PASS | 本机 Xcode 27.1 / mobilebuildmcp 2.7.1 | —（过程记录：真机诊断） |
| 分支保护（2026-11-09） | **PASS**：`PUT /branches/main/protection` → `allow_force_pushes=false`、`allow_deletions=false`、`enforce_admins=true`（无必过检查/PR，直接 push 不受影响）；随后普通 push `9c39952..4e0b994` 成功，CI run `42623318875` **success** | GitHub API（classic token）+ 本机 git | —（外部记录：分支保护） |

| 真机单元（2026-11-09，设备侧） | **PASS**：`APM_TEAM=… APM_DEVICE=… device-test.sh unit` → 预热 5/5 + 目标 120/120，failed=0 skipped=0，≈8.5s；干净工作树生成证据（git.dirty=false，commit 800db5c）；`verify-claim` PASS；CI run `42626863075` success | iPhone 13 / iOS 27.0.1（网络配对）；Xcode 27.1；mobilebuildmcp 2.7.1 | `harness/evidence/20261109T133618Z-unit-tests-pass.json` |
| 真机 UI（2026-11-09，负向） | **UNVERIFIED**：`device-test.sh ui` → 预热通过、UI runner `Early unexpected exit ... code 74`（网络配对无法准备 DeviceSupport / 自动化密码弹窗）；脚本已改为失败不写证据（实测未生成 `*-pass` 文件） | 同上 | —（未验证，环境限制） |
| 真机全套（2026-11-09，设备侧） | **PASS**：设备侧密码弹窗响应后 `device-test.sh all` → 预热 5/5 + 目标 123/123，failed=0 skipped=0，171.7s；干净工作树生成证据（`git.dirty=false`，commit `66f3372`）；UI exit 74 的结论被后续成功运行取代 | iPhone 13 / iOS 27.0.1（网络配对）；Xcode 27.1；mobilebuildmcp 2.7.1 | `harness/evidence/20261109T142307Z-device-tests-pass.json` |

## 未验证项

- 首访：作者自测 4/5；Phase 4 由无上下文 AI 代理按公开 clone 复测 4/5；**人类非作者首访已完成**（2026-11-09 用户确认、反馈无阻塞；仓库内无该次首访记录，仅用户报告）。
- 独立复评为只读：未跑 xcodebuild/模拟器/真机/clean clone；3.6/5 与 24/35 为当前口径，不证明动态行为正确。
- clean clone 已实测（Phase 3.1，PASS）；独立复评时的未提交状态已提交，clone 可复现。
- 仓库改名已执行（2026-11-09）；历史档案（reviews/release-notes/evidence）内旧仓库名保留（GitHub 301 生效，不再单独改历史文档）。
- Claude Code 环境未实测（本机未安装）；hooks/CLAUDE.md/agent 示例与 `adapters-check` 为设计资产，发布前补实测或标未验证。
- 首次真实 PR / 分支保护（PR 强制 static）未验证：当前 PAT 受组织策略 403，无法用 API 配置；需仓库管理员在 GitHub Settings 设置或提供可用凭据。
- GitHub Release / description/topics/social preview **已创建**（2026-11-09，用户操作，公开 API 复核）；`gh` PAT 仍受组织策略 403，后续仓库管理操作（改名/分支保护）仍只能由用户或换 PAT。
- 真机：**单元与全套（123/123）均已 fresh PASS**（`20261109T133618Z-unit-tests-pass`、`20261109T142307Z-device-tests-pass`）；UI exit 74 仅为网络配对下的过程现象，设备侧响应密码弹窗后全套通过（2026-11-09）。
- 真机签名构建未验证（本机无 Team；仅验证模拟器 Debug 构建）。
- 历史敏感信息/作者邮箱已用 `git filter-repo` 两轮清理（2026-11-07），本地与远端分支历史 0 命中；远端 unreachable 旧对象仍可按 SHA 访问（用户已接受现状，不再联系 GitHub Support）。
- DSH hooks 能力随版本变化（0.2.1-rc.5 未打包）；模板按「门禁 + CI + 适配层」设计，不依赖 hooks 可用。
- Phase 2.5 已完成（2.5.1–2.5.8）；其中 done 的 `submitted`/证据绑定目前只在单测负向 fixture 演练，本计划尚未 done，Phase 4 收尾时以本计划走一遍真实 done 演练。
- P1 残留（Phase 2.5 独立复核）：`make end` 对 STALE 只告警（`release-check` strict 阻断，设计保留）；CI/pre-push 不跑 verify-claim 判定；P0-1/P0-3 行为测试与性能门禁仍缺（Phase 6）。
- 远端旧 commit 仍可通过 SHA 访问（GitHub 保留 unreachable objects）；用户已接受「分支干净、旧对象不可达」状态（2026-11-07 决策）。
- Phase 5 外部试点已由 AI 代理在空白 Python 项目完成（standard 接入成功，报告见上）；作者另一个真实项目、人类采用者、已有历史文档的冲突整合仍未验证。
- Phase 5 独立模板仓未创建：PAT 受组织策略 403；当前交付为仓库内 `harness-kit/` 可复制目录（`git clone` 后 `cp -r`/subtree 拆分）。
- kit 语言覆盖：Python/Node/SwiftPM 已端到端实测；**Go 未安装未实测、Xcode iOS 工程未实测**（需显式 `--test-command` 给 xcodebuild 参数）；**Android/Gradle 已完成真实仓完整试点（Stage A+B，2026-11-10）并在 v0.2.3 矩阵转 ✅**；测试计数仍由宿主写入 evidence（kit 不解析测试输出）。
- Android 试点局限：`harness-adopt` 的 profile/过期标记为启发式（可能误报）；绝对符号链接目标未脱敏（v0.2.3 候选）；`--write-plan` 未在真实仓执行；超大仓性能未验证（当前 <1s / 115 文件）。
- Android 仓 Stage B 已完成并推送（16 commits 至 `eaae1b6`；历史已 filter-repo 清洗、作者邮箱与本机路径出库；分支保护 `static gates` 必过已开）；残留：真机未复跑、release/native 未重建、非荣耀设备未验证、ktlint baseline 存量债；kit v0.2.3 候选（check_plan 支持无扩展名根文件、宿主 `check_hygiene`/`check_layers` 上游化、Android 矩阵行转 ✅）。
- kit 版本升级路径已在 Android/Gradle 存量仓（v0.2.2→v0.2.3）完成真实验证（2026-11-10，selftest 8/8；详情见该仓归档计划与 kit playbook）；**profile 升级（minimal↔standard↔strict）仍未在真实项目验证**，其他语言/版本组合也未验证。
- kit 独立仓 CI 已由公开 API 确认 success（run `42374549293`）；**后续 kit 变更已提供 `make kit-publish` 手动同步 + `make kit-drift` 漂移检查（2026-11-09）**，但不自动触发（不引入 CI 跨仓写权限）；strict 档与 hooks 远端触发未由外部试点覆盖（kit 自身测试覆盖 strict/release-check）。
- `Order/` 是否被 Release 构建配置引用未核实（不影响文档主线）。

## 参考（外部事实核对，2026-11-07）

- Claude Code Hooks reference（生命周期/hook 事件/`.claude/settings.json` 可提交）：https://code.claude.com/docs/en/hooks
- Claude Code memory（CLAUDE.md 体系；**原生读取 AGENTS.md，v2.1.277+**）：https://code.claude.com/docs/en/memory
- Claude Code 扩展总览（skills/subagents/hooks/MCP/plugins 的选择矩阵）：https://code.claude.com/docs/en/features-overview
- DeepSeek API：Anthropic API 兼容（`base_url=https://api.deepseek.com/anthropic`）：https://api-docs.deepseek.com/guides/anthropic_api
- DeepSeek × Claude Code 官方集成（环境变量/模型映射）：https://api-docs.deepseek.com/quick_start/agent_integrations/claude_code
- DeepSeek Harness 文档入口：https://deepseek-harness.github.io/deepseek-harness/en/guide/quickstart
- DSH 可编程面盘点（本机 0.2.1-rc.5 安装包核查，仓库外底稿）：`harness/runs/harness-audit/01-research.md`（gitignore，不随仓库发布）

## 尝试记录

| 尝试# | 动作 | 结果 | 时间 |
| --- | --- | --- | --- |
| 1 | 盘点文档面/门禁现状 + 读取上游计划与模板 | 完成，事实写入 §1.3 | 2026-11-06 |
| 2 | 派生独立审计员做双视角首访/标杆评估 | 团队席位已满（8/8）；复用 docs 子代理完成只读审计（17/35；底稿 `harness/runs/benchmark-audit/notes.md`，未改 tracked 文件） | 2026-11-06 |
| 3 | 盘点敏感信息与 evidence xcresult 路径 | Team/UDID/绝对路径已定位到 file:line；evidence 的 xcresultPath 已是仓库相对路径（换机器会 UNVERIFIED，属设计） | 2026-11-06 |
| 4 | 执行 Phase 1 第一批（HANDOFF 拆分、README/LICENSE/CONTRIBUTING/decisions、脱敏、白名单） | 完成；`make check` / `verify-static` PASS、`make build` BUILD SUCCEEDED；额外清掉 10 个文件的真实硬件 UDID | 2026-11-07 |
| 5 | 计划"未提交改动"与 git status 不一致（scope.allow 缺嵌套 AGENTS、目录通配解析问题） | 已修：补齐 allow + 改精确路径；`make check-plan` PASS | 2026-11-07 |
| 6 | 作者邮箱从 git 历史移除（用户确认） | `git filter-repo --mailmap` 重写 48 commit；commit-map 混入首轮旧映射，改用「提交顺序 + subject 全等」index-map 回填 7 文件 / 16 引用并逐条校验；强推 `main` | 2026-11-07 |
| 7 | Phase 2.5 P0 工具整改（3 个并行 agent：plan.py / check-harness / doctor） | 全部完成：plan.py +198/−47（14 用例）、check-harness +151/−33（12 用例）、doctor +146（20 用例）；Lead 集成、计划记录、负向验证 | 2026-11-07 |
| 13 | kit v0.2.2 存量接入能力（3 个并行 agent：adopt / JUnit+android / docs+SPEC） | 全部落地：harness-adopt（只读盘点，12 用例）、JUnit XML 证据适配器（16 用例）、`--language android`、brownfield 七步 playbook、改造计划模板；98 kit tests PASS；Lead 复查修正 3 项（android 命令对齐、wrapper jar 误报、过期标记词）；Android 真实仓只读试点 PASS（0 改动） | 2026-11-10 |
| 14 | Android 真实仓 Stage B（brownfield P1–P5，5 个并行 agent + Lead 集成） | 16 commits 推送 `eaae1b6`（历史 filter-repo 清洗后）：文档蒸馏（11 当前 + 10 归档、D1–D15）、清洁批次、`check-host`/`check-quality`/JUnit 证据链、负向注入 12/12、冷启动 5/5、计划 done+归档；注入修出 `check_layers` 前缀匹配空转与 `check_hygiene` `/home/` 误报；分支保护（`static gates`）已开；CI run `42760441698` success | 2026-11-10 |
| 15 | kit `v0.2.3`（3 个并行 agent：宿主传感器/自测工具/文档） | `check_hygiene`/`check_layers` 上游化（16 用例）、`check_plan` 无扩展名根文件（2 用例）、`harness-selftest`（5 用例，条件宿主 8/8）、文档同步；kit 121 tests PASS；Android 矩阵转 ✅ | 2026-11-10 |
| 16 | kit `v0.2.4` 升级路径实证回写（文档） | playbook 新增「升级路径」：版本升级已验证步骤（临时渲染→逐文件 diff→只回写 kit 管理面→`verify-static`+selftest）、profile 升级仍未验证；README/SPEC/CHANGELOG/来源案例同步；VERSION 0.2.4；kit 121 tests PASS；镜像 `main` `c47fdf9` + tag `v0.2.4`（CI run `42764622139` success）、`kit-drift` in sync | 2026-11-10 |
| 17 | kit `v0.2.5` 接入/治理文档与 README 重写 | `docs/adoption.md`（三条接入路径 + 接入前后五子系统评分案例 + 验收清单 + FAQ）、`docs/governance.md`（反臃肿九原则、演化机制、行为级评估 v0.3+ 议题、多人与多 Agent 协作）、README 重写（症状→机制、适合谁、评分案例、反臃肿/多人摘要）；新文档纳入 kit 链接检查；kit 121 tests PASS；镜像 `main` `52b9119` + tag `v0.2.5`（CI run `42803540280` success）、`kit-drift` in sync | 2026-11-10 |
| 12 | 设备信任后复跑真机 + 取证 | 单元 120/120 PASS 并写设备证据（干净树，`verify-claim` PASS）；UI 仍 exit 74（网络配对限制）；首证因 dirty 工作树被判 FAIL → 改为「先提交再取证」；脚本改为失败不写证据（避免 `*-pass` 文件自相矛盾） | 2026-11-09 |
| 11 | 用户按 README 走真机路径 + 开启分支保护 | 真机预热 6s/0 用例：脚本吞掉 `diagnostics.errors`，真实原因是测试 target 无 Team；已修脚本（打印原因+`APM_TEAM`+证书信任提示）与文档；分支保护已开（禁 force push/删除，普通 push 已实测通过） | 2026-11-09 |
| 10 | 重登 gh + API 改名 | 组织策略「fine-grained token 有效期 ≤366 天」导致 403；用户重登为 classic token（`repo`/`workflow`）→ 改名成功、旧名 302/301 保留；同时确认 kit `v0.2.0` 发布链路可用 | 2026-11-09 |
| 9 | 用户完成 Release + 仓库元数据；评估改名与双份 kit 维护 | 改名成本：仓库级 ≈15 分钟（4 处文档 + remote，GitHub 301），App 工程级不建议；kit 维护定为「上游唯一源 + 镜像只读」，已加 `kit-publish`/`kit-drift` 并升 0.2.0；API 改名 403 → 交用户 UI 执行 | 2026-11-09 |
| 8 | Phase 2.5 后独立复核 + 外部首访（并行 2 个 agent） | 复核：P0×3 关闭、综合 ≈4.0/5、L3 达成（有条件）；首访：4/5 可答、浅克隆 P0 → 已修并浅克隆复核；报告见 `harness/reviews/2026-11-07-phase2.5-reaudit.md`、`harness/reviews/2026-11-07-external-first-visit.md` | 2026-11-07 |

## 未提交改动

- 无未提交改动（kit v0.2.5 发布记录已提交）。

## 下一步

1. 本计划主线（Phase 1–5.9）完成：iOS 标杆 + kit v0.2.2 + Android 真实仓 Stage A/B 均已收口；Stage B 结果已回写（报告见上）。
2. 用户决定：Android 产品 Next（延迟探针/流式回字幕/增量翻译 A/B）**本会话不做**，按目标仓 `docs/06-roadmap.md` 另行排期。
3. kit `v0.2.3` 已发版（镜像 tag `v0.2.3` + CI success + drift in sync）：Android 矩阵 ✅、`check_plan` 无扩展名根文件、宿主 `check_hygiene`/`check_layers` 上游化、`harness-selftest` 工具化。
4. Phase 6（可选）：P0-1 并发 / P0-3 持久化行为测试，独立排期。
5. kit `v0.2.4`（文档）已发版（镜像 `c47fdf9` + tag `v0.2.4`、CI success、drift in sync）：升级路径实证已回写；Android 仓 pin 仍为 v0.2.3（无接口/门禁变化，无需升级）。
6. kit `v0.2.5`（接入指南 + 演化治理 + README 重写）已发版（镜像 `52b9119` + tag `v0.2.5`、CI success、drift in sync）：用例覆盖接入指南/治理文档；无脚本/门禁行为变化，Android 仓 pin 不变。

## 待确认

- 远端旧 commit 仍可按 SHA 访问；用户已接受现状（2026-11-07），不联系 GitHub Support。
- GitHub Actions 已在新普通提交上验证；如后续仍不触发，检查仓库 Actions 设置/额度。
- D-B6 仓库改名、D-B7 发布节奏仍待发布阶段再定。
