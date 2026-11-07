# v1.0.0 · 对译 Duiyi

> 一个把「AI Coding Agent 研发范式 + Harness Engineering 工程化」完整落进真实 iOS 项目的开源标杆。
> 不只是一份文档：每条主张都有可复跑的门禁、可三值判定的证据、可复现的 clean clone。

## 是什么

- **产品**：端侧 iOS 实时翻译 App（麦克风 → 听写 → `Translation.framework` → 字幕/TTS；任务结束存本机 SwiftData）。
- **无后端、无 API Key、无上传**；iOS 26.4+ / Swift 6.0，无第三方依赖。
- **Harness**：仓库本身就是一套 Agent 可执行的工程约束系统——指令层（AGENTS/skills）、状态层（plans/evidence）、验证层（门禁/三值判定）、范围层（L0/L1/L2 + scope）、会话生命周期（doctor/resume/end/handoff）。

## 10 分钟验证（不需要 Xcode）

```bash
git clone --depth 1 https://github.com/DavidTeam2008/realtimeTranslatorOptimize.git
cd realtimeTranslatorOptimize
make check          # 6 组静态门禁（docs/架构/测试计数/harness/计划/adapters），约 1s
make verify-static  # + 证据 schema + 91 个脚本单测 + 脚本语法，约 5-15s
make verify-claim   # 3 条 clean-tree evidence 三值判定 → PASS×3
```

预期：`make check` PASS；`make verify-static` PASS；`make verify-claim` SUMMARY pass=3 fail=0 unverified=0。
用 `git clone --depth 1` 浅克隆时先 `git fetch --unshallow`（脚本单测会读取提交历史）。
完整 iOS 环境（Xcode + iOS 26.4 模拟器）见 `CONTRIBUTING.md` 的 30 分钟路径。

## 本版包含

- **文档信息架构收敛**：根目录 ≤5 个 markdown；`docs/README.md` 唯一索引；历史文档蒸馏为案例页（启动性能负结果可复核）。
- **Harness 机制**：`HARNESS.md` 实践地图（问题 → 五子系统 → 落地矩阵 → 证据政策 → 10 步采用指南 → 评分卡 → 局限）；`docs/harness-scorecard.md` 自评 + 独立复评；`harness/reviews/` 两轮独立只读复核。
- **证据链**：evidence JSON schema + `tools/evidence.py` + `tools/verify-claim.py` 三值判定（PASS/FAIL/UNVERIFIED）；`make end`/`make release-check` 接入时效与 strict 检查。
- **计划状态机**：front matter/唯一 active/未提交改动交叉比对；证据 ID 硬校验；done 计划必须 `submitted` 且证据 commit 绑定 HEAD/submitted。
- **指令 sensor**：token 预算（AGENTS ≈1576/1650；references ≤975）、13 个指令文件的 `§N`/`第 N 节` 引用校验、6 个嵌套 AGENTS、6 个 skills、敏感信息扫描。
- **多 Agent 适配**：`harness/adapters/`（DeepSeek Harness / Claude Code；skills 单源同步 + hooks 示例 + red-team agent）。
- **CI/门禁**：`verify.yml`（ubuntu static 必跑；macOS 自托管单测可选）、pre-push hook、`make doctor` 环境自检（失败给"影响/如何补/必需性"）。
- **发布卫生**：两轮 `git filter-repo` 清除 Team/设备 ID/本机路径与作者邮箱；树/历史/提交消息 0 命中；备份仅在本机。

## 已知限制（不粉饰）

- **行为测试缺位**：P0-1 语音并发仲裁、P0-3 SwiftData 持久化的行为测试尚未做（独立排期）；`check-arch` 是文本规则，可被绕过。
- **动态 CI 默认跳过**：macOS 单测需自托管 runner（`MACOS_CI_ENABLED=true`）；GitHub 托管 macOS 是否具备 iOS 26.4 runtime 未验证。
- **真机证据时效**：3 条 evidence 中 unit/UI 已在发布前重跑；真机 device evidence 生成于 2026-11-06，对当前 HEAD 已 **STALE**（`verify-claim --fresh` 会告警，`--strict` 判 UNVERIFIED）——发布不据此声称"真机当前通过"，需有设备时重跑。
- **证据可伪造**：三值判定提高说谎成本，不提供密码学保证；高风险改动仍走独立审查 + 人工体验。
- **Claude Code 未实测**：本机未安装；适配层是设计资产（`make adapters-check` 保证与单源一致）。
- **GitHub 旧对象**：force push 后旧 commit 仍可按 SHA 访问（平台不可达对象）；已接受，不用 Support 清除。

## 复现与引用

- 入口：`README.md`（产品 + 快速开始）、`HARNESS.md`（方法与实践）、`docs/README.md`（唯一文档索引）。
- 证据与审计：`harness/evidence/`、`harness/reviews/`、`docs/harness-scorecard.md`。
- 计划：`harness/plans/2026-11-06-benchmark-opensource.md`（含阶段验收、负向验证与未验证项）。
- 许可证：MIT。

**English summary**: On-device iOS real-time translation app with zero backend and no third-party dependencies, shipped with a complete Harness Engineering system: AGENTS-based instructions, plan/evidence state, static + evidence gates, three-valued claim verification, multi-agent adapters, and two independent read-only audits. Verify in 10 minutes without Xcode via `make check && make verify-static && make verify-claim`.
