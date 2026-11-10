【前置｜未接入项目（接入阶段）】工作目录（仓库根）：{{TARGET}}；harness-kit 位置：{{KIT}}
下文所有 kit 路径都指 {{KIT}}；本仓库可能还没有 Makefile / harness/ / tools/，这是正常的。
接入阶段规则：
1) 先读 {{KIT}}/README.md 与 {{KIT}}/docs/adoption.md 的相关章节，再执行；不要凭记忆。
2) 先只读盘点，后改造：harness-adopt 只读；harness-init 先 --dry-run 给我确认。
3) 命令不存在 = 尚未接入：直接说明，不要伪造输出，也不要假设 make check 可用。
4) 不删除或弱化既有检查；不用 --force 覆盖既有文档；历史文档只归档不改写；越界先停。
5) 每阶段返回：命令 + exit code + 产物路径 + 未验证项；接入完成后改用已接入流程（0A）。
