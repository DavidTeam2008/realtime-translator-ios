# Delivery Contract

- Change: cache-language-capabilities
- Level: L2
- Owner: david
- Base: 1961368
- Scope allow: openspec/changes/cache-language-capabilities/, harness/records/2026-11-18-cache-language-capabilities.md, Duiyi/Domain/LanguageCatalog.swift, Duiyi/Services/, Duiyi/App/AppEnvironment.swift, Duiyi/Features/Shared/LanguageChipGrid.swift, Duiyi/Features/Home/HomeSettingsSheet.swift, DuiyiTests/, references/verification.md, harness/test-baseline.json
- Scope deny: Duiyi.xcodeproj/, Duiyi/Features/Speech/, Duiyi/Features/Translation/, .env, "*.p12", "*.mobileprovision"
- Acceptance: A1=cached probes do not repeat (unit-tests-pass); A2=capability and pair mapping is correct (unit-tests-pass); A3=grid disables catalog-reported unsupported languages (unit-tests-pass); A4=current pre-refresh behavior preserved (unit-tests-pass)
- Verify: make delivery-check CHANGE=cache-language-capabilities; make verify-static; make release-check
- Evidence: unit-tests-pass (JUnit + manifest, required)
- Review: required；path=harness/reviews/2026-11-18-cache-language-capabilities.md，覆盖 Base..Head，P0/P1 closed
- Archive gate: all tasks checked + Harness PASS + required review closed
- CI: not applicable (static CI is not asserted as delivery evidence)

## Tasks

### Task 1: Add red tests for cache and mapping

- [x] Task 1: catalog cache, mapping, same-language and selection-derivation tests fail against the current implementation.

**Files:** `DuiyiTests/SystemLanguageCatalogTests.swift`, `harness/test-baseline.json`, `references/verification.md`

1. Add injected-boundary tests for one-refresh caching, repeated refresh without re-probing, capability mapping, same-language pair rejection, and disabled-language derivation.
   - Expected: focused unit command fails because `SystemLanguageCatalog` and the selection helper do not exist.
2. Update the unit floor, expected skip, and verification count only for tests that actually exist.
   - Expected: baseline check fails until the count is aligned.
3. Commit the red tests.

### Task 2: Implement cached system language catalog

- [x] Task 2: production catalog passes injected-boundary tests and preserves pre-refresh behavior.

**Files:** `Duiyi/Domain/LanguageCatalog.swift`, `Duiyi/Services/Language/SystemLanguageCatalog.swift`, `DuiyiTests/SystemLanguageCatalogTests.swift`

1. Add narrow speech, TTS, and translation probe boundaries plus production adapters using system frameworks.
   - Expected: production adapters contain no test fakes.
2. Implement lock-protected caching and explicit `refreshCapabilities()`.
   - Expected: repeated refresh does not re-probe; `capability(_:)` does not probe.
3. Keep default capability values permissive before the first refresh, map probes after it, and retain same-language rejection.
   - Expected: focused and full unit tests pass.

### Task 3: Render catalog-derived disabled languages

- [ ] Task 3: `LanguageChipGrid` can disable catalog-reported unsupported languages and Home settings supplies the catalog data.

**Files:** `Duiyi/Features/Shared/LanguageChipGrid.swift`, `Duiyi/Features/Home/HomeSettingsSheet.swift`, `Duiyi/App/AppEnvironment.swift`

1. Add an optional unavailable-language input and accessibility/disabled presentation to `LanguageChipGrid`.
   - Expected: the default grid API remains unchanged for previews and existing callers.
2. Refresh capabilities and derive disabled languages from the catalog in Home settings.
   - Expected: preview/static catalog causes no disabled language; system catalog disables only reported unsupported entries.

### Task 4: Verify, evidence, and review

- [ ] Task 4: focused/full gates, delivery-check, evidence, and required review pass.

**Files:** `references/verification.md`, `harness/test-baseline.json`, `harness/reviews/2026-11-18-cache-language-capabilities.md`, `openspec/changes/cache-language-capabilities/tasks.md`

1. Run `make verify-static`, `make delivery-check CHANGE=cache-language-capabilities`, and `make release-check`.
   - Expected: all exit 0 and evidence is fresh/strict.
2. Generate required unit evidence from a clean commit and record review report covering `Base..Head` with P0/P1 closed.
   - Expected: delivery-check archive-gate facts can be recomputed.
3. Commit the evidence and review; do not run OpenSpec archive in this task.

## Evidence

| 任务 | 证据 ID | 结果 | 环境 |
| --- | --- | --- | --- |
| Task 1-3 | `unit-tests-pass` | 待生成 | 本机模拟器 |
