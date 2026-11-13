---
id: feedback
title: 反馈 kit 问题（缺陷 / 文档不一致 / 需求）
short: 反馈 kit 问题
number: 23
group: 协作与收尾
stage: both
kind: task
when: 接入或日常使用中遇到 kit 自身的缺陷、模板/文档不一致，或想提能力需求
returns: 可粘贴的 issue 草稿（版本/环境/命令/期望/最小复现）与是否已提交
fail_signal: 改宿主仓的 kit 门禁绕过，或未确认就对外发 issue
placeholders: KIND
---

处理 kit 自身问题的反馈（类型：{{KIND}}）。先分诊，再产出 issue 草稿，不要替用户直接发布：
1) 分诊：kit 缺陷 / 文档不一致 / 宿主侧问题 / 需求建议。宿主侧问题（文档未登记、测试命令不真实、环境差异）先在宿主内修，不占 kit issue；kit 未承诺能力（不跑测试、不解析测试输出）先读 kit README 的「局限与未验证」。
2) 收集最小信息：kit 版本（`{{KIT}}/VERSION` 或 `.harness-manifest.json` 的 kitVersion）、profile、宿主技术栈、复现命令原文 + 退出码 + 关键输出（脱敏）、期望 vs 实际、最小复现（空白临时仓 init 或一个最小 commit）。
3) 输出一份可直接粘贴的 issue 草稿：标题 `[缺陷|文档|需求] 一句话现象`，正文按上面的信息分段；提交地址 <https://github.com/DavidTeam2008/harness-engineering-kit/issues>（公开镜像仓受理，镜像只读）。
4) 对外动作先问：建议用户确认后再提交；修复发布后按升级流程回流——`{{KIT}}/scripts/harness-upgrade --check/--plan` → 只回写 kit 管理面 → 重装入口 skill → `make verify-static` 复核。
禁止：改宿主 `tools/` / kit 模板绕过缺陷（升级会覆盖）；删除或弱化门禁。
