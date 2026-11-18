# language-catalog Specification

## Purpose
TBD - created by archiving change cache-language-capabilities. Update Purpose after archive.

## Requirements

### Requirement: Cached language capabilities
The system SHALL provide language capability values from a cache populated by explicit system probes.

#### Scenario: Repeated refresh uses cached probe results
- **GIVEN** the catalog has completed one refresh
- **WHEN** `refreshCapabilities()` is called again
- **THEN** system probes are not called again for the same catalog lifetime
- **AND** cached capability values remain stable

#### Scenario: Capability lookup does not perform system I/O
- **GIVEN** a capability snapshot has been cached
- **WHEN** `capability(_:)` is called
- **THEN** it returns from the cache without invoking a system probe

### Requirement: Actual system capability mapping
The system SHALL map speech locale, translation availability, and TTS voice probes to language capabilities.

#### Scenario: Supported system probes map to a capable language
- **GIVEN** speech locale, TTS voice, and at least one translation pair are supported
- **WHEN** the catalog refreshes
- **THEN** the language reports speech, translation, and speak as true

#### Scenario: Unsupported probes map to a disabled language
- **GIVEN** speech locale, TTS voice, or every translation pair is unsupported
- **WHEN** the catalog refreshes
- **THEN** the corresponding capability is false

#### Scenario: Same-language translation is unsupported
- **GIVEN** the source language equals the target language
- **WHEN** a translation pair is requested
- **THEN** the catalog reports `.unsupported`

### Requirement: Catalog-driven language selection
The system SHALL let language selection views render catalog-reported unsupported languages as disabled.

#### Scenario: Unsupported language is disabled
- **GIVEN** the catalog reports a language as not speech-capable
- **WHEN** a language grid is rendered
- **THEN** that language is disabled and not selected by the default grid interaction

#### Scenario: Current behavior is preserved before probing
- **GIVEN** capabilities have not yet been refreshed
- **WHEN** a language grid is rendered
- **THEN** no language is disabled because of unknown capability
