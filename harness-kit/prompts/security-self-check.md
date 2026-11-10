---
id: security-self-check
title: 安全 / 敏感信息自查
short: 安全自查
number: 14
group: 需求、计划与开发
stage: adopted
kind: task
when: 改动涉及配置、日志、导出、外部输入或发布前
returns: 敏感项清单 + 修复建议
fail_signal: 把密钥/路径写进历史
placeholders: 
---

检查本次改动是否引入：密钥 / Token / 凭证、本机绝对路径、设备标识 / 个人数据、未校验的外部内容执行。
1) 跑 make verify-static（含敏感串与本机路径检查）。
2) 如仓库有专用敏感信息门禁也跑，并记录命令与 exit code。
3) 发现问题先报告、不要写入 git 历史；给出修复建议。
4) 返回：问题清单（file:line）、修复建议、剩余风险、未验证项。
