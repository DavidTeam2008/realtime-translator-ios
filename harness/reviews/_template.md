---
base: <base-commit>
head: <head-commit>
reviewer: <agent / 人>
p0: <closed|open>
p1: <closed|open>
p2: <closed|open>
verdict: <pass|conditional|fail>
# 可选：review 方法溯源（不参与 delivery-check 门禁）
review_method: <mattpocock-code-review | custom>
review_method_commit: <commit>
axes: standards,spec
---

# 独立审查 · <topic>

> 审查日期：YYYY-MM-DD ｜ 对象：<commit / 分支 / 工作树> ｜ 审查者：<agent / 人>
> 声明：只读；未使用起草对话、作者自评或既往结论。
> 方法：**两轴审查（Standards / Spec）**；两轴各自给最严重问题，不跨轴排序；所有发现归一为 P0/P1/P2，交付结论以「结论 + 归一问题表」为准。

## 1. 结论

- 结论：通过 / 有条件通过 / 不通过
- 一句话理由：

## 2. 复跑与边界

- 命令 + 退出码：
- 未覆盖范围：

## 3. Standards 轴

> 依据：仓库标准优先（AGENTS.md、references/、CONTRIBUTING.md 等）；Fowler smell 基线仅作判断参考，仓库标准覆盖基线。

| 严重度 | 问题 | 证据 / 位置 | 标准引用 | 建议 |
| --- | --- | --- | --- | --- |
|  |  |  |  |  |

- 本轴最严重问题（不与 Spec 轴比较）：

## 4. Spec 轴

> 依据：proposal / design / spec delta / acceptance / originating issue；每条 finding 引用需求或场景 ID。

| 严重度 | 需求 / 场景 | 缺失 / 偏差 / 越界 | 证据 / 位置 | 建议 |
| --- | --- | --- | --- | --- |
|  |  |  |  |  |

- 本轴最严重问题（不与 Standards 轴比较）：

## 5. 归一问题表（门禁口径）

| ID | 轴 | 严重度 | 问题 | 关闭状态 |
| --- | --- | --- | --- | --- |
|  | standards / spec | P0 / P1 / P2 |  | open / closed |

## 6. 被挑战假设、缺失信息与最小验证

- 被挑战假设：
- 缺失信息：
- 最小验证清单：

| 命令 | 期望结果 |
| --- | --- |
|  |  |

## 7. 作者回应

| 条目 | 回应（接受 / 拒绝 / 待定） | 理由 |
| --- | --- | --- |
|  |  |  |
