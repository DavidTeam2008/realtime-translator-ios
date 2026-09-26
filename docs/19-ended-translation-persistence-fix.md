# 19. 已结束会议译文持久化修复

> 2026-09-26。第一个不依赖性能目标的可验证功能闭环。

## 发现

`TaskDetailView.handleTranslated` 先更新内存中的 `TaskSession`，随后调用
`TaskStore.append` 回填译文。但历史详情只接收 `ended` 任务，而
`InMemoryTaskStore.append` 与 `SwiftDataTaskStore.append` 都对 ended 任务直接 return。

结果：页面当场显示译文，但重新进入后译文消失。

## 红测

在修复前新增两条测试：

- `endedTaskTranslationBackfillInMemory`
- `endedTaskTranslationBackfillInSwiftData`

结果：

```text
3 passed, 2 failed
读回 translatedText = ""
```

## 单变量修复

新增专用通道：

```swift
func updateTranslations(taskID: UUID, entries: [TranscriptEntry]) async
```

语义：

- 只更新**已有条目**的 `translatedText`；
- 允许对 ended 任务执行；
- 普通 `append` 仍拒绝 ended 任务，不放宽 transcript 写入规则；
- `DeferredTaskStore` 只做透明转发。

## 绿测与回归

```text
TaskStoreTests：5 passed, 0 failed
全部单元测试：120 passed, 0 failed
Release device build：SUCCEEDED
```

## 未混入本次修复

`ExportShareButton` 使用 `.task(id: task.id)`，译文更新后 task.id 不变，导出 URL
可能仍是旧内容。这是独立问题，已记录在 `ISSUE-FUNC-001` 的 knownFollowUp，
没有与持久化修复同时修改。

## 证据

- `.apm/issues/ISSUE-FUNC-001-ended-translation-not-persisted.json`
- `.apm/issues/ISSUE-UI-001-home-entry-not-hittable.json`
