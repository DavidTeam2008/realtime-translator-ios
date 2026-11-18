# Proposal: Use a cached system language capability catalog

## Why

`StaticLanguageCatalog` reports every language as speech, translation and TTS capable. The settings grids therefore cannot distinguish a language that the device can actually recognize, translate, or speak.

## What Changes

- Add a system-backed language catalog that probes speech locales, translation availability, and TTS voices.
- Cache probe results for the catalog lifetime and refresh explicitly; repeated refreshes do not re-probe unchanged entries.
- Keep same-language translation pairs unsupported.
- Let `LanguageChipGrid` render languages reported unsupported by the catalog as disabled while retaining the current static catalog as the preview/fallback adapter.

## Out of Scope

- Downloading or installing language assets.
- Replacing `SpeechAssetPreparer`, `BilingualSpeechEngine`, or the audio session policy.
- Changing language persistence or introducing a cloud language catalog.
- Claiming device capability in unit tests without a system adapter; unit tests exercise injected probe boundaries, while final capability acceptance remains device-dependent.
