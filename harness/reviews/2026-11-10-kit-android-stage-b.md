# kit v0.2.2 · Android 真实仓改造（Stage B）验收报告

> 日期：2026-11-10；工具：harness-kit **v0.2.2**（standard profile）；目标仓：`realtime-translator-android`。
> 目标仓结果：重写后 16 个 Stage B 相关 commit，已推送 `d313fdf..eaae1b6`；CI run `42760441698` success；历史已 filter-repo 清洗、分支保护已开。
> 说明：本报告是 Phase 5.9 外部试点记录，证据细节在目标仓 `harness/` 内，不在本仓重复。

## 1. 试点范围

在真实存量 Android 仓（Kotlin/Compose/Hilt/Room + NDK/CMake、5.6 万 token 文档、无既有门禁）执行完整 brownfield 七步法：

| 阶段 | 内容 | 目标仓验证 |
| --- | --- | --- |
| P1 接入 | `harness-adopt` 只读盘点 → `harness-init --profile standard --language android` → 首次 `make check` | `make check` / `verify-static` PASS；scaffold `5179fdd` |
| P2 文档蒸馏 | 当前文档 11 篇重写 + 01–10 原文归档 `docs/_archive/` + `docs/03-decisions.md`（D1–D15）+ AGENTS/CONTRIBUTING/HARNESS/README/references 重写 | `make check`：164 条链接、11 篇公开文档、预算内 |
| P3 清洁 | 删死代码 4 处、debug 入口移 `src/debug/`（release manifest 0）、删绝对符号链接改 pinned tag、本机脚本迁 `scripts/`、补 `.gitignore` | `check_layers`/`check_hygiene` PASS；65 单测 PASS |
| P4 传感器/证据 | `check-host`（分层/卫生）并入 `verify-static`；detekt+ktlint+Android Lint 接 `check-quality`；JUnit XML→`verify-claim` 证据链 | `tests-pass` 证据 `20261109T163805Z-tests-pass`（65/65）PASS |
| P5 验收 | 12 项负向注入；冷启动陌生代理；计划 done/归档演练 | 12/12 命中门禁；首访 5/5；归档后门禁 PASS |

## 2. 关键验证（目标仓）

- 最终门禁（干净树）：`make check` 0、`make verify-static` 0、`make verify-claim` PASS、`make check-quality` 0。
- 单测基线 65/65（JUnit XML 聚合；`unit.floor=65` 只增不减）。
- 负向注入修出**门禁自身真实缺陷**：
  1. `check_layers.py` 对 `androidx.` 等带点前缀双重拼接，导致 domain 层 Android import 从不命中（空门禁）→ 修复后注入 exit 0→1；
  2. `check_hygiene.py` 把 `features/home/` 误判为 `/home/` 本机路径 → 改为绝对路径边界匹配。
- 冷启动（无仓库上下文的陌生代理，只读）：**5/5 可答**；指出 3 个文档问题（状态滞后、kit 复制命令不在官方阅读链、evidence README 三值语义与代码冲突），当场修复。

## 3. kit 使用结论

- `harness-adopt` → `harness-init` 的 brownfield 流程在真实仓上可用：盘点报告直接转化为 P1–P5 计划输入。
- `--language android` 探测 + JUnit 证据适配器 + standard profile 全链路成立；kit 不需要改动即可完成接入。
- 边界与缺口（v0.2.3 候选，未在本批修改 kit）：
  1. `check_plan.py` 不支持声明无扩展名根文件（`Makefile`）→ 目标仓宿主副本临时允许（上游修复后应删除补丁）；
  2. kit README 语言矩阵 Android 行仍为 ⚠️（只读试点）→ 可改 ✅；
  3. 宿主 `check_hygiene`/`check_layers` 已在真实仓验证，可作为 v0.3.0 C6 的通用传感器输入；
  4. 门禁自测（`sensors-selftest`）仍为手工矩阵，可考虑工具化（原 C10）。

## 4. 残留与未验证（目标仓）

- 真机未复跑（仅 JVM 单测与 manifest 合并验证）；非荣耀/泰越/桩功能仍未验证。
- release APK / native 重建未做（llama.cpp 改为 CMake `FetchContent` 拉 pinned tag，首次需网络）。
- detekt/ktlint/Android Lint 为 baseline 起步（存量债记录，不代表已修）。
- 目标仓 CI 只跑静态（venv 门禁 + check-host）；质量/单测/真机仍在本机。

## 5. 历史清洗与仓库治理（2026-11-10）

- 目标仓 `git filter-repo --replace-text --mailmap` 重写 18 个 commit：作者邮箱 → GitHub noreply；历史中的本机路径（`/Volumes/...`、`/Users/...`）→ `/local`；历史绝对符号链接目标脱敏。当前树此前已由 P3 清理为 0 命中。
- 重写后为 19 个 commit（Stage B 相关 16 个），force push `main` 至 `eaae1b6`；CI run `42760441698` success。
- 证据 `20261109T163805Z-tests-pass` 的 `git.commit` 回填为重写后的等价提交 `2c3b479`（同一内容状态；计划/归档中的旧短 hash 同步替换）。
- 分支保护已开：required status check `static gates`（strict）、enforce admins、禁 force push/删除。
- 本地备份 bundle 未入库。

## 6. 后续

- 产品方向按目标仓 `docs/06-roadmap.md` 的 Next：先跑延迟探针（不先调 VAD/HOLD），再流式回字幕/增量翻译 A/B。
- kit v0.2.3 候选见 §3；是否发布由后续决定（本批不触发 kit 变更）。
