> 冻结副本：来源 `harness/runs/kit-eval/usability-audit.md`（2026-11-11）；原始命令输出仍在 gitignored 的 `harness/runs/kit-eval/`。
> 本文件为提案/评审冻结稿，实施记录见 `harness/plans/2026-11-06-benchmark-opensource.md` 与 `harness-kit/CHANGELOG.md`。

# harness-kit v0.2.11 可用性审计（首个 AI coding Agent 视角）

> 日期 2026-11-11｜对象 `harness-kit/` v0.2.11｜环境 macOS 27.0.1 / Python 3.14.7｜方法：只读 + 仅在 `harness/runs/kit-eval/` 内建 fake 项目实测；未改仓库文件、未对真实项目跑 init/adopt、未 commit。
> 证据：`harness/runs/kit-eval/out-*.txt`、`err-*.txt`（命令输出原样保存）；fakes：fake-project / fake-init / fake-daily / fake-flow / fake-edge。
> 定位基准：从「脚手架」转向「给 AI coding agent 用的 Harness Engineering 项目管理工具」；判据＝人零学习成本、agent 负担不增加。

## 0. 一句话结论

接入动作本身已足够快且可解释（dry-run→init→post-check PASS 共 <1s，冲突/阶段/占位符提示清晰）；**真正的成本在“用起来之前怎么开始”和“日常/发布/交接时维护第二套状态”**——前者靠人肉复制提示词，后者靠手改计划/证据并反复对账。当前**未达到零学习成本**，但离“一句话触发”只差统一 CLI + 自动注入的 skill 入口。

优点（先记）：`init --dry-run` 0.13s/35 行/29 文件动作；实际 init 0.25s 且 post-init `make check` PASS；重复 init exit 1 并列 CONFLICT；`make check` 0.12s、`verify-static` 0.21s；`harness-prompt` 阶段自动判断（未接入+日常模板→WARN）与占位符提示有效；`harness-adopt --json` 全程只读、174 行结构化输出、不写目标仓；`render --check` 0s 确认文档与模板单源；错误信息可读（如“front matter 缺少字段 owner”）。

## 1. 入口链路实测

### 1.1 从零到第一个动作：要读多少？

| 路径 | 文件/行数 | ~tokens | 说明 |
| --- | --- | --- | --- |
| 人·最短（只照 README 入口段） | `README.md:1-11,66-81` = 1 文件 16 行 | 669 | 知道 `harness-prompt list/copy` 后即可行动 |
| 人·推荐（README+adoption+prompts 用法） | 3 文件 81 行（README 1-11/66-81、adoption 19-56、agent-prompts 7-24） | ~1.9k | 覆盖新项目/存量/提示词 3 条路 |
| Agent·0B 提示要求 | README 307 行 + adoption 261 行 = 568 行（“相关章节”未指段落） | ~13.1k | 按字面读全文；“相关章节”歧义本身即摩擦 |
| kit 文档总面 | README+adoption+agent-prompts+playbook+governance+SPEC = 6 文件 1356 行 | ~35.9k | 另有 `prompts/` 24 文件 ~7.3k tokens（渲染单源） |

- 实测行动序列：`harness-prompt list`（21 场景 + 2 附加片段，自动判断目标仓是否已接入）→ `copy <场景>`（写剪贴板，stdout 仅 2 行/274B）→ 人粘贴给 Agent。**人至少 2 条命令 + 1 次粘贴**；agent 侧无自主发现路径。
- `harness-prompt show` 体积可控：adopt-new 22 行/2642B、adopt-brownfield 26 行/2904B、fix-bug 19/1518、release-prep 18/1514、handoff 16/1501、cold-start 18/1596——即取即用，不必读 390 行提示词库。

### 1.2 harness-prompt / init / adopt 实测

| 命令 | 实测行为 | 证据 |
| --- | --- | --- |
| `harness-prompt list` | 21 场景分组 + 阶段标注；cwd=kit 克隆目录时 WARN 提示换目标；Makefile-only 项目仍正确判“未接入” | 命令输出（§1.4 复现） |
| `harness-prompt copy` | 复制到剪贴板（macOS）；无剪贴板时输出 16 行到 stdout + WARN；阶段不符 WARN（未接入+fix-bug）并提示补 `<SYMPTOM>` | out-copy-*.txt / err-copy-*.txt |
| `harness-init --dry-run` | 0.13s、35 行、29 文件动作（RENDER/COPY/APPEND），不写盘；已有 Makefile 时列 `RENDER Makefile.harness`（不提示需手工 `include`） | out-init-dry.txt / out-init-edge-dry.txt |
| `harness-init`（实际） | 0.25s、31 行、post-init `make check` PASS；Next steps 5 条（复核 config/跑门禁/读文档/提交/可选 hooks） | out-init-real.txt / err-init-real.txt |
| 重复 init | exit 1，33 行 CONFLICT 清单（不静默覆盖） | out-init-again.txt |
| `harness-adopt --json --target harness-kit` | 0.19s、174 行/7108B JSON、`readOnly:true`、不写目标仓；空项目 human 报告 65 行 | out-adopt-kit.json / out-adopt-fake.txt |
| `make check` / `verify-static` / `verify-claim` | 0.12s / 0.21s；无证据时 `verify-claim` exit 2 UNVERIFIED（语义正确但首见像失败） | out-make-check.txt / out-final-claim.txt |

### 1.3 五个目标场景成本（实测拼接估算）

| 场景 | 命令数（含 1 次人肉粘贴） | 需读文档 | 人工判断点 | 失败/歧义点 |
| --- | --- | --- | --- | --- |
| 接入存量项目 | 6–7（adopt、dry-run、init、commit、plan、编辑、check） | README+adoption，或仅有 0B 提示 26 行 | profile、真实测试命令、dry-run 批准、是否 --force | 存量有 Makefile 需手加 include；首次 plan 不绿 |
| 新项目 | 5–6（git init、dry-run、init、commit、plan） | 同上 | 项目名、测试命令、目标目录需已存在 | init 不执行 git init |
| 日常改需求 | 8–9（prompt、plan、改码、check、verify-static、证据 3 步、commit） | 0–1 份（有 0A 提示时） | scope 声明、未提交段同步、是否适用证据 | plan↔git 状态反复红；证据需 JUnit+clean tree |
| 发布 | 7–8（plan done/submitted、证据绑定、verify-static、verify-claim、版本/CHANGELOG、tag/push） | release-prep 18 行 + README 工作流 | standard 无 release-check；哪些证据 fresh；tag/push 需人确认 | standard（真实仓推荐档）缺发布单命令；done/submitted/证据绑定复杂 |
| 交接换 agent | 5–6（prompt、更新计划、commit、新会话 check、brief） | handoff 16 行 | 摘要写什么、worktree 是否干净 | brief 未暴露成 make 目标；无 `resume/end` 入口 |

## 2. 摩擦清单（按严重级）

| # | 步骤 | 摩擦 | 级别 | 证据 |
| --- | --- | --- | --- | --- |
| 1 | 日常任务的 plan/check 循环 | 计划「未提交改动」必须与 `git status` 严格互等：改码未声明→FAIL；已声明但已提交→FAIL（“计划声明未提交但 git 无改动”）。agent 需每步维护第二份状态 | **P1** | out-flow-check3.txt（声明后 PASS）→ out-flow-check4.txt（提交后 FAIL）；README:245-255 未提这条 |
| 2 | 启动入口 | kit 4 个脚本（init/adopt/prompt/selftest）+ 项目 Makefile + 提示词库 + 4 份文档；`copy` 只进剪贴板，**AI agent 无法自己用**，必须人或改 `show` | **P1** | out-copy-adopt.txt（2 行 stdout）；scripts/ 目录；README:58-82 |
| 3 | 学习面 | 入口命令在 README/adoption/agent-prompts 三处重复（669/769/445 tokens）；文档 1356 行，0B 提示要求读 568 行/13.1k | **P1** | 行号与 token 见 §1.1；docs 重复段落 |
| 4 | `make plan` 首次可用性 | 生成的 plan 保留 `owner: <owner>`，`make check` 报“缺少字段 owner”；命令输出只说“填目标/验收/下一步/scope”，不提 owner/未提交段 | **P2** | out-make-plan.txt vs out-flow-check1.txt |
| 5 | 生命周期命令 | Makefile 无 brief/resume/handoff/end（仅 help/check/check-evidence/check-host/verify-static/verify-claim/plan）；交接摘要命令藏在 README:254 的 `python3 tools/check_plan.py brief`；handoff prompt 只说“生成交接摘要” | **P2** | `grep -E '^[a-zA-Z_-]+:' Makefile`；out-show-handoff.txt |
| 6 | 发布 | adoption 推荐 standard，但 `release-check` 仅 strict；release-prep 要人判断档位；standard 发布=多步手工 | **P2** | out-show-release-prep.txt；README:245-255、§profiles |
| 7 | 证据闭环 | init 接受 `--test-command "echo ok"` 不校验能产 JUnit；claims.tests-pass 默认 test-count；`evidence_from_junit` 需 XML（无 XML exit 2）；`evidence.py write` 需 clean tree + `--from-json` | **P2** | harness-init 输出（test=echo ok）；out-flow-verify.txt；evidence.py --help |
| 8 | 存量项目 Makefile | 已有 Makefile → 写 `Makefile.harness`，dry-run 只显示 RENDER，不显示“需在原 Makefile 加 include” | **P2** | out-init-edge-dry.txt；README:104 |
| 9 | 首日门禁噪音 | 未提交 scaffold + 未填 plan 时 `make check` 一次 35 error，agent 易误判“门禁坏了” | **P2** | out-check-after-plan.txt |
| 10 | 路径/阶段 | init 要求目标目录已存在且不自做 git init；`<kit>` 需手工替换；`copy` 成功输出含本机绝对路径（粘贴/分享会带出） | **P3** | README:85；out-copy-adopt.txt |
| 11 | 提示词维护 | prompts 24 文件 + 生成 docs 双层；`render --check` 0s 已保证一致（成本可控，但概念多一层） | **P3** | out-render-check.txt |
| 12 | adopt 输出 | `--json` 174 行需二次解析；默认 human 报告 65 行尚可 | **P3** | out-adopt-kit.json / out-adopt-fake.txt |

## 3. 只允许一个动作时，agent 还缺什么？

`@harness 改造这个项目` 要安全开始，最小信息集（缺一不可）：

1. **kit 位置+版本**（本地路径或 clone URL；否则 agent 不知道去哪找 scripts/）。
2. **目标仓库路径 + git 状态**（是否 clean；是否允许 commit）。
3. **意图三分**：只读盘点 / 接入（profile 默认 standard）/ 日常任务；对应动作差异很大。
4. **写权限边界**：能否写目标仓、能否 `--force` 覆盖、能否改文档、哪些操作需先问。
5. **真实测试命令**（或授权“探测后向我确认”）；假的 test command 会让证据链闭环失败。
6. **完成标准与验证环境**（能否跑测试/真机；不可运行则必须允许 UNVERIFIED）。

示例一句话：`@harness 接入 <路径>：kit=<路径>，profile=standard，test="<命令>"；先只读盘点并给报告，确认后再写；可 commit，不 push。`

## 4. Top 10 简化方案（按收益/成本）

| 排序 | 方案 | 收益 | 成本 | 评估 |
| --- | --- | --- | --- | --- |
| 1 | 统一 `harness` 单入口 CLI（`status/start/verify/release/handoff`，内部调现有脚本+Makefile） | 高（5 场景→5 子命令，消除 scenario→工具映射） | 中（薄壳，兼容现有命令） | **最值得做**；v0.3 可先只读 status/verify |
| 2 | skill 自动注入（DSH/Claude adapter 生成仓库内 skill，直接调 `harness status/verify`，不再复制提示词） | 高（agent 自发现，人 0 粘贴） | 中（复用 adapters/ 雏形，先做 DSH 首发） | **最值得做**；与 1 组合后提示词层可删 |
| 3 | 状态一屏 `harness status`（active 计划关键字段/下一步/未验证/门禁/证据三值） | 高（替代 brief+手读计划+make help） | 低（聚合现有输出） | **最值得做**；15–30 行输出即可 |
| 4 | 去掉独立「提示词库」层（降为 `harness prompt` 内部模板/help，文档仅保留维护者说明） | 高（删 390 行文档 + 24 文件人工层 + 复制步骤） | 中（需 1/2 先承接） | 值得；短期先把 prompt 库标为“维护者内部” |
| 5 | `harness start` 幂等建计划（自动填 owner、把计划文件纳入 scope、未提交段自动为空，建完即绿） | 高（消除首个 plan 必红的 2 个坑） | 中低 | 值得，直接减少日常步骤 |
| 6 | 计划↔git 同步自动化（未提交段自动更新，或 check 将“未声明”降为 WARN + status 提示） | 高（消除 P1 反复红） | 低 | **性价比最高** |
| 7 | standard 增加 `release-check`/`harness release`（复用 strict 逻辑，仅 fresh 检查分级） | 中高（发布路径不再依赖 strict 知识） | 低 | 值得 |
| 8 | 把 `brief`/`handoff` 纳入 Makefile 目标，并在 handoff prompt 直接引用 | 中 | 低 | 值得 |
| 9 | init 后自动生成第一条 active 计划（含 scaffold 验证项），“接入后第一件事”4 步→1 步 | 中 | 低 | 值得 |
| 10 | 文档收敛：README 入口 30 秒+一条命令，adoption/playbook 合并去重，agent-prompts 降为机器模板 | 中（1356 行→~400 行） | 中 | 中期做 |

**四个特别评估**：①统一 CLI＝收益最高、成本可控，优先只读子命令；②skill 自动注入＝对“零学习成本”提升最大，建议 DSH 首发（当前 dsh adapter 仍为预留）；③dashboard＝最低成本的高感知改进，先做；④去提示词层＝方向正确但依赖 1/2 承接，不要先删后补。

### 4.5 v0.3 方向评估：1 个总控 skill + 统一 CLI + 仓库原生状态

| 现有摩擦 | v0.3 是否能消 | 条件 / 残余 |
| --- | --- | --- |
| P1-2 入口分散、人肉复制提示词（§2-#2） | **能** | skill 由 adapter 落进目标仓、`harness` 命令在仓库内可见可执行；否则仍退回 `scripts/` 路径 + 粘贴 |
| P1-3 学习面 1356 行 / 0B 要求 568 行（§2-#3） | **大部分能** | 总控 skill 只装“何时做什么”短清单 + `status` 输出；首次接入仍需 1 页说明（目标/授权/profile） |
| 5 场景→工具映射 | **能** | CLI 子命令覆盖 status/start/verify/release/handoff；`prompt` 层降为内部模板 |
| P2-5 生命周期命令缺失 | **能** | 子命令补齐；若 CLI 只提示“请手动改计划”，则只半消 |
| P2-6 发布依赖 strict 知识 | **部分** | CLI 统一 standard/strict 判定；tag/push、版本策略、风险接受仍需人确认 |
| P1-1 计划↔git 双状态反复红 | **不能自动消**（方向是入口不是机制） | 必须显式定 policy：`start/status` 自动维护“未提交段”，或 check 对“未声明”降 WARN；否则仓库原生状态反而让冲突更显眼 |
| P2-7 证据闭环（测试→JUnit→PASS） | **部分** | CLI 可编排 evidence/verify；不能替项目产出可信测试结果，真实 test command/XML 仍靠宿主 |
| 仓库自描述（本次实测：adopted 仓仅 Makefile 注释提到 kit，AGENTS/skill 均未提） | **能，但缺三件套** | skill + AGENTS 路由 + `status` 缺一不可；只加 CLI 不加仓库内入口，agent 仍不知道有 CLI |
| 语义工作（文档蒸馏、死代码、真机/性能、行为质量） | **不能** | 不在工具范围；skill 只能把它显式列为“未验证/需人评审” |
| 人工决策（profile、测试命令、--force、提交/发布） | **不能** | 可减少（默认值+dry-run+一次确认），不能取消 |
| 证据可伪造 / 行为级评估 | **不能** | 不做 A/B eval 时只能说成本更高，不能证明 agent 表现变好 |

> 判断：v0.3 方向**能消掉“入口/复制/发现”这层成本（P1-2、P1-3 的大头）**，让 kit 从“外部文档 + 剪贴板”变成“仓库里可见可调用的工具”；但 **P1-1 双状态对账、P2-7 证据闭环属于机制问题，不会因换入口自动消失**，必须在 CLI 里显式编排（自动同步计划/证据，或调整门禁严格度），否则摩擦只是从“人记文档”转移到“agent 记 CLI 规则”。要让“仓库原生状态”真正原生，adopted 仓需落地三件套：`make status`（或 `harness/status.json`）+ AGENTS 一行路由 + `.dsh/skills/harness/SKILL.md`；只做 CLI 不够。

## 5. 结论

- **学习成本主要来自前 3**：①入口分散（4 脚本+Makefile+提示词库+4 份文档，人要做场景→工具映射并复制粘贴）；②计划/证据需要与 git/提交/证据三界对账（日常每步维护第二状态）；③文档体积与重复（1356 行/35.9k tokens，0B 要求 568 行）。
- **是否零学习成本：否。** 人仍需 clone、`cd`、`copy`、paste；agent 在“接入后日常”已可只靠 AGENTS+`make help` 运转（这是亮点），但发布/交接仍要读文档和隐藏命令。差距不在安装动作（<1s），而在“启动入口”和“状态维护”。
- **对 v0.3 的判断**：1 个总控 skill + 统一 CLI + 仓库原生状态，足以把“入口/复制/发现”成本降到接近零（见 §4.5）；但若不把“计划↔git 同步”和“证据生成”编进 CLI 流程，日常与发布的摩擦会保留。skill/CLI 是入口层，机制层仍需 1 个政策决定 + 2 个自动编排。
- **一句话触发需要**：§3 最小信息集 + 目标仓内可发现入口（skill 或 AGENTS 指向 `harness` CLI）+ CLI 默认只读/dry-run + `status` 直接输出“下一步”。做到这三点后，人只需说一句话并确认一次，agent 全程可自服务；其中 kit 路径与测试命令可进一步由 skill 探测 + 一次询问替代，最小信息集可压到“目标路径 + 意图 + 写权限”3 项。
