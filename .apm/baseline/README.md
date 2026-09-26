# Baseline 状态

`startup-p0-working-tree.json` 是 2026-09-25 的旧 provisional baseline，
来自 dirty working tree 的 Release 构建。它已被后续证据否定，**不得用于确认改善或劣化**。

旧证据：同一 commit 的 n=5 跨 run 漂移、固定等待后的首样本异常，以及 warmup=3
的 n=10 独立重复漂移（见 `../issues/ISSUE-P0-002-cross-run-shift.json` 与
`../issues/ISSUE-P0-003-warmup-repeatability.json`）。

当前正式 baseline：`startup-clean-2b3a1ea-warmup3-n10.json`。

- commit：`2b3a1ea`
- 工作树：clean
- 口径：Release / iPhone 13 / warmup=3 / n=10
- 独立 run C：p50=252ms，CV=3.5%
- 独立 run D：p50=257ms，CV=2.8%
- 跨 run：`consistent`，Δp50=5ms
- baseline compare：`no-significant-change`，退出码 0

此前 `startup-post-reboot-warmup3-n10.json` 是 dirty working tree 的 provisional
baseline；同 commit 的第一轮 clean run B 曾出现 368–413ms 的启动多簇并被拒绝，
没有挑选后续样本。B/C/D 全部保留在 `.apm/runs/`，该失败是正式 baseline 的筛选依据。
