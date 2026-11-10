---
id: adopt-new
title: 接入新项目（Agent-first）
short: 接入新项目
number: 1
group: 接入与接手
stage: unadopted
kind: task
when: 新项目 / 空仓还没有 harness/，要接入 harness-kit
returns: init dry-run 计划、首次 make check 输出、第一份计划
fail_signal: 直接改业务代码 / 跳过 dry-run
placeholders: 
---

目标：用 harness-kit 接入本仓库（新项目 / 空仓，standard profile），接入后能跑通首次 make check。

步骤：
1) 读 {{KIT}}/README.md 与 {{KIT}}/docs/adoption.md 的接入章节，不要凭记忆。
2) 盘点本仓库：语言、构建系统、真实测试命令（实际跑一下确认可用）；给出 profile、项目名、语言与测试命令的选择理由。拿不准先问我。
3) 先出计划并执行 dry-run（不写文件），把计划给我确认；把第 2 步确定的参数加到命令上：
   python3 {{KIT}}/scripts/harness-init --profile standard --target . --dry-run
   参数示例（仅示形，用第 2 步的结论替换）：--name MyApp --language python --test-command "python3 -m unittest discover -s tests -q"
4) 我确认后去掉 --dry-run 执行；init 会自动跑首次 make check。若 FAIL，按提示修内容，不要删检查。
5) 检查产物（git status / 文件列表）后提交；再用 make plan TOPIC=first-milestone 建第一份 active 计划（目标/非目标、scope、验收、下一步；TOPIC 用你定的里程碑名）。
6) 返回：改动列表、make check 输出（命令 + exit code）、下一步 1 条。

约束：不改业务代码；不引入 kit 运行时依赖；测试命令必须真实存在。
