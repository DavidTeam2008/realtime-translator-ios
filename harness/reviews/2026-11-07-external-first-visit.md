# 2026-11-07 外部首访与可复现性测试（公开 clone，陌生人视角）

> **评估者身份：AI 代理、非人类陌生人。** 本报告不冒充人类首访结论；阅读是文本驱动的，缺少人类的视觉浏览、目录点击与直觉判断。
> 对象：公开仓库 `DavidTeam2008/realtimeTranslatorOptimize`，`main` @ `631d334`（2026-11-07），`git clone --depth 1` 干净 clone。
> 协议：只按 `README.md` → `docs/README.md` → `CONTRIBUTING.md` 阅读；在 clean clone 运行 `make check`、`make verify-static`；全程不改项目仓库，唯一写入为本报告。
> 环境：macOS 27.0.1、GNU Make 3.81、Python 3.14.7、git 2.54.0；**未使用 Xcode**。路径均为仓库相对路径；临时目录只写占位 `<tmp>`。

## 1. 结论

- **5 问可答数：4/5（含 1 个部分）；严格计 3/5。**
  - 完整可答：Q1 是什么、Q2 为什么值得看、Q3 怎么跑（无 Xcode 可做）；
  - 部分可答：Q4 怎么验证（有门禁/证据政策，但"证据 JSON 怎么生成/长什么样"需第 4 个文件）；
  - 不可答：Q5 怎么复制整套 harness（协议路径内没有"10 步采用指南"，三处入口都指向 `HARNESS.md`）。
- **10 分钟复现：按协议 FAIL，按仓库默认 clone PASS。**
  - 协议 `git clone --depth 1` 下：`make check` **exit 0 / 1s**；`make verify-static` **exit 2 / 9s**（`test_verify_claim` 的 `git rev-parse HEAD~1` 在浅克隆无父提交）。
  - `git fetch --unshallow`（2s）后重跑：`make verify-static` **exit 0 / 15s**，88 个工具单测 `OK`。
- **用时**：clone ≈1s；两条门禁 + 根因复核的完整命令链路 **≈100s**，远低于 10 分钟窗口；文档阅读（3 个文件共 290 行）在窗口内完成。
- **判定**：README/CONTRIBUTING 的"10 分钟、不需要 Xcode"路径在**默认全历史 clone** 下成立；在**本协议的浅克隆**下不成立，仓库未提示该限制 → 这是一处可一行修复的外部首访卡点。

## 2. 逐问证据与卡点

| # | 问题 | 答案（陌生人视角摘要） | 来源（file:line） | 可答性 | 卡点 |
|---|---|---|---|---|---|
| Q1 | 是什么 | 端侧 iOS 实时翻译 App：麦克风 → 听写 → `Translation.framework` → 字幕/可选 TTS；三模块（面对面 / 同声传译 / 会议记录）；本机 SwiftData 历史；无后端、无 API Key、不上传音频；同时是"可审计的 Harness Engineering 实践样本" | README.md:1-8, 18-24, 130-136 | ✅ 完整 | 无 |
| Q2 | 为什么值得看 | 三条理由：真实产品非 demo；端侧隐私（系统端侧能力、文本只在本机）；harness 可审计（"已验证"可被脚本否证，非自述）。另有 5 层机制表（Guides/Sensors/Evidence/独立审查/工具适配）与"当前状态+主要技术债" | README.md:12-16, 77-87, 111-116 | ✅ 完整 | 无 |
| Q3 | 怎么跑（无 Xcode 可做？） | 无 Xcode 可做：只依赖 `python3`+`make`+`git`，跑 `make check` 与 `make verify-static`，可验证规则/结构/证据/代码边界；**但跑不了 App**（截图在 docs/images）。完整 iOS：macOS+Xcode 26.4+、改三个 target 的 Team/Bundle ID、真机开发者模式、`make build/test/test-ui`、`harness/tools/device-test.sh` 真机套件 | README.md:34-42, 44-57；CONTRIBUTING.md:6-41 | ✅ 完整（但见 §3 实测失败） | README 未显式写"无 Xcode 时只能做仓库检查、不能运行 App"的直白结论，需从"能验证什么"反推 |
| Q4 | 怎么验证（门禁与证据） | 按变更类型选最低验证：Domain/VM→`make test`，UI→`make test-ui`，语音/翻译/TTS/音频/持久化→真机（模拟器不能替代），文档/规则/工具→`make verify-static`。完成声明必须附命令、退出码、环境、证据 ID；未运行写"未验证"；`make verify-claim` 输出 PASS/FAIL/UNVERIFIED；测试计数/真机矩阵唯一源在 `references/verification.md` | README.md:82-94；CONTRIBUTING.md:43-61 | ◐ 部分 | 证据文件如何生成、schema/模板与证据 ID 规则在 `harness/evidence/README.md`（第 4 跳，协议外）；3 文件内只能知道"要有证据"，不知道"怎么造一条合法证据" |
| Q5 | 怎么复制整套 harness（10 步采用指南是否够） | **在协议路径内无法回答。** 3 个文件都说 harness 系统地图在 `HARNESS.md`，但没有"10 步采用指南"的内容；`AGENTS.md`、`.dsh/skills/`、`references/` 只被提及为入口，其规则体系未展开。是否"够"必须读 `HARNESS.md`（第 4 个文件）才能判断 | README.md:16, 81-85, 101；docs/README.md:10, 17, 34, 56；CONTRIBUTING.md:5, 58-61 | ❌ 不可答 | **协议路径与仓库自身推荐的首访顺序不一致**：docs/README.md:10 的"第一次来"顺序是 `README → HARNESS.md`，不是 `README → docs/README → CONTRIBUTING`；按协议走反而不经过采用指南 |

**可答性计数说明**：Q1–Q3 完整、Q4 部分、Q5 不可答 → 汇报口径 **4/5**；若只计"完整可答"则为 **3/5**。

## 3. clean clone 与门禁输出摘要

命令（占位 `<tmp>` 为协议指定临时目录，避免记录本机绝对路径）：

```bash
rm -rf <tmp>/duiyi-external-firstvisit
git clone --depth 1 https://github.com/DavidTeam2008/realtimeTranslatorOptimize.git <tmp>/duiyi-external-firstvisit   # exit 0，≈1s，HEAD 631d334
cd <tmp>/duiyi-external-firstvisit
make check           # exit 0，≈1s
make verify-static   # exit 2，≈9s
```

`make check`（PASS，exit 0）：文档 25 篇 / 135 条相对链接、token 预算（如 AGENTS.md ≈1576/1650 tokens）、架构规则 0 违规、测试计数、6 个 `.dsh/skills` frontmatter、`check-harness` 19 项 PASS、1 个 active 计划、adapters PASS。

`make verify-static`（**FAIL，exit 2，浅克隆**）：

```
FAIL: test_ancestor_commit_pass (test_verify_claim.VerifyClaimTests.test_ancestor_commit_pass)
AssertionError: git ('rev-parse', 'HEAD~1') 失败：fatal: ambiguous argument 'HEAD~1': unknown revision or path not in the working tree.
Ran 88 tests in 8.294s
FAILED (failures=1)
make: *** [test-tools] Error 1
```

根因复核：`git rev-parse --is-shallow-repository` = `true`；`git fetch --unshallow`（≈2s）后再跑 `make verify-static` → **exit 0 / ≈15s**（88 tests 13.792s，`OK`）。同一门禁在浅克隆失败、全历史通过，失败与业务代码无关，属**克隆形态兼容性缺口**。

## 4. CONTRIBUTING 的 10 分钟走查

| 步骤（CONTRIBUTING.md:17-25） | 是否可完成 | 证据 |
|---|---|---|
| 1. `git clone … && cd …` | ✅ | clone exit 0，≈1s |
| 2. `make check`（声明约 0.3s） | ✅ PASS | exit 0，实测 ≈1s（含 Python 启动；声明值偏乐观） |
| 3. `make verify-static`（声明约 4.3s） | ❌ 浅克隆 FAIL / ✅ 全历史 PASS | 浅克隆 exit 2 ≈9s；unshallow 后 exit 0 ≈15s |
| 完整 iOS 环境路径（§3，需 Xcode/真机） | 未走查 | 超出"不需要 Xcode"范围；本报告不下结论 |

**结论**：CONTRIBUTING 的 10 分钟路径本身设计合理（两条命令、依赖最小），但对 clone 形态敏感；README:36-42 与 CONTRIBUTING:19-23 均未提示 `--depth 1` 会破坏 `verify-static`。这是"首访陌生人最容易踩、修复成本最低"的点。

## 5. 对 README / CONTRIBUTING 的最小修复建议

1. **浅克隆兼容（P0，二选一，均 ≤几行）**
   - 首选：`tools/tests/test_verify_claim.py::test_ancestor_commit_pass` 在 `git rev-parse --is-shallow-repository` 为 `true` 时 `self.skipTest("shallow clone: HEAD~1 unavailable")`（CI 与首访常 `--depth 1`，应视为合法环境）；
   - 或 `make verify-static` / `test-tools` 入口先检测浅克隆，打印 `git fetch --unshallow` 指引后跳过该测试，而不是 `FAILED (failures=1)`。
2. **首访路径补齐（P1）**
   - README §10 分钟快速开始加一行：「若用 `--depth 1` 克隆，先 `git fetch --unshallow`（工具单测会读 git 历史）」；
   - 把 `HARNESS.md` 纳入"第一次来"的必读路径（与 docs/README.md:10 自身推荐一致），或在 README 内联 5–10 行"采用 harness 的 10 步摘要"——否则协议限定的 3 文件路径无法回答 Q5。
3. **校准耗时声明（P2）**：README:38-39、CONTRIBUTING:21-22 的"约 0.3s / 约 4.3s"与实测（≈1s / 9–15s）差 2–3 倍；建议改为区间或注明"本机实测，随机器/历史浮动"。
4. **补一句无 Xcode 边界（可选）**：README:42 后加「无 Xcode 时只能做静态验证与文档/证据检查，不能构建或运行 App；界面见 docs/images」。

## 6. 局限

- **AI 代理、非人类陌生人**：阅读是文本驱动，没有人类的视觉浏览/目录点选/中断行为；不能代表真实人类的首访完成率。
- **"陌生人"纯度不完全**：本会话在更早任务中接触过本仓库的 harness 研究材料。本报告每一条 Q1–Q5 结论仅引用 clean clone 内协议路径文档的行号，未引用记忆中的结论；但无法宣称零先验知识，读者应折价看待"陌生感"相关结论（尤其"找不到/歧义"判断）。
- **只按协议读了 3 个文件**，未读 `HARNESS.md`、`AGENTS.md`、`references/`、`harness/evidence/README.md`。因此 Q4 的部分与 Q5 的不可答是"**协议路径的缺失**"，不排除第 4 跳文档已完整回答。
- **只跑静态门禁**：未跑 Xcode/模拟器/真机，未验证构建、UI、语音/翻译链路；不评价产品功能。
- **单次测量**：耗时未多次取中位数；浅克隆失败已用 unshallow 对照确认因果（同环境、同 commit、仅历史深度不同）。
- 未修改项目仓库；唯一写入为本报告。
