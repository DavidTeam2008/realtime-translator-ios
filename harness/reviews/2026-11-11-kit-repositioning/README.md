# harness-kit 重定位与重构 · 提案与独立评审（2026-11-11 冻结）

> 状态：提案已获用户确认（按建议默认值），v0.2.12 证据链加固已实施，其余按路线图推进。
> 复现与校验：`bash repro.sh`（核对本目录 sha256 + 重跑 kit 测试与伪造证据回归）。
> 原始命令输出（`out-*.txt`、fake 仓、asar 抽取物）保留在本机 `harness/runs/kit-eval/`（不入库）。

## 文件

| 文件 | 来源（runs 目录） | sha256（本目录文件） |
| --- | --- | --- |
| [`report.md`](report.md) | `REPORT.md` | `18e7bc2d6431b563d3fce328a07095132faf43fb4df6aff97d65dd0e46c82a72` |
| [`positioning-audit.md`](positioning-audit.md) | `positioning-audit.md` | `a5aacb6d37d548229314eb58e8340f9765d2766e3c63a4998361ad81bcb42768` |
| [`research-ecosystem.md`](research-ecosystem.md) | `research-ecosystem.md` | `b9aa1e177b30084069a9e2fd8fb4a1d0fa45e061eef99f8b174de574c782a0ac` |
| [`usability-audit.md`](usability-audit.md) | `usability-audit.md` | `0f52aceb26f2db0329d2540549c6a87275ec3b7ee0b8e5084493acda5b0c1e63` |
| [`dsh-extensibility.md`](dsh-extensibility.md) | `dsh-extensibility.md` | `ab9d82d68019767bc6b956496c1d818dd11e5b6d449dd3e3f1dead52f4e21542` |
| [`review-instructions.md`](review-instructions.md) | `review-instructions.md` | `de37e83ead0d45ca383b1eabded5dbc506a0d77e15d3aabcf9b509a998881823` |
| [`review-quality.md`](review-quality.md) | `review-quality.md` | `c8ae17c9de0383d2007d18788efceacc77c139a5ed2ba5c522768b771c8fa79e` |

## 结论摘要

- 定位：从「脚手架」改为「给 AI Coding Agent 用的 Harness Engineering 项目管理工具（治理层）」。
- 形态：统一 `harness` CLI + AGENTS 入口（+ 待 A/B 的 router skill）；DSH 插件暂缓产品化。
- 核心卖点：跨 Agent 可移植状态 + 完成声明强制可复核 + 多 Agent 协作协议（路线图）+ 自进化。
- P0 证据可伪造：两名独立红队实测当前 kit 可被手写 PASS 证据绕过；v0.2.12 已按报告 §3.7 加固。
- 完整路线图与验收见 [`report.md`](report.md) §7。

## 复现

```bash
bash repro.sh        # 校验 sha256 并重跑 kit 测试 + 伪造证据回归
```
