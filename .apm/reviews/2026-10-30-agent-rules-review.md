# Agent 规则骨架引入 · 独立审查报告

> 审查日期：2026-10-30
> 审查对象：`AGENTS.md`、`references/`、`tools/`、`Makefile`、`.github/workflows/docs.yml`、`.apm/plans/_template.md`、`docs/21-cross-session-handoff.md`，以及 `HANDOFF.md`、`docs/README.md`、`.gitignore` 的修改。
> 审查方式：独立只读审查；未修改被审查文件，未读 `.env`；未使用起草对话、作者自评或既往审查结论。
> 行号说明：文中行号为 2026-10-30 审查时的仓库快照；后续编辑可能漂移。

## 复跑与边界

实际运行的只读检查：

- `PYTHONDONTWRITEBYTECODE=1 python3 tools/check-docs.py` → **PASS**（33 篇文档、110 条相对链接）
- 团队基线 `sync_team_baseline.py --check AGENTS.md` → `[OK]`
- `make help`、`make check`、`make handoff` → 本机通过
- `TEAM_RULES=/nonexistent make check` → check-docs 先 PASS，随后 **exit 2**
- token（按模板 `est_tokens` 口径）→ AGENTS **1930/2000**、contracts **800/800**、verification **788/800**、workflow **770/800**
- 链接目标精确大小写检查 → **0 处不匹配**（Linux CI 可用）
- `tools/plan.py` 在 `/tmp` 副本冒烟 → `new`、同日重复拒绝、`brief` 可用；同日建第二个计划后 `latest` 选错；缺 `_template.md` 时 traceback
- `make -n` 核对所有目标命令展开；`make test`、`make test-ui`、`make build`、`make device-test`、`make measure-launch` 未执行

## 1. 结论

**有条件通过**。文档门禁、团队基线、token 预算（按模板口径）通过，未发现 P0。P1 集中在接手闭环、无模板仓行为、计划入库未决、`SpeechSessionGate` 措辞和红队范围；建议在用户确认前解决或明确接受，否则验收 #1/#5/#6 只能算部分满足。

## 2. 问题表

### P0

无。

### P1

| 问题 | 证据/位置 | 影响 | 建议 |
|---|---|---|---|
| P1-1 “最新计划”按文件名字典序选择，不按活跃状态或修改时间 | [tools/plan.py:22-30](../../tools/plan.py#L22-L30)；[docs/21-cross-session-handoff.md:60](../../docs/21-cross-session-handoff.md#L60)；[AGENTS.md:50](../../AGENTS.md#L50)；副本实测先建 `speech-gate` 再建 `alpha-one`，`latest` 仍返回 `speech-gate` | `make handoff` 可能让下一棒读错计划；本次审查计划提交后本身会成为“最新计划” | 用 mtime、活动指针或计划状态字段；归档已完成计划；`brief` 明确标注 active |
| P1-2 无模板仓的机器上 `make check` 必红，但被写成通用门禁 | [Makefile:7](../../Makefile#L7)、[Makefile:46-50](../../Makefile#L46-L50)；[HANDOFF.md:560](../../HANDOFF.md#L560)；[AGENTS.md:8](../../AGENTS.md#L8)、[AGENTS.md:43](../../AGENTS.md#L43)、[AGENTS.md:93](../../AGENTS.md#L93)；[docs/21-cross-session-handoff.md:30](../../docs/21-cross-session-handoff.md#L30) | 新机器/新 Agent 卡在第一天清单；可能反复克隆外部仓或改规则绕过；验收 #5 未闭环 | 明确“报错还是降级”；建议拆 `check-local` / `check-team`，无模板仓时 SKIP 并提示；HANDOFF 清单标注前置条件 |
| P1-3 `.apm/plans/` 是否入库未决，但文档与 CI 已依赖 | `git status` 显示未跟踪，`git check-ignore` 确认未忽略；[docs/README.md:77](../../docs/README.md#L77)；[docs/21-cross-session-handoff.md:5](../../docs/21-cross-session-handoff.md#L5)；[tools/plan.py:61](../../tools/plan.py#L61) | 若不入库，干净 clone 的 docs CI 因 `../.apm/plans/` 链接缺失变红，接手闭环也不存在 | 至少提交 `_template.md`（建议连同活跃计划）；`plan.py` 对缺失模板给清晰错误；明确完成计划归档策略 |
| P1-4 铁律 3 把尚未实现的 `SpeechSessionGate` 写成现行“必须经”约束 | [AGENTS.md:61](../../AGENTS.md#L61)；[references/contracts.md:18](../../references/contracts.md#L18)；[HANDOFF.md:393](../../HANDOFF.md#L393) 仅为“建议”；全仓 `grep` 无 `SpeechSessionGate`；[AppEnvironment.swift:10](../../Duiyi/App/AppEnvironment.swift#L10) 只有共享 `SpeechRecognizing` | Agent 会误判既有机制，或擅自实现 P0-1（L2，需确认） | 区分“现行约束”与“P0-1 目标”；实现前写清当前只能共享单引擎、禁止每 VM 建引擎 |
| P1-5 红队范围在 AGENTS 与 workflow 间冲突 | [AGENTS.md:91](../../AGENTS.md#L91) 限定并发/持久化/发布；[references/workflow.md:11](../../references/workflow.md#L11) 的 L2 含跨模块重构且一律“独立红队”；[references/workflow.md:24](../../references/workflow.md#L24) 又写“只用于 L2”；[AGENTS.md:15](../../AGENTS.md#L15) 团队基线要求 L2 对抗审查 | 跨模块重构是否红队不确定；验收 #1“规则自洽”不成立 | 统一措辞：把跨模块重构纳入红队，或明确 workflow 以 §7 为准 |

### P2

| 问题 | 证据/位置 | 影响 | 建议 |
|---|---|---|---|
| P2-1 token 预算无门禁且已贴顶 | 模板仓 `scripts/check_rules.py:66-68` 的估计器；AGENTS 1930/2000、contracts 800/800、verification 788/800、workflow 770/800；`make check` 与 CI 都不统计 | 下一次编辑就可能超预算且无人发现；验收 #4 未定义分词器，不可复现 | 把 token 检查加入 `check-docs.py`（固定估计器）；给 AGENTS/contracts 留余量 |
| P2-2 AGENTS 自身违反“计数只放 verification” | [AGENTS.md:27](../../AGENTS.md#L27)、[AGENTS.md:64](../../AGENTS.md#L64) 含精确计数；[AGENTS.md:90](../../AGENTS.md#L90) 说本文件只写“只增不减”；[references/verification.md:33](../../references/verification.md#L33) 才是声明的位置 | 计数变更要改多处，易漂移 | 从 AGENTS 删除精确计数，或修改 §7 规则 |
| P2-3 `make handoff` 摘要缺 5 项中的 2 项 | [tools/plan.py:69-74](../../tools/plan.py#L69-L74) 只打印进度/未提交/下一步/待确认；[docs/21-cross-session-handoff.md:22](../../docs/21-cross-session-handoff.md#L22) 要求 5 项、[:36](../../docs/21-cross-session-handoff.md#L36) 说把该输出整段发给下一棒 | 下一棒可能漏掉“已排除/验证证据”，重复无效方案 | `brief` 增加这两节，或文档改为“发 brief + 必读计划文件” |
| P2-4 `measure-launch` 默认 5 次与 n≥10 规则冲突 | [Makefile:8](../../Makefile#L8)、[Makefile:62](../../Makefile#L62) 默认 5；[references/verification.md:28](../../references/verification.md#L28)、[:49](../../references/verification.md#L49) 要求 n≥10；[HANDOFF.md:299](../../HANDOFF.md#L299) 也写默认 5 | 默认命令产出不合规样本，可能被当作性能结论 | `N ?= 10`，或在 N<10 时告警 |
| P2-5 docs CI 把计划纳入链接/围栏检查且无 path filter | [tools/check-docs.py:21-28](../../tools/check-docs.py#L21-L28) 扫描 `.apm/**/*.md`；[docs.yml:3-5](../../.github/workflows/docs.yml#L3-L5) 所有 push/PR 触发 | 计划里的临时或历史链接会让 CI 变红；每次 push 都跑 | 排除 `.apm/plans/`（或只查 `_template.md`）；加 `paths` 过滤（待确认） |
| P2-6 `references/` 与 HANDOFF/docs13 内容重叠，未声明优先级 | [references/contracts.md:1-9](../../references/contracts.md#L1-L9) 与 [HANDOFF.md:307](../../HANDOFF.md#L307)、[docs/13-architecture-analysis.md:69](../../docs/13-architecture-analysis.md#L69)；[docs/README.md:34-40](../../docs/README.md#L34-L40) 又列一套命令/规则表 | 规则变更时多处要同步，单一真源被削弱 | 明确“代码/docs13 为事实、references 为规则视图”的优先级；能链接就不复述 |
| P2-7 `plan.py` 缺少模板与输入校验 | [tools/plan.py:61](../../tools/plan.py#L61) 缺模板直接 traceback；[docs/21-cross-session-handoff.md:32](../../docs/21-cross-session-handoff.md#L32) 声称 2–5 个英文小写词但 [tools/plan.py:54](../../tools/plan.py#L54) 未校验；目标/验收为空也能 handoff | 首次使用体验差；空计划可被交接 | 缺失模板给明确错误；校验目标/验收非空（或 `brief` 告警） |
| P2-8 `APM_DEVICE` 的 ID 类型文档不一致（不确定） | [references/verification.md:14](../../references/verification.md#L14) 写 mobilebuildmcp ID；[.apm/tools/device-test.sh:32](../tools/device-test.sh#L32) 写 UDID；脚本又把同一值传给 `xcrun devicectl`（[:41](../tools/device-test.sh#L41)、[:59](../tools/device-test.sh#L59)） | 换设备时可能环境检查失败；未经真机验证 | 在真机确认 devicectl 接受哪种 ID，统一 HANDOFF/verification/脚本措辞 |
| P2-9 停止上报的格式链断了 | [references/verification.md:54](../../references/verification.md#L54) 让转 `workflow.md`，但 workflow 无“上报/阻塞报告”模板；模板仓 `references/verification.md:28` 原有“## 阻塞报告”字段 | Agent 停下来了但不知道该报什么，交接质量下降 | 在 workflow.md 或 verification.md 补 5 行阻塞报告模板 |

### 安全与提交卫生

未发现密钥/凭证；`tools/*.py` 不读 `.env`；改动未包含 `build/`、`.apm/runs/`、trace。唯一提醒：审查计划 `2026-10-30-agent-rules-review.md` 含本机绝对路径，若随 `.apm/plans` 入库建议脱敏；`actions/checkout@v4` 未 pin SHA 属低风险改进。

## 3. 被挑战的假设

- **“文件名排序 = 最新/活跃计划”**：不成立。`latest()` 只做路径字典序；同日多计划时与创建/修改时间无关，已用副本复现。
- **“`references/` 仍是单一真源的一部分”**：部分是。它是第四个规则内容位置，且与 HANDOFF/docs13 重叠，未声明优先级；测试计数已经出现“AGENTS 自己违反自己规则”的具体漂移。
- **“`make check` 是通用门禁”**：不成立。它依赖仓库外 `../../agent/template`，新机器必红；错误信息清楚，但文档把它写成标准门禁。
- **“token 预算已通过”**：只在模板 `est_tokens` 口径下通过（AGENTS 1930/2000，contracts 恰好 800/800）；无门禁、无余量，换更严格分词器可能超 2000。
- **“CI 只跑 check-docs 所以稳定”**：对团队仓成立，但仍依赖 `.apm/plans` 和 `references/` 被提交；`.apm/plans` 的入库决定未定即可让 CI 变红。
- **“`SpeechSessionGate` 是现行铁律”**：不成立。代码无此类型；HANDOFF P0-1 只是建议。
- **“`make handoff` 输出足够交接”**：不完整。`brief` 只打印 5 项中的 3 项，靠“先读计划文件”兜底。

## 4. 缺失信息

- 团队模板仓的访问方式与新机器 clone 路径（是否私有、`TEAM_RULES` 放在哪）。
- `.apm/plans/` 是否入库；完成后的计划是归档、删除还是保留。
- 无模板仓时 `make check` 的期望行为：报错还是降级提示。
- token 预算使用哪个估计器、是否要纳入 `make check`。
- P0-1/`SpeechSessionGate` 是否已授权实现、什么时候实现。
- `APM_DEVICE` 应填 mobilebuildmcp ID 还是 devicectl UDID；需真机确认。
- CI 是否需要 path filter、是否应检查 `.apm/plans`。
- `references/` 与 HANDOFF/docs13 冲突时的优先级。

## 5. 最小验证清单

- [ ] 干净 clone（无模板仓）：`make check-docs` 通过；`make check-agents` 行为符合已定策略；文档写清前置条件。
- [ ] 干净 clone（plans 入库）：在 Linux/大小写敏感文件系统跑 `python3 tools/check-docs.py`，确认 `../.apm/plans/` 链接。
- [ ] 同日创建两个计划后跑 `make handoff`，确认选到预期计划；再验证完成计划不会被当作活跃计划。
- [ ] 用固定估计器复跑 token 统计，并接入 `make check`/CI。
- [ ] 对 5 项齐全的计划跑 `make handoff`，确认摘要包含“已排除/验证证据”（或文档改为发完整计划）。
- [ ] `make test`、`make test-ui`、`make build`（本次未跑）。
- [ ] 真机 `make device-test` 与 `make measure-launch N=10`（本次未跑）。
- [ ] `git status --short` 复查无 `__pycache__`、`build/`、`.apm/runs/`、trace；扫描新文件无密钥。
- [ ] 修订 `SpeechSessionGate` 与红队范围措辞后重跑 `make check`，并在 GitHub 干净 checkout 上跑一次 docs CI。

## 附：本次审查的只读性

本报告由独立审查者生成，未修改被审查文件。审查计划 `2026-10-30-agent-rules-review.md` 保持原样；如需将本报告并入计划，请由作者追加。
