> 冻结副本：来源 `harness/runs/kit-eval/review-quality.md`（2026-11-11）；原始命令输出仍在 gitignored 的 `harness/runs/kit-eval/`。
> 本文件为提案/评审冻结稿，实施记录见 `harness/plans/2026-11-06-benchmark-opensource.md` 与 `harness-kit/CHANGELOG.md`。

# 对抗性质量评审：harness-kit v0.3 提案（REPORT.md）

> 评审对象：`harness/runs/kit-eval/REPORT.md`（v0.3 提案）｜快照：503 行，sha256 `f0660654…`，mtime 2026-11-11 12:22（评审期间文件仍被作者修改：12:17→12:22，结论以本快照为准）
> 方法：只读；本地复跑 kit 测试/脚本；在临时 git fixture 上做伪造证据实验（未改仓库）；外部竞品数据仅抽查 GitHub API。
> 结论：**方向可继续，但当前不能按报告口径对外主打 M2，且路线图验收不可执行；先修 P0 再进入 v0.2.12/v0.3.0。**

## 1. 结论

- **定位重构（项目管理工具/治理层）合理**：证据（usability/positioning 审计）充分，"入口难用 + 双状态对账"的诊断成立；§6.2.1（按需计算 + fixture + M9）是全报告最可执行的一段，应作为其他验收的模板。
- **M2「完成可被机械否证」目前是口号而非机制**：报告已加"不承诺防伪造"的诚实边界（REPORT:165），但现状栏仍写"已有、可对外主打"（:159），机制描述（clean tree + commit 绑定 + 负向自测）与 kit 实际行为不符；**实测伪造证据可通过全部现有关卡**（P0-1）。
- **路线图验收不可机械执行**（P0-2）："3 步内、命令数各减半、一屏、两 Agent 并发、有基线报告"无命令/退出码/fixture/阈值，等于把"完成"交回自述——正是报告要解决的问题。
- **兼容/升级与自进化四件套缺前置**（P1）：无 kit 管理面 manifest/hash、`kitVersion` 不校验（已验证）、无 `harness upgrade` 实现；A/B 指标不可操作。
- 已独立验证成立的报告主张：140 tests（复跑 `Ran 140 tests … OK`, 20.9s）；standard 无 `release-check`/`doctor`/`resume`/`end`/`handoff`，strict 有 `release-check`（templates：standard:5-28、strict:5-41）；`check_plan` 对 done 计划做 submitted/HEAD 绑定（check_plan.py:609-686）；DSH adapter 为空（manifest dsh:[]）；`config.kitVersion` 只读不校验（core 无版本比较）；竞品 stars 抽查一致（api.github.com：spec-kit 149,227 vs 报告 149,224；superpowers 315,820 vs 315,816）。

## 2. P0 / P1 / P2

| 级别 | 问题 | 证据 / 实测 | 影响 | 建议（可执行） |
| --- | --- | --- | --- | --- |
| **P0-1** | **M2 可被伪造，不满足"机械否证"；不能对外主打** | 出厂 config `requireArtifact:false`（config template:58）；verifier 仅在 requireArtifact=true 时要求 `xcresultPath` 非空，且**不检查存在/内容、不重算 counts、不复核 dirty/祖先**（verify_claim.py:238-251, 305-343）；schema 不要求 artifact（evidence schema:result required=status）。**伪造实验**：clean git fixture + 0 个测试 + evidence `{passed:9999, dirty:false, commit:HEAD, 无 artifact}` + done 计划 → `evidence validate` PASS、`verify_claim --all` PASS、`--fresh --strict`（≈strict release-check）PASS、`check_plan check` PASS；把 commit 改成 `deadbeef` 时前两项仍 PASS（仅 strict/fresh 抓）。 | 卖点 M2、§3.1"确定性否证"、§3.5 话术、v0.4 A/B 主指标全部失真；"伪造成本显著变高"未成立（成本=1 个 JSON + 计划 1 行）。 | v0.2.12 先做最小加固再营销：①模板默认 `requireArtifact:true`；②verifier 校验 artifact 存在并从 JUnit XML/xcresult summary **重算 passed/failed/skipped**，与自报值不符→FAIL；注意 adapter 现在输出 `result.artifacts` 而 verifier 只读 `xcresultPath`（evidence_from_junit.py:8-20 vs verify_claim.py:238），先统一 artifact 契约；③commit 必须可解析且为 HEAD 祖先、verify 时复核 dirty；④把本伪造 fixture 加入 kit tests（现有 selftest M1–M8 只证明"缺失/不一致会红"，不覆盖伪造 PASS）；⑤未加固前措辞降为"未验证不能通过 + 证据可审计"。 |
| **P0-2** | **路线图验收不可执行（自指失败）** | REPORT:447-452："3 步内完成"(448)、"5 场景命令数各减半"(449)、"`harness status` 一屏可用"(449)、"两 Agent 并发→证据可合并"(451)、"有基线报告与趋势数据"(452)；无命令/退出码/fixture/阈值。对照 §6.2.1:360 给出了好样板（fixture + M9 门禁）。 | 阶段无法判"完成"，只能自述，重演报告批评的问题；无法决定是否继续投下一阶段。 | 每阶段改成"命令 + 退出码 + 可观察输出"：①status 契约测试（`--json` 必需字段、人读 ≤30 行、exit 0 / 版本不符 exit 3）；②5 场景命令预算：fixture 仓 + 包装命令计数，基线取 usability §1.3（6-7/5-6/8-9/7-8/5-6 → 目标 ≤3/3/4/4/3），并定义"一步"=一次工具调用；③"3 步内"用录制的冷启动 transcript 计 tool rounds ≤3；④v0.3.2 用两个 worktree + 两个脚本 Agent 并发、断言证据合并与 status 双任务；⑤v0.4 A/B 先预注册（见 P1-4）。 |
| P1-1 | **已接入 v0.2.x 仓的升级/兼容未设计** | 无 kit 管理面 manifest/hash：`harness-init` 不写文件清单，adapters.py 只对 `.claude/skills` 做 hash manifest；`config.kitVersion` 不校验（core 仅 presence/打印）；REPORT:345 承诺 upgrade"消除手工升级"、:460 只承诺保留 target 别名。Android 仓 pin v0.2.3；iOS 仓已有 6 个项目 skills（`.dsh/skills/*`）。 | v0.3 入口改造后：旧仓无法安全升级/回滚；新 skill 全局版 vs 仓库 pin 混版；router 与既有 skills 触发冲突；新严格门禁可能把旧证据翻成 UNVERIFIED。 | v0.2.12 加 `.harness-manifest.json`（path/sha256/template/kitVersion，init 写）+ `upgrade --plan` 三方 diff（manifest hash vs 现文件 vs 新模板；conflict 不覆盖、写 .new）；`harness status` 校验 config.kitVersion≠预期→exit 3 并让 skill 拒绝执行；旧 target 行为冻结表 + 3 profile × 旧仓 fixture 回归（Android v0.2.3 fixture）；新增 skill 迁移映射（router 吸收/委托既有 6 skills）。 |
| P1-2 | **评审/证据包不入库，不可复现** | `.gitignore:14` 忽略 `harness/runs/`：REPORT、三份 audit、`out-*.txt`、`_asar/`、`dsh-tree.json` 全未跟踪；REPORT:6/494-503 引用的证据在 fresh clone 不存在；评审期间 REPORT 仍在改（12:17→12:22）。 | 决策文档与证据不可审计/不可交接；后续无法判断结论是否随证据更新；评审可能基于过期快照。 | 把 REPORT + 三份 audit + 本评审移到 tracked `harness/reviews/2026-11-11-kit-eval-*.md`（或 docs/）；raw 产物留 runs；加 tracked `repro.sh`（命令、版本、环境）+ 证据索引；定稿前冻结文件并记录 sha256。 |
| P1-3 | **多处数字/行为引用与实测不符（影响可信度）** | ①REPORT:34 "6 文件 1356 行/≈35.9k tokens"：实测 6 文件=1619 行/35,877 tokens；1356 行/29,070 tokens 是不含 SPEC 的 5 文件（kit token_estimate.py 复算）；②REPORT:33 "`copy` 只进剪贴板"：无剪贴板时会打印 16 行+WARN（out-copy-noclip.txt）；③REPORT:46 "Claude Code 适配只转发"：manifest 有 4 个 claude-code 产物+adapters.py hash sync，只有 dsh 为空；④REPORT:3 "24 prompts" 与 §0/§1.2 "21 流程提示词"未对账（实测 24 文件=19 场景+2 附加片段+3 前置；harness-prompt list；CHANGELOG 0.2.11 写 2+19+2=23 与 24 文件不符）；⑤"140 个 end-to-end 测试"(25) 实为混合单元/fixture 测试；⑥v0.2.12 验收 "kit-check"(447) 只在父仓 Makefile:68（kit 镜像无 Makefile）；⑦"本机 DSH 0.2.2-rc.1"(253) 指 Desktop runtime，但 PATH 上 `dsh --version`=0.2.1-rc.5。 | 证据表的可信度；对外引用会被抓错；"文档膨胀"幅度差约 20%。 | 逐条改正并给复算命令（`wc -l`、`python3 tools/token_estimate.py`、`harness-prompt list`、`dsh --version` / runtime.json）；矩阵与数字加"复算命令"脚注；DSH 版本写清二进制来源。 |
| P1-4 | **自进化四件套缺可落地起点** | capability probe：可行但未定义探测信号/输出 schema；version pin：机制缺失（P1-1）；upgrade：缺 manifest 与 ownership 模型（REPORT:345/429 承诺过度）；A/B(430)：指标"完成声明准确率/越界率/…"无任务集、ground truth、样本量、计分脚本，属空话。 | M6 无法按"四件套"验收；A/B 若照此执行会得到不可解释结果。 | probe：检测 env/CLI（CLAUDECODE、DSH_*、codex）+ `--help` 能力自述，输出本地 JSON（不入库），1–2 天可做；version pin：status 比对 manifest/kitVersion + skill min_version；upgrade：先建 manifest 再做 diff（见 P1-1），承诺改"手工升级降到一次 diff 确认"；A/B 最小设计：3 个 fixture 任务（修 bug 带红测/加功能带验收测试/文档改）、2 条件、每 3 次、主指标 **false-claim acceptance rate**（构造"声称 PASS 但隐藏测试失败"的提交，看门禁是否抓住）+ 越界文件数 + 首过率，脚本自动计分；未完成前不对外声称收益。 |
| P2-1 | §3.4 不适用场景缺"无法产出机读测试结果/无 git/无 CI/不愿维护证据"的项目 | REPORT:167-172 | 这类用户接入后只能得到 UNVERIFIED，却不在"不适用"清单。 | 补两条不适用场景 + README 明示"证据链需要可重复的测试命令/产物"。 |
| P2-2 | §3.5 话术仍暗示确定性 | REPORT:174-178 "任何完成都要过确定性门禁" | 与 P0-1 冲突；对外首发会被打脸。 | M2 加固前话术加限定："PASS=存在可复核证据记录；防伪造在 v0.2.12 加固后生效"。 |
| P2-3 | 竞品"完成可证伪"列断言强于研究证据 | research-ecosystem §F.4 明示竞品能力"仅 README 自述、未实测"；REPORT:142-150 删去该限定 | 差异化论证依赖未证实前提。 | 表格加"未实测/README 未提"标记；stars 快照保存 API JSON（本次抽查 spec-kit/superpowers 与报告一致）。 |
| P2-4 | selftest 声称 M1–M8 全跑 | harness-selftest:223-233：M6/M7/M8 条件执行（需 active 计划/证据/hygiene），普通 standard 宿主只跑 M1–M5 | 高估自检覆盖。 | 改写"M1–M5 必跑 + M6–M8 条件 SKIP"，并在普通宿主输出 SKIP 原因。 |
| P2-5 | "README ≤200 行"红线无门禁 | REPORT:434-439；check_docs 预算只覆盖 AGENTS/references（config template budgets） | 红线是愿望，不挡回归。 | 把 README/skill 长度加进 config budgets，或降级为审计项。 |
| P2-6 | 工期估算无依据 | REPORT:447-452 "1–2 天/3–5 天/1–2 周" | 影响排期信任。 | 给假设（1 agent、无中断）与区间，或改"待估"。 |

## 3. 被挑战的假设

1. **"140 tests + selftest + 三值 ⇒ 完成可被机械否证"**：selftest 只证明门禁会"拒绝缺失/不一致"；伪造 PASS 全链路可过门禁（实测），"否证"对象是纸面记录而非测试执行。
2. **"clean tree + commit 绑定能提高伪造成本"**：clean tree 只在 `evidence.py write` 时检查（可手写 JSON 绕过）；verifier 不复核 dirty/祖先；伪造成本≈写一条真实摘要的成本。
3. **"竞品没有完成可证伪 ⇒ 空白区"**：竞品能力来自 README 自述（研究文件自己标"未证实"）；即使成立，机制未交付前不能作为主打。
4. **"换入口即可消除日常摩擦"**：§6.2.1 已承认是机制问题（好），但 v0.3.0-alpha 验收未包含该 fixture/M9，存在"入口做完、摩擦仍在"风险。
5. **"3 步/命令减半/一屏是验收"**：当前不可测；需先定义"一步"和 fixture，否则是营销数字。
6. **"v0.3 不破坏现有接入"**：target 别名只保命令名，不保行为/证据语义；无 manifest/version gate 时风险不可控。

## 4. 缺失信息

- 外部陌生 Agent/人的实测数据（零学习成本）；多模型（Claude/Codex/DSH）交叉接手实测；DSH 插件 spike 未做（报告承认）；Claude Code 未安装实测。
- 竞品"证据/门禁"能力的一手核对（现在只有 README 自述）。
- 已接入 v0.2.3 的 Android 仓：当前生成文件清单、diff、升级演练/回滚结果。
- "5 场景命令数"口径与基线测量脚本；A/B 的任务集、预算、样本量、计分口径。
- 6 个项目 skills 与 router 的去重/废弃决策；发布后（运维）阶段是否覆盖的边界决定。
- 工期估算依据与可投入人力；REPORT 定稿冻结时间（评审期间仍在改）。

## 5. 最小验证清单

1. **伪造证据回归（P0）**：临时 git fixture + 0 测试 + 无 artifact 的 PASS 证据 + done 计划 → 目标：`verify_claim --all` 必须 FAIL/UNVERIFIED、`check_plan check` 必须 FAIL；加入 kit tests，修复前记录当前全 PASS 基线。
2. **真实 vs 伪造对照**：真实测试→`evidence_from_junit.py`→evidence→verify 与伪造证据的输出必须可区分（当前不可区分）。
3. **数字复算**：对 README/SPEC 等 5/6 文件跑 `wc -l` + `python3 tools/token_estimate.py`，修正 REPORT:34；其余 P1-3 各条给出复算命令。
4. **验收判据化**：v0.3.0-alpha 先写 `status_contract` 测试（JSON schema/≤30 行/exit code）+ 5 场景 fixture 命令计数器（基线见 usability §1.3）+ transcript tool-round 计数。
5. **兼容回归**：3 profile fixture + 旧版仓 fixture（Android v0.2.3）跑 `upgrade --plan`，断言无覆盖冲突、旧 target exit code 不变、版本不符时 status exit 3。
6. **DSH spike**：独立 `DSH_HOME`/非默认 profile 安装最小只读 tool，验证 catalog/tool 可见、卸载无残留；记录 desktop runtime 0.2.2-rc.1 与 PATH CLI 0.2.1-rc.5 的差异。
7. **A/B 预注册**：3 任务×2 条件×3 次，主指标 false-claim acceptance rate；脚本计分；未做前不写收益结论。
8. **入库与冻结**：本评审 + REPORT + 三份审计移入 tracked `harness/reviews/`；raw 留 `harness/runs/`；加 `repro.sh` 与 sha256 快照。

## 附：本次实测命令与结果（节选）

- `cd harness-kit && python3 -m unittest discover -s tests -q` → `Ran 140 tests in 20.854s OK`（140 成立）。
- 伪造 fixture（临时目录）：`evidence.py validate` PASS；`verify_claim.py --all` PASS（`passed=9999`）；`--fresh --strict` PASS（真实 HEAD commit）；`check_plan.py check` PASS（done 计划、0 测试、无 artifact）。
- `config.kitVersion`：grep 全部 core/scripts 只在 load 校验存在/打印，无与 VERSION 比较。
- `adapters/manifest.json`：`"dsh": []`；claude-code 4 项产物。
- 文档面：6 文件 1619 行/35,877 tokens；5 文件（不含 SPEC）1356 行/29,070 tokens。
- `out-copy-noclip.txt`：无剪贴板时输出提示词到 stdout + WARN（非"只进剪贴板"）。
- GitHub API 抽查（2026-11-11）：github/spec-kit 149,227★、obra/superpowers 315,820★，与报告数字一致。
