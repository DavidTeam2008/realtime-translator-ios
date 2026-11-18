# Design: Cache-backed language capability catalog

## Decisions

- Keep `LanguageCataloging` in Domain and add a production `SystemLanguageCatalog` in Services.
- Inject narrow probe boundaries for speech locale lookup, TTS voice lookup, and translation pair availability. Production adapters call `SpeechTranscriber`, `AVSpeechSynthesisVoice`, and `LanguageAvailability`; tests use deterministic fakes.
- Cache capability snapshots in a lock-protected store. `refreshCapabilities()` is the explicit probe entry point; `capability(_:)` returns the cached snapshot without blocking I/O.
- Before the first successful refresh, preserve the current permissive catalog behavior so existing screens do not regress while capabilities are unknown.
- After refresh, a language is speech-capable only when the system reports a supported speech locale, TTS-capable only when a matching voice exists, and translation-capable only when it participates in at least one supported or installed pair.
- Translation pair status is cached by ordered language pair; same source and target remains unsupported.
- `LanguageChipGrid` accepts an explicit set of unavailable languages. A shared selection helper derives that set from `LanguageCapability`, keeping View logic thin and testable without mocking system APIs.

## Verification boundary

Injected-boundary tests prove cache identity, repeat-refresh behavior, status mapping, same-language rejection, and the disabled-language derivation. They do not prove that a specific physical device has downloaded assets or that all vendor locales are available; real device acceptance remains out of unit-test scope.
