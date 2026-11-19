# 最终方案评审：合理性与可执行性（2026-11-19）

> **用途**：对最终设计 + Phase 2 计划 + 外部 v0.4.0 计划做独立合理性评审，不作为交付门禁证据。
> **执行环境**：Claude Code 2.1.310 + DeepSeek V4.1 Flash（`deepseek-flash`）；Read/Grep/Glob/Bash，只读；未读取历史 review 报告。
> **耗时/规模**：约 375 秒；输出约 11.9k 字符。
> **结论**：有条件合理；发现 P0×4 / P1×8 / P2×6（详见正文）。

## 评审边界与基线

- 只读评审，未修改仓库文件；未读取 `harness/reviews` 历史报告，只读取了 `harness/reviews/README.md`、`_template.md` 及计划中的处置摘要。
- 已运行只读检查：
  - `make release-check`：**PASS**（332 个 harness-kit 测试；139 单元 + 2 UI + 1 skip；3 条当前证据 PASS）。
  - `python3 tools/check_plan.py check`：**PASS**（0 error / 21 warn）。
  - `python3 tools/check_docs.py`：**PASS**（62 篇文档）。
  - `python3 tools/evidence_chain.py check-pin`：**PASS**（v0.2.0）。
  - `make doctor-skills`：**PASS**。
  - **`make delivery-check-fixtures`：FAIL**（`scope deny 命中：Duiyi/Features/Home/HomeSettingsSheet.swift、Duiyi/Features/Shared/LanguageChipGrid.swift、openspec/specs/language-catalog/spec.md`）。
  - 离线缓存中的 OpenSpec 2.1.0 CLI 已验证：`--version`、`new change --help`、`instructions --help`（含 `--json`）均可用；未在本仓实际创建 Change。

---

## 1. 结论

**有条件合理。**

方向是对的：把 OpenSpec 从“手工工件”变成可追溯的 scaffold/instruction/validate 回执，把 Superpowers 从“自觉纪律”变成可审计的 skill/discipline 回执，职责边界（OpenSpec 契约、tasks.md 状态、Harness 证据、Toolchain 门禁）基本自洽，也直接对应 G1–G3。

但当前方案**不能按 Phase 2 原样执行**，主要不是架构错，而是几个关键闭环没接上：

- 作为验收前提的 `delivery-check-fixtures` 基线已经是红的；`delivery-provenance-fixtures` 还不存在。
- 原生 skill 的自身指令与“tasks.md 唯一状态”冲突：`openspec` skill 说 tasks.md 只是指针；`brainstorming` skill 要求调用 `writing-plans`，而设计明确禁用。按用户要求“直接调用”这两款工具，反而会制造第二份计划。
- OpenSpec 的 prompt 源没有配置：`openspec/config.yaml` 没有 artifact rules/context，CLI 默认 instructions 不会生成宿主 lint 要求的 Files/验证命令/Expected 和 traceability 字段。
- 门禁执行链不完整：CI 只跑 `verify-static`，`hooks-install` 只安装 pre-push，pre-commit 即使写出来也不会自动生效。
- 11 条 lint、6 类回执、3 种交付模式在首个真实 Change 之前就铺开，局部过度设计，首跑返工概率高。

**建议**：先把 P0 修到“基线可复现 + 原生 skill 可覆盖 + OpenSpec 模板可产出 + 门禁链可执行”，再把 Phase 2 收窄为“回执 + 最小 lint + 一个真实试点”，全量 lint/light 模式/portfolio 留到试点之后。

---

## 2. P0/P1/P2 表

> P0 = 不修就不能按计划执行或验收；P1 = 影响效果、可执行性或会产生错误信心；P2 = 文档、取舍或后续优化。

| 级别 | 问题 | 证据或位置 | 影响 | 建议 |
|---|---|---|---|---|
| **P0** | delivery fixtures 基线已红，provenance fixture 不存在 | `make delivery-check-fixtures` 当前 FAIL；`harness/fixtures/delivery-check/tasks-positive.md:6-7`（Base `5ad38d1`，deny `openspec/specs/`、`Duiyi/Features/`）；`tools/delivery_fixtures.py` 直接跑真实仓库；`Makefile` 无 `delivery-provenance-fixtures` | 验收中“正样例 PASS / fixtures 全绿”当前不成立；Phase 2 一开始就带红基线，后续无法判断新门禁是否引入回归 | 把 fixture 改成临时 git 仓或固定 fixture base，不依赖真实仓库历史；补齐 provenance fixture；Phase 2 第一步先记录并修复该红基线 |
| **P0** | 原生 skill 与“单一任务状态”冲突 | `~/.agents/skills/openspec/SKILL.md` 明确说 tasks.md 是“Harness 计划的指针”，不维护 checklist/任务状态；`~/.cache/.../superpowers/.../brainstorming/SKILL.md` 第 4 步要求 `Invoke superpowers:writing-plans`；设计 5.2:327 禁用 `writing-plans`；设计 4.3:209 又要求 brainstorming 产出写入 proposal/design | 按用户要求“直接调用”时，agent 会被上游 skill 推向第二份计划，或不维护 tasks.md；首个原生 Change 很可能在流程层失败，而不是代码层失败 | 增加仓库内 skill overlay：brainstorming 在写 plan 前停止，改为写 OpenSpec proposal/design + tasks；明确 tasks.md 唯一状态；把 overlay 的 SKILL.md/hash 纳入 config/receipt；加一个 dry-run 用例验证不会生成 `docs/superpowers/plans` |
| **P0** | OpenSpec prompt 源没有配置，CLI 默认模板与 lint 不匹配 | `openspec/config.yaml:1` 只有 `schema: spec-driven`，rules/context 全是注释；设计 5.3 L5/L6/L8 要求 Files/验证命令/Expected、scenario→task traceability；Phase 2 scope allow（plan:8-31）不含 `openspec/config.yaml`；已确认 OpenSpec 2.1.0 `instructions --json` 可用 | 默认 `openspec instructions tasks` 不会生成宿主 lint 需要的字段；agent 只能手写补齐，lint 变成事后补丁，“prompt 来自 CLI”不成立；这正是用户要解决的“工件手工编写”问题换了个位置 | 在 `openspec/config.yaml` 增加 artifact rules/context（任务字段、GWT、`Covers: R1/S1` traceability）；把 config 纳入 Phase 2 scope；用 `instructions tasks` 的真实输出跑 lint 作为 fixture |
| **P0** | 门禁执行链不完整：CI 未跑 delivery-check，pre-commit 未安装 | `.github/workflows/verify.yml:103-104` 只跑 `make verify-static`；`Makefile:212-215` 只安装/chmod pre-push；Phase 2 步骤 8 新增 pre-commit，但未改 `hooks-install`；设计 5.4/5.6 把 CI 作为最终信任锚 | 本地可用 `--no-verify` 绕过；CI 不会发现缺失回执；Phase 2 的 gate 实际上只是本地自证，和设计宣称的“Git/CI/review 收口”不一致 | 更新 `hooks-install` 安装 pre-commit；为 PR 增加 delivery-check job（仅在触达 OpenSpec Change/receipt 时）；若本期不做 CI，则明确降级为 local-only，并修改验收与信任模型 |
| **P1** | receipt 日志被 `.gitignore` 忽略 | `.gitignore:15` `harness/**/*.log`；设计 5.1:301 的 `outputArtifact` 是 `harness/receipts/openspec/<change>/scaffold.log`；Phase 2 步骤 5 要求回执 tracked | scaffold/validate 回执 artifact 默认不入库，gate 的“artifact 未跟踪”直接失败；靠 `git add -f` 容易漏 | 回执 artifact 改用 `.json`/`.txt`，或加 `!harness/receipts/**/*.log`；加 `git check-ignore` fixture |
| **P1** | P0-1 被称“已关闭”但无证据 ID | plan:133、198 记录 spike“UNVERIFIED”；plan:201 写“P0-1 已关闭”；验收:55 要求 P0/P1 逐条验证 | 违反仓库“无 evidence id 即未验证”；关闭表和验收不可信 | 补 tracked evidence（命令/退出码/环境/提交），或保持 open；同步“进度/验收/下一步”三处 |
| **P1** | 评审执行器 B 默认，但 B 未跑门禁且漏过 P0 | plan:161-175：B 225s、未跑 delivery-check、漏 P0；`harness/reviews/README.md:26` 只写“必须复跑或明确未复跑”；`_template.md` 的 `review_method` 不参与门禁 | 对 `tools/**`、门禁、CI 这类变更，默认评审可能不跑关键门禁；“复跑”是文字要求，无法机检 | 风险分级：门禁/工具/CI 变更默认 A 或单独的 gate-runner；给 review front matter 加 `gates_rerun`/`gate_results` 并纳入 delivery-check；B 继续作为普通代码/Spec 快速轴 |
| **P1** | 宿主 skill 入口未 pin，adapter 不覆盖 | `.dsh/skills/` 只有 6 个自定义 skill；`~/.agents/skills/{openspec,superpowers}` 是用户级；`tools/adapters.py` 把 `.dsh/skills` 同步到 `.claude/skills`；`tools/doctor_skills.py` 检查用户级软链；设计 5.2:354 只校验 hostSkill 实际副本 | 新机器/新宿主 clone 后缺少两个关键 skill；入口内容可漂移；receipt 只证明“当时那份”，没有仓库内期望 hash；CI 无法复算 | 把 overlay/入口放进仓库或纳入 manifest；adapter/doctor 覆盖 openspec/superpowers；PIN 增加入口 hash；明确 CI 只能验 source，不能验 hostSkill |
| **P1** | `doctor-delivery` 验收不可判定 | plan:52“断网时 fail-closed 或正确降级” | 两种实现都能过；无法判断 offline/online 是否符合设计 5.5 | 明确两条：offline 模式断网 PASS 且不调 npx；online 模式断网非零并提示切换；各一个 fixture |
| **P1** | v0.4.0 一次发布把版本卫生与四大能力耦合 | 设计 DD-5:624；external plan:41-52；external `pyproject.toml:7`、`cli.py:21` 仍为 0.2.0 | 宿主被一个大版本阻塞；接口不匹配时返工面大；版本卫生这个独立 bug 被拖住 | 先冻结 profile/receipt schema 再实现；评估 v0.3.1（仅版本卫生 + discipline pin）解耦；v0.4.0 再做 provenance/lint/skills |
| **P1** | traceability 没有机器可读语法 | 设计 5.3 L6；现有 `tasks.md`/`harness/records/_template.md` 没有 scenario→task 映射；`docs/case-native-openspec-delivery.md` 5.1 也未定义 | L6 只能靠关键词猜测，误报/漏报；“每个 scenario 至少一个 task”无法稳定复算 | 定义 `Covers: R1/S1` 或等价字段；tasks lint 校验；fixture 覆盖缺链/多链/错链 |
| **P1** | 首个试点前铺满 11 条 lint/6 类回执/3 种模式，局部过度设计 | 设计 5.3/5.7；Phase 2 步骤 5/7；P2C 之前没有真实 Change | 规则未经过真实 OpenSpec 工件验证，首跑大概率返工；门禁疲劳 | Phase 2 先落 4 条硬规则（占位符、复选框唯一、Delivery Contract、validate 新鲜）+ 回执；L3/L5/L8/L11 先 WARN/advisory，试点后再升级 |
| **P2** | `harness/reviews/README.md:11` 写“两轴审查是 M2/M3 起推荐方法”，但 M2/M3 未定义 | `harness/reviews/README.md:11` | 读者无法判断与 L0/L1/L2 的关系 | 改为 L2 口径，或定义 M2/M3 |
| **P2** | 红队触发范围与 Phase 2 自身要求不一致 | `references/workflow.md:24` 只强制并发/持久化/发布；Phase 2 作为规则/工具/CI 变更却要求独立对抗复核 | 未来类似治理变更可能按旧规则跳过独立复核 | 在 workflow 增加“治理/门禁/工具链自身大改”触发项，或记录本期用户批准的例外 |
| **P2** | `check_plan` 把 records 当 plans 计数 | `tools/check_plan.py:441-447` 把 `harness/records/*.md` 并入 plan_files；`:1156-1171` 对全部 active 做唯一判定 | “0 active plan + 1 active record”实际是“1 个 active 文件”；若未来同时有 active plan 和 active record 会直接失败 | 明确记录类型，或增加 fixture 覆盖“0 plan + 1 record”和“1 plan + 1 record” |
| **P2** | 信任模型仍缺 CI 侧 hostSkill 复算、PIN 无签名 | 设计 5.6 承认 PIN tag/tree 自述、无签名；CI 无法访问 `~/.cache`/宿主机 skill；`load_pin` 只校验哈希形状 | 在 CI/干净 checkout 上，回执只能证明 source manifest，不能证明 agent 真的加载了宿主副本 | 在文档/验收中按环境分开声明：本地可验 hostSkill，CI 只验 source；P4 再评估签名 |
| **P2** | DD-2“单人项目默认 light”与 Duiyi 本期 full 的默认值需要更清晰的模式选择 | 设计 5.7；Phase 2“Duiyi mode: full”；DD-2 | 新项目默认 light 可能削弱用户“保障 prompt 质量”的目标，且用户不容易意识到哪些门禁被关闭 | `init --mode` 必须显式选择；status/report 显示关闭的门禁；L2-in-light 必须 waiver |

---

## 3. 被挑战的假设

1. **“直接调用 Superpowers = 按设计执行。”** 不成立。`brainstorming` 的 SKILL.md 自己要求调用 `writing-plans`，而设计禁用；`openspec` skill 又说 tasks.md 只是指针。原生调用会与“单一任务状态”直接冲突。
2. **“CLI 生成 instructions = prompt 质量。”** 不成立。`instructions` 只是确定性指令块，工件仍是 agent 写的；默认模板不包含宿主 lint 的 Files/验证命令/Expected/traceability 字段。没有 `openspec/config.yaml` 的 rules/context，prompt 质量仍靠人。
3. **“回执 = 调用证明。”** 不成立。设计自己也承认 receipt 不能证明 agent 读了 skill；它只能让“不调用”成为可检测的违规。当前门禁只能做到“可审计的工程纪律”，不是“调用证明”。
4. **“fixtures 是隔离的。”** 不成立。`delivery-check-fixtures` 直接跑真实仓库，Base `5ad38d1` 之后的 `Duiyi/Features`、`openspec/specs` 变更命中 deny，基线已红。
5. **“CI 是最终信任锚。”** Phase 2 没有接 CI；当前只有本地 `verify-static`。在 CI 接上之前，最终锚是“本地 hook + 人工 review”，可被 `--no-verify` 绕过。
6. **“B 更快，所以默认 B。”** 速度有数据；但 B 在试跑中没有跑 delivery-check，漏掉 P0。“没跑门禁”的代价没有被纳入默认策略。
7. **“v0.4.0 一次发布风险更低。”** 它降低 pin 次数，但把版本卫生、provenance、lint、skill receipt、offline、release manifest 绑在一起，接口不匹配时返工面更大；v0.3.1 解耦是值得重新评估的选项。
8. **“先铺满 lint 再试点更稳。”** 规则没有经过真实 OpenSpec 工件验证；首跑很可能因模板/字段不匹配而大面积返工，反而增加流程成本。

---

## 4. 缺失信息与待验证项

- `openspec new change` 在本仓 root selection 下实际创建什么路径、`.openspec.yaml` 包含哪些字段（`schema`/`created`/`skip_specs`）；目前只验证了 help/version，未在本仓实跑。
- `openspec instructions tasks --json` 的真实输出是否包含宿主 lint 所需字段；`openspec/config.yaml` 的 `rules`/`context` 是否会被 `instructions` 采纳。
- `make delivery-check-fixtures` 在干净工作树或固定 base 下是否本来能过；当前红是 fixture 设计问题还是 delivery-check 逻辑问题。
- `load_pin` 扩展后对 JSON/shell 文件的文件集合语义；`delivery_check.py` 如何把 provenance/lint/skills/discipline 字段透传给外部 profile。
- `validate --json` 是否能提供/复算工件树哈希；offline 模式下如何用落盘 `validateJson` 替代 npx。
- 外部 v0.4.0 的 L2 复核、用户确认、annotated tag、release manifest 尚未发生；宿主无法把外部测试当宿主证据。
- 宿主 skill 入口（`~/.agents/skills/openspec`、`superpowers`）是否会被纳入仓库 pin；`~/.claude/skills/code-review` 的版本/commit 如何记录。
- `archive-gate` 在 v0.4.0 中是否明确校验 `total>0` 与 `state=all_done`；外部 plan 只写了 delivery-check 集成，archive-gate 未单列。
- pre-commit 在真实仓库的性能/误杀率；`--no-verify` 的原生绕过如何被 CI 或 waiver 捕获。
- P2C 试点选择哪个小行为变更；流程成本（首次门禁通过率、返工次数、回执覆盖率）如何记录。

---

## 5. 最小验证清单（命令 + 期望）

| 命令 | 期望 |
|---|---|
| `make release-check` | 当前基线 **PASS**；改动 `tools/**` 后需重跑，不能只看旧证据 |
| `make delivery-check-fixtures` | **当前 FAIL**；修复 fixture 后 exit 0，且正/负样例都可复现 |
| `make delivery-provenance-fixtures` | 当前 target 不存在；新增后正样例 PASS、缺 scaffold/哈希不符/validate 后改工件均非零 |
| `python3 tools/evidence_chain.py check-pin` | v0.4.0 pin 后 PASS，且包含 OpenSpec wrapper 与 Superpowers manifest 哈希 |
| `tools/openspec new change <tmp> --json`（临时副本） | exit 0，生成 `.openspec.yaml`；记录 scaffold receipt |
| `tools/openspec instructions tasks --change <tmp> --json` | 输出可用；与 lint 要求对齐，不出现“CLI 模板不含 Files/Expected”的冲突 |
| `tools/openspec validate <tmp> --type change --strict --json` | `valid=true`，失败时非零 |
| `git check-ignore -v harness/receipts/openspec/<tmp>/scaffold.log` | 修复后应无输出（或改用不被忽略的扩展名） |
| `git ls-files harness/receipts/...` | 回执 artifact 必须被 tracked |
| `make doctor-delivery`（断网） | offline 模式 PASS；online 模式非零并提示切 offline |
| `make delivery-check CHANGE=<pilot>` + 篡改一个回执哈希 | 正样例 PASS；篡改后非零 |
| fixture 仓中 `git commit`（缺回执） | pre-commit 拒绝；`SKIP_AI_DELIVERY=1` 写 waiver；`--no-verify` 记录为已知绕过 |
| `grep -n 'delivery-check' .github/workflows/verify.yml` | 修复后应出现 PR 触达 Change 的 job |
| `python3 tools/check_plan.py check --strict` | PASS；“0 active plan + 1 active record” fixture 可恢复 |

---

## 6. 优先改进建议（3–5 条）

1. **先修 P0 基线，再收窄 Phase 2。** 把 `delivery-check-fixtures` 改成 hermetic fixture，补 `delivery-provenance-fixtures`；Phase 2 先只做“scaffold + validate + skill/discipline receipts + delivery-check 集成 + 一个真实试点”，把 11 条 lint、pre-commit、Record v2、doctor、portfolio 分成后续增量。这样先用真实 Change 验证规则，而不是先铺满规则。

2. **补上 OpenSpec 配置和 Superpowers overlay。** 在 `openspec/config.yaml` 写入项目 artifact rules/context（任务字段、GWT、`Covers: R1/S1`）；增加仓库内 skill overlay，明确 brainstorming 在写 plan 前停止、tasks.md 是唯一任务状态，并把 overlay 的 hash 纳入 config/receipt。否则“直接调用工具”和“单一真源”无法同时成立。

3. **把门禁链真正接上。** 修 `.gitignore` 的 receipt log 例外；更新 `hooks-install` 安装 pre-commit；给 PR 增加 delivery-check job；给 review front matter 增加 `gates_rerun`/`gate_results`，对 `tools/**`、`.githooks/**`、`.github/**`、`harness/config.json` 的变更默认走 A 或独立 gate-runner，而不是只靠 B 的“未复跑”声明。

4. **把验收写成可判定项。** `doctor-delivery` 明确 offline/online 两条命令与退出码；P0-1 要么补 tracked evidence，要么保持 open；外部 v0.4.0 的“测试”只作为前置，不作为宿主证据；明确 CI 只能验 source、不能验 hostSkill。

5. **重新评估 DD-5 与 B/A 默认值。** DD-5 可考虑 v0.3.1 先解耦版本卫生和 discipline pin，v0.4.0 再做 provenance/lint/skills；review 执行器按风险分层：B 作为普通代码/Spec 快速轴，A 或 gate-runner 作为门禁/工具变更的默认。两轴格式本身合理，保留 front matter 兼容和“不跨轴排序”即可。
