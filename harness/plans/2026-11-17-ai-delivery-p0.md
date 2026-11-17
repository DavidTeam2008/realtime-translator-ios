---
id: 2026-11-17-ai-delivery-p0
status: active
level: L2
owner: david
updated: 2026-11-17
scope:
  allow:
    - docs/decisions.md
    - docs/04-roadmap.md
    - references/verification.md
    - openspec/
    - harness/
    - tools/
    - Makefile
    - .github/workflows/verify.yml
    - Duiyi/Services/Export/TranscriptExportService.swift
    - Duiyi/Features/Shared/ExportShareButton.swift
    - DuiyiTests/
    - DuiyiUITests/
  deny:
    - harness-kit/
    - Duiyi.xcodeproj/
    - Duiyi/Services/Speech/
    - Duiyi/Services/Translation/
    - Duiyi/Services/Persistence/
    - AGENTS.local.md
    - .env
acceptance:
  - OpenSpec Change `fix-transcript-export` 通过固定版本工具校验；Harness 是唯一执行计划，不新增竞争的 tasks/plan 真源
  - 导出回归覆盖译文更新后重新准备、连续分享不删在读快照、只清理过期文件；新增测试先红后绿且既有断言不变
  - 真实单元与 UI xcresult 均转换为 JUnit 并生成 Harness evidence，计数可独立重算；unit/ui 新证据 `requireArtifact=true`
  - 缺失/损坏 xcresult、JUnit 计数不符、无 artifact 自报 PASS 均被拒绝；CI macOS 测试启用时上传同一 JUnit 产物
  - `make verify-static`、`make verify-all`、`make release-check`、`make test`、`make test-ui` 通过；测试总数只增不减
  - QoderCN 与 Claude Code 分别走完同一 L2 流程并记录耗时、返工、门禁结果；未实测的 Agent 不得标 PASS
  - 独立对抗审查覆盖导出并发与证据伪造路径，发现项已修复或明确记录为未验证
verify:
  - make verify-static
  - make verify-all
  - make release-check
  - make test
  - make test-ui
  - python3 tools/check_plan.py check --strict
---

# 2026-11-17-ai-delivery-p0 · AI Coding 交付链单仓试点（L2）

> 决策唯一来源：[`docs/decisions.md`](../../docs/decisions.md) D-AI1–D-AI10。
> 通用治理内核仍是 `harness-kit`；独立 `ai-delivery-toolchain` 仓拥有通用集成资产。本计划只授权当前宿主仓改动，不授权修改两个外部仓。
> 旧开源标杆计划已作为历史快照归档到 `_archive/2026-11-06-benchmark-opensource.md`，未验证限制没有改写成完成。

## 目标与非目标

- **目标**：用一个真实产品缺陷和一条真实 iOS 证据链，验证“OpenSpec 管行为契约、Harness 管执行/范围/证据、Superpowers 管执行纪律”的最小闭环。
- **产品切片**：修复 [`docs/04-roadmap.md`](../../docs/04-roadmap.md) P1-2 的导出清理竞态与译文更新后分享内容不刷新。
- **基础设施切片**：打通 `xcresult → JUnit → Harness evidence`，让新 unit/ui PASS 都能由 artifact 独立重算。
- **评价口径**：只记录机制有效性、证据完整性、流程耗时与返工，不承诺效率提升百分比。
- **非目标**：不重建全 APP OpenSpec 基线；不改 `harness-kit` 内核；不做多仓 Change Set；不实现 OC/RN 桥接；不引入 ECC 运行时、中央平台或新后端；不处理 P0-1/P0-2/P0-3。

## 契约与工件所有权

| 工件 | 唯一所有者 | 本计划约束 |
| --- | --- | --- |
| 导出外部行为 | OpenSpec Change `fix-transcript-export` | 只写用户可观察行为，不复制 `docs/01-product-design.md` |
| 执行顺序、scope、验收、证据 | 本 Harness 计划 | 引用 Change ID；不另建 Superpowers `plan.md` |
| 执行纪律 | Superpowers | 固定版本、先 spike；不作为第二份持久计划 |
| 通用转换器与 Agent 适配 | `ai-delivery-toolchain` | 独立仓独立提交；宿主只保留薄调用与配置 |
| iOS 业务规则、测试、CI、证据 | 当前宿主仓 | 不进入公共通用层 |

OpenSpec 若强制生成 `tasks.md`，只允许保留指向本计划的最小适配文件，不得复制任务状态或验收进度。PDF 所述 `superpowers-bridge` 尚未核实，未完成兼容性 spike 前不得成为依赖。

## 兼容性 spike 结论（2026-11-17）

- **OpenSpec 固定版本**：`@fission-ai/openspec@2.1.0`，源码 tag `v2.1.0`、commit `8bd4b3557b5bf1d231cd2f165b28f24e2d90a2a0`。在临时夹具以 `--tools none --scope project` 初始化，只生成 `openspec/`，不写全局技能或其他 Agent 目录。
- **最小契约已验证**：proposal / design / 单个行为 delta / 无清单 tasks 指针齐备时，`validate fix-transcript-export --type change --strict --json` 返回 `valid=true`、`failed=0`；空 Change 同命令返回 `valid=false`、退出 1。
- **执行边界**：无清单 tasks 指针不影响严格校验，但 `openspec instructions apply` 返回 `state=blocked`、`total=0`；`status.isComplete` 也不能作为交付完成判据。本计划不使用 OpenSpec apply 驱动实现，任务状态、验收和证据只由 Harness 判定。
- **Superpowers 固定版本**：`v7.0.2`、commit `22f0b463e7a5e579904dd6211a520321035526f7`。Claude Code `2.1.310` 通过临时 `--plugin-dir` 和 `--setting-sources user` 加载后，SessionStart bootstrap 可见，`superpowers:test-driven-development` 经 Skill 工具实际调用成功；未全局安装插件。`--safe-mode` 会同时禁用该显式插件，不能用于此加载路径。
- **QoderCN 边界**：上游 Superpowers 未列出 QoderCN 集成；本会话只显式读取并遵循同一固定版本的 TDD、systematic-debugging、verification-before-completion，不声称自动加载或 hook 生效。
- **不采用项**：社区 `superpowers-bridge`（审查 commit `f5d40404856ad0f4ce9eb482cbb0e28cf434411f`）强制新增 `plan.md`、任务状态和子代理流程；npm `openspec-superpowers@1.0.1` 同样生成 `docs/superpowers/plans/` 并回写 OpenSpec tasks。两者都与 Harness 单一执行真源冲突，只审查未执行、不成为依赖。OpenSpec Stores beta、全局技能、ECC 和 Superpowers 自动 worktree/commit 流程均不在本切片采用。

## 独立对抗审查收口（2026-11-17）

审查会话 `4c36f194-3aeb-5c12-adbc-90d95fe73bd7` 已完成只读最终报告，结论为 B1–B8 阻断；主会话逐项复核了报告引用的实现与门禁行号。审查未运行测试、未修改文件，不视为动态验证证据。

| ID | 已核实失败路径 | 本计划处置与解除阻断条件 |
| --- | --- | --- |
| B1 | 属性-only / 空 / 未知根 XML 可伪造计数，suite 汇总与 testcase 可不一致 | **证据链阻断**：PASS 只从 testcase 明细重算；四类负向 fixture 必须非零；legacy 证据不代表新链通过 |
| B2 | 旧 JUnit、部分运行、unit/ui 或设备环境错配可复用为本次 PASS | **证据链阻断**：唯一空 xcresult 路径 + 单次运行 manifest，绑定 claim/target/结构化命令/run ID/摘要；精确测试集合或计数，不只检查 floor |
| B3 | 后续准备删除快照；同分钟/同任务同路径会替换 URL 内容 | **产品红测试阻断**：不可变快照；A→B 后 A 字节不变，同分钟不同任务与同任务不同译文均隔离 |
| B4 | `.task(id: task.id)` 不响应译文、摘要和导出语言变化 | **产品红测试阻断**：以完整导出内容和 language 形成准备版本；同 ID 内容变化触发重新准备；真实 ShareSheet 仍单列手工验收 |
| B5 | 清理可误删非导出文件/目录；7 天与在读保护未定义 | **产品契约阻断**：专用目录、普通文件与完整文件名匹配、mtime 严格超过 7 天才清理；恰好 7 天、未来/缺失日期保留；进程内已准备 URL 永远受保护，进程重启后仅过期快照可回收 |
| B6 | `verify-all` 及当前 freshness 可接受代码/命令/转换器修改前的旧证据 | **最终验收阻断**：最终增加 `make release-check`（fresh + strict）；freshness 纳入 Makefile、工具、测试与工程测试配置，并做三类陈旧证据负向验证 |
| B7 | CI 未跑转换/三值判定，artifact 缺失被 ignore，无 UI job | **CI 验收阻断**：run ID/attempt 隔离，显式转换唯一产物，必需 JUnit 缺失即 error；UI CI 若未开启必须保持未验证 |
| B8 | 外部转换器是步骤但当前 scope 未授权外部仓 | **跨仓阻断**：先在 `ai-delivery-toolchain` 建独立获批计划并完成实现/测试/固定版本；提交或 tag 必须另行确认。未固定前宿主不得把外部工作树当证据 |

本切片对 `Duiyi/Services/AGENTS.md` 的“P1-2 未修前不改共享语义”仅作已确认的 P1-2 修复例外：仍不改变导出文本结构与系统 `ShareLink`，只修复快照、清理和内容刷新。

## 验收

- [x] 固定 OpenSpec / Superpowers 版本并完成兼容性 spike，记录实际支持能力与不采用项。
- [x] OpenSpec Change 校验通过，至少覆盖：译文更新后重新准备、连续导出/分享、过期清理边界、非导出文件不受影响。
- [x] 新增导出回归测试在修复前复现失败，修复后通过；既有测试与断言不修改。
- [x] 每次准备分享得到稳定且不可被后续导出破坏的快照；清理不再删除全部 `Duiyi-*.txt`。
- [x] 详情页任务 ID 不变但译文、摘要或导出语言变化时，导出内容仍反映最新可观察内容。
- [ ] 真实 unit/ui xcresult 转成 JUnit，证据计数由 XML 重算；单元证据 `20261117T063557Z-unit-tests-pass` 已入库，UI 被模拟器 runner preflight 阻断；旧 legacy 证据按归档/supersedes 规则迁移后再收紧 unit/ui claims。
- [ ] 缺失或损坏 xcresult、XML 计数不一致、无 artifact 的自报 PASS 都有负向测试并非零退出。
- [ ] macOS CI 测试开启时使用同一转换路径并上传 JUnit；未开启时明确标记 CI 动态链未验证。
- [ ] QoderCN 与 Claude Code 的同流程实测记录包含开始/结束耗时、人工干预、返工、门禁与证据 ID。
- [ ] 最终 `make verify-static`、`make verify-all`、`make release-check`、`make test`、`make test-ui` PASS；新增动态 PASS 均有可重算 artifact，freshness 覆盖代码、命令、转换器和测试配置。

## 改动范围

- **允许**：导出服务与分享按钮、为回归新增的测试、OpenSpec 当前 Change、宿主证据转换薄适配、相关 Makefile/CI/配置、验证记录。
- **测试约束**：只增不减；先增加红测试复现，再改实现；更新 `references/verification.md` 的真实计数。
- **禁止**：语音、翻译、持久化主链路；工程签名文件；`harness-kit`；其他业务重构；任何凭证或本机私有配置入库。
- **跨仓边界**：`ai-delivery-toolchain` 的通用实现、版本 pin 与测试在该仓单独管理；本计划不以其未提交工作树充当宿主证据。

## 实施步骤

1. **基线与对抗审查**：确认导出当前失败路径、现有 evidence/CI 接口和 Xcode 实际 xcresult 格式；独立审查导出并发与证据伪造路径。
2. **兼容性 spike**：固定 OpenSpec / Superpowers 版本，最小验证 Change 校验、执行纪律入口和适配边界；不实现臆测的 bridge schema。
3. **行为契约与红测试**：创建 `fix-transcript-export`，新增导出清理、快照稳定性、内容签名回归；保存修复前失败输出。
4. **最小产品修复**：文件名关联 task 与内容版本，快照写入避免原地破坏；清理只针对过期导出；分享准备以内容签名刷新。
5. **证据链**：先为 `ai-delivery-toolchain` 建立独立获批变更，在通用仓实现并测试 xcresult 转换及运行 manifest；固定版本后宿主接薄适配。生成真实 unit/ui JUnit 与 evidence，完成 B1/B2/B6/B7 负向验证，再迁移 legacy claims。
6. **CI 与双 Agent 验证**：复用同一命令，记录 QoderCN / Claude Code 的流程成本与差异；不以静态门禁代替动态测试。
7. **收尾**：独立复核、更新 P1-2 状态与验证计数、跑全量门禁；完成后按 `submitted + done + _archive` 流程处理。

## 导出技术约束

- 快照写入专用导出目录，文件名绑定 task UUID 与完整导出内容摘要；同内容可复用同一不可变快照，不同任务或内容不得复写同一路径，禁止依赖分钟时间或 Swift `hashValue`。
- 清理仅匹配本服务生成的普通文件，以文件 mtime 严格超过 7×24 小时为过期；恰好 7 天、未来时间、元数据缺失均保留。进程内已准备 URL 加入保护集，即使过期也不由后续准备删除；进程重启后只允许回收未被新进程准备的过期快照。
- 分享准备版本由完整导出内容和 language 计算；同 task.id 的译文、摘要或语言变化均产生新版本。`ShareLink` 没有可靠完成回调，不虚构分享完成事件，真实 ShareSheet 读取仍须单独验收。
- 不扩大为导出格式重设计，不改变现有文本内容结构与系统分享方式。

## 进度

- [x] 完成参考方案、宿主与 `harness-kit` 边界核实。
- [x] 确认 D-AI1–D-AI10，建立独立 `ai-delivery-toolchain` 仓及 3 份架构 ADR。
- [x] 归档旧 active 计划并建立本 P0 计划。
- [x] 独立对抗审查与发现项收口（B1–B8 已分阶段设门禁；不代表对应实现已完成）。
- [x] OpenSpec / Superpowers 固定版本兼容性 spike。
- [x] 导出 OpenSpec Change 与修复前红测试。
- [x] 导出最小修复与聚焦/完整单元/UI 回归。
- [x] `ai-delivery-toolchain` 实现、49 项测试、真实 8/8 转换与负向路径；固定 `v0.1.0`（tag `6a2a475`，实现 `8c45e96`）。
- [x] 宿主 vendoring + pin 校验 + 严格 JUnit/manifest 适配与 7 类负向 fixture（`make evidence-chain-check`）。
- [x] freshness 三类陈旧证据负向自检（Makefile / tools / xcodeproj）与过程目录豁免（4 类负向）。
- [x] B7 CI 工作流改为 `make evidence-unit` / `make evidence-ui`，JUnit/manifest 缺失即 error，artifact 名含 run/attempt；尚未在 GitHub Actions 实际运行。
- [x] 单元真实 xcresult → strict JUnit + manifest 生成并独立重算通过；最终证据 `20261117T071412Z-unit-tests-pass`（131/131、0 skip，runId `dc4c7d5d-802b-4f52-89a0-06a7ab9e8e5d`）来自 clean 提交 `e3f5779`。
- [x] UI 真实 xcresult：恢复模拟器环境后 `make evidence-ui WRITE=1` 通过，证据 `20261117T071338Z-ui-tests-pass`（2 passed / 1 expected skip，runId `e1fdc475-d12f-410d-951d-759d50674f28`）来自 clean 提交 `e3f5779`；真机 iPhone 13 非写入试跑 3/3、0 skip 通过，但正式 `ui-device-tests-pass` 被证书信任阻断，claim 保持可选未验证。
- [x] 新增 `ui-device-tests-pass` claim 与 `make evidence-ui-device`：预热 testmanagerd、本机 Team 签名、device destination、deviceId/deviceName 脱敏；`required:false`，不阻断无真机环境。
- [x] 新 unit/ui 证据入库、迁移 legacy claims 并收紧 `requireArtifact/requireManifest`：unit/ui 均为严格链，旧 unit/ui/device 证据归档并由新证据 `supersedes` 接管。
- [ ] 双 Agent 实测、成本记录与最终复核。

## 验证证据

| 命令 | 结果 | 环境 | 证据ID |
| --- | --- | --- | --- |
| `python3 tools/check_docs.py`（既有当前证据） | PASS：文档门禁；不代表动态测试已重跑 | 本机 macOS；python3 | `20261116T055240Z-docs-pass` |
| `python3 tools/harness.py verify`（计划建立前基线） | PASS：静态门禁与 330 kit tests；5 PASS / 0 FAIL / 0 UNVERIFIED；历史 test-count 为 legacy 未重算 | 本机 macOS；python3 | —（过程记录：计划建立前基线） |
| `make check && python3 tools/check_plan.py check --strict && git diff --check` | PASS：新 active 计划与旧计划归档结构通过；仅有归档历史证据提示 | 本机 macOS；python3 | —（过程记录：P0 计划建立） |
| `python3 tools/harness.py verify && git diff --check`（计划建立后） | PASS：330 kit tests、严格计划校验、证据三值 5 PASS / 0 FAIL / 0 UNVERIFIED；仅有归档历史证据提示 | 本机 macOS；python3 | —（过程记录：P0 计划验证；动态测试未重跑） |
| `npx @fission-ai/openspec@2.1.0 init/new change/validate --strict`（临时夹具） | PASS：`valid=true`、`failed=0`；空 Change 负向校验退出 1；未写宿主或全局技能 | 本机 macOS；Node v25.8.1；OpenSpec commit `8bd4b35` | —（过程记录：OpenSpec 兼容性 spike） |
| `claude -p --setting-sources user --plugin-dir "$SUPERPOWERS_7_0_2" ...` | PASS：临时加载 bootstrap，并成功调用 `superpowers:test-driven-development`；未全局安装 | 本机 macOS；Claude Code 2.1.310；Superpowers commit `22f0b46` | —（过程记录：Superpowers 兼容性 spike） |
| 独立 Qoder 会话只读对抗审查 + 主会话行号复核 | 完成：B1–B8 均确认并写入分阶段门禁；未运行动态测试 | 独立会话 `4c36f194-3aeb-5c12-adbc-90d95fe73bd7` + 当前宿主源码 | —（过程记录：独立对抗审查） |
| `npx @fission-ai/openspec@2.1.0 validate fix-transcript-export --strict --json`（宿主） | PASS：`valid=true`、`failed=0` | 宿主仓；OpenSpec 2.1.0 | —（过程记录：行为契约） |
| MobileBuildMCP 导出聚焦测试（旧实现，第一轮） | 预期编译红：11 个用例发现，`TranscriptExportService(exportDirectory:now:)` 不存在；不计为目标缺陷复现 | iPhone 17 Pro Max / iOS 26.4 模拟器；Debug | —（过程记录：TDD 编译红） |
| MobileBuildMCP 导出聚焦测试（旧实现，强化断言后） | FAIL：1 passed / 10 failed；快照被删或覆写、清理误删、视图不按内容/语言刷新均复现；日志 `/tmp/duiyi-p0-export-red-behavior-2.log` | 同上 | —（过程记录：TDD 行为红） |
| MobileBuildMCP `DuiyiTests/TranscriptExportServiceTests + ExportShareButtonTests`（修复后） | PASS：11/11；A→B 快照字节不变、同分钟隔离、7 天边界、进程内保护、三类视图刷新 | 同上 | —（过程记录：聚焦绿） |
| MobileBuildMCP `-only-testing:DuiyiTests` | PASS：131 passed / 0 failed / 0 skipped；既有 120 个用例未改 | 同上 | —（过程记录：完整单元） |
| MobileBuildMCP `-only-testing:DuiyiUITests` | PASS：2 passed / 0 failed / 1 expected skipped（语音能力用例） | 同上 | —（过程记录：UI 回归） |
| `make verify-static && make check-tests && git diff --check` | PASS：330 kit tests、严格计划校验、131 floor 与文档计数一致；证据三值未由本命令判定 | 本机 macOS；python3 | —（过程记录：静态门禁） |
| `ai-delivery-toolchain`（v0.1.0）49 tests + 真实 8/8 转换 + 3 条负向 CLI | PASS：严格 JUnit/manifest 拒绝属性-only、复用路径、claim 错配；固定 tag `v0.1.0` | 本机 macOS；Python 3.14.7；Xcode 27.1 | —（过程记录：外部仓证据，见其计划） |
| `make evidence-chain-check`（宿主） | PASS：pin `v0.1.0` 哈希一致；8 cases（7 个 manifest 负向）全部拒绝；freshness 5 cases（4 个负向：Makefile/tools/xcodeproj + 过程目录豁免） | 本机 macOS；python3 | —（过程记录：宿主证据链自检） |
| `make evidence-unit WRITE=1`（clean 提交 `db4dcd2`） | PASS（历史）：131/131、0 skip；runId `dd37804b-b3d3-4a47-8c31-7baaa5479103`；已被最终单元证据取代，原证据已归档 | iPhone 17 Pro Max / iOS 26.4.1 模拟器；Xcode 27.1；Debug | `20261117T063557Z-unit-tests-pass` |
| `APM_TEAM=... make evidence-ui-device`（非写入试跑） | PASS：UI 3/3、0 failed、0 skipped；manifest 绑定 `physical-device`、iPhone 13 / iOS 27.0.1；runId `a7077cba-431d-4f4a-bb16-dbd70859d0d2`；试跑 artifact 已清理，未写证据 | iPhone 13 / iOS 27.0.1 真机；Xcode 27.1；Debug | —（过程记录：真机 UI 试跑） |
| `APM_TEAM=... make evidence-ui-device WRITE=1`（clean 提交 `e3f5779`） | FAIL（环境）：预热 `DuiyiTests/TaskStoreTests` 退出 65；`Developer App Certificate is not trusted` / profile 未显式信任；设备已连接、未锁定，签名 Team 为 `VV865TW6B3`；按规则停止重试，无正式真机证据 | iPhone 13 / iOS 27.0.1 真机；Xcode 27.1；Debug | —（未验证：真机 UI 证书信任） |
| `make evidence-ui WRITE=1`（clean 提交 `e3f5779`） | PASS：恢复目标模拟器后 3 tests / 2 passed / 0 failed / 1 expected skipped；strict JUnit + manifest；runId `e1fdc475-d12f-410d-951d-759d50674f28` | iPhone 17 Pro Max / iOS 26.4.1 模拟器；Xcode 27.1；Debug | `20261117T071338Z-ui-tests-pass` |
| `make evidence-unit WRITE=1`（clean 提交 `e3f5779`） | PASS：131 tests / 131 passed / 0 failed / 0 skipped；strict JUnit + manifest；runId `dc4c7d5d-802b-4f52-89a0-06a7ab9e8e5d` | 同上 | `20261117T071412Z-unit-tests-pass` |
| `ruby -e 'YAML.load_file(".github/workflows/verify.yml")'` | PASS：workflow YAML 语法；`make evidence-unit/ui`、必需 JUnit `if-no-files-found: error`、run/attempt artifact 命名已写入；GitHub Actions 未实际运行 | 本机 macOS；Ruby | —（未验证：CI 动态链） |
| `python3 tools/verify_claim_chain.py --all`（迁移前） | FAIL（历史）：旧 unit/device 证据 passed 低于新 floor；未重算 legacy；新链证据已接管 | 本机 macOS；python3 | —（过程记录：迁移前红灯） |
| Claude Code 同流程实测 | 未运行 | — | —（未验证） |

## 未验证项

- B1/B2 宿主严格链已完成：unit 131/131 与 UI 2 passed + 1 expected skip 均来自 clean 提交 `e3f5779`，legacy unit/ui/device 证据已归档并由 `supersedes` 接管。
- 真机 UI 正式证据未生成：设备已连接且未锁定、App 签名 Team 为 `VV865TW6B3`，但 iOS 报 Developer App 证书/profile 未显式信任；`ui-device-tests-pass` 为 `required:false`，保持未验证且不阻断聚合。模拟器 UI 已在恢复环境后通过，不能据此宣称真机 UI 已验证。
- B6 freshness 已覆盖 Makefile/tools/工程配置，并完成三类陈旧证据与过程目录的负向自检；最终 `make release-check` 仍待新证据。B7 workflow 已接入唯一产物与必需 JUnit，但尚未在 GitHub Actions 实际运行；UI CI 默认关闭时保持未验证。
- B8 已由 `v0.1.0` pin 解除阻塞；宿主禁止引用未固定工作树。
- 真实 ShareLink/ShareSheet 在系统分享扩展中的读取行为尚未人工实测；文件级与宿主测试不能替代该结论。
- Claude Code 是否可用及同流程结果尚未验证；不能以 QoderCN 结果代替。

## 未验证豁免（done 前有未验证项时必须填）

> 当前为 active，不豁免上述核心验收；若环境阻塞，保持 active/blocked 并报告，不以豁免伪造 P0 完成。

| 项目 | 理由 | 负责人 | 到期日 |
| --- | --- | --- | --- |

## 未提交改动

- 无未提交改动（unit/ui 正式证据、legacy 归档与计划更新随本次提交入库）。

## 下一步

1. 在 clean 提交上运行 `make verify-static` / `make verify-all` / `make release-check`，确认严格证据链与 freshness 通过。
2. 处理真机 Developer App 证书信任后再运行 `APM_TEAM=<Team ID> make evidence-ui-device WRITE=1`；该 claim 保持可选，未完成不阻断 P0。
3. B7 CI 实际运行与双 Agent 实测；提交、push 与发版仍需单独确认。
