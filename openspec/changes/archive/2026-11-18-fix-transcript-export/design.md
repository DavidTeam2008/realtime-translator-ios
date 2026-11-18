# Design: Immutable, content-versioned export snapshots

## Decisions

- Store generated snapshots in a dedicated export directory under the app caches location.
- Bind each snapshot name to the task UUID and a SHA-256 digest of the complete UTF-8 export payload plus export language. Identical payloads may reuse a snapshot; different tasks or payloads must not overwrite one another.
- Treat an existing snapshot as immutable. A later preparation must not rewrite it.
- Derive the share preparation identity from the complete rendered content and export language rather than task ID alone.
- Clean only regular files whose complete names match the generated snapshot format. Use file modification time for retention.
- Consider a snapshot expired only when its age is strictly greater than 7 x 24 hours. Keep files at exactly the boundary, files with future timestamps, and files with unavailable timestamps.
- Protect every URL prepared during the current process from cleanup, including expired URLs. After process restart, unprotected expired snapshots become eligible for cleanup.

## Verification boundary

File-level tests prove snapshot identity, byte stability, cleanup boundaries, and content-version inputs. They do not prove that every external share extension has finished reading a URL. Real ShareLink/ShareSheet behavior remains a separate manual acceptance item.

## Execution ownership

OpenSpec owns only the externally observable behavior delta. The Harness plan owns implementation sequencing, task state, acceptance, and evidence. Superpowers supplies TDD and verification discipline without creating another plan or ledger.
