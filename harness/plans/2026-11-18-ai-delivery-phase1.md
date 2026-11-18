---
id: 2026-11-18-ai-delivery-phase1
status: active
level: L2
owner: david
updated: 2026-11-18
scope:
  allow:
    - harness/plans/2026-11-18-ai-delivery-phase1.md
    - Makefile
    - tools
    - harness/config.json
    - harness/fixtures
    - harness/records
    - harness/reviews
    - harness/evidence
    - docs/01-product-design.md
    - docs/02-architecture.md
    - docs/03-tech-choices.md
    - docs/04-roadmap.md
    - docs/README.md
    - docs/decisions.md
    - references
    - Duiyi/Services/AGENTS.md
    - .github/workflows
    - harness-kit
    - .harness-manifest.json
    - .gitignore
  deny:
    - harness/plans/_archive
    - harness/evidence/_archive
    - openspec/changes
    - openspec/specs
    - Duiyi/Domain/
    - Duiyi/Features/
    - Duiyi/Services/**/*.swift
    - DuiyiTests/
    - DuiyiUITests/
    - Duiyi.xcodeproj/
    - AGENTS.local.md
    - .env
    - "*.p12"
    - "*.mobileprovision"
acceptance:
  - 外部 toolchain v0.2.0 annotated tag 是前置依赖；本计划只验收宿主 PIN 校验 tag object、peeled commit、source tree 与 vendored 文件哈希，不把外部仓自测当宿主证据
  - 宿主 `make delivery-check` 与 `make delivery-check-fixtures` 可在隔离 fixture 上正校验完成、负校验 0/0、嵌套复选框、未完成任务 archive、scope 越界、缺/陈旧证据、review 过期、CI 未配置却声明 PASS 全部非零退出
  - 新增 Change Record 适配：`harness/records` 的 `tasksSource: openspec` 只引用 tasks，不复制任务状态；`check_plan`/`brief`/`resume` 能读取 Record，0 active plan + 1 Record 可恢复；tasks/ledger 冲突、第二任务清单、指针 tasks 均 fail-closed，有正负 fixture
  - 仓库固定 `tools/openspec` 版本 2.1.0 并校验 tarball/commit 哈希；Makefile 与文档不再依赖全局裸命令
  - manifest schema v2 记录脱敏 build settings 与完整 argv；单点篡改被拒绝，旧 schema 只在 legacy 上下文接受；新证据从 clean commit 重生成
  - check_plan 修复为 closure + 父提交 scope 语义，不再用“计划文件同批即拒”误杀正常提交，也不靠归档路径缺失降级；kit 与宿主导入一致，正负 fixture 覆盖同批放宽与越权 closure
  - review 与 CI 具机器可读字段：review 覆盖 Base..Head 且 P0/P1 关闭；CI required 时校验 run/attempt/commit/jobs，不适用时有结构化 reason，拒绝 static 冒充动态
  - docs/01–03、references/contracts.md、Duiyi/Services/AGENTS.md 的 P1-2 旧行为/规则更新；docs 计数只引用 verification.md
  - Claude Code 通过新会话实际调用验证可发现 openspec 与 superpowers；QoderCN 使用相同文件源或明确记录不支持自动发现
  - 最终 `make kit-check`、`make verify-static`、`make release-check` PASS；所有工具冻结后 unit/UI 证据重新生成且 fresh/strict；不创建任何原生 L2 Change
verify:
  - make kit-check
  - make delivery-check-pin
  - make delivery-check-fixtures
  - make doctor-skills
  - make verify-static
  - make release-check
  - tools/openspec validate --archived --json
---

# 2026-11-18 · AI Delivery Phase 1（L2）

> 目标：完成首个原生 OpenSpec L2 Change 前必须落地的工具、证据与文档能力。本计划不创建原生 Change。
> 上游：P0 已归档；目标态仍为“有条件通过”，见 [`../../docs/case-native-openspec-delivery.md`](../../docs/case-native-openspec-delivery.md)。

## 目标与非目标

- **目标**：把 `delivery-check`、Change Record、固定 wrapper、manifest build settings、done 门禁、review/CI schema 和文档收尾做到可执行、可重算、可回滚。
- **非目标**：不实现业务 Change；不改业务 Swift；不改历史证据/归档计划；不修改目标态规范中 1–13 节；不运行 OpenSpec archive；不提交/推送外部仓或 tag（另行确认）。
- **原则**：外部仓独立计划与 tag；宿主只 pin 与薄适配；所有校验 fail-closed；证据必须来自 clean 提交并可由原始产物重算。

## 外部依赖与跨仓边界

- 外部仓：`/Users/tanwei/Documents/code/ios/ai-delivery-toolchain`，当前 `v0.1.0`，无 delivery-check。
- 外部仓必须在自己的获批 L2 计划中交付 `delivery-check` 与负向 fixtures，并打 annotated `v0.2.0`；宿主验收只看 tag/PIN/哈希/集成行为，不把外部仓测试结果当宿主证据。
- 外部 tag、宿主 pin 更新、外部仓提交均需用户单独确认；未固定前不得创建首个原生 Change。

## 改动范围

- **允许**：本计划、Makefile、tools、指定 harness 配置/夹具/记录/审查、指定 docs/references、Services AGENTS、CI workflow、harness-kit 源与 manifest 元数据。
- **禁止**：业务代码与测试；`.xcodeproj`；签名/凭证；`AGENTS.local.md`；`openspec/changes/` 与 `openspec/specs/`；历史归档计划/证据。
- **规范冻结**：`docs/case-native-openspec-delivery.md` 的第 1–13 节只读；实现冲突先停并上报，不得改规范迁就实现。

## 实施步骤

1. **计划门禁与基线**：先修本计划正文/未提交/verify 占位；建立隔离 fixture 根（`harness/fixtures/`，不是 active Change）；记录当前 0 active、0 OpenSpec change 与 P0 归档事实。
2. **外部 delivery-check（独立仓 L2）**：在其计划中实现 Contract/tasks 解析、任务复选框唯一性、apply/`all_done`、scope Base..HEAD + 工作树、evidence 绑定、acceptance 映射、review 范围、CI 策略、archive gate；负向 fixture 必须覆盖 0/0、嵌套复选框、未完成任务 archive、缺字段、越界、陈旧/缺 artifact、review 过期、CI 假 PASS；打 annotated `v0.2.0`。
3. **变更记录适配**：在 `harness/records/` 定义 `tasksSource: openspec` 的 Change Record schema；让 `check_plan`、`tools/harness.py brief/resume` 读取 Record，fixture 验证“0 active plan + 1 Record”可恢复；tasks 是唯一状态，记录不复制复选框；tasks/ledger 冲突与第二任务清单 fail-closed（ledger 完整适配延后 Phase 3）。
4. **宿主集成**：更新 PIN（annotated tag object、peeled commit、source tree、文件哈希、远端）；新增 `make delivery-check-pin`；vendor `delivery-check`；新增 `tools/delivery_check.py` 薄适配和 `make delivery-check`/`make delivery-check-fixtures`；只从 Contract 读取必需 claims，CLI 不接受省略降级；固定 `tools/openspec` wrapper（2.1.0 tarball URL、sha512、Node 最低版本与离线 fail-closed）并统一 Makefile/文档命令。
5. **manifest v2**：定义 `command.buildSettings`（`source`、有序 entries、sha256）；明确脱敏 allowlist（仅 `OTHER_SWIFT_FLAGS`、`CODE_SIGNING_ALLOWED` 等非敏感项），拒绝 team/profile/UDID/绝对路径；完整 argv 与哈希统一；拒绝重复/空/换行项；schema v1 仅 `_archive` 或显式 legacy 读取；迁移测试；新证据从 clean commit 重生成。
6. **check_plan 修复**：在 `harness-kit` 源实现 closure + 父提交 scope 语义；closure 只允许计划文件 + 过程路径，必须在 submitted 之后；同批放宽 allow、closure 改 tools/Makefile/Duiyi、evidence commit 等于 closure 均拒绝；同步宿主副本、VERSION/CHANGELOG/config/manifest 的 kitVersion、增加 host-vs-kit 文件哈希测试；`make kit-check` 与 `make kit-drift` 或记录镜像豁免；镜像 publish/tag 另行确认。
7. **review / CI / 文档 / 技能**：定义 review schema（`Base`、`Head`、reviewer、P0/P1 状态、结论）与 CI 策略（`required`、reason、expires、workflow、run/attempt/commit/jobs）；增加 review 过期、CI 未配置却声明 PASS 负向；更新 01–03/contracts/Services AGENTS 的 P1-2 现状；增加 `make doctor-skills`：真实 HOME + 临时 cwd 的 Claude 非交互调用，使用临时 HOME 时先复制软链，断言 Skill 实际调用；QoderCN 只记录可验证事实。
8. **冻结与收尾**：工具冻结后在 clean 提交重生成 unit/UI 证据；跑 PIN/fixtures/doctor-skills/kit-check/verify-static/release-check；独立复核；归档本计划需单独确认；不创建原生 Change。

## 改动边界与回滚

- **工具误放宽**：负向 fixture 与 archive gate 任一失败即停止，不写证据。
- **schema 迁移**：先加 v2 读写与 v1 legacy 测试，再迁移新证据；回滚需同时回退 pin、adapter、schema 和证据，禁止只回退代码。
- **check_plan 回滚**：保留旧行为测试；不以 feature flag 作为旁路，修复仅在测试可见的 legacy 参数被禁止。
- **pin 回滚**：保留 v0.1.0 tag 与 PIN 历史；不删除旧证据；回滚后重新验证 fresh/strict。
- **文档越界**：任何需要改规范 1–13 节或业务代码的需求，先更新本计划并重新获批。

## 进度

- [x] 环境：Claude Code 已安装 `openspec` / `superpowers` 用户级软链；仅完成存在性检查，实际调用待步骤 7。
- [x] P0 已完成归档；本计划是唯一 active 计划；0 active OpenSpec Change。
- [ ] 本计划门禁自检通过（正文验收、未提交声明、fixture 命令可执行）。
- [x] toolchain v0.2.0 + annotated tag（外部独立计划；`084925f`，62 tests）。
- [x] 宿主 PIN/固定 OpenSpec wrapper/`tools/delivery_check.py` 薄入口；`make delivery-check-pin` PASS。
- [ ] Change Record `tasksSource: openspec` 适配与 fixtures。
- [ ] manifest v2 + 新证据重生成。
- [ ] check_plan closure/父提交 scope + kit 同步。
- [ ] review/CI schema、文档、技能实际调用。
- [ ] 最终全量门禁与 Phase 1 交接；不创建原生 Change。

## 验收

- [ ] 外部 v0.2.0 tag 与宿主 PIN 可验证；不采用未固定工作树。
- [ ] `make delivery-check-fixtures` 正例通过、所有负向非零退出。
- [ ] Change Record 只引用 tasks，冲突/第二任务清单/指针 tasks 均拒绝。
- [ ] `tools/openspec` 固定 2.1.0；Makefile/文档不再使用裸命令。
- [ ] manifest v2 记录脱敏 build settings；单点篡改拒绝；旧证据只按 legacy 读取。
- [ ] check_plan closure + 父提交 scope 正负 fixture 全过；宿主与 kit 文件哈希一致。
- [ ] review/CI 结构化字段可机检；CI 未配置不得声称 PASS。
- [ ] docs/01–03、contracts、Services AGENTS 的 P1-2 旧描述已更新。
- [ ] Claude Code 临时 HOME/实际调用可发现两个技能；QoderCN 事实有记录。
- [ ] 工具冻结后 unit/UI 证据重生成；`make kit-check`/`verify-static`/`release-check` PASS。
- [ ] 未创建任何原生 L2 Change。

## 验证证据

| 命令 | 结果 | 环境 | 证据ID |
| --- | --- | --- | --- |
| `ls -l ~/.claude/skills/openspec ~/.claude/skills/superpowers` | PASS：两处用户级软链存在 | 本机 macOS；Claude Code 2.1.310 | —（过程记录：环境前置） |
| `make kit-check` | 待实现后运行 | 本机 macOS；python3 | —（未验证） |
| `make delivery-check-fixtures` | 待实现后运行 | 本机 macOS；python3 | —（未验证） |
| `make verify-static` | 待实现后运行 | 本机 macOS；python3 | —（未验证） |
| `make release-check` | 待实现后运行 | 本机 macOS；python3 | —（未验证） |
| `tools/openspec validate --archived --json` | 待实现后运行 | 本机 macOS；OpenSpec 2.1.0 | —（未验证） |

## 未验证项

- 外部 delivery-check v0.2.0 已实现并固定；宿主 Change Record、fixtures、manifest v2、check_plan 修复仍未实现。
- Claude Code 技能尚未做全模型实际调用验证；实现 `make doctor-skills` 后移除本项。
- 真机 UI 正式证据：沿用 P0 书面豁免，本计划不声称已验证。
- 真实 ShareLink/ShareSheet：沿用 P0 书面豁免，本计划不声称已验证。
- GitHub Actions 动态 macOS unit/UI：沿用 P0 书面豁免，本计划不声称已验证。

## 未验证豁免（done 前有未验证项时必须填）

| 项目 | 理由 | 负责人 | 到期日 |
| --- | --- | --- | --- |
| 真机 UI 正式证据 | 沿用 P0 2026-11-17 书面豁免；证书信任属本机环境 | david | 2026-12-31 |
| 真实 ShareLink/ShareSheet | 沿用 P0 2026-11-17 书面豁免；外部扩展行为待人工验收 | david | 2026-12-31 |
| GitHub Actions 动态 macOS unit/UI | 沿用 P0 2026-11-18 书面豁免；本计划只处理 CI 策略与本地证据 | david | 2026-12-31 |

## 未提交改动

- 无未提交改动；Phase 1 工具、记录、fixtures 与文档随本检查点提交。

## 下一步

1. 先让本计划通过 `make check-plan-strict`，并完成第二轮独立红队复核；未确认前不实现工具或修改外部仓。
2. 建立外部 toolchain 的独立 L2 计划，获批后实现 delivery-check 与负向测试，固定 annotated v0.2.0。
3. 再执行宿主适配、manifest/证据重生成、check_plan 修复、文档/CI 收尾；全绿后另行批准首个原生 L2 Change。
