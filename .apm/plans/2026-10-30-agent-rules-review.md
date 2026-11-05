---
id: 2026-10-30-agent-rules-review
status: done
level: L2
owner: david
updated: 2026-11-05
submitted: f57d90a,d9ef01b
---

# Agent 规则骨架引入 · 独立审查包

> 审查对象：2026-10-30 引入 team-agent-template 裁剪版的未提交改动。
> 输入边界：审查者只读；只使用本文件与仓库，不使用起草对话、作者自评或既往审查结论。
> 本文件的“进度 / 验证证据”只表示任务状态，不作为质量证据；结论由审查者独立得出。

## 目标与验收

- 目标：在不引入第二套事实源的前提下，把模板裁剪为项目可用的 Agent 规则骨架：冷启动入口、细则、命令、文档门禁、跨会话计划与接手协议。
- 非目标：不改业务代码；不引入 `MEMORY/` / `Wiki/` / `Resources/`；不照搬 `check_rules.py`；不让 CI 依赖团队仓；不改变既有测试基线。
- 验收：
  1. 规则自洽，与项目铁律无冲突；
  2. 单一真源：`HANDOFF.md` / `docs/` / `.apm/`，无平行知识库；
  3. 命令可执行，路径大小写跨平台安全；
  4. token 预算：`AGENTS.md` ≤ 2000，每个 `references/*.md` ≤ 800；
  5. 新机器 / 无模板仓时行为明确，不误导 Agent；
  6. 接手闭环：新 Agent 只靠仓库能恢复任务；
  7. 不诱导无效操作、死循环或 token 浪费。

## 变更清单

新增：

- `AGENTS.md`
- `references/contracts.md`、`references/verification.md`、`references/workflow.md`
- `tools/check-docs.py`、`tools/plan.py`
- `Makefile`
- `.github/workflows/docs.yml`
- `.apm/plans/_template.md`
- `docs/21-cross-session-handoff.md`

修改：

- `HANDOFF.md`
- `docs/README.md`
- `.gitignore`

未跟踪文件不在 `git diff` 中，需逐个读取；以 `git status --short` 为准。

## 关键决策与理由

1. 只裁剪不照搬：保留团队基线块 + 项目 §7 覆盖，避免模板与项目规则双真源。
2. 团队基线只做本地 `make check-agents`；CI 只跑 `tools/check-docs.py`。原因：团队仓访问未验证，CI 不引入外部依赖。
3. 知识库沿用 `HANDOFF.md` / `docs/` / `.apm/`；不建 `MEMORY/` / `Wiki/` / `Resources/`。
4. 不复制 `check_rules.py`：它校验模板仓自身结构，照搬会产生误报和修复循环。
5. 红队仅用于并发 / 持久化 / 发布；本次为文档与工程脚本，按“配置变更”审查。
6. 工具路径统一小写 `tools/`：macOS 大小写不敏感，避免与既有 `tools/` 冲突。
7. 跨会话任务用 `.apm/plans/` + `make plan` / `make handoff`；`HANDOFF.md` 只管项目阶段与优先级。

## 已排除（勿重试）

- 全量复制模板（含 `MEMORY/` / `Wiki/` / `frontend.md` / `check_rules.py`）：多真源、CI 误报。
- CI 克隆团队仓做基线校验：外部访问未验证，失败会阻断 PR。
- 自动派生 `TOPIC`：无法从任务内容可靠生成，改为人工或 Agent 起短名。
- CI 强制检查计划完整性：无法判断任务状态，易误报。

## 验证证据

审查者独立运行，不采信作者声明：

| 命令 | 目的 |
| --- | --- |
| `PYTHONDONTWRITEBYTECODE=1 python3 tools/check-docs.py` | 链接 / 围栏 / docs 索引 |
| `PYTHONDONTWRITEBYTECODE=1 python3 ../../agent/template/scripts/sync_team_baseline.py --check AGENTS.md` | 团队基线 |
| token 统计脚本 | `AGENTS.md` ≤2000、每个 `references` ≤800 |
| `make plan TOPIC=<临时短名>` + `make handoff` | 计划 / 交接摘要冒烟；测试后删除临时计划 |
| `TEAM_RULES=/nonexistent make check-agents` | 无模板仓时的报错是否清晰 |
| `git status --short` / `git diff` / `git ls-files --others --exclude-standard` | 改动边界 |

## 未提交改动

- 已于 `f57d90a` 提交；后续 `d9ef01b` 为文档整合；当前无本计划未提交改动。
- 历史说明（保留供追溯）：审查阶段曾记录“全部改动未提交”，该状态在提交后已失效。

## 审查任务书

```text
你是未参与起草的独立审查者。目标：找出这次改动会失败、被推翻或引入新风险的理由，而不是证明它可行。

约束：
- 只读：不修改文件，不读 .env，不执行写操作或破坏性命令；可运行只读检查，命令前加 PYTHONDONTWRITEBYTECODE=1。
- 输入只有本说明、仓库路径和模板源路径；不要索取或使用起草对话、作者自评、既往审查结论。
- 无证据标“不确定”；不复述方案；不替作者做决定。

仓库：本仓库根目录（审查时由调用方提供绝对路径）
模板源：team-agent-template 仓（`TEAM_RULES` 指向的目录）
审查对象：本文件（.apm/plans/2026-10-30-agent-rules-review.md）及其中列出的变更清单。

审查重点：
1. 规则合理性与自洽：矛盾、空洞条款、无法执行的触发条件；
2. 与项目既有铁律 / 文档的冲突，是否破坏单一真源；
3. 是否引入无效操作、死循环、token 浪费（L0/L1/L2、停止规则、红队范围、计划维护成本）；
4. 可执行性：make 命令、路径大小写、无模板仓的新机器、CI 依赖；
5. 接手闭环：新 Agent 能否只靠仓库恢复任务；
6. token 预算：AGENTS ≤2000，每个 references ≤800；
7. 安全与提交卫生：密钥、.env、构建产物、他人签名信息。

请自行运行只读检查（至少：文档检查、团队基线 check、token 统计），不要相信作者声称的结果。

输出：
1. 结论：通过 / 有条件通过 / 不通过；
2. P0/P1/P2 问题表：问题 | 证据/位置 | 影响 | 建议；
3. 被挑战的假设；
4. 缺失信息；
5. 最小验证清单。
```

## 进度

- [x] 变更实施
- [x] 作者侧自检（仅供任务状态，审查者必须复跑）
- [x] 独立审查（有条件通过，无 P0）
- [x] 逐条回应与修复（P1 全部修复；P2 全部处理，P2-8 已真机确认）
- [x] 用户确认
- [x] 提交（`f57d90a`；其后 `d9ef01b` 为文档整合）

## 下一步

1. 已完成并归档：本计划工作已收尾（`f57d90a` 采纳规则骨架，`d9ef01b` 文档整合），无后续步骤；新任务另起 `status: active` 计划。

## 待确认（已定）

- 无模板仓：`check-agents` 显示 SKIP，不阻断；`make check` 不依赖模板仓。
- `.apm/plans/`：入库；不写绝对路径、密钥、设备 UDID；完成的计划保留。
- docs CI：加 `paths` 过滤；计划仍纳入链接检查（计划已入库，链接必须有效）。

## 审查结论与作者回应（2026-10-30）

> 审查报告：`.apm/reviews/2026-10-30-agent-rules-review.md`；结论“有条件通过”，无 P0。

### P1

| 编号 | 结论 | 处理 |
|---|---|---|
| P1-1 最新计划按字典序 | 接受 | `tools/plan.py` 改为按 mtime 选择；`make handoff PLAN=<path>` 可显式指定；workflow / docs/21 同步 |
| P1-2 无模板仓 `make check` 必红 | 接受 | `make check` 只跑 docs + token；新增 `make check-all`；`check-agents` 无模板仓时 `[SKIP]` 且 exit 0；AGENTS / HANDOFF / docs/21 同步 |
| P1-3 `.apm/plans` 入库未决 | 接受 | 决策入库；模板与计划禁止本机绝对路径、密钥、UDID；审查计划已脱敏；FAQ 写明 |
| P1-4 `SpeechSessionGate` 写成现行铁律 | 接受 | AGENTS 铁律 3 改为“现行共享 actor；`SpeechSessionGate` 是 P0-1 目标，未实现不得声称”；contracts §3 拆“现行 / P0-1（未实现）” |
| P1-5 红队范围冲突 | 接受 | workflow 的 L2 动作与红队范围统一为“仅并发 / 持久化 / 发布；其他 L2 自检 + 用户确认（AGENTS §7）” |

### P2

| 编号 | 结论 | 处理 |
|---|---|---|
| P2-1 token 无门禁 | 接受 | `tools/check-docs.py` 增加 `est_tokens` 门禁（与模板同口径）；`make check` 与 CI 都执行 |
| P2-2 AGENTS 违反计数规则 | 接受 | 删除 AGENTS 内精确计数，只留“只增不减”；计数唯一在 `references/verification.md` |
| P2-3 handoff 缺 2 项 | 接受 | `brief` 增加“已排除 / 验证证据”；缺“目标与验收 / 下一步”告警 |
| P2-4 measure-launch 默认 5 | 接受 | `N ?= 10`；HANDOFF 注释改为“参数为运行次数，n≥10” |
| P2-5 CI 无 path filter | 接受（部分） | 加 `paths` 过滤；计划仍纳入检查，因为已入库且链接必须有效 |
| P2-6 references 与 HANDOFF/docs 重叠 | 接受（文档层） | docs/README 与 docs/21 声明：代码、docs/01–04、HANDOFF 是事实，references 是规则视图；本轮不做大规模去重 |
| P2-7 plan.py 缺校验 | 接受 | 缺模板给明确错误；`brief` 缺目标/下一步告警；文档改为“2–5 个短词（英文优先，允许汉字）”，与实现一致 |
| P2-8 APM_DEVICE ID 类型 | 接受（已确认） | 真机验证：脚本默认 `REDACTED_CORE_DEVICE_ID` 同时被 `devicectl` 与 mobilebuildmcp 接受；`devicectl list devices` 显示的是另一套硬件 UDID。文档统一称 CoreDevice ID |
| P2-9 停止上报无模板 | 接受 | workflow 增加“阻塞报告”5 行模板 |

安全提醒：计划内绝对路径已脱敏；`actions/checkout@v4` pin SHA 低风险，待可查证 SHA 后再改。

### 修复后验证

- `PYTHONDONTWRITEBYTECODE=1 make check-all` → PASS；34 篇文档、157 条链接；token：AGENTS 1962/2000、contracts 792/800、verification 795/800、workflow 779/800；基线 `[OK]`
- `TEAM_RULES=/nonexistent make check-all` → exit 0，`[SKIP]`
- `make handoff` 自动选最新；`PLAN=<path>` 指定生效；不存在路径明确报错
- `make -n measure-launch` → `.apm/tools/measure-launch.sh 10`
- `make build` → BUILD SUCCEEDED（默认 `iPhone 17 Pro Max,OS=26.4.1`）
- `make test` → 120 passed / 0 failed
- `make test-ui` → 3 executed / 1 skipped（模拟器语音能力，预期）/ 0 failed
- `make device-test` → warmup 5 passed；all 123 passed / 0 failed / 0 skipped；首次真机 UI 需在设备上输入一次 XCTest 授权密码

### 剩余风险

- AGENTS 余量 45 tokens、contracts 余量 8 tokens；后续编辑先跑 `make check`，超预算即失败。
- `.apm/plans/` 与 `.apm/reviews/` 未提交；提交后 docs CI 才能在干净 checkout 验证链接。
