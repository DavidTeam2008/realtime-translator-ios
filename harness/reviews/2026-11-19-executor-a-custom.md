# 执行器 A：自定义两轴 prompt（对照实验，2026-11-19）

> **用途**：executor 对照实验，审查对象为已归档 L2 变更 diff `1961368..f3e2bda`，不是当前 Change 的门禁证据。
> **执行环境**：Claude Code 2.1.310 + DeepSeek V4.1 Flash（`deepseek-flash`）；允许 Read/Grep/Glob/Bash，要求只读；单 agent，顺序执行两轴。
> **耗时/规模**：约 629 秒；输出约 9.8k 字符。
> **对象**：临时 detached worktree at `f3e2bda`；未读取历史 review 报告。

---
base: 1961368
head: f3e2bda
reviewer: 两轴执行器 A（独立只读）
p0: 1
p1: 3
p2: 6
verdict: fail
---

# 独立审查 · 两轴执行器 A

## 1 结论

**结论：FAIL（不通过）。**

- **Standards 轴最严重：S1（P0）**。当前 HEAD 上 `make delivery-check CHANGE=cache-language-capabilities` 直接失败（review HEAD 不一致），但 Change Record 声明该门禁 PASS；交付/归档硬门禁不可复现。
- **Spec 轴最严重：SP1（P1）**。规格要求“language selection views”按目录禁用不可用语言，实际只有 Home 设置页接线；Onboarding、Settings、Interpretation、Meeting、字幕语言选择仍可选中目录报告不可用的语言。
- 两轴独立判断，不做跨轴排序。

通过的部分：`make check-tests`、`make check-arch`、`make verify-static`、`make release-check` 均 exit 0；聚焦复跑 `SystemLanguageCatalogTests` 8/8 通过；证据 JUnit 可重算（139 单元、2 UI + 1 预期 skip）；依赖方向、翻译锚点、单引擎等架构门禁无违规。

但代码主体可继续演进，**当前状态不能按 Delivery Contract 声称完成或归档**：P0 未关闭，且 A3/A4 的证据链不覆盖实际网格行为。

## 2 复跑与边界

| 命令 | 退出码 | 结果 / 关键输出 |
|---|---:|---|
| `git status --short` | 0 | 工作树干净，HEAD=`f3e2bda` |
| `make check-tests` | 0 | unit 139≥139（16 文件）；UI 3≥3；文档计数 139+3、真机 142 一致；skip 1==白名单 |
| `make check-arch` | 0 | 扫描 81 个 Swift 文件，R1–R6 零违规 |
| `make verify-static` | 0 | 含 check/check-plan-strict/evidence/pin/kit-check；有 WARN：Change Record 验证证据表无可解析 evidence id |
| `make delivery-check CHANGE=cache-language-capabilities` | **2** | `[FAIL] review.head 不一致：ae409a6... != f3e2bda...` |
| `make release-check` | 0 | 3 条当前证据 PASS；14 条归档证据 SUPERSEDED；证据链 PASS |
| `xcodebuild test ... -only-testing:DuiyiTests/SystemLanguageCatalogTests` | 0 | Xcode 27.1 / iOS 26.4.1；8/8 通过 |

**边界与说明**

- 证据 JSON 的 `git.commit` 为 `ae409a6`；`git diff ae409a6..f3e2bda -- Duiyi DuiyiTests harness/test-baseline.json references/verification.md` 为空，代码与证据提交一致。因此本次失败**不是代码证据 stale**，而是 `review.head` 仍停在 `ae409a6`，HEAD 已前移到 `f3e2bda`。
- `make verify-static` 与 `make release-check` 均不包含 `delivery-check`；两者绿色不能抵消 delivery-check 红色。
- `delivery-check` 在 `review.head` 处先失败，后续 `p0`/`p1`/`verdict` 字段未被校验；不能据此推断 review 内容。
- 按要求**未读取** `harness/reviews/` 历史报告、`.env` 或密钥；未修改任何文件。
- 未复跑完整 `make test`（139 条）、`make test-ui`、真机测试；UI 结果来自证据（2 pass、1 skip），真机能力实查仍未验证（记录已列未验证项与豁免）。
- 首次用 `OS=26.4` 找不到模拟器，改 `OS=26.4.1` 后成功；这不是产品失败。

## 3 Standards 轴表

| ID | 轴内最严重 | 标准 / 规则 | 证据（位置） | 事实与影响 | P |
|---|---|---|---|---|---|
| S1 | ★ 是 | Delivery Contract、`harness/AGENTS.md` §3、`AGENTS.md` §5 完成判据 | `tasks.md:12-13`；`harness/records/2026-11-18-cache-language-capabilities.md:65`；delivery-check 输出 | `make delivery-check` exit 2（`review.head ae409a6 != f3e2bda`），但记录写“PASS：4/4 tasks、fresh/strict evidence、review Base..Head”。交付/归档门禁未过且不可复现，不能声称完成。 | **P0** |
| S2 | — | 验证矩阵：UI 交互/布局走 `make test-ui`；验收 A3/A4 | `references/verification.md:20-28`；`tasks.md:9`；`DuiyiTests/SystemLanguageCatalogTests.swift:57-209`；UI 证据仅 `SimultaneousFlowTests` 导航 | 8 个单测只测 `LanguageCatalogSelection` 派生；没有构造 `LanguageChipGrid`，没有断言 `.disabled` 或点击无效。UI 证据的 2 个通过用例不打开 Home 设置、不涉及语言 chip。A3“grid disables”与 A4“pre-refresh grid 不禁用”没有被证据覆盖。 | P1 |
| S3 | — | 证据 ID 规则：`AGENTS.md` §5“无 id 即未验证”；`harness/AGENTS.md` §3 完成声明引用证据 ID | Change Record `:61-65`；`make verify-static` 的 WARN | 记录验证表的 evidence ID 为“—（过程记录）”；且“下一步”仍写“Task 1 先写红测试”，与 4/4 已完成自相矛盾。记录不可复核，完成声明缺证据锚点。 | P2 |
| S4 | — | 本地化 / 可访问性基线：项目 UI 文案按 `Copy` 六语切换 | `Duiyi/Features/Shared/LanguageChipGrid.swift:37-40` | 新增 `accessibilityHint` 硬编码英文“Unavailable language”；项目其他 a11y hint 均走 `Copy`。中文/日文 UI 下会出现英文提示，且没有可见的“不可用原因”说明。 | P2 |

## 4 Spec 轴表

| ID | 轴内最严重 | Spec 来源 | 证据（位置） | 事实与影响 | P |
|---|---|---|---|---|---|
| SP1 | ★ 是 | `spec.md:35-41`“language selection views”；Proposal Why“settings grids”；Design `:11` | `LanguageChipGrid.swift:6` 默认空集；只有 `HomeSettingsSheet.swift:22-27` 传入；`SettingsSheet.swift:49,54`、`LanguagePickView.swift:18,24`、`InterpretationSettingsSheet.swift:53,58`、`MeetingSettingsSheet.swift:46`、`CaptionPaneView.swift:74`、`InterpretationView.swift:329` 均未传 | 只有 Home 设置页按目录禁用；Onboarding、Settings、Interpretation、Meeting、字幕语言选择仍可选目录不可用语言。任务 scope 只允许 Home，但 spec/proposal 写的是多视图；二者未收敛，核心需求只在单一入口落地。 | P1 |
| SP2 | — | `spec.md:38-41` 仅以“not speech-capable”定义禁用；Design `:9`；Proposal“recognize, translate, or speak” | `Duiyi/Domain/LanguageCatalog.swift:51-54`；`SystemLanguageCatalogTests.swift:172-196` | 实现条件是 `speech && translate && speak` 全真才可用；缺 TTS voice 或缺任一翻译对也会整语言禁用。TTS 在面对面/会议文本模式并非必需，可能把可文本翻译的语言错误禁用。测试只覆盖 speech=false 且 speak=false 的组合，无法区分 AND/OR 语义。 | P1 |
| SP3 | — | Design `:10`“cached by ordered language pair”；Proposal 缓存声明 | `SystemLanguageCatalog.swift:100-106`（探测后不写回缓存）；`:144-156`（按 rawValue 排序、折叠方向） | `translationPair` 只在 refresh 后命中缓存；refresh 前每次调用都重新探测且不写入。`OrderedLanguagePair` 实际是无序键；当前 `TranslationAvailabilityService` 双向合并掩盖了方向问题，但未来 directional checker 会返回错误方向。 | P2 |
| SP4 | — | `spec.md:6-10`“Repeated refresh uses cached probe results” | `SystemLanguageCatalog.swift:108-109`、`:140`；`SystemLanguageCatalogTests.swift:117-133` 仅顺序调用 | `hasRefreshed` 检查与 `publish` 之间没有 in-flight 标记/锁；两个并发 `.task` 可同时通过 guard，重复执行 6+6+15 次系统探测。单测只证明顺序重复调用不重探，未覆盖并发。 | P2 |
| SP5 | — | `spec.md:6-10`“cached capability values remain stable”；Design `:7`“explicit probe entry point” | `SystemLanguageCatalog.swift:108-109`；`HomeSettingsSheet.swift:54-55,101-126` | 第一次 refresh 后 `refreshCapabilities()` 永久 no-op；没有失效入口。Home 内“重新下载模型”成功后不会重探，系统设置中安装语言后回前台也不会重探；无测试断言第二次 refresh 后 capability 值稳定。若“catalog lifetime”就是进程生命周期，应明确；否则“explicit refresh”名不副实。 | P2 |
| SP6 | — | Proposal“retaining the current static catalog as the preview/fallback adapter”；Design `:8` | `AppEnvironment.swift:29`；`PreviewSupport.swift:159-168,262-271`；`HomeView.swift:109-112`；`LanguageCatalog.swift:20` | 默认已改为 `SystemLanguageCatalog`；Preview 的 `AppEnvironment(...)` 都未注入 `StaticLanguageCatalog`，`StaticLanguageCatalog` 仅定义未使用。预览/回退适配器未接线；模拟器预览若打开设置页会走系统探测（speech 全 false），可能全部禁用。Task 3“static catalog causes no disabled language”也没有对应测试。 | P2 |

## 5 归一问题表

### 5.1 Standards 轴归一

| P | ID | 问题 | 影响 | 最小修复 / 验证 |
|---|---|---|---|---|
| **P0** | S1 | 交付门禁红灯，Change Record 却声明 PASS | 无法归档/交付；记录不可复核，违反完成判据 | 解决 review head 与 HEAD 的流程矛盾；重跑 `make delivery-check` 必须 exit 0；用真实 evidence id 更新记录 |
| P1 | S2 | A3/A4 只有 helper 单测，没有网格/Home 集成证据 | 用户可见的 disabled 行为未被验证，验收声明过度 | 增加 UI 或可注入的视图级测试：不可用 chip `isEnabled == false`，点击不改选；pre-refresh 全 enabled |
| P2 | S3 | 记录缺 evidence ID，下一步仍写 Task 1 | 完成声明不可追溯 | 写入 `20261118T071150Z-unit-tests-pass` / `20261118T071256Z-ui-tests-pass`；更新下一步 |
| P2 | S4 | 新 a11y hint 硬编码英文 | 六语 UI 不一致，辅助技术提示不完整 | 走 `Copy`；补充不可用原因/状态的可访问性表达 |

### 5.2 Spec 轴归一

| P | ID | 问题 | 影响 | 最小修复 / 验证 |
|---|---|---|---|---|
| P1 | SP1 | 只有 Home 设置页接线 unavailable set | 其他入口仍可选不可用语言，规格“language selection views”未满足 | 要么收窄 spec 到 Home 并在文档写明，要么把 `unavailableLanguages` 接到所有选择入口（需扩 scope） |
| P1 | SP2 | “任一能力缺失即整语言禁用”超出 spec 的 speech 触发条件 | 缺 TTS 的可文本翻译语言被错误禁用 | 产品确认判定语义；增加 TTS-only/translation-only 单维 false 测试；若只按 speech 禁用则改 helper |
| P2 | SP3 | `translationPair` 按需不缓存；ordered pair 被折叠方向 | 重复系统探测；未来方向性 checker 会错 | on-demand 写入缓存；明确 pair 是否方向性，必要时保留方向键并加方向测试 |
| P2 | SP4 | 并发 refresh 可重复探测 | “exactly once”缓存保证不成立 | 加 in-flight/actor 串行化；增加并发测试 |
| P2 | SP5 | refresh 首次后永久 no-op，无失效入口；缺“值稳定”断言 | 系统能力变化后仍显示旧禁用状态；缓存语义未闭合 | 定义失效/重探策略（如 redownload 后 invalidate）；补第二次 refresh 值稳定测试 |
| P2 | SP6 | Static preview/fallback 未接线，Static 实际未使用 | 预览可能走系统探测；设计声明未落地 | 在 PreviewSupport/HomePreview 注入 `StaticLanguageCatalog()`，或删除该声明并说明 |

## 6 被挑战假设 / 缺失信息 / 最小验证

### 6.1 被挑战假设

1. **“A1–A4 都由 unit-tests-pass 证明”**：不成立。A3/A4 是网格渲染/交互行为；现有 8 个单测只覆盖 `LanguageCatalogSelection`，UI 证据也不涉及语言 chip。
2. **“`refreshCapabilities()` 是显式刷新入口”**：实现为第一次调用后永久 no-op；没有 invalidate。若产品允许“本次启动内能力变化”，该假设不成立。
3. **“任一能力 false 就该整语言禁用”**：spec 的禁用 scenario 只写了“not speech-capable”；TTS 是否应阻断文本翻译需要产品确认，当前测试无法区分。
4. **“一个 `LanguageChipGrid` 改动就覆盖所有语言选择”**：规格写的是“language selection views”，实际只有 Home 设置页接 line；其他入口仍可绕过。
5. **“pair 缓存是按 ordered pair”**：`OrderedLanguagePair` 在初始化时按 rawValue 排序，方向被折叠；当前生产 checker 双向合并所以未暴露，但设计语义与命名不一致。
6. **“static catalog 仍是 preview/fallback”**：`StaticLanguageCatalog` 仅定义未使用；Preview 的 `AppEnvironment` 默认拿到 `SystemLanguageCatalog`。
7. **“review 可以在 docs/evidence-only 尾提交前指向代码提交”**：delivery-check 要求 `review.head == HEAD`；当前 `f3e2bda` 是证据/评审/记录尾提交，导致门禁失败。需要明确流程（例如允许非代码尾提交，或把评审与代码提交合并/重定 head 规则）。
8. **“真机验收可以完全豁免”**：记录已列未验证项与 waiver，按项目规则可接受；但 `SpeechTranscriber`、`AVSpeechSynthesisVoice`、`LanguageAvailability` 的实际设备矩阵仍未证明，不能把它当成已验证。

### 6.2 缺失信息

- Review 文件的 `p0`/`p1`/`verdict` 字段：因门禁先失败在 `review.head`，未被工具校验；按要求未读取该文件。
- 六种语言在目标真机上的实际 speech locale / translation pair / TTS voice 能力矩阵，以及至少一个真实不支持案例。
- 产品决策：TTS 缺失是否应该禁用整个语言；翻译能力是否应按 pair 而非按语言粒度禁用。
- 产品决策：目录约束是只针对 Home 设置，还是所有语言选择入口。
- 流程决策：`f3e2bda` 是否为有意的 evidence/review 尾提交；若是，delivery-check 应如何定义 review head。
- `LanguageCapability` 的 `speechLocale`/`translation`/`ttsVoice` 字段是否应表示实际探测值；当前始终回填 `AppLanguage` 常量，且无消费者。

### 6.3 最小验证清单

1. **先修交付门禁**：明确 review head 规则或调整提交结构，重跑 `make delivery-check CHANGE=cache-language-capabilities`，必须 exit 0；用真实 evidence id 更新 Change Record。
2. **补 A3/A4 的行为证据**：Home 设置页注入一个“不可用语言”的 catalog，断言对应 `langchip-*` 的 `isEnabled == false`、点击不改选；permissive/未刷新状态断言全 enabled。
3. **补 Static 与单维能力测试**：`StaticLanguageCatalog` → 空 unavailable set；分别构造 speech=false、translate=false、speak=false，锁定 helper 判定语义。
4. **补 pair 缓存与方向测试**：refresh 前后重复调用 `translationPair` 断言探测次数；用 directional fake 验证 `from/to` 方向是否应保留。
5. **补并发 refresh 测试**：两个并发任务调用 `refreshCapabilities()`，断言只探测一轮；否则在文档明确“仅顺序调用安全”。
6. **本地化 a11y**：把“Unavailable language”移入 `Copy`，按当前 UI 语言输出。
7. **预览/回退接线**：PreviewSupport 与 HomePreview 注入 `StaticLanguageCatalog()`，或删除 Proposal 的 fallback 声明。
8. **真机矩阵**：在目标设备上记录六语 speech/translation/TTS 探测结果；若继续豁免，保留 waiver 并在 release 前复验。
9. **最终 HEAD 重跑**：若代码有任何修改，重新生成 unit/UI evidence；当前代码与 `ae409a6` 一致，但 `f3e2bda` 之后若再改代码，现有证据会 stale。

## 7 作者回应（空表）

| 序号 | 回应（接受 / 拒绝 / 待定 + 理由） | 修复提交 / 证据 |
|---|---|---|
|  |  |  |
