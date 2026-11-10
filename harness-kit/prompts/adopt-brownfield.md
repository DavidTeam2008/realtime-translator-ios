---
id: adopt-brownfield
title: 接入存量项目（Agent-first，先只读）
short: 接入存量项目
number: 2
group: 接入与接手
stage: unadopted
kind: task
when: 已有代码与文档，还没接入 harness-kit，要先盘点再改造
returns: 只读盘点摘要、改造顺序、逐步提交与证据
fail_signal: 先重构再盘点 / --force 覆盖文档
placeholders: 
---

目标：用 harness-kit 改造本存量仓库（brownfield），严格先只读、后改造。

步骤：
1) 先只读盘点，不要改任何代码；报告写到系统临时目录（如 /tmp/adoption-report.md），不要写进被盘点仓库：
   python3 {{KIT}}/scripts/harness-adopt --target . --report /tmp/adoption-report.md --json
2) 给我盘点摘要，等我确认：
   - 文档：断链 / 未登记 / 疑似过期 / 索引缺失；
   - 卫生：被跟踪构建产物 / 绝对符号链接 / 本机路径 / 大文件；
   - 现有门禁与 CI、建议 profile 及理由、真实测试命令（实际跑一下确认）；
   - 改造顺序：文档蒸馏 → 清洁 → config hygiene/layers → CI/hooks → JUnit 证据 → harness-selftest。
3) 确认后先 dry-run 再 init；把第 2 步确定的参数带上（--profile 用第 2 步建议的档位，默认 standard；--language / --test-command 用盘点的结论）：
   python3 {{KIT}}/scripts/harness-init --profile standard --target . --dry-run
   复核动作标签 RENDER / COPY / APPEND / CONFLICT（已有文件冲突时才出现 CONFLICT），再执行；首次 make check FAIL 就修内容，不删检查。
4) 按 {{KIT}}/docs/playbook.md 的 brownfield 七步法逐步做；每步先更新计划再改代码，一个可验证点一个提交。
5) 每步返回：命令、exit code、证据 id（接入后）、未验证项。

约束：不用 --force 覆盖既有文档；历史文档只归档不改写；越界改动先停下并更新 scope。盘点完成前不改代码。
