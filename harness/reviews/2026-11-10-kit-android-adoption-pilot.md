# kit v0.2.2 · Android 存量仓只读接入试点

> 生成：2026-11-10；工具：`harness-kit/scripts/harness-adopt`（kit `0.2.2`）；模式：**只读**（目标仓 0 改动）。
> 目标仓：`realtime-translator-android`（`2ff1fae`，115 个跟踪文件，3 commits）。本报告由工具生成后仅做本机路径脱敏，不追加人工结论以外的数据。

## 1. 试点目的（C1 验收）

验证 v0.2.2 的存量盘点能力在**真实 Android 仓库**上能否一次产出可执行的改造清单：语言探测、文档治理缺口、卫生风险、profile/测试命令建议。

## 2. 结论（先行）

| 检查项 | 结果 |
| --- | --- |
| 语言/构建探测 | ✅ `android`（`settings.gradle.kts` 等） |
| 测试命令建议 | ✅ `./gradlew testDebugUnitTest`（与 init C2 建议一致） |
| 文档索引缺口 | ✅ 发现缺 `docs/README.md` + 10 篇未登记文档 |
| 断链 | ✅ 1 条（跨仓库历史链接，指向 iOS 仓本地相对路径） |
| 疑似过期标记 | ✅ 6 处（"写于实现之前 / 已被推翻 / 待真机验证 / 尚未编译"等） |
| 卫生风险 | ✅ 1 个绝对符号链接 + 6 处本机路径；wrapper jar 误报已修复（0 构建产物误报） |
| 既有门禁 | ✅ 正确识别缺失（AGENTS/HARNESS/Makefile/docs 索引/harness 目录） |
| 目标仓改动 | ✅ 0（仅 `/tmp` 报告；`git status` 仍只有评估稿未跟踪文件） |
| 耗时 | <1s |

## 3. 工具输出（脱敏）

> 绝对符号链接的实际目标已替换为 `…`，其余内容为工具原文。

（见下方工具输出）
# realtimeTranslatorAndroid · harness-kit 存量盘点

> 生成时间：2026-11-09T16:09:18Z ｜ kit 版本：0.2.2 ｜ 模式：只读（未修改目标项目；报告不记录绝对路径）

## 概览

| 项 | 值 |
| --- | --- |
| git 仓库 | 是 |
| 分支 | main |
| 跟踪文件 | 115 |
| 提交数 | 3 |
| 未提交改动 | 1 |
| 语言 | android |
| 构建文件 | build.gradle.kts, gradle.properties, gradlew, settings.gradle.kts |

既有门禁文件：

- 已存在：（无）
- 缺少：.githooks/pre-push, .github/workflows/verify.yml, AGENTS.md, CONTRIBUTING.md, HARNESS.md, Makefile, Makefile.harness, docs/README.md, harness/config.json, tools/check_agents.py, tools/check_docs.py, tools/check_plan.py, tools/doctor.py, tools/verify_claim.py

## 文档盘点

- docs 数量：10 篇（Markdown 合计 11 篇）
- docs/README 索引：缺失
- 未登记文档（10）：
  - docs/01-product-prototype.md
  - docs/02-architecture.md
  - docs/03-tech-choices.md
  - docs/04-implementation-principles.md
  - docs/05-obstacles.md
  - docs/06-compromises.md
  - docs/07-roadmap.md
  - docs/08-on-device-llm.md
  - docs/09-current-state.md
  - docs/10-latency-optimization.md
- 根 markdown（1）：
  - README.md
- 断链样本（1）：
  - docs/01-product-prototype.md:10: ../../../realtimeTranslatorOptimize/docs/09-platform-prototype.md
- 围栏奇数文件（0）：
  - （无）
- 疑似过期标记（6）：
  - README.md:116: 尚未编译
  - docs/03-tech-choices.md:3: 写于实现之前
  - docs/03-tech-choices.md:3: 已被推翻
  - docs/04-implementation-principles.md:3: 写于实现之前
  - docs/09-current-state.md:5: 写于实现之前
  - docs/09-current-state.md:113: 待真机验证

## 卫生盘点

- 被跟踪构建产物（0）：
  - （无）
- 绝对符号链接（1）：
  - third_party/llama.cpp → /Volumes/<local>/src/llama.cpp
- 本机路径样本（6）：
  - README.md:32: open -a "/<local>/… Studio.app" .
  - README.md:35: SDK：`/<local>/…`（写在 `local.properties`）。Gradle 用工程自带 wrapper；JDK 用 Android Studio 自带 JBR 21。
  - README.md:60: > ⚠️ `third_party/llama.cpp` 是指向 `/<local>/…` 的符号链接。该目录缺失时构建会从 GitHub 拉 tag `b10775`，**与本机实际编译的版本不一致**。换机器前先确认这个链接指向哪里。
  - docs/09-current-state.md:148: - `third_party/llama.cpp` 是**指向 `/<local>/…` 的符号链接**，那个目录不是 git 仓库、没有 tag。换台机器构建会静默走 `FetchContent` 下载 tag `b10775` —— *
  - gradlew.local.sh:9: export ANDROID_HOME="${ANDROID_HOME:-/<local>/…"
  - gradlew.local.sh:22: export JAVA_HOME="${JAVA_HOME:-/<local>/… Studio.app/Contents/jbr/Contents/Home}"
- >5MiB 被跟踪文件（0）：
  - （无）
- .gitignore 缺失常见项（11）：__pycache__/, *.pyc, node_modules/, .build/, build/, dist/, DerivedData/, *.xcresult, .env, coverage/, .venv/

## 建议

- 建议 profile：**standard**
- 判断理由：启发式得分 2：docs 文档 10 篇、已探测到测试入口 → 建议 profile=standard（接入时可用 --profile 覆盖）
- 建议 test 命令：`./gradlew testDebugUnitTest`
- 风险清单（8）：
  - [高] 绝对符号链接 1 个（换机器/CI 失效）
  - [中] 本机绝对路径 6 处（公开/迁移前需脱敏）
  - [中] Markdown 断链 1 处
  - [中] docs/ 存在但缺 docs/README.md 索引
  - [低] 未登记到 docs/README.md 的文档 10 篇
  - [低] 缺根 AGENTS.md（init 会生成）
  - [中] .gitignore 缺常见项：__pycache__/, *.pyc, node_modules/, .build/, build/, dist/, DerivedData/, *.xcresult, .env, coverage/, .venv/
  - [中] 工作树有 1 处未提交改动（改造前建议先清理）

## 下一步

- [ ] 审阅本报告（默认只读：未改动目标项目）
- [ ] 运行 harness-init 接入（建议 --profile standard）：`python3 harness-kit/scripts/harness-init --profile standard --target <target>`
- [ ] 先处理高风险项（被跟踪构建产物 / 绝对符号链接 / 本机路径）再提交
- [ ] 用 `--write-plan` 生成改造计划草稿，补目标、验收与 scope.allow
- [ ] 接入后运行 `make check` 与 `make verify-static` 复核

## 4. 工具局限与待改进（v0.2.3 候选）

1. 绝对符号链接**目标值**未脱敏（报告会带出真实目标路径）；建议后续对 symlink target 只输出"绝对/相对"与 basename。
2. profile/过期标记为启发式，存在误报可能（报告仅提醒，不阻断门禁）；正式接入时仍需人工审阅。
3. 本试点只验证 `--report` 只读路径；`--write-plan` 已在 kit 测试 fixture 覆盖，但未在真实仓执行（Stage B 执行）。
4. 未覆盖超大仓性能（当前目标仓 115 文件，<1s；上限常量已限流）。

## 5. 下一步（Stage B）

用同一版本 kit 对该仓执行 `harness-init --profile standard --language android`（先 `--dry-run`），随后按评估稿 P1–P5 推进；`--write-plan` 生成的改造计划草稿作为 P1 输入。
