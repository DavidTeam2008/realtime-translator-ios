# 独立红队评审：AI Delivery Phase 2（2026-11-18）

> **只读评审**：未修改仓库文件、未读取 .env/密钥；评审对象为设计文档与 Phase 2 计划，并自行读取仓库现状。
> **执行环境**：Claude Code 2.1.310 + DeepSeek V4.1 Flash（模型别名 `deepseek-flash`，`--allowedTools Read,Grep,Glob`，`--max-turns 35`）。
> 说明：`[claude-code:unrecognized_model]` 只是 Claude Code 对非原生模型别名的告警，不影响本次评审执行；原始输出已保留结论与明细。

# AI Delivery Governance 方案独立红队评审

> 只读评审：未修改仓库文件，未读取 `.env`/密钥；仅运行 `git config`、`ls`、`grep` 等只读检查。工作区当前只有设计、Phase 2 计划与 `.workbuddy/` 未提交。

## 1. 结论

**有条件通过。**

设计的问题意识、单一真源划分、信任边界自述（回执不防伪）和分期策略是成立的，Phase 2 计划的范围控制也基本克制。但有两项 P0 会直接决定方案是否可实施：

1. **按工件调用 `openspec instructions <artifact>` 的 CLI 能力未被证实**——仓库内只有 `instructions apply` 的证据，而整个 G2 prompt provenance 依赖前者。
2. **“回执先于工件”的提交顺序门禁在同一次提交下不可观测**——按当前计划，负向验收无法诚实实现。

放行条件：P0 全部关闭；P1 给出处置（修复或书面接受）；P2 记录排期。外部 v0.4.0 未存在前，本计划只能做设计与夹具，不能进入宿主 PIN。

---

## 2. P0/P1/P2 表

### P0（执行前必须关闭）

| 问题 | 证据或位置 | 影响 | 建议 |
|---|---|---|---|
| [可验证性] OpenSpec 2.1.0 是否支持按工件输出 `instructions proposal/design/specs/tasks` 未验证；仓库只证明 `instructions apply` 存在 | `harness/design/...target.md:100,278`；`docs/case-native-openspec-delivery.md:28,32`；`tools/vendor/ai_delivery_toolchain/delivery_cli.py:52-55`；P0 归档计划只记录 `instructions apply` | 若 2.1.0 只有 `apply`，则五类回执中的 instructions receipt、G2/G3 门禁和外部 v0.4.0 范围全部要改；Phase 2 验收无法成立 | 在临时夹具先做 CLI surface spike：记录 `--help`、逐工件命令、退出码、JSON 结构与两次运行的 stdout sha256。若不支持，降级为“apply receipt + contract lint”，并同步改 DD-5 与验收 |
| [可验证性] “instructions 回执提交是工件首提交的祖先”在同一次提交时恒真，无法检测“先写工件后补回执”；`createdAt` 可伪造且不在 Git 中 | `harness/design/...target.md:281,303`；`harness/plans/2026-11-18-ai-delivery-phase2.md:49,126-130` | 计划验收要求“instructions 回执晚于工件”必须非零，但按当前工作流（命令与文件同一提交）该负向夹具无法真实构造；门禁给出虚假保证 | 二选一：①强制回执独立提交且严格早于工件提交，gate 校验 `receipt_commit != artifact_commit && is-ancestor`；②删除顺序声明，只保留 validate receipt 的工件树哈希 + review。并据此改写验收 |

### P1（执行前应处置）

| 问题 | 证据或位置 | 影响 | 建议 |
|---|---|---|---|
| [供应链/正确性] skill receipt 绑定的是缓存路径哈希，未绑定宿主实际加载的 skill 副本；`doctor-skills` 只检查软链目标，不检查 commit/内容 | `harness/design/...target.md:322-348`；`tools/doctor_skills.py:14-33`；`.dsh/skills` 仅有 6 个宿主 skill | 回执可声称 v7.0.2，实际加载的可能是旧版/被改过的 skill；“原生参与”无法审计 | receipt 记录 resolve 后的宿主路径 + 实际 `SKILL.md` sha256；`doctor-delivery` 校验软链目标属于 pin manifest；负向夹具替换 skill 内容后必须失败 |
| [供应链] 新增 `superpowers.manifest.json`/OpenSpec wrapper 哈希放进 PIN，但 `load_pin` 只校验 vendored 顶层 `*.py`；验收却声称 `delivery-check-pin` 覆盖这些哈希 | `tools/evidence_chain.py:86-101`；`harness/plans/...phase2.md:46,114` | 新 manifest/JSON/子包可被修改而不触发 PIN 失败，形成“PASS 但未验证”的假绿 | 扩展 `load_pin` 为 PIN 列举的任意文件递归哈希（含 JSON/子包/wrapper），并加“篡改 manifest 一个字节 → 非零”夹具 |
| [供应链/可移植性] “离线可复算”与 OpenSpec wrapper 实际依赖 `npx -y` 拉包冲突；CI 的 `ubuntu-latest` 静态 job 也不跑 delivery-check | `tools/openspec:12-18`；`Makefile:139-141`；`.github/workflows/verify.yml:91-104`；设计 P8/5.5 | 干净 checkout、无网络或 registry 不可用时 delivery-check 失败；`npx -y` 默认执行安装脚本且无 tarball 完整性校验 | 明确 online/offline 两种模式：offline 只校验已落盘 receipt 与本地哈希；online 才调用 OpenSpec。长期改为固定 tarball 完整性/本地 node_modules，并加 `--ignore-scripts` |
| [可验证性] pre-commit 无法可靠判断“L2 相关改动”；不建 Change 的 L2 工作天然绕过；waiver 无 owner/到期/结构 | 设计 5.4；计划第 8 步；`harness/plans/...phase2.md:50` | 要么误杀 L0/L1（按代码路径触发），要么只在已有 receipt 时检查（不写 receipt 即绕过）；waiver 可自批 | 明确触发条件：存在未归档 `openspec/changes/<id>` 且提交命中其 `Scope allow`；waiver 定义 schema（理由/负责人/到期/change），并在 `delivery-check` 可见；把“有代码改动但无 Change”纳入 review/CI 抽查 |
| [可验证性] skill/discipline receipt schema 未包含 red 命令与退出码，但计划验收要求“TDD red exitCode=0”负向夹具 | 设计 5.2 的 receipt v1 字段；`harness/plans/...phase2.md:49` | 验收项无法按 schema 实现，或实现成另一套未设计字段 | 在 discipline/skill receipt 增加 `redCommand`、`redExitCode`、`redOutputSha256`、`greenEvidenceId`，并与 Harness evidence 交叉绑定 |
| [正确性] `created` 是本地日期，scaffold receipt 是 UTC 时间；设计一边列为 fail-closed，一边说“不做跨日粒度硬判” | 设计 5.1:281,303；`openspec/changes/archive/.../.openspec.yaml:2` | 东八区凌晨运行会误判；规则自相矛盾 | 用 receipt 派生的本地日期比较，或允许 ±1 天；或在 schema 中直接存日期而非时间戳 |
| [可验证性] L6 traceability 在 G3 plan 阶段要求 acceptance→evidence，但 evidence 到 G5 才存在 | 设计 4.3 G3/G5；5.3 L6 | lint 在 plan 阶段跑必然失败，在 delivery 阶段跑又不是“plan 前消除歧义” | 拆成 `plan-lint`（只查 A#→claim 名称的静态映射）与 `delivery-lint`（claim 实际 PASS/新鲜），并写清各阶段运行哪一个 |
| [正确性] `build_profile` 对缺字段的 claim 静默 `continue`，`delivery`/`ci` 缺失时默认为空；与 fail-closed 及 `harness/AGENTS.md` §1 冲突 | `tools/delivery_check.py:63-88`；`harness/AGENTS.md` §1 | 缺少 `floor`/`target` 的 claim 被跳过；缺少整个 `delivery` 段仍可能 PASS，验收“缺字段 fail-closed”只覆盖新字段 | 对所有必填字段报错；增加“config 缺 `delivery`”“claim 缺 `floor`”两个负向夹具 |
| [可验证性] Phase 2 修改 `tools/**`、`Makefile`、`harness/config.json`，会使现有 unit/UI 证据按 freshness 规则变 STALE；但计划要求最终 `make release-check` PASS 且未安排重跑证据 | `harness/config.json:156-197`；`Makefile:208-210`；`tools/verify_claim.py:55,784-786`；计划验收第 55 行 | 计划完成时 `release-check` 会因 STALE 将 PASS 降为 UNVERIFIED；要么临时改 freshness（作弊），要么补跑动态证据 | 在步骤 11 前增加“重跑模拟器 unit/UI evidence”或填写带负责人/到期日的书面豁免；不要改 freshness 规则 |
| [可维护性] Phase 2 直接修改 harness-kit 生成的 `Makefile`、`.githooks/pre-push`、`harness/config.json`，但未说明 `.harness-manifest.json` 哈希如何更新、未来 kit 升级如何不冲突 | `.harness-manifest.json:76-124`；计划 scope 含 `.harness-manifest.json` 但步骤未提 | 下次 kit 升级/漂移检查会把本地改动视为分叉；“一套工具管理多项目”首先在模板层失真 | 优先把通用目标回贡 harness-kit；否则定义明确 overlay（文件清单 + 生成规则），并在步骤中重算 manifest 哈希 |

### P2（记录排期）

| 问题 | 证据或位置 | 影响 | 建议 |
|---|---|---|---|
| [可维护性] 回执放在 `harness/evidence/` 下，但不是 evidence schema；同一目录存在两套工件与两套校验器 | `harness/evidence/schema.json`；`tools/evidence.py:295-301`；设计 5.4 | 所有权与校验边界模糊，后续工具容易误扫/误判 | 改用 `harness/receipts/`，或在 README 明确“仅顶层证据 ID 文件受 schema 约束” |
| [正确性] skill-invoke receipt 与 discipline receipt 记录重叠事实（谁在何时用了哪条纪律） | 设计 5.2；外部 v0.3.0 discipline receipt | 两份回执可能不一致，gate 需要决定信任哪一份 | 合并为一份 receipt，或明确 skill-invoke 只做“来源绑定”、discipline 只做“红绿证据绑定” |
| [可验证性] prompt receipt 只能证明“取过模板”，不能证明最终 prompt 质量 | 设计 0.2.3、5.3；`instructions` 输出不含项目上下文 | TL;DR 对“prompt 质量可机检”有过度承诺 | 改称“模板 provenance”，质量交给 contract lint + traceability + review；不要用 receipt 数量当质量指标 |
| [可维护性] 每个 L2 需 scaffold + 多份 instructions + validate + N 份 skill + discipline + evidence，流程成本未估算 | 设计 5.1/5.2/5.3；计划验收 | 门禁疲劳会导致常态绕过，反而削弱治理 | 定义“最小回执集”（小 L2 只需 scaffold + 一次 validate + TDD + verification），在 P2C 度量单 Change 成本 |
| [正确性] 归档后 change 目录移动到 `openspec/changes/archive/<date>-<id>/`，回执中的绝对相对路径会失效 | 设计 5.1 schema 的 `openspecYaml`/`artifactPath` | 归档后复核或 CI 重跑会因路径不存在失败 | 回执存 change 相对路径，或 gate 对 archived 路径做映射 |
| [供应链] PIN 的 tagObject/sourceTree 是自述值，宿主无法离线验证 tag 未被移动；无签名 | `tools/vendor/.../PIN.json`；设计 5.6/P4 | 供应链信任仍落在 Git review，不是密码学证明 | 保留为已知残余风险；P4 再评估 Sigstore/minisign；至少加“PIN 值变更必须单独 review”的规则 |
| [可维护性] 设计 5.7 要求项目默认 `mode` 写配置，但 Phase 2 只加 provenance/contractLint/discipline，未加 `mode` | 设计 5.7；计划第 4 步 | P3 引入 light 模式时要再做一次 config/schema 迁移 | 现在加 `delivery.mode: "full"`（只允许 full），P3 再扩展枚举 |
| [回滚] 回滚清单只有 PIN/adapter/config/schema/证据，遗漏 pre-commit hook、Makefile 目标、Record v2 模板、`.harness-manifest.json` 与已生成 receipt | 计划“风险与回滚”第 163 行；设计 P10 | 部分回滚会留下仍会拒绝提交的 hook，或指向不存在模块的 Make 目标 | 列出全部工件与回滚顺序，并加“回滚后 fixtures 仍 PASS”的验证 |

---

## 3. 被挑战的假设

1. **“2.1.0 已提供按工件的 `instructions`”**：目前只有 `instructions apply` 的实测证据；这是整个 prompt provenance 的单点假设。
2. **“提交顺序能证明先读指令后写工件”**：同提交下祖先关系恒真；时间戳不在 Git 中，不可审计。
3. **“skill-invoke 回执让不调用成为可检测违规”**：只有在已创建 Change 且提交命中 scope 时才成立；Agent 仍可运行命令而不读 skill。回执是审计线索，不是遵守证明。
4. **“prompt 质量由 CLI 指令块保证”**：指令块只是模板；项目规则、领域上下文和最终措辞不在回执哈希内。真正的质量门是 contract lint 与 traceability。
5. **“一套工具管理所有项目”在 Phase 2 可验收**：Phase 2 仍是 Duiyi 专用接线；可移植性要到 P3 用真实第二项目验收。
6. **“离线可复算”**：回执本身本地可算，但重跑 OpenSpec 校验依赖 Node/npm registry；Superpowers 依赖用户级缓存与软链。
7. **“pre-commit 快检不会误杀”**：没有真实仓库的误杀率数据；L2 识别规则本身是最大不确定性。
8. **“v0.4.0 一次发布可同时覆盖 provenance/lint/skill receipts”**：依赖未验证的 OpenSpec surface 与外部仓排期，宿主侧没有接口冻结点。

---

## 4. 缺失信息与待验证项

1. OpenSpec 2.1.0 的完整命令面：`new change` 是否非交互、`instructions` 是否接受 proposal/design/specs/tasks、输出是否跨机器确定、`--json` 结构。
2. `.openspec.yaml` 的 `created` 语义（本地日期/UTC）与 `schema` 合法值集合。
3. Superpowers 缓存是否真实存在于 `~/.cache/ai-delivery-toolchain/superpowers/<commit>`、skill 数量、逐 skill sha256；宿主实际加载的软链内容是否一致（本次因目录限制无法读取）。
4. 外部 v0.4.0 的 receipt schema（尤其 red 命令/退出码）、contract-lint 规则 ID、发布清单格式、签名/完整性方案。
5. CI 是否具备 Node/npm/网络；PR 与 push 的触发差异；self-hosted macOS runner 的安全边界。
6. 用户是否接受：Phase 2 只做 full 模式；多项目能力延后到 P3；单人项目默认 light 与 L2 默认 full 的优先级。
7. v0.3.0 tag `e11ae5c` 与 discipline receipt 的外部事实（本次无法访问外部仓）。
8. 本次评审是否可作为计划要求的“独立对抗复核”输入；作者需逐条回应 P0/P1。
9. `.harness-manifest.json` 与 harness-kit 上游的升级/覆盖策略。

---

## 5. 最小验证清单（命令 + 期望）

| # | 命令 | 期望 |
|---|---|---|
| 1 | `tools/openspec --version` | 输出 `2.1.0`；记录是否需要网络、耗时 |
| 2 | 临时夹具：`tools/openspec new change probe-change --json` | 退出 0；生成 `.openspec.yaml`，含 `schema`/`created`；记录实际可用 flags |
| 3 | `tools/openspec instructions proposal --change probe-change --json`（再跑 design/specs/tasks） | 退出 0；两次 stdout 的 `shasum -a 256` 完全一致；若命令不存在，P0-1 成立 |
| 4 | `tools/openspec validate probe-change --type change --strict --json`；随后改一个 spec 再跑 | 第一次 `valid=true`；第二次非零/`valid=false` |
| 5 | `python3 tools/delivery_check.py --pin-only`；在临时副本改一个 vendored 字节再跑 | 当前 PASS；篡改后非零 |
| 6 | `make delivery-check-fixtures`，并新增缺 scaffold、哈希不符、同提交顺序、config 缺 `delivery` 四个负例 | 正例 0；每个负例非零 |
| 7 | 临时 fixture 仓：安装 hooks 后提交 L2 scope 文件但不带回执；再提交纯文档 L0 | 前者被拒绝；后者通过；`SKIP_AI_DELIVERY=1` 通过且 waiver 在 delivery-check 可见 |
| 8 | 断网运行 `make doctor-delivery` | 若能 PASS，离线声明成立；若因 npx 失败，需改设计或改 doctor 模式 |
| 9 | `make doctor-skills`；`readlink -f` 解析宿主 skill，`shasum -a 256` 对比 manifest | 路径属于固定 commit；哈希一致；替换内容后必须失败 |
| 10 | 改动 `tools/**` 后运行 `make release-check` | 预期因 unit/UI 证据 STALE 失败；确认计划已安排重跑证据或书面豁免 |
| 11 | `tools/openspec list --json` | Phase 2 结束后仍为 0 active changes |
| 12 | `git status --short`；`python3 tools/check_plan.py check --strict` | 只有计划声明的未提交文件；PASS |

**建议放行顺序**：先做验证清单 1–5（决定方案是否成立）→ 关闭 P0 → 外部 v0.4.0 立独立 L2 并冻结接口 → 再进入宿主 PIN 与夹具。P1 中涉及供应链（skill 实际内容绑定、PIN 覆盖范围、npx 完整性）和 release-check 证据时效的三项，建议作为宿主 PIN 前的硬条件。
EXIT=0
