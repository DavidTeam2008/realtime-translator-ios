# Baseline 状态

`startup-p0-working-tree.json` 是 2026-09-25 的旧 provisional baseline，
来自 dirty working tree 的 Release 构建。它已被后续证据否定，**不得用于确认改善或劣化**。

旧证据：同一 commit 的 n=5 跨 run 漂移、固定等待后的首样本异常，以及 warmup=3
的 n=10 独立重复漂移（见 `../issues/ISSUE-P0-002-cross-run-shift.json` 与
`../issues/ISSUE-P0-003-warmup-repeatability.json`）。

当前可用候选：`startup-post-reboot-warmup3-n10.json`。设备重启并解锁后，
同一 Release 二进制、warmup=3、n=10 的两次独立 run 分别为 p50=256ms/CV=9.6%
与 p50=266ms/CV=7.1%；跨 run 诊断为 `consistent`，baseline compare 退出码为 0。
由于目标工作树仍是 dirty，这仍是 **provisional baseline**，不是干净 commit 的发布基线。
