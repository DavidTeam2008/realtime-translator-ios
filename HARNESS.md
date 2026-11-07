# HARNESS.md · Harness 系统地图（对译 Duiyi）

> 一句话：本项目把"agent 该做什么"（**guides**，前馈）和"仓库怎么否证 agent 的完成声明"（**sensors**，反馈）都固化进仓库；本文是这张地图的运行手册与索引，**不是事实真源**。
> 真源优先级见 [`docs/README.md`](docs/README.md)；规则入口 [`AGENTS.md`](AGENTS.md)；人读接手 [`CONTRIBUTING.md`](CONTRIBUTING.md)。
> 状态：**Phase 1（2026-11-05）**。Phase 2 行为传感器（P0 对应测试）与 Phase 3 自动审计/指标尚未完成，未做的能力在文中显式标注。

## 1. 目标与边界

**目标**：任意一个 agent 新会话进入仓库后，能在 ≤3 次读取内知道"我是谁、做到哪、下一步、怎么算完成"；任意"完成/已验证"声明都能被仓库脚本判 **PASS / FAIL / UNVERIFIED**，而不是自由文字。

**分层门禁**（成本与可信度匹配）：

| 层 | 内容 | 何时跑 |
| --- | --- | --- |
| 静态（约 3–5s，无 Xcode） | 文档/架构/计数/harness/计划/证据 lint + 41 个脚本单测 | 每次改动；CI ubuntu；pre-push |
| 动态（分钟级） | 模拟器单元/UI 测试 | 对应代码改动后；可选 self-hosted macOS CI |
| 人工（真机） | 语音/翻译/TTS/音频/持久化/SwiftData | 相关改动与发版前；不可替代 |

**诚实边界**：静态门禁不能证明行为正确；evidence 只提高说谎成本、不绝对防伪（仍需独立审查）；profile/会话级能力（Agent Teams、worktree、MCP、hooks）不是仓库能强制的东西，见 §8。

## 2. `harness/` 是什么，为什么计划与证据放这里

**定义**：`harness/` 是**项目自定义的 Agent 工作区目录**。它不是 App 运行时目录、不是构建产物，也**不是 DSH 框架要求**。目录名来自 2026-09「启动性能自主闭环演练」的 APM 测量工作区，2026-11 更名并收敛为跨会话计划、证据与工具的统一位置；产品文档仍在 `docs/`。

**为什么放这里**：

1. **单一真源 + 可恢复**：与仓库一起版本化，换 agent / 换机器只靠仓库就能恢复任务与证据。
2. **与产品文档分层**：`docs/` 写"当前规范与理由"；`harness/` 写"某次任务的执行状态、证据与审查"。项目阶段与路线图写 `docs/04-roadmap.md`。
3. **体积可控**：原始测量/日志/trace 全部 gitignore，入库的只有摘要（JSON/Markdown）。

| 子目录 | 职责 | 入库 |
| --- | --- | --- |
| `harness/plans/` | 跨会话计划（唯一进度真源）；`_template.md` | 是 |
| `harness/evidence/` | 可复核证据（schema、TEMPLATE、摘要 JSON） | 是（1–3KB/条） |
| `harness/tools/` | 真机测试/启动测量脚本 | 是 |
| `harness/test-baseline.json` | 测试计数与 skip 白名单基线 | 是 |
| `harness/runs/`、日志/截图/trace | 原始测量产物 | **否**（gitignore，可由脚本重建） |

`harness/` 的目录级协议见 [`harness/AGENTS.md`](harness/AGENTS.md)；工作区索引见 [`harness/README.md`](harness/README.md)；证据规范见 [`harness/evidence/README.md`](harness/evidence/README.md)。

## 3. Guides / Sensors 矩阵

| 类型 | 资产 | 作用 | 入口 |
| --- | --- | --- | --- |
| Guide | [`AGENTS.md`](AGENTS.md) + 6 个嵌套 `AGENTS.md` | 冷启动定位、铁律、路由、执行协议 | 自动注入（DSH）；其他工具当 Markdown 读 |
| Guide | [`docs/README.md`](docs/README.md)、`docs/01`–`04` | 真源优先级、产品/架构/选型/排期 | 按任务读段落 |
| Guide | [`CONTRIBUTING.md`](CONTRIBUTING.md) | 本地环境、签名、测试入口与已知坑 | 接手第一篇 |
| Guide | [`references/contracts.md`](references/contracts.md)、[`verification.md`](references/verification.md)、[`workflow.md`](references/workflow.md) | 契约细则、验证矩阵、任务分级/红队 | 按任务按需读 |
| Guide | [`.dsh/skills/`](.dsh/skills/) | 6 个可调用动作（见 §6） | `skill` 工具（DSH） |
| Sensor | `make check-docs` | 链接 / 围栏 / docs 索引 / token 预算 | 静态 |
| Sensor | `make check-arch` | 架构铁律 R1–R6（依赖单向/翻译锚 View/单引擎/内存为准） | 静态 |
| Sensor | `make check-tests` | 测试计数下限 + skip 白名单（防删测试变绿） | 静态 |
| Sensor | `make check-harness` | 预算 / § 引用 / 嵌套 AGENTS / skills / 敏感路径 | 静态 |
| Sensor | `make check-plan` | 计划状态机与必填字段 / 未提交改动 vs git | 静态 |
| Sensor | `make verify-static` | 以上全部 + 证据 schema 校验 + harness 脚本单测 + 脚本语法 | 静态（约 3–5s） |
| Sensor | [`harness/evidence/`](harness/evidence/README.md) + `tools/evidence.py` / `tools/verify-claim.py` | 证据摘要与三值判定 | 声明前 |
| Sensor | [`.githooks/pre-push`](.githooks/pre-push) | push 前自动跑 `make verify-static` | 本地 git |
| Sensor | [`.github/workflows/verify.yml`](.github/workflows/verify.yml) | CI：ubuntu 静态 + 可选 self-hosted macOS 单测 | 远程 |
| Sensor | `harness/tools/device-test.sh`、`measure-launch.sh` | 真机测试 / 启动测量（写 evidence） | 人工真机 |
| Sensor | `red-team` skill / 只读子 agent | L2 中并发·持久化·发布工程的独立审查 | 人工触发 |

## 4. 运行手册

| 场景 | 命令 | 说明 |
| --- | --- | --- |
| 环境自检 | `make doctor` | Xcode/模拟器 runtime/真机工具/模板仓；exit 2 = 动态验证不可用 → 结论"未验证" |
| 接手 / 开工 | `make resume` | active 计划 + git 状态 + 下一步 1 条 + 建议阅读 |
| 秒级门禁 | `make check` / `make verify-static` | 前者 5 项静态；后者加证据校验 + 脚本单测 + 脚本语法 |
| 按类型验证 | `make test` / `make test-ui` / `make device-test` | 见 [`references/verification.md`](references/verification.md) |
| 证据 | 写：`python3 tools/evidence.py write ...`（真机/测量脚本自动写）；查：`make evidence`（ls）/ `make check-evidence`（validate） | 手写示例见证据 README |
| 判定声明 | `make verify-claim CLAIM=<证据路径>` | 缺省 `--all`；PASS/FAIL/UNVERIFIED 三值 |
| 收尾 | `make check-plan` → `make end` → `make handoff` | 计划更新后跑；提交前询问 |
| 安装 hook | `make hooks-install` | 等价 `git config core.hooksPath .githooks`；每克隆一次 |
| 月度审计 | `make harness-audit` | `check-all` + `doctor` + `evidence`，再按 §9 清单**人工打分**（Phase 3 前不自动判绿） |
| 红队 | `red-team` skill（或只读子 agent） | 仅 L2 并发/持久化/发布工程强制 |

## 5. 证据政策

- **三值判定**：`PASS`(exit 0) / `FAIL`(exit 1) / `UNVERIFIED`(exit 2)；UNVERIFIED 不绿。
- **摘要入库、原始不入库**：`harness/evidence/*.json`（1–3KB/条）随仓库提交；xcresult、日志、截图、trace 不进库（可由命令重跑）。
- **无 evidence id = 未验证**：完成声明必须能指向 evidence id / 可复核命令；Phase 0 之前的历史记录保留当时口径。
- **测试类 claim**：`passed ≥` 基线 floor、`failed=0`、`skipped == expected`、xcresult 指纹存在，否则 UNVERIFIED；不得用旧结论当新验证。
- **文档/架构 claim**：`verify-claim` 直接复跑对应静态门禁。
- **性能 claim**：必须同 context、n≥10、CV/显著性达标；否则 UNVERIFIED；性能结论不能由模拟器或单次样本得出。
- **commit 校验**：证据的 commit 必须是 HEAD 或 HEAD 祖先且 `dirty=false`；过期/伪造证据判 FAIL 或 UNVERIFIED。
- **不绝对防伪**：证据可以被伪造；高风险改动仍走独立审查 + 人工真机体验。

## 6. 项目级 skills（`.dsh/skills/`）

| Skill | 触发 | 动作 |
| --- | --- | --- |
| `session-bootstrap` | 新会话/接手 | `make doctor` → `make resume` → 只输出"一个下一步 + 建议阅读" |
| `verify-change` | 任何完成声明前 | 按变更类型选验证 → 记录证据 → 给 PASS/FAIL/UNVERIFIED |
| `handoff` | 中断/收工/交接 | 更新计划 → `make check-plan` → `make end` → `make handoff` |
| `red-team` | L2 并发/持久化/发布工程 | 只读独立审查：P0/P1/P2 表 + 被挑战假设 + 最小验证清单 |
| `harness-audit` | 月度/大改后 | 跑门禁与证据命令，按 §9 打分（Phase 3 前人工） |
| `device-verify` | 真机验收 | `device-test.sh` 流程；处理 exit 2/74/密码弹窗；失败写"未验证 + 手动步骤" |

说明：`.dsh/skills/` 是**仓库内真实文件**、DSH 原生发现（项目 skill 根）；其他 agent 工具可当 Markdown 动作卡读，但不保证自动加载。机器本地覆盖（签名 Team、设备 ID）用 `AGENTS.local.md`（gitignore，模板 [`AGENTS.local.md.example`](AGENTS.local.md.example)）。

## 7. CI 与 hooks

- **CI** [`.github/workflows/verify.yml`](.github/workflows/verify.yml)：`static`（ubuntu-latest，`make verify-static`，约 3–5s）+ `unit-tests`（self-hosted macOS，`make test`，`needs: static`）。后者默认跳过，仓库变量 `MACOS_CI_ENABLED=true` 才启用；失败也上传 xcresult/日志（保留 7 天）。GitHub 托管 macOS 是否带 iOS 26.4 runtime **未验证**，故默认自托管。
- **旧** `.github/workflows/docs.yml` 保留（只查文档），static job 已覆盖全量静态门禁。
- **hooks** [`.githooks/pre-push`](.githooks/pre-push)：push 前跑 `make verify-static`，失败退出 1；`SKIP_HARNESS_HOOK=1` 可跳过（须在计划/PR 记录原因）。
- **分层**：CI 不跑真机/性能；`device-test.sh`、`measure-launch.sh` 只在本地人工执行。

## 8. DSH 用户级配置建议（**非仓库强制**）

以下全部配置在**用户自己的 `~/.dsh`**，本仓库不提供、不校验、**不承诺自动生效**；仓库内能固化的只有 AGENTS.md 谱系与 `.dsh/skills/`。

**（1）profile patch 片段**（`~/.dsh/profiles/<profile>/cordis.patch.yml`，以本机 DSH 0.2.1-rc.5 的层序为例）：

```yaml
- id: agent-default-model
  name: "@deepseek-ai/dsh-agent-default-model"
  config:
    provider: deepseek-official
    model: deepseek-v4-flash-vision-exp
    reasoningEffort: high

- id: subagent-model-selection-settings
  name: "@deepseek-ai/dsh-tool-subagent/model-selection-settings"
  config:
    enabled: true
    allowedModels:
      - provider: deepseek-official
        model: deepseek-flash
```

**（2）启用实验能力**（Agent Teams / worktree，按版本语法可能变化）：

```bash
dsh plugin --profile <profile> add @deepseek-ai/dsh-experimental-agent-team-profile
dsh plugin --profile <profile> add @deepseek-ai/dsh-experimental-tool-worktree
```

**（3）建议用法**：长任务用 goal / `make plan`；L2 复核用 Agent Teams 或只读子 agent（maker-checker）；并行实验用 worktree；月度审计可用 `schedule` 提醒。以上是**会话级操作**，不写进仓库规则。**（4）未验证**：hooks / MCP 在 DSH 0.2.1-rc.5 未随包启用，不要假设存在；不同 DSH 版本以 `dsh plugin list` / `--help` 为准。

## 9. 月度 harness 审计清单

每月或大改后按 §4 跑命令，逐项给 PASS/WARN/FAIL，输出 `harness/reviews/harness-YYYY-MM.md`（目录按需创建），失败模式回写计划或改进项（Phase 3 前人工）。

- **Instructions**：`AGENTS.md` ≤1600；6 个嵌套 AGENTS 存在且未膨胀；§ 引用命中目标标题；规则未在 references/docs 重复。
- **State**：同一时间只有一个 active 计划；front matter 与证据四列完整；done 计划已归档；`make resume` 只靠仓库能答"下一步"。
- **Verification**：`make verify-static` PASS；负向测试仍红（删 1 个 `@Test`、Domain 加 `import SwiftUI`、伪造 UDID）；`evidence validate` 无错；未验证声明被显式记录。
- **Scope**：计划 `scope.allow/deny` 与实际改动一致；越界有记录与更新。
- **Lifecycle**：`make doctor` 结论被正确解读（环境问题 ≠ 代码问题）；hook 已安装；CI static 绿、unit-tests 按开关状态如实说明。

**三指标**（月度对比，不看文档数量）：① 首次门禁通过率；② 同一失败返工轮次（2 次停止规则）；③ 未验证声明覆盖率（目标 100%）。

## 10. Changelog

| 日期 | 变更 |
| --- | --- |
| 2026-11-05 | Phase 0：AGENTS 压缩+嵌套、静态门禁（arch/tests/harness）、计划状态机（resume/end/doctor）、单一真源清理（D1–D7） |
| 2026-11-05 | Phase 1：evidence 三值判定、6 个 `.dsh/skills`、CI `verify.yml` + pre-push、HARNESS.md 初版、`AGENTS.local.md` 模板 |
| 2026-11-07 | Phase 1 第一批：HANDOFF 拆分（CONTRIBUTING + docs/decisions）、LICENSE/README 重写、脱敏（Team/设备 ID/路径）、公开文档白名单门禁 |
| 2026-11-07 | 第二阶段：历史文档蒸馏为案例并删除、原 APM 工作区更名 `harness/` 并瘦身、新增 `harness/README.md` |
