# 执行器 B：mattpocock code-review skill（对照实验，2026-11-19）

> **用途**：executor 对照实验，审查对象为已归档 L2 变更 diff `1961368..f3e2bda`，不是当前 Change 的门禁证据。
> **执行环境**：Claude Code 2.1.310 + DeepSeek V4.1 Flash（`deepseek-flash`）；Read/Grep/Glob/Bash/Task；按 `mattpocock/skills` code-review SKILL.md 执行，宿主支持 subagent 时并行两轴。
> **耗时/规模**：约 225 秒；输出约 8.8k 字符。
> **对象**：临时 detached worktree at `f3e2bda`；未读取历史 review 报告。

## 审查过程

- 固定点 `1961368`，终点 `f3e2bda`；`git diff 1961368...f3e2bda` 非空（22 文件，+925/−8），5 条提交。
- 规格源：`openspec/changes/cache-language-capabilities/{proposal,design,tasks}.md` + `specs/language-catalog/spec.md`。
- 标准源：根/嵌套 `AGENTS.md`、`CONTRIBUTING.md`、`references/{contracts,verification,workflow}.md`、`docs/{02-architecture,decisions,AGENTS}.md`、`harness/AGENTS.md`。
- 宿主支持 subagent：Standards 与 Spec 两个审查者以全新上下文并行启动，互不共享上下文。以下为两份报告（轻整理）。除调用点数量与文档行号外，我未单独复跑门禁；报告中 `PASS` 为子审查者的复跑声明。

---

## Standards

**Agent-reported clean:** every changed path is inside the Delivery Contract allowlist and the deny list is untouched; `tools/check-arch.py` PASS (0 violations); `check-test-baseline.py` PASS (139 unit / 3 UI / 142 device consistent); `verify_claim.py --all --fresh --strict` PASS (unit 139≥139, UI 2≥2, skip 1, evidence recomputed from JUnit); no existing test or assertion modified.

1. **HARD (docs sync, low risk)** — `docs/02-architecture.md` still documents the old state: line 67 lists `LanguageCataloging` default as `StaticLanguageCatalog`, line 26 omits `Duiyi/Services/Language/`, line 350 says capability probing is "仍散在 View". `docs/AGENTS.md` §2 requires "文档与代码冲突时以代码/最新验证为准，并顺手修正文档"; `references/contracts.md` §1 routes new modules through docs/02. Scope allow omits `docs/`, so this needs a scope update or explicit follow-up.

2. **HARD (delivery evidence, minor)** — `tasks.md` Task 4 is `[x]` claiming `make verify-static` and `make release-check` exit 0, but the Change Record's 验证证据 table records only `make delivery-check`, with no exit code or evidence ID. Violates root AGENTS §5 ("证据：完成声明附命令/退出码/环境") and CONTRIBUTING §4; `tools/delivery_check.py` does not run those two commands.

3. **JUDGEMENT (device verification)** — the matrix requires 真机 for 语音/翻译/TTS (`references/verification.md` 验证矩阵; CONTRIBUTING §4), yet evidence is simulator-only and the tests fake speech/TTS/translation probes (`contracts.md` §6 "不得 mock 能力检查"). The record's 未验证项/豁免 makes this rule-compliant, but device acceptance stays open and the fakes are acceptable only because they exercise cache semantics.

4. **JUDGEMENT (Duplicated Code)** — default `LanguageCapability` construction is repeated in `Duiyi/Domain/LanguageCatalog.swift:23-32` and `Duiyi/Services/Language/SystemLanguageCatalog.swift:44-52`; the pair-order predicate `source.rawValue < target.rawValue` (`SystemLanguageCatalog.swift:120`) duplicates `OrderedLanguagePair.init` (`:149`).

5. **JUDGEMENT (Mysterious Name / brittle test)** — `SystemLanguageCatalogTests.swift:132` asserts `translation.currentCallCount() == 15` next to `AppLanguage.allCases.count` at lines 130-131; 15 is C(6,2), so adding a language fails the test without a behavior change (`DuiyiTests/AGENTS.md` §1 "与实现细节解耦"). Derive the expected count.

6. **JUDGEMENT (hardcoded copy)** — `LanguageChipGrid.swift:40` emits the user-facing English hint `"Unavailable language"` instead of going through `Domain/Copy.swift`; pass a localized hint from the caller.

7. **JUDGEMENT (composition / Refused Bequest)** — `SystemLanguageCatalog.swift:81-83` constructs its concrete adapters as default arguments rather than at `AppEnvironment` (`Services/AGENTS.md` §4 "由 AppEnvironment 注入"); injectable, so low risk. `StaticLanguageCatalog.refreshCapabilities()` (`LanguageCatalog.swift:42-44`) is a no-op added only to satisfy the widened protocol.

---

## Spec

### (a) Missing or partial

1. **Refresh is one-shot, never refreshing changed entries.** `refreshCapabilities()` returns immediately once `refreshed` is true. Proposal: "*Cache probe results for the catalog lifetime and refresh explicitly; repeated refreshes do not re-probe unchanged entries.*" Only *unchanged* entries are exempt in the wording, but nothing is ever re-probed. The catalog is the app-lifetime default in `AppEnvironment`, so a language installed later (even via the sheet's own "redownload models") stays disabled until relaunch.

2. **Only Home applies the disabled set.** Nine other `LanguageChipGrid` call sites (`SettingsSheet` ×2, `LanguagePickView` ×2, `InterpretationSettingsSheet` ×2, `MeetingSettingsSheet`, `CaptionPaneView`, `InterpretationView`) never pass `unavailableLanguages`. Spec Requirement: "*The system SHALL let language selection views render catalog-reported unsupported languages as disabled.*" Tasks scope this to Home, but the requirement says "views". *(调用点数量已由我核对为 9。)*

3. **Direct pair results are never cached.** `translationPair(from:to:)` reads `pairStatuses` but does not write the probe result back. Design: "*Translation pair status is cached by ordered language pair.*" Any pair not populated by a prior full refresh (including every call before first refresh) re-probes on each call.

4. **A3 is unverified at the grid level.** Acceptance A3 = "*grid disables catalog-reported unsupported languages*", but the only test calls `LanguageCatalogSelection.unavailableLanguages`; no test exercises `LanguageChipGrid`/`.disabled`.

### (b) Not asked for (scope creep)

5. **All-three capability AND.** The helper disables a language if `speech`, `translate`, or `speak` is false. The spec only requires: "*GIVEN the catalog reports a language as not speech-capable … THEN that language is disabled.*" A speech-capable language with no TTS voice or translation pair is now disabled in the language picker — not requested, and the test (`.thai` with `speech=false`, `speak=false`) can't distinguish the two rules.

### (c) Implemented but looks wrong

6. **"Ordered" pairs are actually unordered.** `OrderedLanguagePair.init` sorts by `rawValue`, so reverse lookups alias, and refresh probes only `source.rawValue < target.rawValue`. Design: "*Translation pair status is cached by ordered language pair.*" A directional adapter's reverse answer is lost; `TranslationAvailabilityService`'s internal symmetrization masks this in production.

7. **Pre-refresh permissiveness is incomplete.** Design: "*Before the first successful refresh, preserve the current permissive catalog behavior.*" `capability(_:)`/`speechSupported` are permissive, but `translationPair` probes the live system and can return `.unsupported` pre-refresh, unlike `StaticLanguageCatalog`'s `.supported`. No test covers this.

8. **Current selection can become disabled.** After refresh, Home can render the persisted `userLanguage` chip disabled; spec says such a language is "*disabled and not selected*".

Minor: the `hasRefreshed` guard isn't atomic, so concurrent refreshes can double-probe.

---

**Summary:** Standards: 7 findings (2 hard, 5 judgement); worst within axis — #2, completion claimed for commands the evidence table does not record. Spec: 8 substantive findings + 1 minor; worst within axis — #2, the spec requirement covers selection views but only Home supplies the disabled set.

---

## 可映射性

> 本节独立于 skill 原始报告。仓库可见的 `harness/reviews/_template.md` **没有 YAML front matter**，只有标题下元信息（日期/对象/审查者/只读声明）；因此 findings 本身不映射到 front matter。若目标审查文件另有 front matter，我未读历史报告，无法确认其字段；按模板只能映射审查对象、日期、只读声明与总体结论，不映射具体问题。

| 条目 | 建议级别 | 映射理由 / 限制 |
| --- | --- | --- |
| Standards #2 证据声明不完整 | **P1** | 完成声明与实际证据不一致，属于交付门禁问题；不选 P0，因为代码本身无阻断风险。 |
| Spec #2 仅 Home 应用禁用集 | **P1** | 规格要求 "selection views" 复数，当前只覆盖一处；属缺失需求。 |
| Spec #4 A3 网格级未验证 | **P1** | 验收 A3 没有对应测试证据；是证据缺口，不是实现必然错误。 |
| Spec #1 一次性 refresh | **P1** | 与 proposal "unchanged entries" 措辞冲突，且造成运行期无法启用新装语言；是否阻断取决于"显式刷新"的产品解释。 |
| Spec #8 当前选中项变灰 | **P1** | 用户可见状态自相矛盾（已选中但不可选），需产品/交互决策后修。 |
| Standards #1 docs/02 未同步 | **P2** | 文档漂移无可运行影响；若团队把文档同步作为交付硬门禁，可升 P1。 |
| Standards #4/#5/#6/#7 重复、脆弱计数、硬编码文案、注入位置 | **P2** | 均为可维护性/一致性 judgement，且 smell baseline 明确是启发式，不自动构成违例。 |
| Spec #3 直接 pair 结果不回写 | **P2** | 设计措辞不一致；当前 `languageCatalog.translationPair` 在 App 内无调用点，影响主要是契约一致性。 |
| Spec #5 三项能力取 AND | **P2 / 待决策** | 当前行为比 spec 场景更严格；先映射到"被挑战的假设/待决策"，产品确认后才可能升 P1，不能直接定级。 |
| Spec #6 ordered/unordered 措辞 | **P2** | 生产适配器已双向合并，掩盖了方向性差异；属设计文档与实现语义对齐问题。 |
| Spec #7 pre-refresh `translationPair` 非宽松 | **P2** | 设计要求保留旧行为，但该 API 当前无调用点；是契约一致性缺口。 |
| Spec 末条并发 refresh 非原子 | **P2** | 仅导致重复探测，无数据损坏；可记录排期。 |

**无法映射到 P0–P2 的内容：**

- **"verified clean" 复跑事实**（架构/计数/证据门禁 PASS）→ 模板 §2「复跑与边界」，不是问题条目。
- **Standards #3 真机验证缺口** → 模板 §5「缺失信息与待验证」/记录的「未验证豁免」；它不是可通过代码修复的 P 级缺陷，也无法由 P1 关闭。
- **两轴分离本身、以及"不在两轴之间选唯一最严重项"** → 属于报告结构约束，不映射任何条目。
- **smell baseline 的判定性意见**（Duplicated Code 等）→ 只能作为 P2 候选；若团队不认可该 smell，则不应进入问题表，故不存在"必然的 P 级"映射。
- **需要产品解释的歧义**（"views" 覆盖范围、"ordered" 语义、AND 规则）→ 先落模板 §4「被挑战的假设」/§5，再由决策结果决定是否升 P1；在此之前强行定 P 级会把审查判断伪装成事实。
- **P0：两轴均未发现** 安全、数据丢失、启动/发布阻断或核心功能不可用级别的问题；不要为了填表把 P1 升为 P0。

**映射的两个限制：** 子审查者使用的是 HARD / JUDGEMENT 标签，**HARD ≠ P0/P1**（如文档漂移是 HARD 但可 P2），judgement 也可能因用户可见影响而升 P1；因此上述级别是聚合后的再评分，不是原始报告自带的字段。
