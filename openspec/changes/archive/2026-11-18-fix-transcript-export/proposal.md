# Proposal: Preserve and refresh transcript export snapshots

## Why

Preparing another export can currently delete or replace a file that is already being shared. A task whose translation changes keeps its task ID, so the share view can continue preparing stale content. Cleanup also matches unrelated files too broadly.

## What Changes

- Preserve immutable export snapshots across repeated preparations.
- Refresh the prepared snapshot when observable export content or export language changes, even if the task ID does not.
- Limit retention cleanup to expired export snapshots while protecting unrelated files and snapshots prepared in the current process.

## Out of Scope

- Changing the transcript text format.
- Replacing the system share interface or inventing a share-completion callback.
- Changing speech, translation, persistence, or task lifecycle behavior.
