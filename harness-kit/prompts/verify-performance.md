---
id: verify-performance
title: 性能 / 延迟验证（先测量）
short: 性能验证
number: 13
group: 需求、计划与开发
stage: adopted
kind: task
when: 需要证明性能、延迟或资源占用是否变化
returns: 指标/基线数据/复测数据
fail_signal: 无数据宣称更快
placeholders: METRIC, SAMPLE_SIZE
---

先测量再优化：
1) 定义指标（{{METRIC}}）、口径、环境（设备 / 版本 / 数据规模），写清楚再跑。
2) 跑基线 n≥{{SAMPLE_SIZE}} 次，记录命令与原始数据。
3) 改动后用同一口径复测；没有数据不声称“更快”。
4) 把方法与结果写进 evidence / 性能文档；返回前后对比、波动范围、未验证项。
