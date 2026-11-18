## ADDED Requirements

### Requirement: Stable export snapshots
The system SHALL preserve the identity and contents of an export snapshot when another export is prepared.

#### Scenario: Preparing another export preserves an earlier snapshot
- **GIVEN** snapshot A has been prepared for sharing
- **WHEN** snapshot B is prepared
- **THEN** snapshot A remains openable and retains its original bytes
- **AND** preparing snapshot B does not rewrite snapshot A

#### Scenario: Tasks started in the same minute remain isolated
- **GIVEN** two tasks have the same feature and start minute
- **WHEN** an export snapshot is prepared for each task
- **THEN** each task has a distinct snapshot
- **AND** neither snapshot contains the other task's content

#### Scenario: Changed task content produces a new snapshot
- **GIVEN** a task already has an export snapshot
- **WHEN** its translated content changes and another snapshot is prepared
- **THEN** the new content has a distinct snapshot
- **AND** the earlier snapshot retains its original content

### Requirement: Current export content
The system SHALL prepare sharing from the current observable export content and selected export language, even when the task ID is unchanged.

#### Scenario: Translation changes after an earlier preparation
- **GIVEN** a task has already been prepared for sharing
- **WHEN** a translation in that task changes
- **THEN** the next prepared snapshot contains the latest translation

#### Scenario: Summary or export language changes after an earlier preparation
- **GIVEN** a task has already been prepared for sharing
- **WHEN** its summary or selected export language changes
- **THEN** the next prepared snapshot reflects that change

### Requirement: Retention-safe export cleanup
The system SHALL limit automatic cleanup to expired generated export snapshots and SHALL NOT delete unrelated files or directories.

#### Scenario: Fresh snapshots survive later preparations
- **GIVEN** generated snapshots are no more than 7 x 24 hours old
- **WHEN** another export is prepared
- **THEN** those snapshots are not deleted

#### Scenario: Expired generated snapshots are eligible for cleanup
- **GIVEN** a generated regular-file snapshot is strictly more than 7 x 24 hours old
- **AND** its URL has not been prepared during the current process
- **WHEN** retention cleanup runs
- **THEN** the expired snapshot may be deleted

#### Scenario: Cleanup is conservative at uncertain boundaries
- **GIVEN** a generated file is exactly 7 x 24 hours old, has a future modification time, or has no readable modification time
- **WHEN** retention cleanup runs
- **THEN** the file is retained

#### Scenario: Unrelated files and directories are preserved
- **GIVEN** the export location contains unrelated files or directories, including names resembling export names
- **WHEN** retention cleanup runs
- **THEN** those files and directories are not deleted

#### Scenario: Snapshots prepared in the current process are protected
- **GIVEN** a snapshot URL has been prepared during the current process
- **WHEN** retention cleanup runs, including after that snapshot becomes expired
- **THEN** that URL is not deleted or rewritten by another preparation in the same process
