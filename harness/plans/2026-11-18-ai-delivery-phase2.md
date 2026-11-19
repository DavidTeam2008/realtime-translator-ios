---
id: 2026-11-18-ai-delivery-phase2
status: active
level: L2
owner: david
updated: 2026-11-19
scope:
  allow:
    - harness/design/
    - harness/plans/
    - harness/records/
    - harness/fixtures/
    - harness/evidence/
    - harness/receipts/
    - harness/reviews/
    - harness/superpowers-overlay.md
    - harness/config.json
    - tools/
    - Makefile
    - references/
    - docs/decisions.md
    - docs/04-roadmap.md
    - docs/README.md
    - .harness-manifest.json
    - .gitignore
    - .dsh/skills/
    - openspec/config.yaml
    - AGENTS.md
    - .workbuddy/
  deny:
    - harness/plans/_archive/
    - harness/evidence/_archive/
    - openspec/changes/
    - openspec/specs/
    - Duiyi/
    - DuiyiTests/
    - DuiyiUITests/
    - Duiyi.xcodeproj/
    - .githooks/
    - .github/workflows/
    - AGENTS.local.md
    - .env
    - "*.p12"
    - "*.mobileprovision"
acceptance:
  - "红基线修复：`make delivery-check-fixtures` 改为 hermetic fixture，正例 PASS、负例非零；provenance 正负 fixtures 与 v0.4.0 同步在步骤 5 新增"
  - "外部 ai-delivery-toolchain `v0.3.1`（版本卫生 + discipline pin + 确定性 release manifest）annotated tag 固定；宿主 PIN 含 tag/commit/tree/逐文件哈希；`make delivery-check-pin` 离线 PASS"
  - "宿主 discipline 最小接入：`delivery.discipline.required=true`；v0.3.0/v0.3.1 discipline receipt 正负 fixture 可校验；缺 receipt/红绿颠倒/错 task 非零"
  - "外部 `v0.4.0`（provenance + contract lint + skill receipts + skills manifest + offline + discipline v2 红绿字段）annotated tag 固定；宿主 PIN 更新"
  - "宿主最小回执：scaffold / instructions / clarification / validate / skill-receipt 五类 + discipline 校验，落 `harness/receipts/`，tracked、hash/commit 绑定；缺回执/哈希不符/validate 后改工件非零"
  - "全量契约 lint L1–L11 在 `delivery-check` 中启用：ERROR 级硬失败；v0.4.0 中 L3 措辞、L5 任务数、L6 Covers 缺失、L11 澄清仍为 WARN，由 `change-lint` 展示并在 review 核对；WARN→ERROR 升级登记为后续增量，不声称已完成"
  - "OpenSpec prompt 源与 overlay：`openspec/config.yaml` 增加 artifact rules/context 与 `Covers: R/S` traceability；仓库内 Superpowers overlay 明确 brainstorming 不写第二份 plan、tasks.md 唯一状态；overlay hash 纳入 skill receipt 并由 `delivery-check` 复算；dry-run 不生成 `docs/superpowers/plans`"
  - "一个真实 L2 试点：使用新流程完成一个真实行为变更（用户确认 Change/计划），provenance + 4 条 lint + skill/discipline receipts + evidence + review 全链 PASS；archive 单独确认"
  - "不改业务 Swift/既有测试断言（试点变更除外，且按 L2 流程审批）；不创建第二计划/ledger；不 auto commit/push/tag"
  - "门禁：`make delivery-check-fixtures`、`make delivery-provenance-fixtures`、`make delivery-check-pin`、`make verify-static`、`make release-check` 全绿；改动 `tools/**` 后 unit/UI 证据重跑，不接受 waiver 替代"
  - "后续增量登记：pre-commit、Record v2、doctor-delivery、portfolio、剩余 7 条 lint、CI job、light 模式明确排期/负责人，不在本计划声称完成"
  - "计划门禁：`make check-plan` 与 `make check-plan-strict` PASS（active 计划未提交改动已声明）"
verify:
  - make delivery-check-fixtures
  - make delivery-provenance-fixtures
  - make delivery-check-pin
  - python3 tools/check_plan.py check --strict
  - make check-docs
  - make verify-static
  - make release-check
  - tools/openspec list --json
---

# 2026-11-18 · AI Delivery Phase 2（L2）：最小回执 + 试点

> **状态**：2026-11-19 用户确认收窄：先做「回执 + 契约 lint + 一个真实 L2 试点」；同日用户选 A，lint 采用 v0.4.0 全量 L1–L11（ERROR 硬失败、WARN advisory），不再收窄为 4 条。其余 pre-commit/Record v2/doctor/portfolio 后置为增量。
> **外部依赖**：DD-5 拆为 v0.3.1（版本卫生 + discipline pin）与 v0.4.0（provenance/lint/skill/offline）；两版均需外部仓独立计划、测试、annotated tag 与用户确认。
> **设计输入**：[目标态设计](../design/2026-11-18-ai-delivery-governance-target.md)；评审输入见 `harness/reviews/`。
> **分级**：L2；执行前需关闭「复核处置」中的 P0/P1。

## 目标与非目标

- **目标**：用最小增量把 OpenSpec/Superpowers 变成可机检的原生参与：先修红基线，再 pin v0.3.1/v0.4.0，落最小回执 + 全量契约 lint（L1–L11）+ OpenSpec prompt 源/overlay，最后用一个真实 L2 试点验证全链。
- **非目标**：本增量**不做** pre-commit、Record v2、doctor-delivery、portfolio、lint WARN→ERROR 升级（L3/L5 数量/L6 Covers 缺失/L11）、CI job、light 模式；不创建第二计划/ledger；不重写历史工件；不做平台/后端。
- **顺序原则**：红基线修复 → 外部 v0.3.1 → 宿主纪律回执 → 外部 v0.4.0 → 宿主最小接入 → 试点；每一步不过门禁不进入下一步。

## 约束与假设

- **Bootstrap 例外**：本计划自身是引导性 L2，不在 Phase 2 创建 OpenSpec Change；D-AI11 的“下一个 L2 用 tasks.md”从试点（Phase C）起生效。
- **Duiyi mode**：本期只落 `delivery.mode: full`；单人项目默认 light 在 P3 生效。
- **外部仓**：v0.3.1/v0.4.0 在外部仓独立计划完成；宿主只 pin 与集成，不把外部测试当宿主证据。
- **信任边界**：回执是自述性过程证据；本增量不接 CI，最终锚是“后续 hooks + 人工 review”，不宣称 CI 门禁已成立。
- **范围收窄**：任何“顺手把剩余 lint/Record/doctor 做了”的冲动都先停下，登记后续增量。

## 实施步骤

0. **红基线修复（最终评审 P0-A）**：把 `make delivery-check-fixtures` 改成 hermetic fixture（临时 git 仓，不依赖本仓历史/deny 路径）；provenance fixtures 与 v0.4.0 同步在步骤 5 新增。
1. **计划门禁与基线**：跑 `check-plan`/`check-plan-strict`；记录 HEAD、`make check`、当前 fixture 红基线、PIN v0.2.0、0 active changes；CLI surface spike（new change/instructions --json 双跑一致）作为设计依据，正式 evidence 待补。
2. **外部 v0.3.1（另一仓）**：版本卫生（pyproject/CLI/__version__ 一致）、discipline pin、确定性 release manifest；全量测试；annotated tag `v0.3.1`；发布清单；用户确认 tag/push。
3. **宿主 pin v0.3.1 + discipline 最小接入**：更新 vendor/PIN；`delivery.discipline.required=true`；fixtures 覆盖缺 receipt、红绿颠倒、错 task/change；不引入 pre-commit。
4. **外部 v0.4.0（另一仓）**：provenance、contract lint（全量实现、宿主本期只启用 4 条）、skill receipts + manifest、discipline v2 红绿字段、offline、release manifest；全量测试；annotated tag `v0.4.0`；用户确认 tag/push。
5. **宿主最小接入**：pin v0.4.0；新增 `tools/delivery_receipts.py` + Make 目标；回执落 `harness/receipts/`（tracked、hash/commit 绑定，artifact 用 .json/.txt）；delivery-check 启用 provenance + 全量 L1–L11（ERROR 硬失败）+ skill/discipline；新增 `delivery-provenance-fixtures`/`delivery-skills-fixtures` 正负样例；补 `openspec/config.yaml` rules/context + `Covers: R/S`；加 Superpowers overlay（brainstorming 不写 plan、tasks.md 唯一状态、overlay hash 入 skill receipt 并由宿主复算）。
6. **一个真实 L2 试点（Phase C）**：用户选小行为变更；按新流程走 scaffold/instructions/validate/lint/skill/TDD/evidence/review；记录首次门禁通过率、返工、回执覆盖率、人工干预；archive 单独确认；失败按 blocked 回滚。
7. **收尾与增量登记**：更新证据/计划/决策；列出后续增量（pre-commit、Record v2、doctor、portfolio、剩余 7 条 lint、CI、light）与负责人/时点；冻结 PIN，提交/push 单独确认。

## 验收

- [x] 红基线修复：`delivery-check-fixtures` 正例 PASS、负例非零（hermetic 临时仓）；provenance fixtures 与 v0.4.0 在步骤 5 同步。
- [x] v0.3.1 annotated tag/发布清单/宿主 PIN 一致；`make delivery-check-pin` PASS（2026-11-19）。
- [x] v0.4.0 annotated tag/发布清单/宿主 PIN 更新；`make delivery-check-pin` PASS（2026-11-19）。
- [x] discipline 最小接入正负 fixture 通过；`delivery.discipline.required=true` 缺 receipt fail-closed。
- [x] 五类回执 + discipline 校验可用；provenance 正负样例全绿；缺回执/哈希不符/validate 后改工件/错 task 非零（2026-11-19）。
- [x] 全量 L1–L11 在 delivery-check 中启用；contract-lint failure fixture 非零；WARN 级（L3/L5 数量/L6 Covers 缺失/L11）为 advisory 并经 change-lint/review 核对（2026-11-19）。
- [x] OpenSpec config rules/context + traceability 生效；Superpowers overlay 存在且 hash 入 skill receipt 并由宿主复算；dry-run 不生成 `docs/superpowers/plans`（2026-11-19）。
- [ ] 一个真实 L2 试点全链 PASS（或 blocked + 回滚记录）；archive 单独确认。
- [x] 后续增量有清单、建议负责人与时点；不在本计划声称完成（建议值待用户确认）。
- [x] `delivery-check-fixtures`/`delivery-receipts-fixtures`/`delivery-skills-fixtures`/`delivery-check-pin`/`verify-static`/`release-check` 全绿；`check-plan --strict` PASS（2026-11-19）。
- [x] 不创建第二计划/ledger；不改历史工件；commit 均经用户确认后执行，未 auto commit/push/tag。

## 进度

- [x] 设计输入与 Phase 2 收窄版计划落盘（2026-11-19）。
- [x] 步骤 0 红基线修复：`make delivery-check-fixtures` 改为 hermetic 临时仓，正例 0 / 负例非零（2026-11-19）。
- [x] 外部 v0.3.1：版本卫生 + discipline pin + release manifest（commit `03ffa74`，tag `v0.3.1`，2026-11-19）。
- [x] 宿主 pin v0.3.1 + discipline 最小接入（PIN/vendor/delivery_check/config + fixtures，2026-11-19）。
- [x] 宿主 pin v0.4.0：vendor 18 py + skills manifest + PIN；provenance/contractLint/skills profile 透传（2026-11-19）。
- [x] 外部 v0.4.0：provenance/lint/skills/offline（commit `b3a7098`，tag `v0.4.0`，2026-11-19）。
- [x] 宿主回执生成器（scaffold/instructions/validate/clarification/skill-receipt）+ provenance 正/负 fixture（2026-11-19）。
- [x] 全量 lint 接入（v0.4.0 L1–L11；ERROR 硬失败 / WARN advisory）+ OpenSpec config/overlay + skill/clarification 负例（2026-11-19）。
- [x] 步骤 5 回执/lint/config/overlay 完成；收口门禁 fixtures / pin / receipts / skills / verify-static / check-plan-strict PASS；unit/UI 证据已在 clean commit 上重跑（2026-11-19）。
- [x] 步骤 5 门禁全部 PASS：`make verify-claim`（3 PASS / 0 FAIL / 0 UNVERIFIED）与 `make release-check` 在 clean commit `f3f3336` 上 PASS（2026-11-19）。
- [ ] 一个真实 L2 试点 + 后续增量登记。

## 验证证据

| 命令 | 结果 | 环境 | 证据ID |
| --- | --- | --- | --- |
| `make check` | PASS：既有静态门禁基线（2026-11-18，0 active plan） | 本机 macOS；kit 0.5.5 | —（过程记录） |
| `make delivery-check-fixtures` | PASS：hermetic 临时 git 仓正例 0；zero-tasks / discipline / contract-lint failure 均非零（2026-11-19） | 本机 macOS；Python 3.14 | —（过程记录） |
| OpenSpec CLI spike（new change/instructions --json） | PASS（过程记录）：均 exit 0；proposal 双跑 sha256 一致 | 本机 macOS；OpenSpec 2.1.0 | —（未验证） |
| 最终方案评审（Claude Code + DeepSeek V4.1 Flash） | 完成：有条件合理；P0×4 / P1×8 / P2×6 | 本机 | —（外部） |
| 两轴试跑 / 执行器对照 | 完成：A 629s、B 225s；B 未跑门禁漏 P0 | 本机 | —（外部） |
| `make delivery-check-pin` | PASS：v0.3.1 → `03ffa74`；vendored 11 文件哈希一致 | 本机 macOS | —（过程记录） |
| `make delivery-check-fixtures` | PASS：positive=0、zero-tasks!=0、discipline-required-missing!=0 | 本机 macOS | —（过程记录） |
| `make delivery-discipline-fixtures` | PASS：positive=0、tampered!=0 | 本机 macOS | —（过程记录） |
| `make delivery-check-pin` | PASS：v0.4.0 → `b3a7098`；vendored 19 文件（含 skills manifest）哈希一致 | 本机 macOS | —（过程记录） |
| `make delivery-receipts-fixtures` | PASS：五类回执生成 + provenance 正例 + validate 后改工件/缺 receipt 负例 + L11 澄清 + L10 第二计划（2026-11-19） | 本机 macOS；Python 3.14 | —（过程记录） |
| `make delivery-skills-fixtures` | PASS：skill receipt 绑定 overlay；宿主 skill 篡改/错 task/overlay 失效/缺 task receipt 全部拦截（2026-11-19） | 本机 macOS | —（过程记录） |
| `make delivery-check-pin` | PASS：v0.4.0 → `b3a7098`（2026-11-19 复跑） | 本机 macOS | —（过程记录） |
| OpenSpec config 注入验证（scratch） | PASS：instructions proposal/tasks 均包含 context 与 artifact rules（2026-11-19） | 本机 macOS；OpenSpec 2.1.0 | —（过程记录） |
| `make verify-static` | PASS：332 kit tests + 宿主静态门禁（2026-11-19） | 本机 macOS；Python 3.14 | —（过程记录） |
| `make evidence-unit WRITE=1` | PASS：139 passed / 0 failed / 0 skipped；证据 `20261119T042907Z-unit-tests-pass`，artifact+manifest tracked | 本机 macOS；iPhone 17 Pro Max / iOS 26.4.1 | 20261119T042907Z-unit-tests-pass |
| `make evidence-ui WRITE=1` | PASS：2 passed / 0 failed / 1 skipped；证据 `20261119T043007Z-ui-tests-pass`，artifact+manifest tracked | 本机 macOS；iPhone 17 Pro Max / iOS 26.4.1 | 20261119T043007Z-ui-tests-pass |
| `make verify-claim` | PASS：3 条当前证据（docs/unit/UI）全部 PASS；UI 证据 `20261119T043007Z-ui-tests-pass`；归档 16 条 SUPERSEDED；0 FAIL / 0 UNVERIFIED（2026-11-19） | 本机 macOS；Python 3.14 | 20261119T042907Z-unit-tests-pass |
| `make release-check` | PASS：verify-static + verify-claim + scorecard + plan strict（commit `f3f3336`，2026-11-19） | 本机 macOS；Python 3.14 | —（过程记录） |
| 契约格式兼容验证（scratch） | PASS：Delivery Contract + `### Task N:` 复选框通过 `validate --strict`；全量 lint issues=[]；apply 全勾选后 state=all_done | 本机 macOS；OpenSpec 2.1.0 + v0.4.0 lint | —（过程记录） |
| `make change-lint` smoke（临时 change，已清理） | PASS：L1/L2/L4 ERROR + L11 WARN 输出；退出非零 | 本机 macOS；v0.4.0 lint | —（过程记录） |

## 复核处置（2026-11-19 最终评审）

| ID | 问题 | 处置 |
| --- | --- | --- |
| P0-A | delivery-check-fixtures 红基线 | 步骤 0 修复；验收首项 |
| P0-B | 原生 skill 与单一任务状态冲突 | 已落 `harness/superpowers-overlay.md` + repo skill；overlay hash 入 skill receipt 并由 delivery-check 复算；L10 dry-run fixture 覆盖（2026-11-19） |
| P0-C | OpenSpec prompt 源未配置 | 已落 `openspec/config.yaml` context/rules/operations；instructions 实测注入（2026-11-19） |
| P0-D | 门禁链不完整（CI/pre-commit） | 本期不做；登记后续增量，不声称 CI 门禁已成立 |
| P1 | 回执 log 被忽略 | 步骤 5 用 .json/.txt |
| P1 | P0-1 无 evidence ID | 步骤 1 补 tracked evidence，或保持 UNVERIFIED |
| P1 | B 默认执行器风险 | DD-7 风险分层：工具/CI/配置变更默认 A 或 gate-runner |
| P1 | 宿主 skill 入口未 pin | 已落 overlay + repo skill；skill receipt 绑定固定 source/hostSkill/overlay；CI 只验 source |
| P1 | doctor 离线判据 / DD-5 一次发布 | doctor 后置；DD-5 已拆 v0.3.1/v0.4.0 |
| P1 | traceability 语法 / 过度设计 | `Covers: R/S/A#` 写入 config rules；本期启用 v0.4.0 全量 L1–L11，WARN 级为 advisory |

## 风险与回滚

- **红基线未修**：不进入 PIN；fixture 失败先停。
- **外部版本不一致**：不 pin；保留旧 tag/PIN 历史。
- **试点失败**：Change Record 标 blocked，保留 tasks/补丁；不降级门禁。
- **回滚**：按 PIN → adapter → config → schema → 证据顺序；回滚后 fixtures 仍须 PASS。
- **范围漂移**：要做 WARN→ERROR/Record/doctor 时先停，登记后续增量。

## 后续增量（不计入本计划完成）

| 增量 | 内容 | 建议负责人 | 建议时点 |
| --- | --- | --- | --- |
| lint severity | L3/L5 任务数/L6 Covers 缺失/L11 的 WARN→ERROR 升级 + profile 语义落地 | lead | P3 前 |
| pre-commit | 回执存在性/哈希快速校验，命中 Change scope 才拦截 | lead | P2B2 |
| Record v2 | provenance/skills/discipline/lint 字段追加（只增不复制任务状态） | lead | P2B2 |
| doctor-delivery | PIN/技能发现/回执能力/offline 判据自检 | lead | P2B2 |
| portfolio | 多项目只读聚合与升级检查 | lead | P3 |
| CI job | 干净 checkout 复算 `verify-static` + delivery-check | lead | P2B2 |
| light modes | full/light-spec/light-agent 与 L2 mode_waiver | lead | P3 |
| 外部仓 push | v0.3.1/v0.4.0 tag 推送（外部仓暂无 remote） | lead | 用户提供 remote 后 |

## 未验证项

- P0-1 正式 evidence 未补（当前过程记录）。
- 真实 L2 试点未开始；试点通过前不能声称全链已成立。
- lint WARN 级（L3/L5 任务数/L6 Covers 缺失/L11）尚未升为 ERROR；当前由 change-lint 展示 + review 核对。
- CI/pre-commit/Record v2/doctor/portfolio/light 模式均后置未实现。
- 真机/UI/性能不在本计划范围。

## 未提交改动

- 无（2026-11-19 门禁收尾；本计划提交后工作树 clean）。

## 下一步

1. 用户选一个真实小行为变更作为 L2 试点，确认 Change 与执行计划后进入步骤 6。
2. 试点按 scaffold/instructions/validate/lint/skill/TDD/evidence/review 全链执行；archive 单独确认。
3. 试点结束后登记后续增量（WARN→ERROR、pre-commit、Record v2、doctor、portfolio、CI、light）的最终负责人与时点。
4. 任何 push/tag/archive 每次单独确认；commit 按改动批次确认。

## 待确认

- 真实试点选哪个小行为变更（建议用户指定；需用户确认 Change/计划）。
- v0.3.1/v0.4.0 tag/push 时点与确认方式（外部仓暂无 remote）。
- 后续增量（WARN→ERROR、pre-commit、Record v2、doctor、portfolio、CI、light）负责人与时点。