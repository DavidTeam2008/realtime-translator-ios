---
id: 2026-11-05-harness-engineering
status: active
level: L2
owner: david
updated: 2026-11-05
phase0_commit: d83bb05
phase1_commit: 3935e60
phase1_state: committed-evidence-recorded-pushed
device_state: device-connected-ui-automation-password-needed
scope:
  allow:              # 方案 §5.7 新增/修改清单；子任务拆分时以任务级 write scope 为准
    - .gitignore
    - AGENTS.md
    - AGENTS.local.md.example
    - HARNESS.md
    - README.md
    - HANDOFF.md
    - Makefile
    - references/
    - docs/
    - tools/
    - .apm/
    - .dsh/
    - .githooks/
    - .github/
    - Duiyi/Services/AGENTS.md
    - Duiyi/Features/AGENTS.md
    - DuiyiTests/AGENTS.md
    - DuiyiUITests/AGENTS.md
    - Duiyi.xcodeproj/project.pbxproj   # 例外：3 个 target 同步文件夹排除 AGENTS.md 资源
  deny:               # 方案 §5.7“不动”：业务代码、测试断言、签名信息
    - Duiyi/**/*.swift
    - DuiyiTests/**/*.swift
    - DuiyiUITests/**/*.swift
    - Duiyi.xcodeproj/xcuserdata/
acceptance:           # Phase 0 判据（§6 Phase 0：每条都做“故意破坏→红”）
  - make check PASS（含 check-plan，token 预算内）
  - 删 1 个 @Test → 测试基线门禁红
  - Domain 加 import SwiftUI → 架构门禁红
  - 计划缺证据行或“未提交改动”与 git 不一致 → plan.py check 红
  - plan.py latest --active 只返回本计划；现有已完成计划已标 status: done
  - make resume 输出正确“下一步”；新会话 ≤3 次读取能定位“下一步”
verify:               # Phase 0 完成前必须跑的命令
  - make verify-static
  - make check
  - PYTHONDONTWRITEBYTECODE=1 python3 tools/plan.py check
  - PYTHONDONTWRITEBYTECODE=1 python3 tools/plan.py latest --active
  - make resume
  - PYTHONDONTWRITEBYTECODE=1 python3 tools/doctor.py
---

# Harness Engineering 研发工程体系落地 · 改造方案（L2 计划）

> 状态：**Phase 0 已实施（未提交）；Phase 1–3 待做**　|　级别：L2（流程 + 仓库结构）　|　日期：2026-11-05
> 用户已确认第 8 节全部决策并授权 Phase 0；本文是方案 + 执行计划 + 实施记录。规则/流程类改动按决策 6 仅红队场景强制独立复核。
> 计划入库规则：不写本机绝对路径、密钥、设备 UDID；本文件使用仓库相对路径。

## 0. 结论摘要（TL;DR）

1. **定义**：Harness Engineering（驾驭工程）不是提示词技巧，而是"模型之外、让模型行为可控的研发工程体系"——以仓库为唯一真源，用 **guides（前馈：指令/规范/技能/结构约束）** + **sensors（反馈：测试/静态检查/结构检查/证据/红队）** 构成闭环，把非确定性的 agent 约束成**可验收**的交付系统。
2. **判定**：本项目**部分符合**。规则骨架、铁律、测试文化、证据文化是真的；但 **验证层/状态层/进化层不成立**——agent 声称"修好/测试通过"时仓库基本无法自动否证。综合判断约 **2.5/5**，属于"文档型 Harness 1.0"。
3. **是否改造**：需要，但**不是推倒重来**。改造主线：把"文档告诉 agent 该做什么"升级为"仓库能自动判定 agent 做对了没有"，并把"人/好 agent 的自觉"替换为"机器门禁 + 独立验证"。
4. **改造范围**：A. 指令层（AGENTS.md 从 1964→≈1400，新增嵌套 AGENTS.md + `.dsh/skills` + 执行协议）；B. 项目层（测试基线门禁、架构铁律脚本、证据 schema/verify-claim、状态机、`doctor/resume/end`、CI 扩展、maker-checker、月度 harness 审计与失败回写）。
5. **投入**：A+B 主体约 **5–7 人日**（不含 P0-1/P0-2/P0-3 的行为测试，那属于产品工作）；分 4 阶段，每阶段可单提交回滚。
6. **最大风险**：流程税与"假绿"（有 evidence 不等于真对）。因此门禁必须分层（**静态 <2s / 动态分钟级 / 真机人工**）、证据三值判定（PASS/FAIL/UNVERIFIED），并诚实声明行为质量仍需真机 + 人工。
7. **当前进展**：第 8 节决策已全部确认；**Phase 0 已实施**（AGENTS 压缩+嵌套、静态门禁、状态机、单源清理），`make check` / `make verify-static` PASS；动态测试因本会话沙箱内 SwiftData 宏插件失败而未验证（§10）。Phase 1–3 待做。

---

## 1. 目标与非目标

### 目标

- 用 Harness Engineering 五子系统（Instructions / State / Verification / Scope / Session Lifecycle）对照现状，给出**可执行的差距清单**与改造顺序。
- 改造后，任意一个 agent（含 deepseek V4.1 flash）新会话进入仓库时：能在 ≤3 次读取内知道"我是谁、做到哪、下一步是什么、怎么算完成"。
- 任意"完成/已验证"声明都能被仓库脚本**判 PASS / FAIL / UNVERIFIED**，而不是自由的文字。
- 规则/门禁本身可持续演进：新增规则要么配机检，要么配固定动作；不把规则塞进不受控文档来绕过预算。
- 改造后规则层仍保持单一真源、可 diff、可回滚。

### 非目标

- 不重写业务代码；不改测试既有断言；不恢复已暂停的启动优化；不改变"显式结束才入历史"等产品语义。
- 不照搬大厂五层组织级驾驭工程流程——本项目是单人/小团队 iOS 项目，只取它的原则（可验收闭环、人机边界、指引+传感器、失败回写）。信通院 L1–L5 成熟度模型**只作外部参照**（其正文未能取得，见 10 节），不作验收标准。
- 不引入重型 BDD/评测平台/外部服务；不依赖团队模板仓可用；不把真机测试塞进 CI。
- 不为"有 CI"而买 macOS runner；先做零成本静态门禁，macOS 动态测试作为可选增强。
- 不承诺 DSH 的 hooks/MCP/Agent Teams/workflow 在仓库内"自动生效"（这些是 profile/会话级能力，见 4.7）。
- 本计划**不执行**任何改造；本文交付后等用户确认。

---

## 2. 判定：这个项目遵从 Harness Engineering 吗？

### 2.1 一页版定义（详细底稿与逐源引用见第 12 节）

**（1）宽定义（共识）**：`Agent = Model + Harness`。Harness 是模型之外、决定模型能力能否兑现的全部工程基础设施（Thoughtworks/Böckeler，转引 LangChain）。在 coding agent 场景要区分三层：模型内置的 builder harness / 你作为用户构建的 **user harness** / 你的组织治理层；本方案关心 user harness。

**（2）控制论模型（Fowler/Böckeler，2026-04）**：外层 harness = **Guides（前馈控制）** + **Sensors（反馈控制）**；二者都分 **computational（确定性、毫秒–秒级）** 与 **inferential（LLM 判断、慢且不确定）**。人负责 **steering loop**：同一问题重复出现时，改 guide/sensor，而不是反复修 prompt。三类被调节对象：maintainability harness（最成熟）、architecture fitness harness、**behaviour harness（最大空白）**。

**（3）工程落地框架（learn-harness-engineering / Anthropic）**：五子系统 **Instructions / State / Verification / Scope / Session Lifecycle**（注意：该课程 L02 另有一套 instructions/tools/environment/state/feedback 口径，本方案采用 README 五子系统 + Fowler 的 guides/sensors，不混用）。Anthropic 的长任务三件套：**initializer agent + coding agent**、`init.sh`、`feature_list.json`、progress 日志、每会话只做一个 feature、干净提交与 handoff；后来演化出 **maker / evaluator 分离**（"让做事的 agent 和评判的 agent 分开"是强杠杆）。

**（4）仓库工程（OpenAI，2026-02，部分为二手摘要）**：repo-as-spec / docs-as-system-of-record；`AGENTS.md` 应是 **~100 行的目录页**，不是百科；知识放结构化 `docs/` 树，配 linter + CI + 周期性 "doc-gardening"；"golden principles" 用后台 agent 持续扫描并开小 PR 修复。核心结论句："Our most difficult challenges now center on designing environments, feedback loops, and control systems."

**（5）中国产业界（信通院/CCSA，2026-09）**：称之为"驾驭工程"，强调从"让模型听懂"到"让模型行为可控"，是"智能原生时代软件工程的核心管控框架与生态底座"；提出设计原则、核心技术体系、关键工程原语、L1–L5 能力成熟度模型。核心判据：**"编译通过、测试通过不足以判定可交付"**，要建可验收的研发闭环。本方案只取其框架级佐证（PDF 正文未验证，见第 10 节）。

**（6）DSH 运行时视角（二手转述 DSH 文档）**：`Agent = Model + Environment + Tools + State`；"everything is a plugin"；"**Model-visible means logged**"——模型能看到的东西必须能从会话日志重建。这为"可观测性"提供了平台底座：仓库侧补 evidence 摘要，平台侧已有会话日志可查（`~/.dsh/sessions`，本地、不入库）。

> **一句话**：Harness Engineering 是把资深工程师的隐性经验（规范、验收、上下文、边界、交接）外化为**可执行、可版本化、可反馈**的工程设施；目标是**提高一次做对的概率 + 在到人眼之前自纠**，而不是让模型变聪明。

### 2.2 判定表（审计判断，非精确度量）

| 维度 | 现状 | 评级 | 关键证据 |
|---|---|---|---|
| Instructions（指令层） | AGENTS.md 有冷启动/铁律/路由/命令/验证矩阵，references 分层，token 有硬门禁；但单文件已 1964/2000 顶格、约 1/4–1/3 与 references/HANDOFF 重复，规则以"声明"为主，L1 路由断裂 | 3/5 | `AGENTS.md:1-98`；`tools/check-docs.py:18-23`；`references/workflow.md:10` vs `AGENTS.md:55` |
| State（状态层） | 有 `.apm/plans` 模板 + `make handoff` + git 状态；但唯一计划已完成却被当活跃，`make handoff` 同一次输出里"全部未提交"与 "(clean)" 自相矛盾；无 status/active 指针；证据表不强制 | 2/5 | `.apm/plans/2026-10-30-agent-rules-review.md:70-75,110-125`；`tools/plan.py:26-30,80-102` |
| Scope（范围层） | L0/L1/L2 + 红队范围 + 计划模板；但"一次只做一件事"只是建议，无改动范围字段，L1 短方案无载体，规则层改动可被判 L0 | 3/5 | `HANDOFF.md:388`；`.apm/plans/_template.md:1-42`；`references/workflow.md:9-11` |
| Verification（验证层） | 真有 120 单元 + 3 UI、验证矩阵、真机预热脚本；但没有任何机器门禁：删测试/放宽 skip/违反分层/伪造"已验证"都不会红；`make check` 只跑 docs；CI 只跑 docs；测试计数"只增不减"仅文档约定 | 2/5 | `Makefile:56-57`；`.github/workflows/docs.yml:3-24`；`references/verification.md:33`；本项目审计原型：架构铁律当前 0 违规但无脚本 |
| Observability/Evolution（可观测/进化） | issues/baseline/plans/reviews 的"策展证据"质量高、诚实；但原始产物易失（`.apm/runs` gitignore、derived 在 /tmp、xcresult 不保存）、无 evidence schema、无 metrics、无 harness 自检、无失败模式回写 | 2.5/5 | `.gitignore:14`；`Makefile:7`；`.apm/issues/*.json` 无 schema；commit `d9ef01b` 的 "Verified with…" 无可复核引用 |
| **综合** | **有骨架、有纪律、有文化；缺可执行传感器、可信状态与进化闭环** | **≈2.5/5（部分符合）** | 三份独立只读底稿（第 12 节） |

**判定结论**：

> 问"项目是否遵从 Harness Engineering"——**遵从了前半程（instructions/state 的骨架、evidence 文化、verification 矩阵），但没有构成完整研发工程体系**。准确说法是：**"文档型 Harness 1.0，尚未升级为可执行 Harness 2.0"**。所以需要改造，方向是补齐 sensors + 状态机 + 闭环，而不是推翻现有规则。

### 2.3 三个最能说明问题的实测事实

1. **`make handoff` 会误导下一棒**：唯一计划是已完成的审查任务，仍被 mtime 选为"最新"；计划写着"全部改动未提交"，实际工作区 clean、改动已提交（`f57d90a`/`d9ef01b`）。新 agent 按规则会去"保护"不存在的未提交改动。
2. **删掉 10 个测试，门禁仍然全绿**：`make check` 只跑 `tools/check-docs.py`（0.05s，只查链接/围栏/索引/token）；CI 只在 Markdown 变更时跑同一脚本；`Swift` 变更零触发。
3. **零成本门禁证明可行**：审计原型对当前 HEAD 80 个 Swift 文件跑 R1–R6 架构铁律，**0 违规、0.03s**——说明"秒级、无 Xcode、可上 ubuntu CI"的传感器今天就能落地，不是空想。

---

## 3. 总体设计：本项目的 Harness 目标形态

### 3.1 分层模型（项目级，砍掉组织层）

```text
┌──────────────────────────────────────────────────────────────┐
│ 进化层 Evolution：失败模式→规则/门禁回写、月度 harness 审计、指标 │
├──────────────────────────────────────────────────────────────┤
│ 验证层 Sensors：静态门禁(<2s) → 单元/UI(分钟) → 真机(人工)      │
│                 + evidence schema + verify-claim 三值判定       │
├──────────────────────────────────────────────────────────────┤
│ 状态层 State：active 计划(机器可读) + 证据 + 归档 + handoff      │
├──────────────────────────────────────────────────────────────┤
│ 指令层 Guides：根 AGENTS.md(目录页) + 嵌套 AGENTS.md + skills    │
├──────────────────────────────────────────────────────────────┤
│ 安全/治理：sandbox、审批、密钥、签名、单源真源、可回滚           │
└──────────────────────────────────────────────────────────────┘
```

### 3.2 八条设计原则（后续每个改动都要能对应）

1. **仓库即唯一真源**：能被 agent 看到的才算数；规则、状态、证据都入库（原始大产物除外）。
2. **渐进披露**：根 AGENTS.md 只做目录页；细节按目录/任务下沉（DSH 原生支持嵌套 AGENTS.md 与项目 skills）。
3. **一次只做一件事**：一个 active 计划、一个可验证点、一个改动范围；越界先停。
4. **只认可运行证据**：完成 = 验收判据满足 + 命令/退出码/环境已记录；未运行必须写"未验证"。
5. **质量左移 + 分层门禁**：能在 2 秒内用 ubuntu 跑的绝不拖到分钟级；必须真机的绝不假装 CI 能覆盖。
6. **每条规则配机检或固定动作**：没有执行载体的规则不新增；新增规则同时新增 gate。
7. **harness 本身是代码**：脚本/模板/技能要有测试、要审查、要 changelog、要能回滚。
8. **用对照/指标评估，不用文档数量评估**：改造效果看"首次通过率、返工轮次、未验证声明覆盖率"，不看写了多少规则。

### 3.3 目标产物总览（改造后仓库应新增/变化的东西）

| 类别 | 产物 | 作用 |
|---|---|---|
| 指令 | 精简根 `AGENTS.md`（≤1400 tokens）+ 6 个嵌套 `AGENTS.md` + `AGENTS.local.md`（gitignore） | 渐进披露，冷启动更小 |
| 技能 | `.dsh/skills/`：`session-bootstrap`、`verify-change`、`handoff`、`red-team`、`harness-audit`、`device-verify` | 把流程从"文字"变成"可调用动作" |
| 状态 | `.apm/plans/` 模板 v2（front matter + scope + DoD + evidence + attempts）；`_archive/`；`make resume/doctor/end` | 状态可信、可恢复 |
| 验证 | `.apm/test-baseline.json`、`tools/check-test-baseline.py`、`tools/check-arch.py`、`tools/check-harness.py`、`make verify-static` | 秒级门禁 |
| 证据 | `.apm/evidence/schema.json` + `tools/verify-claim.py` + `device-test.sh` 自动写 evidence | 完成声明可否证 |
| CI | `.github/workflows/verify.yml`（ubuntu 静态门禁；Swift 路径也触发） | 每次 PR 有信号 |
| 看板 | 根 `HARNESS.md`：guides/sensors 矩阵、运行手册、审计清单、changelog | harness 系统地图 |
| 进化 | `make harness-audit`、`.apm/reviews/harness-*.md`、`.apm/issues` 回写字段、`make harness-stats` | steering loop |
| 角色 | `red-team`/`verifier` 独立审查流程（DSH subagent / Agent Teams；用户级启用时） | maker-checker |

---

## 4. 改造 A：AGENTS.md 与指令层

### 4.1 根 AGENTS.md 目标结构（编号约束：§7 必须保留）

> 团队基线块（§0）由 `sync_team_baseline.py` 生成、不可手改，约 413 tokens；§7 编号被团队基线文本引用，不可改号。目标：**1964 → ≈1400（现行口径），硬上限 1500；修正估算器后等效上限 1600**。

```markdown
# AGENTS.md · 对译 Duiyi
> 冷启动入口（目录页）：只定位/约束；事实 → HANDOFF/docs/references；代码+最新验证是事实源。

## 0. 团队基线（同步块，勿手改）                     ← 保留原样（≈413）
## 1. 项目一句话与硬事实（≤100）                     ← 只留：端侧实时翻译、iOS/Swift/Xcode、无后端、三模块
## 2. 命令入口（≤55）                                 ← 指向 make help + references/verification.md（删表）
## 3. 阅读路由（≤170）                                ← 按任务段落级路由；含 L0/L1/L2 判定入口
## 4. 铁律 1–8（≤260）                               ← 8 条全留，压缩措辞，每条链 contracts 锚点
## 5. 执行与交付协议（≤200，新增）                    ← 开工/分级/小步/证据/收尾/停止
## 6. 验证与完成（≤80）                               ← DoD + 未验证规则 + 验证矩阵指针
## 7. 项目级覆盖（≤150，编号不可动）                  ← 保留 7 行，压缩理由列
维护（≤15）                                          ← 负责人 + 复核触发条件（去掉易过期手写日期）
```

**§5 执行协议草案（新增，≈200 tokens）**：

```markdown
## 5. 执行与交付协议（照做，不复述细则）
- 开工：`make resume`；在计划写"改动范围：允许修改的文件/目录"，越界先停并更新计划。
- 分级：L0/L1/L2 见 `references/workflow.md`；改 AGENTS/references/tools/Makefile/计划模板/CI 至少 L1，并做一次独立只读审查。
- 一次只做一件事：每步只改一个可验证点；每步结束把"命令 | 结果 | 环境"记入计划验证证据。
- 完成（DoD）：验收判据全满足 + 证据行已记录 + `make check` PASS + 计划已更新；未运行/未验证单列。
- 停止：同一失败修 2 次 / 同一子任务 3 轮无进展 → 按 `references/workflow.md` 阻塞报告上报。
```

**§6 验证与完成草案（≈80 tokens）**：

```markdown
## 6. 验证与完成
- 验证矩阵 / 真机入口 / 性能口径：`references/verification.md`（唯一）。
- 文档/规则/工具改动：`make check` 必须 PASS；`check-agents` 的 SKIP 不算验证。
- 完成声明必须附 `.apm/evidence/` 的 evidence id；无 id 按未验证处理。
- 未跑/未验证必须单列，不得写成已验证。
```

### 4.2 内容迁移映射（保留/删除/搬移，先搬后删）

| 现状内容 | 现 est | 处理 | 目标位置 |
|---|---:|---|---|
| §0 团队基线 | 413 | 保留（团队层才能瘦身） | 同步块 |
| §4 八条铁律 | 332 | 保留，压缩到 ≈260 | 保留 + 链 `references/contracts.md` |
| §7 项目级覆盖 | 230 | 压缩理由列到 ≈150 | 本文件 |
| §3 必读顺序 | 161 | 改为段落级路由 + 分级入口 | 本文件 |
| §2 命令表 | 192 | 删除表格，1–2 行指针 | `make help` + `references/verification.md` |
| §5 关键约束/已知坑 | 184 | 删除，一行指针 | `HANDOFF.md` §2 + `references/verification.md` 真机坑 |
| §6 验证与交付 | 161 | 压缩到 ≈80（DoD + 未验证 + 矩阵指针） | 本文件 |
| §1 大部分事实 | 224 | 压缩到 ≈100；细节链 HANDOFF/docs | `HANDOFF.md:14-50`、`docs/02` §0 |
| 测试计数 | 27 | 只留"只增不减"，数字只在 verification | `references/verification.md:33` |

> 校验方法：逐条 grep 目标位置能命中；`git diff` 只应看到搬移/压缩；改完 `make check` PASS。禁止把规则挪到 HANDOFF/docs 来绕过 token 预算。

### 4.3 修正 token 估算器 + 重标预算（否则 AGENTS 一改就红）

- 现状：`tools/check-docs.py:90-91` 把中文标点按 1/4 token 计；公平口径（标点≈1 token）下 AGENTS≈2141、contracts≈865、verification≈861、workflow≈861，**当前"绿色"是口径红利**。
- 改造：
  1. 估算器把 U+3000–303F、U+FF00–FFEF 等中文标点按 1 token；英文/数字按 len/4；固定口径写进注释与 `docs/README.md`。
  2. 预算表从硬编码常量改为**单一配置**（如 `tools/rules-budget.json` 或脚本常量 + `--report` 输出余量），新增 references 必须同时登记预算与 docs 索引。
  3. 重标预算：AGENTS **1500 现行 / 1600 修正**；每个 `references/*.md` **800 现行 / 950 修正**；目标余量 ≥100 tokens，避免再次"加一条就红"。
  4. 规则层新增前先跑 `--report`；超预算先删重复，不允许删有效规则腾位置。

### 4.4 嵌套 AGENTS.md：DSH 原生的渐进披露（关键改造）

**机制事实（来自本机 DSH 安装包 `dsh-agent-instructions` README 与独立审计）**：DSH 首次请求加载用户全局（`$DSH_HOME/AGENTS.md`、`~/.agents/AGENTS.md`）→ 项目根（`.git` 标记）到会话 cwd 的指令链，基础候选 `AGENTS.md`/`CLAUDE.md`，叠加 `AGENTS.local.md`/`CLAUDE.local.md`；默认预算 65536 bytes，预算紧张时先省略宽泛文件、最后截断最具体文件。更深层目录的 `AGENTS.md` 在文件操作到达后才被发现并注入。

**本项目的嵌套布局（新增 6 个，每个 30–100 行，只写"该目录/任务特有的约束"，不复制根规则）**：

| 文件 | 触发场景 | 内容（只写增量） |
|---|---|---|
| `.apm/AGENTS.md` | 读写计划/证据/审查时 | 计划 status/scope/DoD/证据格式；归档规则；红队输入输出协议；不写绝对路径/UDID |
| `Duiyi/Services/AGENTS.md` | 改 Speech/Translation/Audio/SpeechSynthesis/Persistence/Export | 单引擎与 P0-1 gate（未实现不得声称）；TranslationSession 只在 Host View；SwiftData 内存为准/异步落盘；测试替身规则；改持久化先备份样例 |
| `Duiyi/Features/AGENTS.md` | 改 ViewModel/View | 依赖方向、@MainActor/并发约定；View 不直读 SwiftData 当实时状态；新增 UI 入口必须加 accessibilityIdentifier |
| `DuiyiTests/AGENTS.md` | 写/改单元测试 | Swift Testing 约定、命名、假引擎/假 store、只增不减、不得改既有断言、skip 白名单与 baseline 更新流程 |
| `DuiyiUITests/AGENTS.md` | 写/改 UI 测试 | 预条件 `-duiyi.onboardingComplete YES`、`nav-home`、真机预热、语音用例 skip 是预期、exit 74 排查顺序 |
| `docs/AGENTS.md` | 改文档 | 01–04 当前规范、14–21 历史不改数字、新增 docs 必须登记索引、真源优先级只写一次 |

**注意**：DSH 在 cwd=仓库根时，首轮只加载根 AGENTS.md（更深的在文件操作后注入）；这正是"按需加载"的来源。落地后要做一次 smoke test（见 9 节）。嵌套文件不纳入 token 硬预算，但纳入 `check-harness` 的"存在性/链接/长度"检查。

### 4.5 项目级 Skills：把流程从"文字"变成"可调用动作"

**机制事实**：DSH 项目级 skill 根为 `<project>/.dsh/skills`（rank 100）与 `<project>/.agents/skills`（rank 200）；格式为目录 bundle `<name>/SKILL.md` 或平铺 `<name>.md`，YAML frontmatter 必填 `name`（kebab-case）/`description`，可选 `whenToUse`；被监控、无需重启；只扫一层、不递归。当前仓库**没有 `.dsh/`**，属于零成本新增。

建议技能（每个 ≤800 tokens，只写动作与硬约束，不复制 references）：

| Skill | 触发 | 行为要点 |
|---|---|---|
| `session-bootstrap` | 新会话/接手 | 跑 `make doctor`（或降级检查）→ `make resume` → 输出"一个下一步 + 建议阅读清单"；不直接改代码 |
| `verify-change` | 任何"完成"前 | 按变更类型映射命令（Domain→unit；UI→sim；语音/翻译/TTS/持久化→device；文档→check）→ 跑 `make verify-static`/`verify-unit` → 写 evidence → 输出 PASS/FAIL/UNVERIFIED |
| `handoff` | 长任务中断/提交前 | 更新计划 status/进度/证据/未验证/下一步 → `make check-plan` → `make handoff`；完成后归档 |
| `red-team` | L2/高风险改动 | 只读独立审查：输入=任务+方案+仓库路径，不传起草历史；输出 P0/P1/P2 表 + 被挑战假设 + 最小验证清单 |
| `harness-audit` | 每月/大改后 | 跑 `make harness-audit`，按五子系统打分，输出改进项 |
| `device-verify` | 真机验收 | 走 `.apm/tools/device-test.sh`，处理 exit 2/exit 74/锁屏/密码；写 evidence；不能操作设备时标"未验证" |

> 首次落地后必须验证：在新会话里 skill 目录出现、可加载（当前无法离线验证，见 10 节）。若 DSH 版本差异导致不生效，退化为"references 按需读 + make 命令"，不阻塞主体方案。

### 4.6 `AGENTS.local.md` 与机器差异

- 新增 `AGENTS.local.md`（`.gitignore` 忽略，**当前 .gitignore 尚无此模式，需补**）承载：本机签名 Team、设备 CoreDevice ID、Xcode/模拟器路径、mobilebuildmcp 环境差异等**机器本地事实**。
- 根 AGENTS.md 只写"机器相关见 `AGENTS.local.md`（如存在）"，保持入库文件干净、跨机器可用。
- 与现有"签名属本地环境、未经确认不提交他人 Team"规则一致。

### 4.7 DSH 机制的分层使用（重要：仓库内只固化两类）

独立研究结论：**DSH 仓库内可原生固化的只有两类**——① AGENTS.md 谱系（含嵌套与 `.local.md` overlay）；② 项目 skills（`.dsh/skills` / `.agents/skills`）。其余能力均为 **profile/会话级**，不能靠仓库文件自动生效。因此方案分三栏：

| 类别 | 内容 | 归属/落地方式 |
|---|---|---|
| 仓库内可固化 | 根+嵌套 `AGENTS.md`、`AGENTS.local.md`（本机）、`.dsh/skills/*/SKILL.md`、docs/references/.apm、Makefile 门禁脚本 | 入库，走本计划第 4–5 节 |
| 一次性人工配置 | profile 插件（Agent Teams、worktree、ralph、auto-review、subagent）、MCP 服务器、模型/provider、permission presets、hooks | **用户级**，由用户在主目录 profile 配置；仓库只写"启用后如何使用" |
| 会话/运行时操作 | `goal`（长任务）、`schedule`（月度审计提醒）、`subagent`/Agent Teams（maker-checker）、`workflow`（批量审计）、`worktree`（并行实验）、受控 shell/python 脚本执行；sandbox/approval 切换 | 会话操作手册，写进 `.dsh/skills` 或 `HARNESS.md`，不承诺自动生效 |

**明确不做**：不新增项目级 hook 插件（本机 DSH 0.2.1-rc.5 未打包 hooks，判不可用）；跨工具门禁统一走 **git hook + make**（`.githooks/pre-push` + `core.hooksPath`），对 DSH/其他 agent 都生效。

### 4.8 指令层机检：`tools/check-harness.py`（新增）

检查项（纯 Python 标准库，<1s，可 ubuntu CI）：
1. token 预算（根 AGENTS + 每个 references + 每个嵌套 AGENTS 的长度上限；`--report` 打印余量）。
2. 根 AGENTS 的 `§` 引用能在目标文件命中对应标题（防"引用漂移"）。
3. 嵌套 AGENTS/skills 存在性 + skill frontmatter（name kebab-case、description 非空）+ 不得有绝对路径/UDID/密钥模式。
4. `docs/README.md` 登记所有 docs；references 均登记。
5. 脚本语法：`bash -n`、`python3 -m py_compile`。
6. `§7` 非空、团队基线覆盖语义闭合（补回"对团队规则的覆盖只写第 7 节"半句）。

---

## 5. 改造 B：项目层（验证/状态/生命周期/可观测/进化）

### 5.1 验证层：从"文档约定"到"可执行传感器"

**B1. 测试基线门禁（先做，防"删测试变绿"）**

- 新增 `.apm/test-baseline.json`：`unit.floor=120`、`ui.floor=3`、`expectedSkipped.simulator=1`、`expectedSkipped.device=0`、源码/文档计数锚点。
- 新增 `tools/check-test-baseline.py`：统计 `@Test`/`func test`、比对 floor、解析 `references/verification.md` 与 `docs/02` 的计数字段、检测新增 `XCTSkip` 未入白名单。
- 验收（故意破坏→红）：删 1 个 `@Test` → exit 1；文档 120→119 → exit 1；恢复 → PASS（<0.1s）。
- 依赖前提：当前 `@Test` 计数=执行数（无参数化；审计已确认 0 处 `arguments:`）；若未来引入参数化，改为以 xcresult 执行结果数为权威。

**B2. 架构铁律门禁（R1–R6，静态、可立即上线）**

- 新增 `tools/check-arch.py`：Domain 不 import SwiftUI/语音/翻译/SwiftData；Features 不 import 语音/音频/翻译/SwiftData（Translation 仅 Host View）；Services 不引用 ViewModel；`TranslationSession` 仅在 `TranslationHostView`；`BilingualSpeechEngine()` 实例化白名单；Features 不直读 SwiftData。
- 审计原型已对当前 HEAD 80 文件跑通：**0 违规、0.03s**；规则白名单写在脚本顶部，新增白名单需 L1 审查。
- 验收：在 `Duiyi/Domain/` 加 `import SwiftUI` → exit 1；改回 PASS。

**B3. `make verify-static`（<2s、无 Xcode、可 ubuntu CI）**

```make
verify: verify-static
verify-static: check-docs
	python3 tools/check-arch.py
	python3 tools/check-test-baseline.py
	python3 tools/check-harness.py
	python3 tools/check-evidence.py
	bash -n .apm/tools/*.sh tools/*.sh
	python3 -m py_compile tools/*.py
```

**B4. 证据链与 `verify-claim`（三值判定，核心）**

- 新增 `.apm/evidence/schema.json`（draft-07，无依赖）+ `.apm/evidence/*.json`（1–3KB/条，入库，不含大产物）。
- 证据必需字段：`id`、`claim`、`createdAt`、`git.commit`+`dirty`、`command`、`environment`（Xcode/模拟器/设备）、`result`（status/passed/failed/skipped/duration/xcresult 路径或摘要 sha256）、`verdict`、`verifier`。
- 新增 `tools/verify-claim.py`：**PASS / FAIL / UNVERIFIED** 三值；规则：
  - 无 evidence 文件 → FAIL（"未验证的声明"）。
  - commit 必须是 HEAD 或 HEAD 祖先且 dirty=false；否则 FAIL。
  - 测试声明：passed ≥ floor、failed=0、skipped=expected；xcresult（或摘要指纹）缺失 → **UNVERIFIED（exit 2）**，绝不绿。
  - 性能声明：同 context + n≥10 + CV 阈值 + 最小效应/显著性；不达标 → INVALID→UNVERIFIED。
  - docs/arch 声明：直接复跑对应静态门禁。
- `device-test.sh` 改造：成功后写 evidence（commit/设备/计数/xcresult/耗时），`skipped != expected` 时 exit 1；`measure-launch.sh` 完成后写 evidence（metrics 摘要 + n + CV）。
- 计划模板"验证证据"固定三列：`命令 | 结果（exit/通过数） | 环境`，并加"证据 ID"列。

**B5. 行为传感器（与 P0-1/P0-2/P0-3 绑定，产品工作，另计工期）**

- P0-1：假引擎记录 start/stop 顺序，覆盖 20 次模块切换 + 10 次前后台；`SpeechSessionGate` owner/generation 单测。
- P0-2：500 条/模拟 1h 文字稿，结束→杀进程→重开→导出含首末条。
- P0-3：容器打开失败注入 → UI/日志显性提示；v1→v2 迁移演练测试。
- 翻译/听写质量：固定音频夹具或预录字幕断言（目标语言非空 + 关键词/数字/专名 case）；夹具就绪前，质量声明一律 UNVERIFIED。
- 这是 Harness Engineering 的 **behaviour harness**（Thoughtworks 三类中最难的一类），不能假装静态门禁能覆盖。

### 5.2 状态层：active 计划 + 机器可读状态

**B6. 计划模板 v2（front matter + 强制字段）**

```yaml
---
id: 2026-11-05-harness-engineering
status: active            # active | done | blocked | archived
level: L2                 # L0 | L1 | L2
owner: lead
updated: 2026-11-05
scope:                    # 改动范围（允许的文件/目录）
  allow: [AGENTS.md, references/, tools/, .apm/plans/, .github/]
  deny:  [Duiyi/, DuiyiTests/]   # 本计划不改业务代码
acceptance:               # 可执行判据
  - make check PASS
  - 删 1 个 @Test 时门禁变红
verify:                   # 完成前必须跑的命令
  - make verify-static
---
```

正文保留模板现有节：目标与验收、进度、关键决策、已排除、验证证据（加证据 ID/环境）、未提交改动、下一步、待确认；新增：**非目标**、**改动范围**、**DoD**、**未验证项**、**尝试记录**（尝试#/动作/结果/时间，用于 2 次/3 轮停止规则的外部载体）。

**B7. `tools/plan.py` 扩展 + 生命周期命令**

- `plan.py check`：status 合法；目标/验收/下一步/范围非空；证据表 ≥1 行且列为 命令/结果/环境；"未提交改动"与 `git status` 交叉比对（不一致报错/警告）；完成后归档。
- `latest` 只取 active（legacy 无 status → WARN 兜底，不直接 FAIL）；完成计划移入 `.apm/plans/_archive/`。
- `make resume`：active 计划 brief（含目标/验收/关键决策）+ `git status`/`git log -5` + "下一步 1 条" + 建议阅读清单。
- `make doctor`：检查 `xcodebuild -version`、`xcrun simctl list runtimes` 含 `SIM_OS`、`mobilebuildmcp`、python3、模板仓存在性、git 状态；缺失 → WARN + 非 0（语义对齐 device-test.sh exit 2）；**本机无 Xcode 时明确输出"动态验证不可执行，结论=未验证"，而不是把环境问题误诊为代码问题**。
- `make end`：`make check` + `plan.py check` + git 状态/计划未提交差异 + 未验证项清单 + "提交前询问"提示。
- 清理现有唯一计划（已完成却 active）：标 `status: done`、补提交号 `f57d90a`/`d9ef01b`、修正"未提交改动/下一步"，或移入 `_archive/`。

### 5.3 单一真源清理（双真源已实际发生，不是潜在风险）

审计确认的漂移：
- HANDOFF §6 六决策 vs docs/04 §7 六决策有 2 项不同（HANDOFF 独有"启动目标"，docs/04 独有"长会策略"）；AGENTS/contracts 只引用 HANDOFF 那套 → **"长会策略"没进阻断列表**。
- "下一件事"顺序两套（HANDOFF §5 vs docs/04 §6）；P0/P1 验收判据两套；真源优先级四种措辞。
- 测试计数出现在 8+ 处；命令表 5 处重复；真机坑 3 处重复。

改造规则：
1. **决策表唯一**：合并为一张表（含"启动口径"与"长会策略"），只放 `HANDOFF.md` §6；AGENTS/contracts 引用表 ID。
2. **下一步唯一**：`docs/04` P0/P1 条目加"状态/负责人/证据链接"列，成为唯一排期源；HANDOFF §5 改"当前摘要 + 链接"。
3. **验收判据唯一**：只放 docs/04；计划里的验收复制 ID 并链接。
4. **真源优先级只写一次**（docs/README），其余引用。
5. **测试计数唯一**：`references/verification.md`；其他位置改"120（见 verification）"式引用；历史文档保留当时口径。
6. **补回团队基线覆盖语义**：AGENTS §0 附近补"对团队规则的覆盖只写第 7 节"。

### 5.4 可观测性与证据索引

- 新增 `.apm/evidence/README.md`：证据目录规范、命名（时间-claim-commit 短 hash）、生产命令、校验命令。
- `make evidence ls|show|check`：列出证据、按 claim 查询、schema 校验；计划/交接引用 evidence id。
- 会话/命令留痕：DSH "Model-visible means logged"——模型可见内容都能从会话日志重建；日志在 `~/.dsh/sessions/<workspace>`（本地、不入库）。evidence 里记录 agent 会话 id（可得时）+ 命令原文，保证"谁在什么 commit/环境下得到什么结果"可追溯。
- 不把 `.apm/runs/` 原始大产物入库（保持 gitignore）；入库的是**摘要 evidence + 结论 + 引用**。

### 5.5 进化层：maker-checker、审计、失败回写、指标

1. **maker-checker（L2 默认）**：实现者（改代码）与 verifier（只读、fresh context、禁止看起草历史）分离；采用**两级**：① DSH 子 agent/Agent Teams 独立复核（只看任务、方案、diff、证据，不看实现者叙述）；② 人工体验复核（UI/音频/翻译质量，LLM 不可替代）。verifier 输出 P0/P1/P2 表 + 被挑战假设 + 最小验证清单，写入 `.apm/reviews/`；作者逐条回应。
2. **失败模式回写**（steering loop）：每个逃逸缺陷/返工，在 `.apm/issues/*.json` 增字段 `missingGuide`/`missingSensor`/`action`；每月把重复≥2 次的问题转成新 guide/sensor，并在 `HARNESS.md` changelog 记录。**没有回写，harness 不会进化。**
3. **月度 harness 审计**：`make harness-audit` 输出五子系统 scorecard（PASS/WARN/FAIL + 证据），存 `.apm/reviews/harness-YYYY-MM.md`；DSH schedule 可做提醒（用户级）。
4. **指标（用对照/可测指标评估，不数文档）**：`make harness-stats` 统计 ① 首次交付即通过指定门禁的比例；② 同一失败修复-验证轮次（2 次停止规则）；③ 交付中显式"未验证"声明覆盖率（目标 100%）；辅以任务数、claim→verified 时长、测试数趋势、门禁失败次数、红队 P0/P1 数。JSON+Markdown 摘要，月度复盘。
5. **harness 自身回归**：`tools/` 脚本加 fixtures 测试（删测试→红、坏计划→红、架构违规→红、伪造 evidence→UNVERIFIED），CI 执行；harness 改动走 L1/L2 + 独立审查 + changelog（`HARNESS.md`）。

### 5.6 CI 与本地门禁分工

| 检查 | 位置 | 触发 | 耗时 | 失败条件 |
|---|---|---|---|---|
| 文档/token/架构/计数/harness/evidence lint | ubuntu CI + 本地 `make verify-static` | md/swift/tools/plans/Makefile | <2s | 任一红 |
| 单元测试（模拟器） | 本地（有 Xcode）或自托管 Mac；可选 nightly | 代码变更/夜间 | 分钟级 | 测试失败/计数<floor/skip≠expected |
| UI 导航（模拟器） | 同上 | UI 变更 | ~11s/用例 + 构建 | 失败/超时 |
| 真机套件（语音/翻译/TTS/持久化） | **只本地**（人+真机+解锁/密码） | 相关变更/发版前 | 分钟级+人工 | exit 1/2；skip≠0 |
| 启动性能（Release 真机 n≥10） | **只本地** | 性能变更/发版前 | 分钟级 | n<10/CV 超阈值/显著回归 |
| 签名/安装/发版 | 只本地 | 发版 | 人工 | — |

- CI 新建 `verify.yml`（ubuntu）而不是改 `docs.yml`，减少对现有绿线扰动；`paths` 覆盖 `**/*.swift`、`tools/**`、`Makefile`、`.apm/plans/**`、`.dsh/**`、workflow 自身。
- 本地 `.githooks/pre-push` 跑 `make verify-static`（`core.hooksPath=.githooks`），跨 agent 工具通用。
- **诚实边界**：当前开发机（本会话环境）`xcode-select` 指向 CommandLineTools、无 Xcode/simctl/devicectl → **动态门禁在本机不可执行**；CI 或装有 Xcode 的机器是唯一稳定替代。这是环境决策，不是仓库能单方面解决的。

### 5.7 项目结构变更清单（文件级）

**新增**

| 路径 | 说明 |
|---|---|
| `HARNESS.md` | harness 系统地图：五子系统 × guides/sensors 矩阵、运行手册、审计清单、changelog |
| `AGENTS.local.md` | 机器本地覆盖（入库时不提交；加入 .gitignore） |
| `.apm/AGENTS.md` | 计划/证据/审查协议（嵌套 AGENTS） |
| `Duiyi/Services/AGENTS.md`、`Duiyi/Features/AGENTS.md`、`DuiyiTests/AGENTS.md`、`DuiyiUITests/AGENTS.md`、`docs/AGENTS.md` | 目录级增量规则 |
| `.dsh/skills/{session-bootstrap,verify-change,handoff,red-team,harness-audit,device-verify}/SKILL.md` | 项目级技能 |
| `.apm/test-baseline.json` | 测试基线 + skip 白名单 |
| `.apm/evidence/{README.md,schema.json,TEMPLATE.json}` | 证据规范 |
| `tools/check-test-baseline.py`、`tools/check-arch.py`、`tools/check-harness.py`、`tools/check-evidence.py`、`tools/verify-claim.py`、`tools/harness-audit.py`、`tools/harness-stats.py` | 门禁与审计脚本 |
| `.githooks/pre-push` | 本地推送前静态门禁 |
| `.github/workflows/verify.yml` | ubuntu 静态 CI |

**修改**

| 路径 | 说明 |
|---|---|
| `AGENTS.md` | 按 4.1 重写（1964→≈1400），加 §5 执行协议、§6 DoD、嵌套/skill 指针 |
| `tools/check-docs.py` | 修 token 估算器；预算表配置化；`--report` |
| `tools/plan.py` | `check`/`latest --active`/brief 增目标与关键决策/未提交 vs git 比对 |
| `.apm/plans/_template.md` | front matter + scope/非目标/DoD/未验证/尝试记录/证据 ID 列 |
| `Makefile` | 新增 `verify-static/verify/verify-unit/verify-device/verify-claim/evidence/doctor/resume/end/check-plan/check-harness/harness-audit/harness-stats` |
| `.gitignore` | `AGENTS.local.md`、原始证据/日志（保持 `.apm/runs/`） |
| `.github/workflows/docs.yml` | 改为 `make verify-static`（或保留并新增 verify.yml；二选一需确认） |
| `references/verification.md` | 计数改为指向 baseline；补"无 evidence 即未验证" |
| `references/workflow.md` | maker-checker 流程、L1 路由、尝试记录、红队降级路径 |
| `HANDOFF.md` | §6 决策表合并（含长会策略）；§5 改摘要+链接；修正基线 hash；§7 文档地图 |
| `docs/04-roadmap.md` | P0/P1 条目加状态/负责人/证据列；验收判据唯一源 |
| `docs/README.md` | 登记 HARNESS.md、新 tools、新 references 预算口径 |
| `README.md` | 更新项目结构/工具说明（只改事实，不扩写） |

**不动**：`Duiyi/**` 业务代码（本计划）、测试断言、`Duiyi.xcodeproj`、启动优化决定、签名信息。

---

## 6. 分阶段实施与验收

> 依赖：预算/去重先做（否则新增规则文本必被预算门禁拦）；状态/证据次之；CI/角色/指标最后。每阶段单提交，可回滚。

### Phase 0 · 止损与冻结（0.5–1 人日）

- 修 token 估算器 + 预算配置化；按 4.2 压缩/搬移根 AGENTS 到 ≈1400，新增 §5/§6；改 docs 引用。
- 加 `.apm/test-baseline.json` + `tools/check-test-baseline.py` + `tools/check-arch.py` + `make verify-static`；`make check` 纳入。
- 状态止损：现有计划标 `done`/归档；模板加 status/scope/DoD；`make resume` + `make doctor` + `make end`（薄）。
- **验收（每条都做"故意破坏→红"）**：`make check` PASS；删 1 个 `@Test` → 红；Domain 加 `import SwiftUI` → 红；计划缺证据 → 红；`make resume` 输出正确答案；新会话 ≤3 次读取能定位"下一步"。

### Phase 1 · 证据闭环（1–2 人日）

- `.apm/evidence/` schema/TEMPLATE/README；`tools/verify-claim.py`（三值）；`device-test.sh` 自动写 evidence + skip 断言；`measure-launch.sh` 写 evidence 摘要。
- `.dsh/skills/verify-change` + `session-bootstrap` + `handoff`；`AGENTS.local.md` + `.gitignore`。
- CI `verify.yml`（ubuntu，含 Swift 路径）；`.githooks/pre-push`；`HARNESS.md` 初版。
- **验收**：伪造"123 全过"无 xcresult → UNVERIFIED(exit 2)；真实记录 → PASS；`make verify-static` <2s；CI 在改一个 `.swift` 时被触发且 <60s。

### Phase 2 · 行为传感器（3–5 人日，与 P0 实现绑定，另计）

- P0-1 假引擎并发测试；P0-2 长会话/重开/导出测试；P0-3 容器失败/迁移测试；翻译夹具 eval。
- **验收**：docs/04 每条 P0 验收判据都有对应测试/命令；agent 能跑 `make verify-unit` 自证；未就绪的质量声明标 UNVERIFIED。

### Phase 3 · 闭环与进化（持续，首轮约 1 人日搭骨架）

- maker-checker（DSH subagent/Agent Teams，用户级启用）：L2 默认独立 verifier；`red-team` skill；审查报告入 `.apm/reviews/`。
- `make harness-audit`（五子系统 scorecard）+ `.apm/issues` 回写字段 + `make harness-stats` + 月度复盘；DSH schedule 提醒。
- **验收（三指标，对照式评估）**：一次 L2 改动的审查报告+回应在仓库内可查；① 首次门禁通过率、② 同一失败修复轮次、③ 未验证声明覆盖率 — 改造后 vs 改造前有可比较数据；至少 1 条失败模式转化为新 gate。

### 总投入估算

| 阶段 | 人日（agent 辅助下） | 说明 |
|---|---|---|
| Phase 0 | 0.5–1 | 静态脚本纯 Python，审计已给原型 |
| Phase 1 | 1–2 | evidence + CI + skills |
| Phase 2 | 3–5 | 产品测试（P0 前置），另计 |
| Phase 3 | 1 + 持续 | 流程/指标/审查 |
| **Harness 主体** | **≈3–4（P0+P1）**，含行为测试 **≈6–9** | 不含 P0 产品修复本身 |

---

## 6.1 Phase 0 实施记录（2026-11-05）

> 用户已确认第 8 节全部决策并授权 Phase 0。本记录是实际执行结果；未验证项见 §10。

### 交付（已写入工作区，未提交）

| 层 | 交付 |
|---|---|
| 指令 | `AGENTS.md` 重写为目录页（≈1535/1600 tokens，余 65）；6 个嵌套 `AGENTS.md`（`.apm/`、`Duiyi/Services`、`Duiyi/Features`、`DuiyiTests/`、`DuiyiUITests/`、`docs/`）；`AGENTS.local.md`/`CLAUDE.local.md` 加入 `.gitignore` |
| 门禁 | `tools/token_estimate.py`（v2 估算器）、`tools/rules-budget.json`（预算配置）、`tools/check-docs.py`（读配置+余量）、`tools/check-arch.py`（R1–R6）、`tools/check-test-baseline.py`（120/3/123+skip）、`tools/check-harness.py`（预算/嵌套/敏感/§引用）、`.apm/test-baseline.json` |
| 状态 | `tools/plan.py`（front matter/status/active/check/brief/resume/end）、`tools/doctor.py`、模板 v2、旧计划 `status: done`、本计划 front matter |
| 生命周期 | Makefile：`check`=docs+arch+tests+harness+plan；`verify-static`（+`bash -n`/`py_compile`）；`doctor`/`resume`/`end`/`check-plan`/`check-arch`/`check-tests`/`check-harness` |
| 单源 | `HANDOFF.md` §6 唯一决策表 D1–D7 + §5 摘要；`docs/04` §7 指针、§6 排期唯一；`docs/README` 真源/预算；`docs/21` 流程；references 三文件同步 |
| 工程 | `Duiyi.xcodeproj/project.pbxproj`：3 个 target 的同步文件夹加 `AGENTS.md` membershipExceptions；否则 app bundle 出现重复 `AGENTS.md`，构建失败 |

### 验收结果（命令 + 结果）

| 命令 | 结果 |
|---|---|
| `make check` | **PASS**：28 篇文档/187 链接；AGENTS 1535/1600、references 899/915/927（≤950）；arch 0 违规；tests 120/3/123+skip 1；harness 13 项；plan check 0 error/1 warn |
| `make verify-static` | **PASS**（同上 + `bash -n` / `py_compile`，exit 0） |
| fixtures（gitignore 内） | **10/10 PASS**：删 @Test / 架构违规 / 伪造 UDID / `sk-` 密钥 / §漂移 / 超预算 / 删嵌套 AGENTS → 均按预期红 |
| `make doctor` | OK 7 / WARN 0 / FAIL 0：Xcode 27.1、iOS 26.4.1 runtime、mobilebuildmcp、python 3.14.7、git、TEAM_RULES |
| `make resume` / `make handoff` | 输出 active 计划 + 三问速答 + 下一步；handoff 只取 active 计划 |
| `make test`（四次：含 TMPDIR/`-skipMacroValidation` 尝试） | **FAIL（环境未验证，不是代码结论）**：SwiftData 宏 `swift-plugin-server produced malformed response`；资源重复问题已由 pbxproj 例外修复，但宏插件在本会话沙箱内仍失败（§10） |

### 偏差与处理

1. 嵌套 AGENTS 位于 app target 目录内会被 Xcode 当资源复制 → 用 `PBXFileSystemSynchronizedBuildFileExceptionSet.membershipExceptions` 排除；项目文件改动已显式加入本计划 scope。
2. `.dsh/skills`、`HARNESS.md`、`.apm/evidence`、CI（ubuntu + macOS）、pre-push、maker-checker 属 Phase 1/3，本阶段未做。
3. 旧计划保留在 `plans/`（`status: done`，未移 `_archive/`）；其历史证据表列口径（命令|目的）只产生 WARN，不改正文。
4. `AGENTS.md` 余量 65 tokens（原目标曾写"余量 ≥100"）：已从 1 token 顶格压到可用余量；后续新增规则须同时删重复或先审查调预算。

---

## 6.2 Phase 1 实施记录（2026-11-05）

> 用户确认继续 Phase 1（决策 1/2/3/4/5/6/7/8 已落）。Phase 0 已提交 `d83bb05`；本节改动尚未提交。

### 交付（工作区，未提交）

| 层 | 交付 |
|---|---|
| Skills | `.dsh/skills/` 6 项：`session-bootstrap`、`verify-change`、`handoff`、`red-team`、`harness-audit`、`device-verify`（各 34–45 行，frontmatter 通过 check-harness；**已在本会话 skill catalog 实时出现，实测可加载**）；`AGENTS.local.md.example` 机器本地覆盖模板 |
| 证据 | `.apm/evidence/{README.md,schema.json,TEMPLATE.json}`；`tools/evidence.py`（ls/show/validate/write，自动填 id/commit/dirty/verifier，路径归一化）；`tools/verify-claim.py`（三值 PASS/FAIL/UNVERIFIED）；`tools/tests/` 41 个 unittest；`.apm/tools/device-test.sh` 自动写证据 + `skipped==0` 断言；`.apm/tools/measure-launch.sh` 写 perf-measurement 证据（n<10/CV>10% → UNVERIFIED） |
| CI/Hooks | `.github/workflows/verify.yml`：`static`（ubuntu，`make verify-static`）+ `unit-tests`（`[self-hosted, macOS]`，`if: vars.MACOS_CI_ENABLED == 'true'` 默认跳过，`needs: static`，artifact 上传）；`.githooks/pre-push`（`make verify-static`，`SKIP_HARNESS_HOOK=1` 可跳）+ `make hooks-install` |
| 文档 | `HARNESS.md`（159 行：`.apm` 解释、Guides/Sensors 矩阵、运行手册、证据政策、skills、CI/hooks、DSH 用户级配置建议、月度审计清单+三指标、Changelog）；`docs/README.md` 同步；`AGENTS.md`/`.apm/AGENTS.md` 指向 evidence 与 skills（AGENTS 1550/1600） |
| 门禁扩展 | Makefile：`check-evidence`、`test-tools`、`verify-claim`、`evidence`、`hooks-install`、`harness-audit`；`verify-static` = 原 check + 证据校验 + 脚本单测 + `bash -n`（含 pre-push）+ `py_compile` |

### 验收结果

| 命令 | 结果 |
|---|---|
| `make test-tools` | **41 tests OK**（verify-claim/evidence：PASS/FAIL/UNVERIFIED、commit/dirty、计数不符、无证据、device skip、perf n=1） |
| `make check-evidence` | PASS（当前 0 条真实 evidence；模板/schema 不参与校验） |
| `make check-docs` | PASS（29 篇文档/200 链接；AGENTS 1550/1600，refs 899/915/919 ≤950） |
| `make check-harness` | PASS 19 项（含 6 个 skill frontmatter；skills 已在 DSH catalog 出现） |
| `make check-arch` / `make check-tests` | PASS（0 违规 / 120+3+123 与 skip 白名单一致） |
| `make verify-static` | PASS（Phase 1 文件就绪后；见最终运行） |
| `make test`（full-access） | **PASS：120/120，0 failed，0 skipped**（xcresult 见 `build/duiyi-test/Logs/Test/…`；工作树 dirty，故暂不生成 PASS evidence） |
| `make test-ui`（full-access） | **PASS：3 executed / 2 passed / 1 skipped（预期无 SpeechTranscriber）/ 0 failed**（xcresult 见 `build/duiyi-test-ui/Logs/Test/…`；同样待 clean tree 证据） |
| 负向演示（evidence） | 伪造"123 全过"无 xcresult → **UNVERIFIED exit 2**；119<floor → **FAIL exit 1**；无 evidence → **FAIL exit 1**；device-test fixture skipped=2 → exit 1 |

### 关键事实：动态测试为何之前失败、现在通过

- 之前 `make test` 失败是 **DSH 会话沙箱拒绝写 `$HOME` / `~/Library/Caches`**（terminal backend 同样被沙箱）：SwiftData 宏的 `swift-plugin-server` 需要写缓存 → `malformed response`。
- 用完整权限（danger-full-access）运行后，单元 120/120、UI 3（1 skip）全过；说明是环境限制，不是代码/工程问题。
- 证据策略要求 **clean tree → 跑验证 → 生成 evidence → 提交**；当前 Phase 1 改动未提交（dirty），因此真实结果先记录在这里，待提交后在 clean tree 重跑并生成 PASS evidence。

### 偏差与处理

1. `.apm/evidence` 的真实 evidence 尚未生成（dirty tree 规则）；`make verify-claim --all` 当前为空（FAIL 是设计：无证据）。
2. `unit-tests` CI 默认跳过（需 repo variable `MACOS_CI_ENABLED=true` + 自托管 runner）；GitHub 托管 macOS 是否带 iOS 26.4 runtime 未验证，故默认自托管。
3. `HARNESS.md` 中 DSH 用户级配置为**建议片段**，仓库不强制、不承诺自动生效；`AGENTS.local.md` 不入库。
4. 测试产物 `build/` 353MB（gitignore）；保留以便下一次 clean-tree 证据校验，之后可删。

---

## 7. 风险与回滚

| 风险 | 触发 | 缓解 / 回滚 |
|---|---|---|
| 流程税过高，迭代变慢 | 门禁全量跑 | 分层：静态 <2s 每次；单元/真机只在对应变更/发版前；`make verify-static` 是默认门禁 |
| "假绿"（有 evidence 但不对） | 伪造/过期 evidence | commit 祖先校验 + xcresult 指纹 + 独立 verifier + CI 复跑静态；诚实声明"提高撒谎成本≠绝对防伪" |
| 预算再次锁死 | 新增规则 | 修估算器 + 配置化 + `--report`；目标余量 ≥100；先删重复再新增 |
| 双真源复发 | 同一事实多处写 | 每类事实指定唯一 owner；`check-harness` 校验引用；计划只引用 ID |
| 门禁误报阻塞 | 正则/白名单太宽 | 先做低误报项（计数/架构/证据存在性）；规则可配置；CI 先非阻断一周再变必需 |
| 环境不可验证被误诊 | 无 Xcode/无设备 | `make doctor` 明确输出"环境不满足→UNVERIFIED"，不得把环境失败记成代码失败 |
| 独立审查被跳过 | 单 agent/无子 agent | `red-team` skill 降级路径：无子 agent 用检查清单自检，标注"未独立审查"；L2 必须留审查记录 |
| 规则层改动破坏自身 | L0 误判 | 改 AGENTS/references/tools/Makefile/plan 模板/CI 至少 L1 + 独立只读审查 + `make check` |
| DSH 项目 skill/嵌套 AGENTS 不生效 | 版本/配置差异 | 落地后先 smoke test；不生效则退化为"references 按需读 + make 命令"（不阻塞主体方案） |
| 团队基线块无法瘦身 | §0 占 21% | 本仓库按 1400 目标执行；同时向团队提议基线"摘要+链接"（团队层决策，不在本仓库单方面改） |
| 性能口径不可复现 | 旧 baseline 由仓库外工具生成 | 本方案不重启性能工作；若恢复，先统一唯一测量入口 + 同 context/n≥10/CV/显著性，再谈门禁 |

**回滚**：每阶段独立提交；`git revert` 单阶段即可。规则文件改动前先 `make check` + 保留旧版 diff；状态迁移保留 `_archive/` 不删除历史计划。

---

## 8. 决策确认（2026-11-05，用户已拍板）

| # | 决策 | 结论 |
|---|---|---|
| 1 | AGENTS 预算 | 接受 1964→≈1400 + 修正估算器（等效上限 1600）；已落为 1550/1600（余 50） |
| 2 | evidence 入库范围 | 接受：摘要 evidence 入库（1–3KB/条），原始 xcresult/日志/会话不入库 |
| 3 | CI 形态 | 加 macOS/自托管 runner 自动跑单测（开发机已有 Xcode）；Phase 1 已实现，默认由 `MACOS_CI_ENABLED` 控制 |
| 4 | 行为测试优先级 | 随后排期（Phase 2，与 P0 实现绑定） |
| 5 | DSH 仓库约定 | 接受 `.dsh/skills/` + `AGENTS.local.md` 入库；Agent Teams/worktree 等用户级配置按 HARNESS.md 建议由用户配（Phase 1 起有文档） |
| 6 | 复核成本 | **仅红队场景（并发/持久化/发布工程）强制**"独立复核 + 人工体验复核"；其他 L2 自检 + 用户确认 |
| 7 | 计划状态迁移 | 已完成计划标 `done`；`_archive/` 归档随后续清理 |
| 8 | 单源清理 | 本轮一并做：HANDOFF §6 决策表合并、§5 改摘要（已完成） |
| 9 | "未验证 + 手动步骤" | 接受为合规交付，但不得写成"已验证" |
| 10 | 提交节奏 | 阶段一提交、提交前询问（Phase 0 已提交 `d83bb05`；Phase 1 待确认提交） |

---

## 9. 验证证据（规划 + Phase 0/1）

> 前 8 行为规划期只读证据；中间为 Phase 0 验收；末尾为 Phase 1 验收。动态测试真实结果与"证据待 clean-tree 重跑"说明见 §6.2/§10。

| 命令 / 动作 | 结果 | 环境 |
|---|---|---|
| `make check`（规划期） | PASS；25 篇文档/155 链接；旧估算器 AGENTS 1964/2000、refs 793/795/783 | 本机，2026-11-05 |
| `git status --short` / `git log -5`（规划期） | HEAD `d9ef01b`；规划前工作区 clean | 本机 |
| 研究底稿（01） | 469 行；A 定义/来源、B 五子系统、C 差异、D DSH 可编程面、E 10 条结论；OpenAI 正文/CAICT PDF 标未验证 | 本机+网络 |
| 审计 1（指令/状态，02） | 607 行；Instructions 3 / State 2 / Scope 3 / Verification 3 / Lifecycle 2；3 P0 + 8 P1 + 12 P2 | 本机 |
| 审计 2（验证/可观测，03） | 470 行；验证门禁 2 / 反馈 2.5 / 可观测 3 / 声明可否证 2；4 P0 | 本机 |
| 架构铁律原型扫描（审计 2 内） | 80 文件、0 违规、0.03s | 本机 |
| 测试计数 grep（审计 2 内） | `@Test`=120、UI `func test`=3、`XCTSkip`=1 | 本机 |
| `dsh --help` / 本机 DSH 包 README | 确认 AGENTS 指令链、`.dsh/skills` rank 100、profile 级 subagent/workflow；hooks 本机不可用 | 本机 |
| `make check`（Phase 0） | **PASS**：28 篇文档/187 链接；AGENTS 1535/1600、refs 899/915/927（≤950）；arch 0 违规；tests 120/3/123+skip 1；harness 13 项；plan 0 error/1 warn | 本机，2026-11-05 |
| `make verify-static`（Phase 0） | **PASS**（含 `bash -n`、`py_compile`），exit 0 | 本机 |
| 负向 fixtures（Phase 0） | **10/10 PASS**：删 @Test / Domain 加 import SwiftUI / 伪造 UDID / `sk-` / §漂移 / 超预算 / 删嵌套 → 全红 | 本机 |
| `make doctor`（Phase 0） | OK 7 / WARN 0 / FAIL 0（Xcode 27.1、iOS 26.4.1 runtime、mobilebuildmcp、python 3.14.7） | 本机 |
| `make resume` / `make handoff`（Phase 0） | active 计划 + 三问 + 下一步；handoff 不再选已完成计划 | 本机 |
| `make test`（Phase 0，四次） | **FAIL**：SwiftData 宏 `swift-plugin-server produced malformed response`（本会话沙箱/环境问题；资源重复已修复；代码结论=未验证） | 本机 |
| `make test`（Phase 1，full-access） | **PASS：120/120**（0 failed / 0 skipped）；xcresult 已生成；因工作树 dirty 暂不生成 PASS evidence | 本机，Xcode 27.1 |
| `make test-ui`（Phase 1，full-access） | **PASS：3 executed / 2 passed / 1 skipped（模拟器无 SpeechTranscriber，预期）/ 0 failed** | 本机 |
| `make test-tools`（Phase 1） | **41 tests OK**（verify-claim/evidence 的 PASS/FAIL/UNVERIFIED、dirty、计数、skip、perf） | 本机 |
| `make check-docs`（Phase 1） | PASS：29 篇文档/200 链接；AGENTS 1550/1600；refs 899/915/919 ≤950 | 本机 |
| `make check-harness`（Phase 1） | PASS 19 项；6 个 skill frontmatter OK，且 6 个 skill 已在 DSH skill catalog 实时出现 | 本机 |
| `make verify-static`（Phase 1） | **PASS**（原 check + check-evidence + test-tools + `bash -n` 含 pre-push + py_compile） | 本机 |
| 负向演示（Phase 1） | 无 xcresult→UNVERIFIED(2)；119<floor→FAIL(1)；无 evidence→FAIL(1)；device-test skip fixture→exit 1 | 本机 |
| **clean-tree evidence（Phase 1）** | `.apm/evidence/20261105T055610Z-unit-tests-pass.json`（120/120，dirty=False，commit 3935e60）与 `...T055845Z-ui-tests-pass.json`（3 executed=2 pass+1 expected skip；dirty=False，commit fb217f6） | 本机，Xcode 27.1 |
| `make verify-claim --all`（Phase 1） | **PASS**：unit + ui 两条均 PASS（exit 0）；`make check-evidence` PASS | 本机 |
| `make device-test`（Phase 1，iPhone 13 ×2） | 第一次 FAIL：`Developer App Certificate is not trusted`；用户信任后第二次：**warmup PASS 5/5，单元 120 通过，UI runner `Timed out while enabling automation mode`**（需设备端输入一次 UI Automation 密码）；未保留 device evidence（FAIL 证据不入库） | 本机 + iPhone 13（iOS 27.0.1） |

## 10. 未运行 / 未验证（必须如实记录）

- **动态测试已验证并落证据（clean tree）**：提交 `3935e60` 后在 clean tree 重跑 `make test` → **120/120**、`make test-ui` → **3 executed / 2 passed / 1 expected skip / 0 failed**；生成 `.apm/evidence/20261105T055610Z-unit-tests-pass.json` 与 `20261105T055845Z-ui-tests-pass.json`（dirty=False），`make verify-claim --all` → **PASS**。
- **真机未验证（环境/授权前置）**：iPhone 13 已连接并解锁；信任开发者证书后第一次 warmup 已通过、真机单元 120 通过，但 UI runner 报 `Timed out while enabling automation mode`——iOS 15+ 真机首次 UI 测试需在手机上输入一次锁屏密码/允许 "Enable UI Automation"（设备重启后会再次要求）。待用户处理设备提示后重跑；本次未保留 device evidence（FAIL 证据不作为 claim 入库）。
- **未验证**：GitHub Actions static job 尚无法从本机核对（已 push；`gh` token 被组织策略拒绝查询），macOS unit-tests 默认跳过（需 `MACOS_CI_ENABLED=true` + 自托管 runner）。
- **已验证**：`.dsh/skills` 6 项已被 DSH 会话 skill catalog 实时发现；`AGENTS.local.md.example` 不写真实机器信息。
- **未验证**：嵌套 AGENTS.md 的注入时机（文件操作后）未单独实测，但 `check-harness` 校验了存在/长度/引用。
- **未验证**：真实 tokenizer 计数（`token_estimate.py` 是预算口径，不是模型 tokenizer）。
- **未验证**：性能口径能否统一（旧 baseline 由仓库外工具生成；本方案不重启性能工作）。
- **未验证（来源级）**：OpenAI 文章正文（仅开头句 + 二手摘要）；CAICT 报告 PDF 正文（只到官方摘要/目录 + 镜像前 5 页）；LangChain/Cursor 原文；DSH architecture.md 事件管线为二手转述。引用时已标注。
- **未执行**：Phase 2（P0-1/P0-2/P0-3 行为测试 + 翻译夹具）与 Phase 3（maker-checker、月度 harness 审计自动打分、失败回写、指标）。

## 11. 未提交改动

> 无未提交改动：Phase 1 代码 `3935e60`、unit evidence `fb217f6`、ui evidence + verify-claim 修正 + 本计划更新已随 HEAD 提交。下次接手先 `git status --short` 核对。

- 无

## 12. 已排除（勿重试）

- 照搬大厂五层组织级驾驭工程流程到单人项目（流程税 > 收益）。
- 把规则从 AGENTS/references 挪到 HANDOFF/docs 来绕过 token 预算（会加剧双真源）。
- 为"有 CI"上 macOS runner/重平台；真机测试进 CI（Phase 1 只上静态 + macOS 单测，真机仍本地）。
- 无 evidence 的"已验证"、用旧结论复述当新验证。
- 用 mtime 继续当"最新计划"的唯一依据；完成计划不归档。
- 新增无执行载体的规则（无脚本/无固定动作）。
- 给每个 VM 建语音引擎、mock SpeechTranscriber、改既有断言来"变绿"（原有铁律，继续有效）。
- 在 Debug 开 ORDER_FILE / 重启启动微优化（既有暂停决定）。
- 在仓库文件里承诺 hooks/MCP/Agent Teams/workflow 自动生效（它们不是仓库级能力）。
- 把嵌套 `AGENTS.md` 放回 app target 资源里而不加 Xcode 例外（会导致构建失败，已修复）。
- 在 dirty 工作树上生成"PASS"证据（证据规则要求 clean tree；当前真实测试结果只作人工记录）。

## 13. 参考与底稿

- 本地底稿（gitignore，不随仓库版本化）：`.apm/runs/harness-audit/01-research.md`、`02-audit-instructions.md`、`03-audit-verification.md`。
- DSH 机制事实：本机 DSH 0.2.1-rc.5 安装包 README（`dsh-agent-instructions`、`dsh-skill-filesystem`）——AGENTS 指令链/预算、项目 skills 根与格式；`~/.dsh/profiles/web/package.json`（bundles，含 experimental Agent Teams）；hooks 未打包。
- 外部来源（一手 ✅ / 二手 ◐ / 未取得 ✗）：
  - OpenAI, “Harness engineering: leveraging Codex in an agent-first world”, 2026-02-11（开头句一手 ✅，正文主张为二手摘要 ◐）: https://openai.com/index/harness-engineering/
  - Birgitta Böckeler (Thoughtworks), “Harness engineering for coding agent users”, 2026-04-02 ✅: https://martinfowler.com/articles/harness-engineering.html
  - Anthropic, “Effective harnesses for long-running agents” ✅: https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
  - Anthropic, “Harness design for long-running application development” ✅: https://www.anthropic.com/engineering/harness-design-long-running-apps
  - learn-harness-engineering 课程（五子系统/loop/graph）✅: https://github.com/walkinglabs/learn-harness-engineering
  - 中国信通院《驾驭工程：赋能智能原生软件工程研究报告》（2026-09；官方页 ✅，PDF 正文 ✗）: https://www.caict.ac.cn/kxyj/qwfb/ztbg//202609/t20260928_741306.htm
  - CCSA《2026 智能研发时代：企业驾驭工程落地实践报告》摘要（五层架构/六大痛点/六步路径，◐）: https://www.sgpjbg.com/labelsyh/zhinengyanfajiayugongchengluodibaogao.html
  - DSH 二手产品分析（DeepSeek breakdown，◐）: https://github.com/walkinglabs/learn-harness-engineering/blob/main/docs/en/harness-designs/deepseek/index.md
  - dshbase 插件页（learn-harness-engineering 简介）: https://dshbase.com/plugins/learn-harness-engineering/

## 14. 进度与下一步

### 进度

- [x] 现状审计（指令/状态；验证/可观测）——两份只读审计
- [x] 权威来源研究 + DSH 机制盘点（第三份底稿）
- [x] 改造方案与分阶段计划（本文）
- [x] 用户确认第 8 节决策（2026-11-05）
- [x] Phase 0 实施：估算器 + AGENTS 压缩 + 嵌套 AGENTS + 静态门禁 + 状态机 + 单源清理
- [x] Phase 0 提交：`d83bb05`
- [x] Phase 0 动态验证：full-access 下 `make test` 120/120、`make test-ui` 3 executed/1 skip/0 failed
- [x] Phase 1：evidence + CI（ubuntu 静态 + macOS 自托管单测，默认跳过）+ `.dsh/skills` + `HARNESS.md` + pre-push
- [x] Phase 1 提交：`3935e60`（代码）、`fb217f6`（unit evidence）、`74485d3`（ui evidence + verify-claim 修正 + 计划）
- [x] Phase 1 clean-tree 证据：unit 120/120、ui 3 executed(2 pass+1 skip)；`make verify-claim --all` PASS
- [x] Push：已推送到 `origin/main`（远端重定向到 DavidTeam2008/realtimeTranslatorOptimize；本机 remote 已更新）
- [ ] 真机验证：iPhone 13 已连接；证书信任后 warmup/单元通过，UI 需在手机上输入一次 UI Automation 密码；重跑后生成 device evidence
- [ ] Phase 2：P0-1/P0-2/P0-3 行为测试 + 翻译夹具（建议 P0-1/P0-3 先做；P0-2 依赖 D5/D7 决策）
- [ ] Phase 3：maker-checker、月度 harness 审计自动打分、失败回写、指标（建议只做最小人工闭环）

### 下一步

1. 设备端处理 `Enable UI Automation` 密码提示后重跑 `make device-test` 生成 device evidence（真机 123/123）；
2. 观察 GitHub Actions `verify` static job（本机 token 查询被组织策略拒绝，需网页确认）；
3. Phase 2 建议先做 P0-1（并发仲裁）红测 + P0-3（持久化）测试；P0-2 等 D5/D7 产品决策；
4. Phase 3 不做完整自动化：保留 HARNESS.md 月度人工审计 + red-team 场景强制。

### 待确认

- 设备信任证书后是否由我重跑真机测试？
- Phase 2 是否按"P0-1 + P0-3 先行、P0-2 等 D5/D7"排期？
