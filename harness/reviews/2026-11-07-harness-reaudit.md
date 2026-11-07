# 2026-11-07 Harness 独立复评（Phase 2.3）

> 审查者：独立只读复评（非作者；auditor-instructions）。对象：`main` @ `1a25880` + Phase 2 未提交工作树；复评期间工作树有并发编辑（如 `harness/evidence/README.md` 中途被改），下文行号/状态以我读取时为准。
> 方法：只读。实际运行 `make check`、`make verify-static`、`make verify-claim`、`make adapters-check`、`make doctor`、`make resume`、`make handoff` 与只读 git/统计命令；未跑 xcodebuild/模拟器/真机；唯一写入为本报告。
> 证据格式：`file:line` + 命令输出。改造前对照：`harness/runs/harness-audit/02-audit-instructions.md`、`03-audit-verification.md`（本机 gitignore）。

## 1. 结论

- **独立五子系统 ≈3.6/5（72%），低于自评 ≈4.0（80%）；建议下调 Verification、State、Scope、Lifecycle。**
- **L3 不能按"已达成"记录，应为"能力就绪、默认流程未接线"**：`verify-claim` 三值真实可用，但不在 `make check`/`verify-static`/`end`/pre-push/CI 中，且旧证据可跨 commit 复用。完成声明的否证依赖 agent 主动跑 skill，而非仓库强制。
- **对外标杆 17/35（2.4/5，11-06）→ 独立估 ≈24/35（3.4/5，+7）**。包装/叙事提升最大；外部可复现与真实首访仍"未验证"，未达 ≥4.2/5 目标。
- 未发现虚报机制：scorecard 列出的主要机制我均独立复跑通过；偏高主要在 Verdict 与分数的解释，见 §2/§5。

## 2. 评分（1–5：自评 vs 独立）

| 子系统 | 自评 | 独立 | 我独立核实的依据（命令/文件） | 下调理由 |
|---|---|---|---|---|
| Instructions | 4.0 | **4.0** | `make check-harness` 19 项 PASS；AGENTS 1576/1600、refs 932/925/929（v2）；6 个嵌套 AGENTS ≤3.6KB；6 个 skills frontmatter | 预算余 24 token；§ 引用 sensors 空转（§5-#5）但主结构成立 |
| State | 4.0 | **3.5** | front matter/唯一 active/未提交交叉比对 PASS（`make check-plan`）；`make resume/end` 可跑；plan 510 行 | 计划"下一步"已过期（plan:497-499 vs 进度 plan:405-420）；resume 打印错误章节（§4-B） |
| Verification | 4.5 | **4.0** | `make check` 6 组 PASS（0.29s）；`verify-static` 4.61s/42 单测；`verify-claim` 3/3 PASS；120@Test/3 UI/80 Swift 0 违规 | verify-claim 未接线；旧证据可蒙混；done 计划免证据；证据 ID 不校验（§4-A/B） |
| Scope | 3.5 | **3.0** | L0/L1/L2 + `scope.allow/deny` + 红队限定在文件里存在 | `plan.py` 用 allow 过滤实际改动，越界不报错；allow 可由 agent 自改（§4-C） |
| Session Lifecycle | 4.0 | **3.5** | 6 skills + `doctor/resume/end/handoff` 可跑；未验证项单列；plan 状态机 | resume/handoff 输出过期/错误章节；无真实交接演练；动态 CI 默认 skip |
| **综合** | **≈4.0** | **≈3.6（72%）** | 上表 | 差距集中在 Verification 接线 + State/Scope 准确性 |

## 3. 证据：哪些是我独立核实、哪些是自评/未验证

**独立核实（本机只读复跑）：**

| 命令 | 实测结果 |
|---|---|
| `make check` | PASS 0.288s；docs 白名单 docs 9/10、根 4 个 md；token AGENTS 1576/1600、contracts 932/950、verification 925/950、workflow 929/950；arch 80 文件 0 违规；计数 120≥120 / 3≥3；harness 19 项；plan 1 active PASS；adapters PASS |
| `make verify-static` | PASS 4.607s；3 条 evidence schema PASS；`Ran 42 tests … OK` |
| `make verify-claim` | `PASS×3`（unit/ui/device），`SUMMARY: pass=3 fail=0 unverified=0`，exit 0 |
| `make adapters-check` | PASS（6 skills；hooks/CLAUDE/agent 示例就绪） |
| `make doctor` | OK 7 / FAIL 0 / exit 0：Xcode 27.1、iOS 26.4.1、mobilebuildmcp、python 3.14.7 |

**自评/未验证（不能当作已核实）：** 构建/单元/UI/真机"通过"——3 条 evidence 分别绑定旧 commit `3935e60`/`fb217f6`/`71bec62`，当前工作树 dirty 且无新证据；首访 4/5 为作者自测（`harness/plans/2026-11-06-benchmark-opensource.md:436-437`），无陌生人记录；Claude Code 适配未实测（`HARNESS.md:115`、plan:457）；17/35 基线为上一轮外部口径，未独立复现。

## 4. "完成声明可否证"：3 个 agent 可能蒙混的声明

| agent 声明 | 仓库现在能否否证 | 关键证据 | 最小修复 |
|---|---|---|---|
| "Phase 2 改动已验证（verify-claim 全 PASS）" | ❌ 不能 | 证据 commit 是 HEAD 祖先即 PASS（`tools/verify-claim.py:95-113`）；当前树无新证据；verify-claim 不在 `Makefile:66,92,109`、`.githooks/pre-push:41`、CI | evidence.commit 必须 == HEAD 或在计划 `submitted`；`make end` 默认跑 `verify-claim --all` |
| "计划已完成（done），证据齐全" | ❌ 默认门禁不能 | done 计划证据缺失只 WARN（`tools/plan.py:735-747`）；`EVIDENCE_COLS` 只查命令/结果/环境（`plan.py:48`），不查"证据ID"、不解析 evidence；当前 active 计划多行写 `—（基线盘点）` 仍 PASS（plan:426-446） | 证据ID列必填并解析到 `harness/evidence/*.json`（verdict=PASS）；done 与 active 同等严格 |
| "测试只增不减 / 范围没越界 / 规则没漂移" | ⚠️ 部分 | 计数与 skip 能拦（`check-tests` PASS；删 @Test 会 exit 1）；但"未改既有断言"不可检；scope 越界不可检（`plan.py:504-516` 用 allow 过滤后比对）；§ 引用实际检查 0 处（`tools/check-harness.py:256-280` 只扫根 AGENTS，根 AGENTS 无 `§` 形式引用） | 断言 diff 检查；全量 `git status` vs allow、allow 外改动 FAIL；解析"第 N 节"+扫嵌套/skills |

> 诚实边界：证据可被伪造已声明（`HARNESS.md:117`、`harness/evidence/README.md:84`）；上表是"低成本蒙混路径"，不要求密码学防伪。

## 5. 被挑战的假设

1. **"完成声明可被三值否证"（scorecard L3）**：只有主动跑 `make verify-claim` 时成立；默认门禁与 CI 不跑 → 只能记"条件成立"，不足以称 L3 达成。
2. **"3 条 clean-tree evidence PASS ⇒ 当前 harness 有动态验证"**：证据全部来自 11-05/06 旧 commit，当前 Phase 2 工作树无证据，不能外推。
3. **"make check / verify-static 绿 = 完成门禁绿"**：`check` 的 6 组不含证据 verdict；`check-evidence` 只验 schema，不验 PASS/FAIL。
4. **"scope.allow 能防越界"**：只比对"声明 vs 实际"且先用 allow 过滤；allow 外改动被丢弃而非报错，allow 本身可由 agent 改。
5. **"§ 引用机检"**：当前输出 `§ 引用：0 处命中` 是空转，不是"0 违规"；nested AGENTS 的引用完全未扫。
6. **"Verification 4.5 / 综合 4.0"**：独立为 4.0 / 3.6；4.5 需要默认完成流程强制 claim 校验才成立。
7. **"17/35 是当前对外分"**：已过期；独立 ≈24/35，但 ≥4.2 目标仍未达。
8. **"预算内可长期演进"**：AGENTS 余 24 token、refs 余 18–25；一条新规则即红。嵌套 AGENTS/skills 是扩展位（可缓解），但根规则实际冻结。
9. **"clean clone 可复现"**：未实测；且 HEAD 缺 Phase 2 文件（`tools/adapters.py`、`docs/harness-scorecard.md`、`harness/adapters/` 未跟踪；Makefile/check-docs 有未提交修改）→ 当前状态不能由 clone 复现。

## 6. 仍缺的 P0/P1（按影响排序，含最小修复）

- **P0-1 Verification 未接线**：`verify-claim` 不在任何默认完成门禁/CI/pre-push（`Makefile:66,92,109`、`pre-push:41`）；done 计划免证据；证据 ID 不解析。→ `make end`/`verify-static` 加 `verify-claim --all`；证据 ID 必填并解析；done 严格。
- **P0-2 证据时效/绑定**：祖先 commit 即 PASS（`verify-claim.py:108-113`）；device evidence 的 xcresult 是 `~/Library/...` 机器路径（`harness/evidence/20261106T053620Z-device-tests-pass.json:16`），换机即 UNVERIFIED。→ 证据 commit 必须 HEAD 或 `submitted`；旧证据对当前 claim FAIL/WARN；记录仓库相对路径或摘要。
- **P0-3 State 准确性**：active 计划"下一步"仍是"等用户授权提交 Phase 1 第一批"（plan:497-499），与进度（:405-420）矛盾；`resume` 因前缀匹配把"## 2. 目标形态"当"目标"整章打印（`plan.py:205-217`）。→ 进度↔下一步一致性机检；section 精确匹配并截断 brief。
- **P1-1 Scope 过滤假绿**：`plan.py:504-516` 只比对 allow 内路径，allow 外改动被忽略；"一次一个 active"仅 WARN。→ 全量 `git status` vs allow，越界 FAIL。
- **P1-2 指令漂移 sensor 空转**：`check-harness.py:256-280` 只扫根 AGENTS 的 `§` 引用，实际 0 处；nested AGENTS/skills 未扫。→ 支持"第 N 节"、扫全部指令文件、加负向 fixture。
- **P1-3 外部可复现未验证**：clean clone 未测（本只读复评未写临时目录）；Phase 2 未提交；`docs.yml` 与 `verify.yml` 双跑 docs。→ 提交 Phase 2 + clean clone `make check` 证据；合并 CI。
- **P1-4 行为/性能不可否证**：P0-1/P0-3 无行为测试（`HARNESS.md:110`）；"不改既有断言"无 diff 检查；无性能回归门禁（`HARNESS.md:113`）。→ 先并发/持久化红测 + assertion diff 检查 + perf 比较脚本。
- **P1-5 token 余量**：AGENTS 24、refs 18–25 token；建议 caps 1650/975 或"新规则只进嵌套/skills"（后者不受预算）。
- **P2**：scorecard "make check 5 组"实为 6 组；"四层验证矩阵"表述与 `references/verification.md` 不完全对应；`doctor` 打印本机绝对路径；"schema v2"仍 `schemaVersion: 1`；`.github` 无 issue/PR 模板/CHANGELOG/release。

## 7. 对外标杆（独立评估，与 2026-11-06 的 17/35 对比）

| 维度 | 11-06 | 现在 | 证据 |
|---|---:|---:|---|
| 文档可读性 | 2 | **4** | README 143 行 + 英文概览（`README.md:124-143`）+ 4 截图 + 无 Xcode quickstart（`:30-38`）+ docs/README 唯一索引；真实首访未验证 |
| 开源包装 | 1 | **3** | MIT LICENSE、CONTRIBUTING 79 行、截图、英文概览；缺 issue/PR 模板、CHANGELOG、release、徽章（`.github` 仅 2 workflows） |
| 外部可复现 | 2 | **3** | 静态链路纯 python3 + ubuntu CI（`verify.yml:74-87`）；clean clone 未实测、Phase 2 未提交 |
| 标杆叙事 | 2 | **4** | HARNESS 160 行：问题/五子系统/落地矩阵/证据政策/采用指南/局限/来源；case 页 + scorecard |
| 体系完整度 | 4 | **4** | 6 组静态门禁 + evidence + 6 skills + CI + pre-push；行为测试/性能门禁仍缺 |
| 证据可审计 | 3 | **3** | 三值 + 3 条 PASS 真实；但未接线、时效、ID 不校验（P0-1/2） |
| 产品与代码 | 3 | **3** | 真实 App、120+3、arch 0 违规；P0-1/P0-2/P0-3 未修（`HARNESS.md:110`） |
| **合计** | **17/35** | **≈24/35（3.4/5）** | +7；距 ≥4.2/5 目标仍差约 0.8；提交 Phase 2 + clean clone 验证后再评 |

## 8. 最小验证清单

- [x] `make check` PASS（0.29s）；`make verify-static` PASS（4.6s，42 单测）；`make verify-claim` pass=3；`make adapters-check` PASS；`make doctor` exit 0。
- [ ] 修 P0-1 后负向验证：无新 evidence 的"已完成"计划应 FAIL/UNVERIFIED；done 计划缺证据应 FAIL。
- [ ] clean clone 复现（需写临时目录；本只读复评未做）：Phase 2 提交后 `git clone . /tmp/duiyi-fresh && make check`。
- [ ] Phase 2 提交后为改动生成 evidence，`make verify-claim --all` 只接受 HEAD 绑定证据。
- [ ] 陌生人首访 5 问实测（现为作者自测 4/5，plan:436-437）。
- [ ] 嵌套 AGENTS § 漂移负向 fixture（改目标节号 → `check-harness` 应 FAIL）。
- [ ] 断言弱化/scope 越界的 diff 门禁 + P0-1/P0-3 红测。

## 9. 局限

- 只读复评：未跑 xcodebuild/模拟器/真机，动态层与行为正确性只能标"未验证"；未做 clean clone（写约束）。
- token 为 v2 估算口径，非真实 tokenizer；五子系统分数是工程判断；17/35 基线为上一轮口径，未独立复现；首访/体验未验证。
- 本报告为唯一写入文件（`harness/reviews/` 新建）。
