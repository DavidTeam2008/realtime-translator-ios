---
id: adversarial-review
title: 新开会话对抗性评审
short: 对抗性评审
number: 10
group: 评审与发布
stage: adopted
kind: task
when: 计划 / PR / 改动需要无起草偏见的独立审查
returns: 结论 + P0/P1/P2 + 被挑战假设 + 最小验证
fail_signal: 复述作者结论、无证据好评
placeholders: REVIEW_SCOPE
---

任务：对 {{REVIEW_SCOPE}} 做对抗性评审。如果你所在的会话带有起草历史或自评，先停下并让我新开会话再继续。

输入（只给这些，不提供起草过程或自评）：当前仓库路径、目标声明、改动清单（可选 git diff）。
规则：
- 只读仓库；不修改文件；可以跑只读命令与 make verify-static 复核。
- 核对门禁与证据是否真的成立；主动找低成本蒙混路径；挑战隐含假设。
- 禁止复述作者结论、禁止无证据好评。

输出：
1) 结论：可合并 / 需修改 / 不可合并；
2) P0/P1/P2 问题表（每条附 file:line 或命令证据）；
3) 被挑战的假设；
4) 缺失信息；
5) 最小验证清单（作者可用哪些命令自证）。
红线：门禁被弱化、证据与提交不绑定、scope 外改动、完成声明无证据 → 直接 P0。
