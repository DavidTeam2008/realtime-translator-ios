# HARNESS.md · Harness Engineering 实践地图（对译 Duiyi）

> 一句话：把"agent 该做什么"（**guides**，前馈）和"仓库怎么否证 agent 的完成声明"（**sensors**，反馈）固化进仓库，让"做完了/已验证"变成可被脚本判定的声明。
> 这是**系统地图与实践案例**，不是事实真源。真源优先级见 [`docs/README.md`](docs/README.md)；规则入口 [`AGENTS.md`](AGENTS.md)；本地开发 [`CONTRIBUTING.md`](CONTRIBUTING.md)。
> 状态：Phase 0/1 已完成（静态门禁、证据三值、CI、skills、目录治理）；Phase 2 完成（适配层 + 评分卡 + 独立复评 ≈3.6/5）；Phase 2.5 接线补强与 Phase 3 可复现进行中；未做的能力在 §8 显式标注。

## 1. 问题：为什么需要 harness

一个真实 iOS 项目用 AI Coding Agent 开发时，最常见的失败不是"不会写代码"，而是：

- **完成声明不可验证**：agent 说"测试通过/已修复"，但仓库里没有任何可复核的证据；
- **上下文每次重建**：新会话不知道项目约束、上一轮做到哪、哪些坑已踩过；
- **验证成本错配**：真机/性能验证很慢，agent 倾向用"看起来对"代替"已验证"；
- **过程文档淹没主线**：计划、问题单、历史记录与产品文档混在一起，人和 agent 都找不到真相；
- **模型/工具换代成本高**：规则写死在某个 agent 的私有配置里，换模型或换 shell 就要重写。

Harness Engineering 的回答：**模型之外的一切工程设施都是 harness；目标不是让模型更聪明，而是提高一次做对的概率，并让错误在到达人眼之前被自纠或显性化。**

## 2. 概念：五子系统与两条回路

| 概念 | 含义 | 在本仓库的落点 |
|---|---|---|
| **Agent = Model + Harness** | 模型能力 ≠ 交付能力；harness 决定能力兑现率 | 整个仓库的规则/门禁/证据 |
| **Guides（前馈）** | 约束、路由、动作卡、结构约束 | `AGENTS.md` 树、`references/`、`.dsh/skills/` |
| **Sensors（反馈）** | 测试、静态检查、架构规则、证据判定 | `make check` / `make verify-static` / 单元 / UI / 真机 |
| **Instructions** | "该做什么、去哪读" | 根 + 嵌套 `AGENTS.md`（token 预算内，指路不抄写） |
| **State** | "做到哪、证据在哪、下一步" | `harness/plans/` active 计划 + `harness/evidence/` |
| **Verification** | "怎么算完成、能否否证" | 四层验证 + PASS/FAIL/UNVERIFIED 三值 |
| **Scope** | "一次只做什么、边界在哪" | L0/L1/L2、计划 `scope.allow/deny`、红队限定场景 |
| **Session Lifecycle** | "开工/交接/收尾" | `make resume/end`、6 个 skills、handoff 协议 |

**计算型优先**：能用脚本、schema、hashes 判定的，不靠模型自觉；推断型控制（人审、红队、AI 评审）只用于无法机检的语义/体验层，并用 L0/L1/L2 分级控制流程税。

## 3. 本仓库落地矩阵

| 子系统 | 机制（可复跑） | 入口 | 类别 |
|---|---|---|---|
| Instructions | AGENTS ≈1576/1650 token；6 个嵌套 AGENTS；敏感信息 / §·第N节 引用机检（13 个指令文件） | `make check-harness` | 前馈+机检 |
| State | 计划 front matter/status；唯一 active；未提交改动与 git 交叉核对 | `make check-plan`、`make resume` | 状态 |
| Verification | 文档/架构/计数/harness/计划/adapters 6 组门禁；证据 schema + 三值判定 + 证据 ID/done submitted 硬校验；88 个脚本单测 | `make check` / `make verify-static` / `make verify-claim` | 反馈 |
| Scope | 计划 `scope.allow/deny`；L0/L1/L2；并发/持久化/发布工程强制独立红队 | `references/workflow.md`、`red-team` skill | 作用域 |
| Lifecycle | 6 个 skills：bootstrap / verify-change / handoff / red-team / harness-audit / device-verify | `.dsh/skills/`、`make resume/end` | 会话 |
| 证据层 | 单元/UI/真机 evidence JSON；三值判定；commit/dirty 校验 | `harness/evidence/` | 可审计 |
| 目录分层 | `docs/`（事实）· `references/`（规则）· `harness/`（过程与证据）· `tools/`（门禁） | `docs/README.md`、`harness/README.md` | 信息架构 |

**门禁分层（成本与可信度匹配）**：

| 层 | 内容 | 何时跑 |
|---|---|---|
| 静态（约 0.3–4.3s，无 Xcode） | docs/架构/计数/harness/计划/证据 + 脚本单测 | 每次改动；CI ubuntu；pre-push |
| 动态（分钟级） | 模拟器单元 / UI 测试 | 对应代码改动后；可选 self-hosted macOS CI |
| 人工（真机） | 语音 / 翻译 / TTS / 音频 / 持久化 / SwiftData | 相关改动与发版前；不可替代 |
| 月度 | harness 审计 + 评分卡更新 | 每月或大改后 |

## 4. 证据怎么验（可审计性是本仓库的差异点）

**三值判定**：`PASS`(exit 0) / `FAIL`(exit 1) / `UNVERIFIED`(exit 2)；UNVERIFIED 不算绿。

```bash
make evidence        # 列出证据
make verify-claim    # 校验全部证据（默认 --all）
make check-evidence  # 只做 schema/语义校验
```

**evidence JSON**（`harness/evidence/*.json`，1–3KB/条）必须包含：claim 类型、命令、环境、通过/失败/skip 计数、commit、`dirty=false`、xcresult/指标路径、verdict。规则：

- 无 evidence id 的"已验证"按未验证处理；换机器 xcresult 不可达 → UNVERIFIED（不伪造）；
- 计划声称 PASS/已完成时，证据 ID 必须解析到 verdict=PASS 的 evidence（或显式标注基线/过程/外部记录）；done 计划的证据 commit 必须绑定 `submitted` 或 HEAD（`make check-plan` 硬校验）；
- 测试类 claim 必须满足 floor（`passed ≥ 基线`）、`failed=0`、`skipped == 预期`；
- 性能 claim 必须同 context、n≥10、CV/显著性达标；模拟器与单次样本不构成性能证据；
- 文档/架构 claim 由 `verify-claim` 直接复跑对应静态门禁；
- **不绝对防伪**：证据可以被伪造；高风险改动仍走独立审查 + 人工真机体验。

**四层验证矩阵**：静态 → 单元/UI → 真机 → 人工体验；变更类型对应的最低验证见 [`references/verification.md`](references/verification.md)。

## 5. 我们踩过的坑与取舍（诚实记录）

- **假绿比失败更贵**：UI 测试"存在但不可点击"、模拟器语音 skip 被当作通过、handoff 输出与 git 事实相反——这些都不能靠"更努力的 agent"解决，只能靠机检和可证伪证据。
- **流程税必须分层**：小改动强制全套流程会让 agent（和人）绕过规则；因此 L0/L1/L2 + 秒级/分钟级/真机/月度四层。
- **规则会漂移**：同一事实写两处必漂移；用 token 预算 + 单一源 + 链接取代复制。
- **工具能力不是仓库能力**：DSH/Claude Code 的 hooks、subagents、teams、worktrees 都是 profile/会话级；仓库内真正可固化的只有 `AGENTS.md` 谱系、skills、CLI 门禁与证据。
- **诚实负结果也是资产**：启动 200ms 目标被对照组地板证伪（p50=210ms），完整证据链见 [`docs/case-startup-performance.md`](docs/case-startup-performance.md)，避免下一棒重复劳动。
- **CI 有边界**：ubuntu static 全绿成本极低；macOS 单测依赖自托管 runner，托管 runtime 未验证，默认按设计跳过。
- **证据路径与隐私**：本机绝对路径、设备 ID、Team ID 不入库；机器事实写 `AGENTS.local.md`（gitignore）。旧 commit 历史中仍可能残留，公开发布前需单独评估（见 §8）。

## 6. 复制到你的仓库（最小起步 → 进阶）

不要求一次做全；按项目风险逐步加。**核心三件套**：AGENTS 指令树 + 秒级静态门禁 + 可复核证据；其余按需。

1. **写冷启动入口**：根 `AGENTS.md` 只做定位/路由/铁律（目标 ≤200 行）；细节放 `references/` 或 skills。
2. **加第一个 sensor**：`tools/check-docs.py` 式文档/链接/围栏检查，`make check` 秒级可跑。
3. **让完成可证伪**：定义 1–2 种 claim（如 `unit-tests-pass`），加 evidence JSON + `verify-claim` 三值判定。
4. **状态外置**：`harness/plans/` 模板 + active 唯一 + `make resume/end`；会话不再靠聊天记忆。
5. **架构 fitness**：用 grep/AST/依赖图把最重要的 3–6 条架构铁律变成秒级检查。
6. **测试基线**：计数下限 + skip 白名单，防"删测试变绿"。
7. **CI 分层**：ubuntu 跑静态；昂贵/平台相关测试放自托管或手动，并写清"未验证"。
8. **skills**：把重复动作（验证/交接/真机/红队）写成 `SKILL.md`，按需加载，省 context。
9. **接入你的 agent**：保持规则在 `AGENTS.md`；用适配层提供工具差异（见 §9 / [`harness/adapters/`](harness/adapters/)）。
10. **周期修剪**：月度审计（评分卡）+ 季度文档修剪；过程只留结论+证据，原始记录进 git 历史。

> 完整模板（profiles + 脚手架 + adapters）在 Phase 5 抽成 `harness-kit`；本项目是它的第一个案例。

## 7. 评分卡与独立复评

- 评分方法与当前分数：[`docs/harness-scorecard.md`](docs/harness-scorecard.md)（五子系统 1–5 分 + 证据）。
- 当前独立复评（2026-11-07）：Instructions 4.0 / State 3.5 / Verification 4.0 / Scope 3.0 / Lifecycle 3.5，综合 **≈3.6 / 5（72%）**；改造前独立审计为 2.5/5。
- L3 判定：**条件成立**——`verify-claim` 已接入 `make end`，但尚未接入 pre-push/CI，且 evidence 时效/ID 校验待补（Phase 2.5）。
- 独立复评报告：[`harness/reviews/2026-11-07-harness-reaudit.md`](harness/reviews/2026-11-07-harness-reaudit.md)。复评规则：每月或大改后由**非作者**只读复评；分数变化必须附证据；自评与复评分差异要解释。

## 8. 局限与未验证（不要当成能力）

- **行为正确性**：静态门禁不能证明语义正确；P0-1 并发仲裁 / P0-3 持久化的行为测试尚未做（独立排期）。
- **动态 CI**：macOS 单测默认跳过，需自托管 runner；GitHub 托管 macOS 是否有 iOS 26.4 runtime 未验证。
- **真机依赖**：语音/翻译/持久化必须在真机验收；不能操作设备时只能写"未验证 + 手动步骤"。
- **性能**：启动优化已暂停；无性能回归门禁；性能结论只认真机 n≥10 同口径。
- **架构强制**：单 target，无编译期模块边界；`check-arch` 是文本规则，可被绕过；无覆盖率门槛。
- **工具适配**：Claude Code 的 hooks 示例、skills 同步为设计资产，未在本机实测（本机未装 Claude Code）。
- **git 历史**：两轮 `git filter-repo`（敏感信息、作者邮箱）后，本地/远端分支历史 0 命中；GitHub 仍保留 unreachable 旧对象（按 SHA 可访问），已由用户接受，不联系 Support 彻底清除。
- **证据可伪造**：三值判定提高说谎成本，不提供密码学保证；高风险仍需独立审查。
- **验证接线**：`verify-claim` 已接入 `make end`（`--fresh` 告警）与 `make release-check`（`--fresh --strict`，STALE 判 UNVERIFIED）；证据 ID/占位、done 的 `submitted` 与证据 commit 绑定由 `make check-plan` 硬校验；旧证据跨 commit 会 STALE，发布前需在 release commit 重跑。
- **scope 越界**：`scope.allow` 已能报「allow 外改动」，但 allow 本身可由执行者修改；范围正确性仍是半自动。
- **§ 引用 sensor**：已覆盖根/嵌套 AGENTS 与 skills（`§N` 与 `第 N 节`，13 个指令文件 7 处命中）；references 文档之间的节号引用尚未纳入。
- **clean clone**：Phase 3.1 已实测（`make check` 0.33s PASS，无 Xcode）；动态层仍无法在 clone 中验证。

## 9. 运行手册与工具适配

| 场景 | 命令 | 说明 |
|---|---|---|
| 环境自检 | `make doctor` | Xcode/模拟器/真机工具；exit 2 = 动态验证不可用 → "未验证" |
| 接手 / 开工 | `make resume` | active 计划 + git 状态 + 下一步 1 条 |
| 秒级门禁 | `make check` / `make verify-static` | 前者 6 组静态；后者加证据/脚本单测/语法 |
| 按类型验证 | `make test` / `make test-ui` / `make device-test` | 见 [`references/verification.md`](references/verification.md) |
| 证据 | `make evidence` / `make verify-claim` | 三值判定 |
| 证据时效 | `make verify-claim-fresh` | 相关文件在证据 commit 后变更 → STALE 告警（不阻断） |
| 发布门禁 | `make release-check` | 静态 + 证据时效 strict（STALE → UNVERIFIED） |
| 收尾 | `make check-plan` → `make end` → `make handoff` | 提交前询问 |
| 月度审计 | `make harness-audit` | 人工打分，结果写 `harness/reviews/` |
| Agent 适配 | `make adapters-sync` / `make adapters-check` | 单源 skills → `.claude/skills`；hooks 示例见 [`harness/adapters/`](harness/adapters/) |

**工具无关核心**：规范在 `AGENTS.md`（DSH 与 Claude Code 均可原生读取）；动作在 skills；门禁在 `Makefile`/`tools/`；证据在 `harness/evidence/`。**工具差异只放在适配层**：

| 能力 | DSH（0.2.1-rc.5） | Claude Code |
|---|---|---|
| 指令 | 原生 AGENTS 链（含嵌套/预算） | v2.1.277+ 原生读取 AGENTS.md |
| Skills | `.dsh/skills/` 自动发现 | `.claude/skills/`（由 `make adapters-sync` 生成） |
| 自动执行 | 无仓库级 hooks；用 skills + pre-push + CI | `PostToolUse`/`Stop` hooks（示例配置） |
| 状态 | 仓库计划 + 会话 goal/plan | 仓库计划 + plan mode |
| 模型 | profile 配置（用户级） | `ANTHROPIC_BASE_URL` 等环境变量（DeepSeek 官方支持） |

**CI 与 hooks**：`.github/workflows/verify.yml` = ubuntu static + 可选 self-hosted macOS 单测；`.githooks/pre-push` 推送前跑 `make verify-static`；真机/性能只在本地人工执行。
**项目级 skills**：`.dsh/skills/` 6 个（bootstrap / verify-change / handoff / red-team / harness-audit / device-verify），详见 [(skills)](.dsh/skills/)。

## 10. 来源与版本

- Claude Code：Hooks <https://code.claude.com/docs/en/hooks>；Memory / AGENTS.md <https://code.claude.com/docs/en/memory>；扩展总览 <https://code.claude.com/docs/en/features-overview>。
- DeepSeek：Anthropic API 兼容 <https://api-docs.deepseek.com/guides/anthropic_api>；Claude Code 集成 <https://api-docs.deepseek.com/quick_start/agent_integrations/claude_code>。
- DeepSeek Harness 文档 <https://deepseek-harness.github.io/deepseek-harness/en/guide/quickstart>；本机能力盘点（0.2.1-rc.5）见 `harness/runs/harness-audit/01-research.md`（gitignore）。
- 方法论来源：Fowler/Thoughtworks（guides + sensors）、OpenAI（repo-as-spec）、Anthropic（外置状态 / maker-checker）、CAICT（驾驭工程）、learn-harness-engineering（五子系统）。

## Changelog

| 日期 | 变更 |
| --- | --- |
| 2026-11-05 | Phase 0：AGENTS 压缩+嵌套、静态门禁（arch/tests/harness）、计划状态机（resume/end/doctor）、单一真源清理（D1–D7） |
| 2026-11-05 | Phase 1：evidence 三值判定、6 个 `.dsh/skills`、CI `verify.yml` + pre-push、HARNESS.md 初版、`AGENTS.local.md` 模板 |
| 2026-11-07 | Phase 1 第一批：HANDOFF 拆分（CONTRIBUTING + docs/decisions）、LICENSE/README 重写、脱敏、公开文档白名单门禁 |
| 2026-11-07 | Phase 1 第二批：历史文档蒸馏为案例并删除、原 APM 工作区更名 `harness/` 并瘦身、截图 |
| 2026-11-07 | Phase 2：HARNESS 重写（案例+方法+采用指南+评分卡+适配层）、独立复评、evidence schema v2 |
| 2026-11-07 | Phase 2.5：证据时效检查（`--fresh` / `--strict`）、`make release-check`、scope 越界 FAIL、计划证据 ID WARN |
